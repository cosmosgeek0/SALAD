#!/usr/bin/env python3
"""Read-only bandwidth API behind the authenticated Cloudflare Unix socket."""

from __future__ import annotations

import argparse
import base64
import csv
import io
import json
import hashlib
import sqlite3
from contextlib import closing
import math
import mimetypes
import os
import signal
import socket
import struct
import pwd
import threading
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from http.server import BaseHTTPRequestHandler
from socketserver import ThreadingUnixStreamServer
from pathlib import Path
from typing import Any, Callable, Dict
from urllib.parse import parse_qs, urlparse

from dashboard.store import APP_NAMES, Store
from dashboard.packetstream import PacketStreamView
from dashboard.fleet_test import FleetTestView, fleet_csv, timestamp_ms, worker_sample_time
from dashboard.native_network import NetworkMinutes, bucket_minutes


SOCKET_PATH = "/run/salad-ui/ui.sock"
ACCESS_ISSUER = "https://dawn-base-75dc.cloudflareaccess.com"
ACCESS_AUDIENCE = "745e29c574f51f5d1d68b1272034c25ae083f6141281c3cfc35cad0749d6623a"
MAX_POINTS = 2000
HONEYGAIN_CREDITS_PER_USD = Decimal("1000")
PACKETSTREAM_USD_PER_GB = Decimal("0.1")
PAWNS_USD_PER_GB = Decimal("0.2")
SALAD_CPU_PRICE_CHANGE_MS = 1789171200000


class DashboardServer(ThreadingUnixStreamServer):
    """Allow the Overview feed burst to queue while handlers are busy."""
    request_queue_size = 64


def iso_ms(value: int) -> str:
    return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def query_window(query: Dict[str, list]) -> tuple:
    try:
        start = int(query.get("start", [""])[0])
        end = int(query.get("end", [""])[0])
        requested_bucket = int(query.get("bucket", ["1"])[0])
    except (TypeError, ValueError):
        raise ValueError("start, end, and bucket must be integers") from None
    if end <= start:
        raise ValueError("end must be after start")
    if requested_bucket < 1 or requested_bucket > 86400:
        raise ValueError("bucket must be between 1 and 86400 seconds")
    minimum_bucket = max(1, math.ceil((end - start) / 1000 / MAX_POINTS))
    return start, end, max(requested_bucket, minimum_bucket)


def csv_export(series: Dict[str, Any]) -> bytes:
    output = io.StringIO(newline="")
    fields = [
        "time_utc",
        "sample_count",
        "instance_ids",
        "coverage_percent",
        "eth0_rx_bytes_per_second",
        "eth0_tx_bytes_per_second",
        "captured_rx_bytes_per_second",
        "captured_tx_bytes_per_second",
        "unassigned_rx_bytes_per_second",
        "unassigned_tx_bytes_per_second",
    ]
    for app in APP_NAMES:
        fields.extend((f"{app}_rx_bytes_per_second", f"{app}_tx_bytes_per_second"))
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for point in series["points"]:
        row = {
            "time_utc": iso_ms(point["time_ms"]),
            "sample_count": point["sample_count"],
            "instance_ids": ";".join(point["instance_ids"]),
            "coverage_percent": point["coverage_percent"],
            "eth0_rx_bytes_per_second": point["eth0"]["rx_bytes_per_second"],
            "eth0_tx_bytes_per_second": point["eth0"]["tx_bytes_per_second"],
            "captured_rx_bytes_per_second": point["captured"]["rx_bytes_per_second"],
            "captured_tx_bytes_per_second": point["captured"]["tx_bytes_per_second"],
            "unassigned_rx_bytes_per_second": point["unassigned"]["rx_bytes_per_second"],
            "unassigned_tx_bytes_per_second": point["unassigned"]["tx_bytes_per_second"],
        }
        for app in APP_NAMES:
            row[f"{app}_rx_bytes_per_second"] = point["applications"][app]["rx_bytes_per_second"]
            row[f"{app}_tx_bytes_per_second"] = point["applications"][app]["tx_bytes_per_second"]
        writer.writerow(row)
    return output.getvalue().encode("utf-8")


def sample_history(db, path, service, test_start, start_ms, end_ms, cache):
    """Caller serializes one cache per ledger. Clipped bins are estimated.

    Samples counts retained records in overlapping bins. EarnFM receipt fields
    belong to each row's latest observation. TM receipt backfills need a reset.
    """
    end, duration_sql, valid, receipt, country, test_column = {
        "tm": ("time_ms", "interval_ms", "rx IS NOT NULL AND tx IS NOT NULL", "received_ms", "NULL", "start_ms"),
        "earnfm": ("end_ms", "end_ms-start_ms", "valid=1 AND seq>0", "NULL", "NULLIF(country,'')", "end_ms"),
    }[service]
    issue = f"seq>0 AND (NOT ({valid}) OR {end}<=start_ms)" if service == "earnfm" else f"NOT ({valid}) OR {end}<=start_ms"
    stat = path.stat()
    binding = stat.st_dev, stat.st_ino, service, test_start
    high = db.execute("SELECT COALESCE(MAX(rowid),0) FROM samples").fetchone()[0]
    if cache.get("binding") != binding or high < cache["cursor"]:
        cache.clear()
        cache.update(binding=binding, cursor=0, bins={})
    if high > cache["cursor"]:
        added = db.execute(f"""SELECT CAST(({end}-1)/60000 AS INTEGER)*60000,
            instance,machine,run,NULLIF(ip,''),MIN(start_ms),MAX({end}),
            SUM(CASE WHEN {valid} THEN rx+tx END),
            SUM(CASE WHEN {valid} THEN {duration_sql} ELSE 0 END),
            COUNT(*),MAX({issue}),MAX({receipt}),
            SUM(CASE WHEN {valid} AND {end}>start_ms THEN {end}-start_ms ELSE 0 END),MAX({country})
            FROM samples WHERE rowid>? AND rowid<=? AND {test_column}>=?
            GROUP BY 1,instance,machine,run,NULLIF(ip,'')""", (cache["cursor"], high, test_start)).fetchall()
        for entry in added:
            key, value = tuple(entry[:5]), list(entry[5:])
            previous = cache["bins"].get(key)
            if previous is None:
                cache["bins"][key] = value
                continue
            previous[0] = min(previous[0], value[0])
            previous[1] = max(previous[1], value[1])
            if value[2] is not None:
                previous[2] = (previous[2] or 0) + value[2]
            previous[3] += value[3]
            previous[4] += value[4]
            previous[5] = previous[5] or value[5]
            if value[6] is not None:
                previous[6] = max(previous[6] or value[6], value[6])
            previous[7] += value[7]
            if value[8] is not None:
                previous[8] = max(previous[8] or value[8], value[8])
        cache["cursor"] = high
    rows = {}
    start_ms = max(start_ms, test_start)
    for key, value in cache["bins"].items():
        first, last, amount, duration, samples, partial, received, coverage, country = value
        if last <= start_ms or first >= end_ms:
            continue
        clipped = first < start_ms or last > end_ms
        fraction = (min(last, end_ms)-max(first, start_ms))/(last-first) if clipped and last > first else 1
        identity = key[1:]
        row = rows.get(identity)
        if row is None:
            row = rows[identity] = dict(zip(("instance", "machine", "run", "ip"), identity))
            row.update(country=country, first_seen_ms=first, last_seen_ms=last, received_ms=None, recorded_ms=None,
                       duration_ms=0, total_mb=None, samples=0, partial=False, estimated=False, _coverage_ms=0)
        row["first_seen_ms"] = min(row["first_seen_ms"], first)
        row["last_seen_ms"] = max(row["last_seen_ms"], last)
        if amount is not None:
            row["total_mb"] = (row["total_mb"] or 0) + amount*fraction/1e6
        row["duration_ms"] += duration*fraction
        row["samples"] += samples
        row["partial"] |= bool(partial or clipped)
        row["estimated"] |= clipped
        row["_coverage_ms"] += coverage*fraction
        if received is not None:
            row["received_ms"] = max(row["received_ms"] or received, received)
        if country is not None:
            row["country"] = max(row["country"] or country, country)
    for row in rows.values():
        coverage = row.pop("_coverage_ms")
        row["partial"] |= row["total_mb"] is None or coverage < row["last_seen_ms"]-row["first_seen_ms"]
        if service == "earnfm":
            times = db.execute("""SELECT json_extract(d.body,'$.received_ms'),json_extract(d.body,'$.recorded_ms')
                FROM samples s INDEXED BY samples_run_time LEFT JOIN sample_details d ON d.run=s.run AND d.seq=s.seq
                WHERE s.run=? AND s.end_ms=? AND s.instance=? AND s.machine IS ?
                AND COALESCE(s.ip,'')=COALESCE(?,'') ORDER BY s.seq DESC LIMIT 1""",
                (row["run"],row["last_seen_ms"],row["instance"],row["machine"],row["ip"])).fetchone()
            if times:
                row["received_ms"], row["recorded_ms"] = times
    return list(rows.values())


def history_snapshot(root, query, fleet_view, cache, read_view):
    service = query.get("service", [""])[0]
    folders = {"hg": "fleet-tests", "ps": "packetstream", "proxyrack": "proxyrack", "rp": "repocket",
               "earnfm": "earnfm", "tm": "traffmonetizer", "pawns": "pawns", "grass": "grass"}
    if service not in folders:
        raise ValueError("Unknown history service")
    hours = query.get("hours", ["24"])[0]
    if hours not in ("1", "6", "12", "24", "all"):
        raise ValueError("hours must be 1, 6, 12, 24, or all")
    selected = query.get("test", ["current"])[0]
    limit, offset = int(query.get("limit", ["50"])[0]), int(query.get("offset", ["0"])[0])
    if not 1 <= limit <= 100 or not 0 <= offset <= 100000:
        raise ValueError("Invalid history page")
    order = query.get("sort", ["last_seen"])[0]
    if order not in ("last_seen", "total_mb"):
        raise ValueError("Unknown history sort")
    search = query.get("q", [""])[0][:200].casefold()
    now = int(time.time() * 1000)
    folder = root / folders[service]
    view_name = "native-census.json" if service == "ps" else "latest.json" if service == "tm" else "view.json"
    metadata_name = {"hg": "current.json", "earnfm": "target.json"}.get(service, view_name)
    metadata_path = folder / metadata_name
    meta = read_view(metadata_path) if metadata_path.exists() else {}
    if service == "tm":
        meta = meta.get("deployment") or {}
    group = meta.get("group_id") or (meta.get("id") if service in ("hg", "earnfm") else None)
    if service == "pawns" and (folder / "traffic.sqlite3").exists():
        with closing(sqlite3.connect((folder / "traffic.sqlite3").as_uri() + "?mode=ro", uri=True)) as db:
            item = db.execute("SELECT group_id FROM collector ORDER BY time_ms DESC LIMIT 1").fetchone()
            group = item[0] if item else None
    # Cached history retains its own observation/window times. New test bindings invalidate immediately.
    key = service, selected, hours
    saved = cache.get(key)
    binding = group, meta.get("measurement_started_ms"), meta.get("started_ms")
    if service not in ("earnfm", "tm") and saved and saved[0] == binding and time.monotonic() - saved[1] < 30:
        result = saved[2]
    else:
        start = 0 if hours == "all" else now // 60000 * 60000 - (int(hours) * 60 - 1) * 60000
        source = read_view(folder / view_name) if (folder / view_name).exists() else {}
        inventory_ms = source.get("inventory_ms", source.get("generated_ms"))
        workers = source.get("workers", source.get("nodes", []))
        tests = [{"id": "current", "label": "Current test", "archived": False}]
        note = "Recorded container RX + TX; provider account/device credits are not allocated to IPs. Unknown traffic is null."
        note += " Search matches recorded fields only; current IP geolocation is not historical country evidence."
        rows, archived, window_end = [], selected != "current", now
        if service == "hg":
            tests += [dict(id=a["id"], label="Archived test · " + a["id"], archived=True) for a in fleet_view.archives()]
            if selected not in {test["id"] for test in tests}:
                raise ValueError("Unknown archived test")
            snapshot = fleet_view.snapshot(archive=selected if archived else None, include_observations=True, honeygain_only=True)
            experiment = snapshot.get("experiment") or {}
            if archived and snapshot.get("latest"):
                window_end = snapshot["latest"]["time_ms"] + 1
                start = 0 if hours == "all" else window_end // 60000 * 60000 - (int(hours) * 60 - 1) * 60000
            start = max(start, experiment.get("started_ms") or 0)
            latest = (snapshot.get("latest") or {}).get("hg", {})
            inventory_ms = latest.get("status_observed_ms")
            workers = latest.get("workers", [])
            series = {}
            for observation in snapshot.get("observations", []):
                for worker in observation["hg"]["workers"]:
                    identity = tuple(worker.get(k) for k in ("group", "device", "machine", "run"))
                    at = worker_sample_time("hg", observation["hg"], worker, observation["time_ms"])
                    if at is not None:
                        points = series.setdefault(identity, {})
                        value = (worker.get("network_bytes"), worker.get("ip"))
                        points[at] = value if at not in points or points[at] == value else (None, None)
            grouped = {}
            for identity, samples in series.items():
                previous = None
                ordered = sorted((at, point) for at, point in samples.items() if at < window_end)
                for at, (amount, ip) in ordered:
                    if at >= start or previous and at > start:
                        row = grouped.setdefault((identity, ip), dict(instance=identity[3], machine=identity[2], run=identity[3],
                            group=identity[0], group_id=None, ip=ip, country=None, first_seen_ms=at, last_seen_ms=at,
                            run_first_observed_ms=ordered[0][0] if identity[3] else None, run_last_observed_ms=ordered[-1][0] if identity[3] else None,
                            duration_ms=0, total_mb=None, samples=0, partial=True, estimated=True))
                        row["first_seen_ms"] = min(row["first_seen_ms"], at)
                        row["last_seen_ms"] = max(row["last_seen_ms"], at)
                        row["samples"] += 1
                        if previous and previous[2] == ip and amount is not None and previous[1] is not None:
                            elapsed, delta = at - previous[0], amount - previous[1]
                            if 0 < elapsed <= 180000 and delta >= 0:
                                overlap = at - max(start, previous[0])
                                if overlap > 0:
                                    row["total_mb"] = (row["total_mb"] or 0) + delta / 1e6 * overlap / elapsed
                                    row["duration_ms"] += overlap
                                    row["first_seen_ms"] = min(row["first_seen_ms"], previous[0])
                    previous = at, amount, ip
            rows = list(grouped.values())
            note += " Honeygain uses accepted counter intervals; gaps, resets and the excluded spike IP do not become traffic."
            note += " Run bounds cover retained observations in this test; period observations follow the selected window."
            if snapshot.get("truncated") or snapshot.get("invalid_lines"):
                note += " Retained-reader coverage is partial: bounded or invalid ledger records are reported by the fleet API."
        else:
            path = folder / ("minutes.sqlite3" if service == "ps" else "traffic.sqlite3")
            if not path.exists():
                note = "No retained ledger is available for this service."
            else:
                with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=10)) as db:
                    db.row_factory = sqlite3.Row
                    db.execute("BEGIN")
                    if service in ("ps", "proxyrack", "pawns"):
                        if service == "ps":
                            inventory_ms = timestamp_ms(source.get("last_success_at") or source.get("checked_at"))
                        if service == "pawns":
                            item = db.execute("SELECT group_id FROM collector ORDER BY time_ms DESC LIMIT 1").fetchone()
                            group = item[0] if item else None
                        groups = [r[0] for r in db.execute("SELECT DISTINCT group_id FROM minutes")]
                        table = """SELECT m.instance,m.machine,m.instance||'/'||m.observer run,m.ip,c.country,
                                   m.start_ms,m.end_ms,m.rx+m.tx amount,m.valid=1 AND m.seq>0 valid,m.seq,
                                   m.received_ms,m.bucket_ms IS NULL estimated FROM minutes m
                                   LEFT JOIN countries c ON c.ip=m.ip WHERE m.group_id=:group"""
                    elif service == "rp":
                        groups = [r[0] for r in db.execute("SELECT DISTINCT group_id FROM events WHERE group_id IS NOT NULL")]
                        table = """SELECT instance,machine,run,ip,NULL country,start_ms,end_ms,rx_bytes+tx_bytes amount,
                                   valid,NULL seq,received_ms,COALESCE(json_extract(body,'$.partial'),0) estimated
                                   FROM events WHERE group_id=:group AND kind='minute'"""
                        note += " Legacy Repocket receipt times and group attribution may be partial; country was not recorded."
                    elif service == "earnapp":
                        groups = [r[0] for r in db.execute("SELECT DISTINCT group_id FROM samples")]
                        table = """SELECT instance,json_extract(body,'$.machine') machine,instance||'/'||observer run,
                                   json_extract(body,'$.ip') ip,json_extract(body,'$.country') country,start_ms,end_ms,
                                   json_extract(body,'$.rx')+json_extract(body,'$.tx') amount,
                                   seq>0 AND COALESCE(json_extract(body,'$.valid'),1)=1 valid,seq,received_ms,0 estimated
                                   FROM samples WHERE group_id=:group"""
                        note += " EarnApp history and network totals include all recorded countries; new placement remains US-only."
                    elif service == "earnfm":
                        item = db.execute("SELECT value FROM collector WHERE name='group_id'").fetchone()
                        if item is None or item[0] != group:
                            raise ValueError("EarnFM ledger does not match the selected test")
                        groups = [group]
                        start = max(start, meta.get("measurement_started_ms") or 0)
                    elif service == "tm":
                        groups = [group]
                        start = max(start, meta.get("measurement_started_ms") or 0)
                        note += " TM history is scoped to the configured test start; its ledger does not store archived group UUIDs."
                    else:
                        groups = [None]
                        table = """WITH samples_with_previous AS (
                                   SELECT body,source_ms,run,LAG(body) OVER(PARTITION BY run ORDER BY source_ms) previous FROM samples)
                                   SELECT json_extract(body,'$.group_id') group_id,
                                   json_extract(body,'$.instance') instance,json_extract(body,'$.machine') machine,run,
                                   json_extract(body,'$.ip') ip,json_extract(body,'$.country') country,
                                   COALESCE(json_extract(previous,'$.source_ms'),source_ms) start_ms,source_ms end_ms,
                                   json_extract(body,'$.rx')+json_extract(body,'$.tx')-json_extract(previous,'$.rx')-json_extract(previous,'$.tx') amount,
                                   previous IS NOT NULL AND json_extract(body,'$.rx')>=json_extract(previous,'$.rx')
                                   AND json_extract(body,'$.tx')>=json_extract(previous,'$.tx')
                                   AND json_extract(body,'$.ip') IS NOT NULL
                                   AND json_extract(body,'$.ip') IS json_extract(previous,'$.ip')
                                   AND json_extract(body,'$.monotonic_ms')>json_extract(previous,'$.monotonic_ms')
                                   AND ABS(source_ms-json_extract(previous,'$.source_ms')-json_extract(body,'$.monotonic_ms')+json_extract(previous,'$.monotonic_ms'))<=5000 valid,
                                   NULL seq,json_extract(body,'$.recorded_ms') received_ms,1 estimated FROM samples_with_previous"""
                        note += " Grass preserves recorded group UUIDs; legacy group identities remain unknown. This view includes the retained groups."
                    tests += [dict(id=g, label="Archived group · " + g, archived=True) for g in groups if g and g != group]
                    if selected != "current":
                        if selected not in {test["id"] for test in tests}:
                            raise ValueError("Unknown archived test")
                        group = selected
                    if service in ("earnfm", "tm"):
                        samples = cache.setdefault("samples", {}).setdefault(service, {})
                        rows = sample_history(db, path, service, meta.get("measurement_started_ms") or 0, start, window_end, samples)
                        for row in rows:
                            row["group_id"] = group
                        note += " Boundary minute bins are estimated; original sample spans and observation times are retained."
                    else:
                        params = dict(group=group, start=start, end=window_end, test_start=meta.get("measurement_started_ms") or 0)
                        if archived:
                            last = db.execute("WITH records AS (" + table + ") SELECT MAX(end_ms) FROM records", params).fetchone()[0]
                            window_end = last + 1 if last is not None else now
                            start = 0 if hours == "all" else window_end // 60000 * 60000 - (int(hours) * 60 - 1) * 60000
                            params.update(start=start, end=window_end)
                        group_column = "group_id" if service == "grass" else ":group"
                        sql = f"""WITH records AS ({table}), selected AS (
                                 SELECT *,MAX(0,MIN(end_ms,:end)-MAX(start_ms,:start)) overlap FROM records
                                 WHERE (end_ms>:start OR end_ms=start_ms AND end_ms>=:start) AND start_ms<:end)
                                 SELECT {group_column} group_id,instance,machine,run,ip,MAX(country) country,MIN(start_ms) first_seen_ms,
                                 MAX(end_ms) last_seen_ms,MAX(received_ms) received_ms,COUNT(*) samples,
                                 SUM(CASE WHEN valid AND amount>=0 THEN amount*CASE WHEN end_ms>start_ms
                                     THEN overlap*1.0/(end_ms-start_ms) ELSE 1 END END)/1e6 total_mb,
                                 SUM(CASE WHEN valid AND amount>=0 THEN overlap ELSE 0 END) duration_ms,
                                 MAX(CASE WHEN seq=0 THEN 0 ELSE NOT valid OR amount IS NULL OR end_ms<=start_ms OR start_ms<:start END) partial,
                                 MAX(estimated OR start_ms<:start) estimated
                                 FROM selected GROUP BY {group_column},instance,machine,run,ip"""
                        rows = [dict(r) for r in db.execute(sql, params)]
                    for row in rows:
                        row["partial"] = bool(row["partial"] or row["total_mb"] is None or service not in ("earnfm", "tm") and row["duration_ms"] < row["last_seen_ms"] - row["first_seen_ms"])
                        row["estimated"] = bool(row["estimated"])
                    if service in ("pawns", "grass") and not group:
                        note += " Current group binding is unavailable."
        for row in rows:
            if row["total_mb"] is None:
                row["duration_ms"] = None
            row["id"] = service + "/" + selected + "/" + "/".join(str(row.get(k) or "") for k in ("group_id", "group", "instance", "machine", "run", "ip"))
            row["provider"] = None
        test = next((t for t in tests if t["id"] == selected), None)
        if test is None:
            raise ValueError("Unknown archived test")
        result = dict(service=service, test=test, tests=tests, start_ms=start or min((r["first_seen_ms"] for r in rows), default=None),
                      end_ms=window_end, source_ms=max((r["last_seen_ms"] for r in rows), default=None),
                      coverage_note=note + " History aggregation may lag new recording by up to 30 seconds.", rows=rows)
        if len(cache) >= 32 and key not in cache:
            cache.pop(next(k for k in cache if isinstance(k, tuple)))
        cache[key] = (binding, time.monotonic(), result)
    if service == "hg":
        current = fleet_view.snapshot(honeygain_only=True)
        source = (current.get("latest") or {}).get("hg", {})
        inventory_ms = source.get("status_observed_ms")
    else:
        source = read_view(folder / view_name) if (folder / view_name).exists() else {}
        inventory_ms = timestamp_ms(source.get("last_success_at") or source.get("checked_at")) if service == "ps" else source.get("inventory_ms", source.get("generated_ms"))
        if service == "proxyrack" and source.get("cloud_error"):
            inventory_ms = None
    workers = source.get("workers", source.get("nodes", []))
    fresh = isinstance(inventory_ms, (int, float)) and 0 <= now - inventory_ms <= (120000 if service in ("hg", "ps") else 90000)
    if source.get("poll_error") or service == "hg" and (source.get("status_stale") or current.get("recorder_stale")):
        fresh = False
    members = {}
    for worker in workers:
        identities = [worker[k] for k in ("id", "instance", "instance_id", "salad_instance", "runtime_instance", "run") if worker.get(k)]
        for identity in identities:
            members[str(identity)] = worker
    newest = {}
    for row in result["rows"]:
        identity = row.get("group"), row["instance"], row["machine"]
        if identity not in newest or row["last_seen_ms"] > newest[identity]["last_seen_ms"]:
            newest[identity] = row
    rows = []
    for saved_row in result["rows"]:
        row = dict(saved_row)
        member = members.get(str(row["instance"])) or members.get(str(row["run"]))
        current_run = member.get("run") if member else None
        if member and member.get("observer_ms") is not None:
            current_run = str(member.get("id")) + "/" + str(member["observer_ms"])
        latest = newest[row.get("group"), row["instance"], row["machine"]]
        current = bool(member and (not current_run or row["run"] == current_run)
                       and (not member.get("machine") or row["machine"] == member["machine"])
                       and (not member.get("ip") or row["ip"] == member["ip"])
                       and row["run"] == latest["run"] and row["ip"] == latest["ip"])
        row["current"] = False if result["test"]["archived"] else None if not fresh or not row["run"] else current
        row["lifecycle"] = "archived" if result["test"]["archived"] else "current" if row["current"] else "retired" if row["current"] is False else "unverified"
        rows.append(row)
    result = dict(result, rows=rows, inventory_ms=inventory_ms)
    rows = [r for r in result["rows"] if not search or search in " ".join(str(r.get(k) or "") for k in ("ip", "country", "instance", "machine", "run", "lifecycle")).casefold()]
    field = "last_seen_ms" if order == "last_seen" else "total_mb"
    rows.sort(key=lambda r: (r[field] is not None, r[field] or 0, r["id"]), reverse=True)
    return dict(result, rows=rows[offset:offset+limit], total=len(rows), has_more=offset+limit<len(rows))


def running_cost(start, end, resources):
    if not isinstance(resources, dict):
        return None
    cpu, memory = resources.get("cpu"), resources.get("memory")
    if resources.get("gpu_classes") or type(cpu) not in (int, float) or type(memory) not in (int, float) or not math.isfinite(cpu) or not math.isfinite(memory) or cpu <= 0 or memory <= 0:
        return None
    before = max(0, min(end, SALAD_CPU_PRICE_CHANGE_MS) - start)
    after = max(0, end - max(start, SALAD_CPU_PRICE_CHANGE_MS))
    amount = Decimal(str(cpu)) * (Decimal("0.004") * before + Decimal("0.005") * after)
    amount += Decimal(str(memory)) / 1024 * Decimal("0.001") * max(0, end - start)
    return float(amount / 3600000)


def cost_snapshot(root, service, start, end, group_ids=None):
    result = {"estimated_usd": None, "running_minutes": None, "usd_per_hour": None, "observed_ms": None,
              "partial": True, "nodes": [], "errors": [], "window": {"start_ms": start, "end_ms": end},
              "basis": "Recorded Salad running-state time at published CPU/RAM prices; not an invoice",
              "rate_source": "https://docs.salad.com/container-engine/explanation/billing-pricing/billing",
              "price_change_source": "https://blog.salad.com/saladcloud-price-changes-september-2026/"}
    path = root / "costs.sqlite3"
    if not path.exists():
        result["errors"] = ["Cost recorder has not published data yet"]
        return result
    try:
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
            targets = db.execute("SELECT body,error FROM targets WHERE service=?", (service,)).fetchall()
            groups = {}
            fresh = bool(targets)
            history_complete = bool(targets)
            for body, error in targets:
                if error:
                    result["errors"].append(error)
                    fresh = False
                if not body:
                    history_complete = False
                    continue
                group = json.loads(body)
                groups[group["id"]] = group
                fresh &= 0 <= end - group["observed_ms"] <= 180000
                query = db.execute("SELECT * FROM cursors WHERE organization=?", (group["organization"],))
                row = query.fetchone()
                cursor = dict(zip((c[0] for c in query.description), row)) if row else {}
                history_complete &= bool(cursor.get("periods_ms") is not None and cursor["periods_ms"] >= end - 180000
                                         and cursor.get("periods_start_ms") is not None
                                         and cursor["periods_start_ms"] <= max(start, group["created_ms"]) and not cursor["error"])
                if cursor.get("error"):
                    result["errors"].append(cursor["error"])
            if not groups:
                return result
            result["observed_ms"] = min(g["observed_ms"] for g in groups.values())
            source_end = min(end, result["observed_ms"])
            selected_groups = set(group_ids) if group_ids else set(groups)
            members = {(g["id"], n["id"]): n for g in groups.values() for n in g["instances"]}
            rate, rate_known = Decimal(0), fresh
            for group in groups.values():
                hour = end // 3600000 * 3600000
                hourly = running_cost(hour, hour + 3600000, group["resources"])
                if hourly is None:
                    rate_known = False
                else:
                    rate += Decimal(str(hourly)) * sum(n["state"] == "running" for n in group["instances"])
            result["usd_per_hour"] = float(rate) if rate_known else None
            values, durations, missing = [], [], not history_complete or not fresh
            for body, in db.execute("SELECT body FROM runs WHERE service=? AND (start_ms IS NULL OR start_ms<=?) AND (end_ms IS NULL OR end_ms>=?)", (service, end, start)):
                node = json.loads(body)
                if node["group_id"] not in selected_groups or node.get("absent_ms") is not None and node["absent_ms"] < start:
                    continue
                member = members.get((node["group_id"], node["instance"]))
                current = bool(member and member["state"] == "running")
                periods = node.get("periods")
                partial = not periods or not history_complete or bool(node.get("resource_assumed")) or bool(node.get("error"))
                if periods is None:
                    periods = [{k: node.get(k) for k in ("start_ms", "end_ms", "last_running_ms")}]
                intervals, amounts, elapsed = [], [], 0
                for period in periods:
                    if period["start_ms"] is None:
                        partial |= period["end_ms"] is None or period["end_ms"] > start
                        continue
                    left = max(start, period["start_ms"])
                    stop = period["end_ms"] if period["end_ms"] is not None else period.get("last_running_ms")
                    if stop is None:
                        partial = True
                        continue
                    right = min(end if period["end_ms"] is not None else source_end, stop)
                    if right < left or period["start_ms"] >= end:
                        if period["end_ms"] is None and period["start_ms"] < end:
                            partial = True
                        continue
                    if period["end_ms"] is None and not current and right == left:
                        partial = True
                        continue
                    amount = running_cost(left, right, node["resources"]) if not node.get("error") else None
                    intervals.append({"start_ms": left, "end_ms": right, "running_minutes": (right-left)/60000 if not node.get("error") else None,
                                      "estimated_usd": amount, "closed": period["end_ms"] is not None})
                    elapsed += right - left
                    if amount is not None:
                        amounts.append(Decimal(str(amount)))
                    partial |= amount is None or (period["end_ms"] is None and (not current or right < end))
                left = intervals[0]["start_ms"] if intervals else None
                right = intervals[-1]["end_ms"] if intervals else None
                cost = float(sum(amounts)) if amounts else 0.0 if not partial else None
                elapsed = elapsed if not node.get("error") and (intervals or not partial) else None
                result["nodes"].append({"instance": node["instance"], "machine": node["machine"], "group_id": node["group_id"], "group": node["group"],
                                        "start_ms": left, "end_ms": right, "running_minutes": elapsed / 60000 if elapsed is not None else None,
                                        "estimated_usd": cost, "current": current if fresh else None, "partial": partial,
                                        "resources": node["resources"], "resource_observed_ms": node["resource_observed_ms"],
                                        "scope": "Salad instance in the selected period", "intervals": intervals, "error": node.get("error")})
                if cost is not None:
                    values.append(Decimal(str(cost)))
                if elapsed is not None:
                    durations.append(elapsed)
                missing |= partial
            result.update(estimated_usd=float(sum(values)) if values else 0.0 if history_complete and not missing else None,
                          running_minutes=sum(durations) / 60000 if durations else 0.0 if history_complete and not missing else None, partial=missing)
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error) as error:
        result["errors"].append("Cost data unavailable: " + type(error).__name__)
    return result


def provider_amount(value, factor=1):
    if value is None or isinstance(value, bool):
        return None
    try:
        value = Decimal(str(value)) * Decimal(str(factor))
        return float(value) if value.is_finite() and value >= 0 else None
    except InvalidOperation:
        return None


def provider_changes(service, root, cache):
    sources = {
        "ps": ("packetstream/provider.sqlite3", "SELECT body FROM readings ORDER BY observed_ms DESC LIMIT 2000", "rolling_bytes", "0.000001", "rolling_bytes", PACKETSTREAM_USD_PER_GB / 1000000000),
        "rp": ("repocket/provider.sqlite3", "SELECT body FROM readings ORDER BY observed_ms DESC LIMIT 2000", "total_bytes", "0.000001", "total_usd_cents", "0.01"),
        "earnfm": ("earnfm/traffic.sqlite3", "SELECT body FROM provider_history ORDER BY observed_ms DESC LIMIT 2000", "gb", 1000, None, 1),
        "tm": ("traffmonetizer/traffic.sqlite3", "SELECT payload FROM provider ORDER BY time_ms DESC LIMIT 2000", "credited_bytes", "0.000001", "credited_usd", 1),
        "pawns": ("pawns/traffic.sqlite3", "SELECT data FROM pawns_events WHERE kind='PROVIDER' AND json_extract(data,'$.balance_ms') IS NOT NULL ORDER BY time_ms DESC LIMIT 2000", "sold_gb", 1000, "sold_gb", PAWNS_USD_PER_GB),
        "earnapp": ("earnapp/traffic.sqlite3", "SELECT body FROM provider ORDER BY observed_ms DESC LIMIT 2000", None, 1, "earned_total", 1),
        "hg": ("hg-fleet/provider-readings.jsonl", None, "gathering_traffic_bytes", "0.000001", "gathering_credits", 1 / HONEYGAIN_CREDITS_PER_USD),
    }
    if service not in sources:
        return []
    name, query, traffic, traffic_factor, earnings, usd_factor = sources[service]
    path = root / name
    stamps = []
    for p in (path, Path(str(path) + "-wal")):
        stat = p.stat() if p.exists() else None
        stamps.append((stat.st_ino, stat.st_size, stat.st_mtime_ns) if stat else None)
    key = "provider_changes", service
    if key in cache and cache[key][0] == stamps:
        return cache[key][1]
    if query:
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
            readings = [json.loads(row[0]) for row in db.execute(query)][::-1]
    else:
        with path.open("rb") as stream:
            offset = max(0, path.stat().st_size - 8 * 1024 * 1024)
            stream.seek(offset)
            if offset:
                stream.readline()
            lines = stream.read().splitlines(keepends=True)
        readings = [json.loads(line) for line in lines[-2000:] if line.endswith(b"\n")]
    identities = ("auth_user_id", "report_user_id", "account_id", "uuid", "baseline_ms", "group_id")
    current_identity = tuple(readings[-1].get(k) for k in identities) if readings else None
    intervals, previous = [], None
    for p in readings:
        if tuple(p.get(k) for k in identities) != current_identity:
            previous = None
            continue
        at = p.get("observed_ms", p.get("balance_ms"))
        mb = Decimal(str(p[traffic])) * Decimal(str(traffic_factor)) if provider_amount(p.get(traffic), traffic_factor) is not None else None
        usd = Decimal(str(p[earnings])) * Decimal(str(usd_factor)) if provider_amount(p.get(earnings), usd_factor) is not None else None
        if not isinstance(at, (int, float)) or mb is None and usd is None:
            previous = None
            continue
        scope = tuple(p.get("report_dates") or []), tuple(day.get("date") for day in p.get("days", []))
        balance = Decimal(str(p["balance"])) if service == "earnfm" and provider_amount(p.get("balance")) is not None else None
        if previous and at > previous[0] and scope == previous[3]:
            old_at, old_mb, old_usd, _, old_balance = previous
            intervals.append({"start_ms": old_at, "end_ms": at,
                              "credited_mb": float(mb - old_mb) if mb is not None and old_mb is not None and mb >= old_mb else None,
                              "earned_usd": float(usd - old_usd) if usd is not None and old_usd is not None and usd >= old_usd else None,
                              **({"balance_change_usd": float(balance-old_balance) if balance is not None and old_balance is not None else None} if service == "earnfm" else {})})
        if not previous or at >= previous[0]:
            previous = at, mb, usd, scope, balance
    cache[key] = stamps, intervals
    return intervals


def provider_metrics(service, data, root, read_view, now):
    result = dict(credited_mb=None, earned_usd=None, balance_usd=None, bandwidth_balance_usd=None,
                  balance_change_usd=None, effective_usd_per_gb=None,
                  withdrawn_usd=None, observed_ms=None, provider_updated_ms=None, fresh=False,
                  scope="account", window={}, raw={}, source=None, error=None, missing=None,
                  accounting_interval_seconds=None, posting_interval_seconds=None,
                  minute_attribution=False, country_attribution=False)

    def read(name):
        path = root / name
        return read_view(path) if path.exists() else {}

    amount = provider_amount

    try:
        if service == "hg":
            p = read("hg-fleet/provider-api-traffic-latest.json")
            days = p.get("days", {})
            values = list(days.values())
            traffic = [amount(v.get("gathering_traffic_bytes")) for v in values]
            credits = [amount(v.get("gathering_credits")) for v in values]
            result.update(source="https://dashboard.honeygain.com/api/v1/earnings/stats",
                          observed_ms=p.get("observed_ms"), raw={"days": days,
                              "account_balance_credits": p.get("account_balance_credits"),
                              "account_balance_observed_ms": p.get("account_balance_observed_ms"),
                              "account_balance_source": "https://dashboard.honeygain.com/api/v1/users/balances"},
                          window={"kind": "provider_days", "first_date": min(days) if days else None,
                                  "last_date": max(days) if days else None, "timezone": None},
                          credited_mb=sum(traffic) / 1e6 if traffic and None not in traffic else None,
                          earned_usd=float(sum(Decimal(str(v["gathering_credits"])) for v in values) / HONEYGAIN_CREDITS_PER_USD) if credits and None not in credits else None,
                          usd_conversion={"credits_per_usd": int(HONEYGAIN_CREDITS_PER_USD), "verified_date": "2026-09-07",
                                          "source": "https://www.honeygain.com/jumptask-mode/"},
                          error=read("hg-fleet/provider-feed-status.json").get("error"))
        elif service == "ps":
            p = read("packetstream/provider.json")
            days = p.get("days", [])
            result.update(source="https://app.packetstream.io/dashboard", observed_ms=p.get("observed_ms"),
                          credited_mb=amount(p.get("rolling_bytes"), "0.000001"), balance_usd=amount(p.get("balance_usd")),
                          earned_usd=amount(p.get("rolling_bytes"), PACKETSTREAM_USD_PER_GB / 1000000000),
                          raw={k: p.get(k) for k in ("rolling_bytes", "balance_usd", "days")},
                          window={"kind": "rolling_provider_days", "first_date": days[0].get("date") if days else None,
                                  "last_date": days[-1].get("date") if days else None, "timezone": "UTC"},
                          error=read("packetstream/provider-status.json").get("error") or p.get("error"),
                          usd_conversion={"usd_per_gb": float(PACKETSTREAM_USD_PER_GB), "basis": "published rate applied to provider-reported traffic",
                                          "verified_date": "2026-09-07", "source": "https://packetstream.io/terms-of-service/"})
        elif service == "proxyrack":
            p = data
            balance = p.get("balance")
            result.update(source="https://peer.proxyrack.com/api/balance", observed_ms=p.get("balance_checked_ms"),
                          balance_usd=amount(balance[1:].replace(",", "")) if isinstance(balance, str) and balance.startswith("$") else None,
                          raw={k: p.get(k) for k in ("provider_bandwidth_value", "provider_bandwidth_unit", "balance", "balance_checked_ms")},
                          window={"kind": "account_balance_and_device_counters"}, error=p.get("balance_error"),
                          missing="The bandwidth API counter's physical unit and separate bandwidth earnings are unverified.")
        elif service == "rp":
            p = read("repocket/provider.json")
            result.update(source="https://api.repocket.com/api/reports/total", observed_ms=p.get("observed_ms"),
                          provider_updated_ms=p.get("provider_updated_ms"), last_changed_ms=p.get("last_changed_ms"),
                          credited_mb=amount(p.get("total_bytes"), "0.000001"), earned_usd=amount(p.get("total_usd_cents"), "0.01"),
                          raw={k: p.get(k) for k in ("total_bytes", "total_usd_cents", "provider_period_start_ms",
                              "pending_bytes", "pending_usd_cents", "account_earned_usd_cents",
                              "account_credited_usd_cents", "account_withdrawn_usd_cents")},
                          window={"kind": "account_lifetime_own_bandwidth"},
                          error=read("repocket/provider-status.json").get("error") or p.get("error"))
            if p.get("total_bytes") is None or p.get("total_usd_cents") is None:
                result["missing"] = "A structured own-bandwidth account reading is unavailable."
        elif service == "earnfm":
            p = data.get("provider") or {}
            result.update(source="https://api.earn.fm/v2/harvester/view_balance", observed_ms=p.get("observed_ms"),
                          credited_mb=amount(p.get("credited_mb")), bandwidth_balance_usd=amount(p.get("balance")), balance_usd=amount(p.get("balance")),
                          balance_change_usd=p.get("earned"), error=p.get("error"),
                          raw={k: p.get(k) for k in ("gb", "balance", "earned", "credited_mb", "baseline_ms", "received_ms")},
                          window={"kind": "account_baseline_change", "start_ms": p.get("baseline_ms"),
                                  "end_ms": p.get("observed_ms"), "start_approximate": True},
                          missing="A bandwidth balance change is available; gross earnings and withdrawals are not separately reported.")
        elif service == "tm":
            p = data.get("credited") or {}
            result.update(source="https://data.traffmonetizer.com/api/dashboard/get_graph_stat?period=month",
                          observed_ms=p.get("observed_ms"), credited_mb=amount(p.get("credited_bytes"), "0.000001"),
                          earned_usd=amount(p.get("credited_usd")), balance_usd=amount(p.get("balance_usd")),
                          balance_change_usd=p.get("balance_change_usd"), error=data.get("errors", {}).get("provider"),
                          raw={k: p.get(k) for k in ("credited_bytes", "credited_usd", "days", "balance_usd", "balance_change_usd")},
                          window={"kind": "account_baseline_change", "start_ms": timestamp_ms(data.get("deployment", {}).get("started_at")),
                                  "end_ms": p.get("observed_ms")})
        else:
            with closing(sqlite3.connect((root / service / "traffic.sqlite3").as_uri() + "?mode=ro", uri=True)) as db:
                if service == "pawns":
                    group = db.execute("SELECT group_id FROM collector ORDER BY time_ms DESC LIMIT 1").fetchone()
                    latest = db.execute("SELECT data FROM pawns_events WHERE group_id=? AND kind='PROVIDER' ORDER BY time_ms DESC LIMIT 1",
                                        (group[0] if group else None,)).fetchone()
                    latest = json.loads(latest[0]) if latest else {}
                    row = db.execute("SELECT data FROM pawns_events WHERE group_id=? AND kind='PROVIDER' "
                                     "AND json_extract(data,'$.account_id')=? AND json_extract(data,'$.balance_ms') IS NOT NULL "
                                     "ORDER BY time_ms DESC LIMIT 1", (group[0] if group else None, latest.get("account_id"))).fetchone()
                    p = json.loads(row[0]) if row else {}
                    result.update(source="https://api.pawns.app/api/v1/users/me/balance", observed_ms=p.get("balance_ms"),
                                  credited_mb=amount(p.get("sold_gb"), 1000), bandwidth_balance_usd=amount(p.get("sharing_usd")),
                                  earned_usd=amount(p.get("sold_gb"), PAWNS_USD_PER_GB),
                                  balance_usd=amount(p.get("balance_usd")), error=latest.get("error"),
                                  raw={k: p.get(k) for k in ("sold_gb", "sharing_usd", "balance_usd")},
                                  window={"kind": "account_totals"},
                                  usd_conversion={"usd_per_gb": float(PAWNS_USD_PER_GB), "basis": "published rate applied to provider-reported sold traffic",
                                                  "verified_date": "2026-09-07", "source": "https://business.pawns.app/sdk/"})
                elif service == "earnapp":
                    source = read("earnapp/view.json")
                    row = db.execute("SELECT body FROM provider WHERE observed_ms=? LIMIT 1", (source.get("provider_observed_ms"),)).fetchone()
                    p = json.loads(row[0]) if row else {}
                    check = db.execute("SELECT body FROM meta WHERE key='provider_check'").fetchone()
                    check = json.loads(check[0]) if check else {}
                    result.update(source="https://earnapp.com/dashboard/api/devices", scope="device", observed_ms=p.get("observed_ms"),
                                  earned_usd=amount(p.get("earned_total")), error=check.get("credit_error"),
                                  raw={k: p.get(k) for k in ("uuid", "earned_total", "usage_ms", "rate", "billing")},
                                  monthly_rate_usd=amount(p.get("rate")) if p.get("billing") == "qualified_uptime" else None,
                                  window={"kind": "device_lifetime"}, accounting_interval_seconds=3600,
                                  missing="EarnApp pays for active usage time; provider credited MB is not reported.")
                elif service == "grass":
                    row = db.execute("SELECT body FROM provider WHERE NOT EXISTS (SELECT 1 FROM conflicts "
                                     "WHERE run=json_extract(provider.body,'$.sample_run') AND source_ms=json_extract(provider.body,'$.sample_ms')) "
                                     "ORDER BY observed_ms DESC LIMIT 1").fetchone()
                    p = json.loads(row[0]) if row and data.get("credited_text") else {}
                    result.update(source="https://api.grass.io/epochEarnings", observed_ms=p.get("observed_ms"),
                                  provider_updated_ms=timestamp_ms(p.get("modified_at")),
                                  raw={k: p.get(k) for k in ("network_points", "total_points", "stage", "epoch", "start_date", "end_date", "modified_at")},
                                  window={"kind": "epoch", "stage": p.get("stage"), "epoch": p.get("epoch"),
                                          "first_date": p.get("start_date"), "last_date": p.get("end_date")},
                                  accounting_interval_seconds=86400,
                                  missing="No verified MB conversion or USD allocation for this recorded stage and epoch.")
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error) as error:
        result["error"] = "Provider measurements unavailable: " + type(error).__name__
    observed = result["observed_ms"]
    max_age = {"hg": 360000, "proxyrack": 900000}.get(service, 180000)
    result["fresh"] = isinstance(observed, (int, float)) and 0 <= now - observed <= max_age and not result["error"]
    if result["earned_usd"] is not None and result["credited_mb"] is not None and result["credited_mb"] > 0:
        result["effective_usd_per_gb"] = result["earned_usd"] * 1000 / result["credited_mb"]
    return result


def traffic_summary(data, hours, now, service=None, changes=()):
    points = next((data[k] for k in ("hg_minutes", "candles", "chart_minutes", "points", "minutes") if isinstance(data.get(k), list)), [])
    end = now // 60000 * 60000 + 60000
    start = end - hours * 3600000
    rows = [(p.get("minute_ms", p.get("time_ms")), p) for p in points]
    rows = [(t, p) for t, p in rows if isinstance(t, (int, float)) and end - 86400000 <= t < end
            and type(p.get("mb")) in (int, float) and math.isfinite(p["mb"]) and p["mb"] >= 0]
    selected = [(t, p) for t, p in rows if t >= start]
    complete = [(t, p) for t, p in selected if t + 60000 <= now]
    peak = max(complete, key=lambda row: row[1]["mb"], default=None)
    by_minute = {t: p for t, p in complete if p.get("coverage_complete") is True
                 or p.get("coverage_complete") is None and p.get("partial") is False}
    comparisons = {}
    for field in (("credited_mb", "earned_usd") if service == "earnapp" else ("credited_mb",)):
        compared, measured, reported, estimated, partial = [], Decimal(0), Decimal(0), False, False
        candidates = [change for change in changes if change[field] is not None]
        for change in candidates:
            traffic, known, allocated, incomplete = Decimal(0), True, False, False
            for minute in range(change["start_ms"] // 60000 * 60000, change["end_ms"], 60000):
                point = by_minute.get(minute)
                if point is None:
                    known = False
                    break
                duration = min(change["end_ms"], minute + 60000) - max(change["start_ms"], minute)
                traffic += Decimal(str(point["mb"])) * duration / 60000
                allocated |= duration != 60000 or bool(point.get("estimated"))
                incomplete |= bool(point.get("partial"))
            if known:
                measured += traffic
                reported += Decimal(str(change[field]))
                compared.append(change)
                estimated |= allocated
                partial |= incomplete
        rate_key, scale = ("ratio_percent", 100) if field == "credited_mb" else ("usd_per_recorded_gb", 1000)
        comparisons[field] = {"basis": "observed provider " + ("credit" if field == "credited_mb" else "earnings") + " changes / recorded traffic in the same observation intervals",
                      "provider_scope": (data.get("provider_metrics") or {}).get("scope"), "traffic_scope": "recorded fleet",
                      "measured_mb": float(measured) if compared else None, field: float(reported) if compared else None,
                      rate_key: float(reported * scale / measured) if compared and measured > 0 else None,
                      "start_ms": compared[0]["start_ms"] if compared else None, "end_ms": compared[-1]["end_ms"] if compared else None,
                      "covered_ms": sum(row["end_ms"] - row["start_ms"] for row in compared), "intervals": len(compared),
                      "estimated": estimated, "partial": partial or len(compared) != len(changes) or not compared
                      or any(a["end_ms"] != b["start_ms"] for a, b in zip(compared, compared[1:]))}
    inventory = ((data.get("latest") or {}).get("hg") or {}) if service == "hg" else data
    total = inventory.get("desired")
    observed = inventory.get("status_observed_ms") if service == "hg" else inventory.get("inventory_ms")
    running = inventory.get("running")
    if service == "hg" and total is None:
        total = ((data.get("experiment") or {}).get("hg") or {}).get("desired")
    if service == "ps":
        observed = data.get("time_ms", now) - data["inventory_age_ms"] if isinstance(data.get("inventory_age_ms"), (int, float)) else None
        running = sum(w.get("salad_state") == "running" for w in data.get("nodes", []))
    elif service in ("proxyrack", "earnfm"):
        total = data.get("requested") if service == "proxyrack" else total
        running = sum(w.get("salad_state") == "running" for w in data.get("workers", []))
    elif service == "tm":
        total = data.get("deployment", {}).get("desired_replicas")
    inventory_fresh = (isinstance(observed, (int, float)) and 0 <= now - observed <= (120000 if service in ("hg", "ps") else 90000)
                       and data.get("inventory_fresh") is not False and not data.get("cloud_error")
                       and not data.get("recorder_stale") and not inventory.get("status_stale"))
    return {"unit": "MB", "start_ms": start, "end_ms": end,
            "containers_running": running if inventory_fresh else None,
            "containers_total": total, "inventory_ms": observed,
            "selected_mb": sum(p["mb"] for _, p in selected) if selected else None,
            "last_24h_mb": sum(p["mb"] for _, p in rows) if rows else None,
            "selected_observed_minutes": len(selected), "last_24h_observed_minutes": len(rows),
            "partial": len(selected) < hours * 60 or any(p.get("partial") for _, p in selected),
            "last_24h_partial": len(rows) < 1440 or any(p.get("partial") for _, p in rows),
            "estimated": any(p.get("estimated") for _, p in selected),
            "average_mb_per_minute": sum(p["mb"] for _, p in complete) / len(complete) if complete else None,
            "average_basis": "completed observed minutes", "average_minutes": len(complete),
            "average_partial": len(complete) < hours * 60 - 1 or any(p.get("partial") or p.get("coverage_complete") is False for _, p in complete),
            "peak_mb_per_minute": peak[1]["mb"] if peak else None, "peak_minute_ms": peak[0] if peak else None,
            "provider_comparison": comparisons["credited_mb"], "earnings_comparison": comparisons.get("earned_usd")}


def make_handler(store: Store, status_provider: Callable[[], Dict[str, Any]], static_dir: Path, ps_view=None, expected_reporters: int = 10, fleet_view=None, minute_view=None, *, trusted_uid):
    static_dir = Path(static_dir)
    fleet_view = fleet_view or FleetTestView(Path(os.environ.get("FLEET_TEST_DIR", str(Path.home() / ".hg1" / "fleet-tests"))))
    view_cache, compact_cache, assets = {}, {}, {}
    cache_lock = threading.RLock()
    history_cache, history_lock = {}, threading.Lock()

    def signature(path):
        stat = path.stat()
        return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns

    def read_view(path):
        with cache_lock:
            stamp = signature(path)
            saved = view_cache.get(path)
            if saved is None or saved[0] != stamp:
                saved = (stamp, json.loads(path.read_text()))
                view_cache[path] = saved
            return saved[1]

    def read_asset(filename):
        path = static_dir / filename
        stamp = signature(path)
        saved = assets.get(filename)
        if saved is None or saved[0] != stamp:
            body = path.read_bytes()
            saved = (stamp, body, hashlib.sha256(body).hexdigest())
            assets[filename] = saved
        return saved[1:]

    def compact(value, path, hours):
        value = dict(value)
        first = int(time.time()) // 60 * 60000 - (hours * 60 - 1) * 60000
        if path == "/api/fleet-test":
            value.pop("buckets", None)
            value["timeline"] = {"hg": {"provider": value.get("timeline", {}).get("hg", {}).get("provider", [])}}
        if path == "/api/proxyrack":
            value.pop("timeline", None)
        fields = [field for field in ("hg_minutes", "minutes", "chart_minutes", "candles", "points") if field in value]
        saved = compact_cache.get((path, hours))
        if saved and saved[0] == first and len(saved[1]) == len(fields) and all(saved[1].get(field) is value[field] for field in fields):
            value.update(saved[2])
            return value
        identities, nodes, charts = {}, [], {}
        for field in ("hg_minutes", "minutes", "chart_minutes", "candles", "points"):
            if field not in value:
                continue
            points = []
            for row in value[field]:
                if row.get("minute_ms", row.get("time_ms", 0)) < first:
                    continue
                point = dict(row)
                if "nodes" in point:
                    contributions = []
                    for node in point.pop("nodes"):
                        identity = {k: v for k, v in node.items() if k != "mb"}
                        key = tuple(sorted(identity.items()))
                        if key not in identities:
                            identities[key] = len(nodes)
                            nodes.append(identity)
                        contributions.append([identities[key], node.get("mb")])
                    point["contributions"] = contributions
                if "contributions" in point:
                    point.pop("by_instance", None)
                points.append(point)
            charts[field] = points
        charts["chart_nodes"] = nodes
        compact_cache[path, hours] = (first, {field: value[field] for field in fields}, charts)
        value.update(charts)
        return value

    class Handler(BaseHTTPRequestHandler):
        server_version = "SaladBandwidthDashboard/1"

        def parse_request(self):
            if not super().parse_request():
                return False
            try:
                peer = struct.unpack("3i", self.connection.getsockopt(
                    socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")))
                segment = self.headers.get("Cf-Access-Jwt-Assertion", "").split(".")[1]
                claims = json.loads(base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4)))
                if not isinstance(claims, dict):
                    raise ValueError("Invalid claims")
                audiences = claims.get("aud", [])
                if isinstance(audiences, str):
                    audiences = [audiences]
                now = time.time()
                allowed = (peer[1] == trusted_uid and claims.get("iss") == ACCESS_ISSUER
                           and ACCESS_AUDIENCE in audiences and claims.get("type") == "app"
                           and bool(claims.get("identity_nonce"))
                           and float(claims.get("nbf", 0)) <= now < float(claims["exp"]))
            except (IndexError, KeyError, TypeError, ValueError):
                allowed = False
            if not allowed:
                self.send_json(403, {"error": "Access denied"})
            return allowed

        def log_message(self, *_args):
            return

        def headers_common(self) -> None:
            self.send_header("Cache-Control", getattr(self, "response_cache", "no-store"))
            if getattr(self, "response_etag", None):
                self.send_header("ETag", self.response_etag)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'sha256-73jcLt49FKK7j84lIDbuIL668lzKMP1qDpt71lj2Npk=' 'sha256-mB3uO6yEdMXW9Zr+xHKIwvt//xdbTPiIEReT1SjiKC4=' 'sha256-urmwqo1xED1EcUDobdl9uYZm5t62T44YYwLMC275HFk=' 'sha256-nejLk73ayNc2c0ychq4L5UgRGNrZgfZBBXtXwcDe+cA=' 'sha256-YrVZl5GHBUQaU8MS6cYOAjWI2zZEPjh+dz3gqMDda6U='; style-src 'self' 'unsafe-inline'; img-src 'self'; font-src 'self'; connect-src 'self' https://api.country.is; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
            self.send_header("Strict-Transport-Security", "max-age=31536000")

        def send_bytes(self, status: int, body: bytes, content_type: str, disposition: str = "") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            if disposition:
                self.send_header("Content-Disposition", disposition)
            self.headers_common()
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, status: int, value: Any, disposition: str = "") -> None:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            services = {"/api/fleet-test": "hg", "/api/ps1/minutes": "ps", "/api/ps1/view": "ps", "/api/proxyrack": "proxyrack",
                        "/api/repocket": "rp", "/api/earnfm": "earnfm", "/ef.json": "earnfm", "/earnfm.json": "earnfm",
                        "/api/traffmonetizer": "tm", "/api/pawns": "pawns", "/api/grass": "grass"}
            if status == 200 and parsed.path in services and "minute" not in query and "archive" not in query:
                hours = int(query.get("hours", ["24"])[0])
                if hours not in (1, 6, 12, 24, 720):
                    raise ValueError("hours must be 1, 6, 12, 24, or 720")
                now = int(time.time() * 1000)
                value = dict(value, provider_metrics=provider_metrics(services[parsed.path], value, Path.home() / ".hg1", read_view, now))
                provider = value["provider_metrics"]
                try:
                    with cache_lock:
                        changes = provider_changes(services[parsed.path], Path.home() / ".hg1", view_cache)
                    start = now // 60000 * 60000 - (hours * 60 - 1) * 60000
                    changes = [row for row in changes if start <= row["start_ms"] < row["end_ms"] <= now]
                    provider["intervals"] = changes
                    period = {"basis": "changes between provider observations", "selected_start_ms": start, "selected_end_ms": now}
                    for field, window in (("credited_mb", "credited_window"), ("earned_usd", "earned_window"), ("balance_change_usd", "balance_window")):
                        rows = [row for row in changes if row.get(field) is not None]
                        period[field] = float(sum(Decimal(str(row[field])) for row in rows)) if rows else None
                        period[window] = {"start_ms": rows[0]["start_ms"] if rows else None,
                                          "end_ms": rows[-1]["end_ms"] if rows else None, "intervals": len(rows),
                                          "covered_ms": sum(row["end_ms"] - row["start_ms"] for row in rows),
                                          "partial": not rows or rows[0]["start_ms"] > start or rows[-1]["end_ms"] < now
                                          or any(a["end_ms"] != b["start_ms"] for a, b in zip(rows, rows[1:]))}
                    provider["observed_period"] = period
                except (OSError, ValueError, TypeError, sqlite3.Error) as error:
                    provider["intervals"] = []
                    provider["changes_error"] = "Provider history unavailable: " + type(error).__name__
                if parsed.path != "/api/ps1/view":
                    value["traffic_summary"] = traffic_summary(value, hours, now, services[parsed.path], provider.get("intervals", []))
                    value["costs"] = cost_snapshot(Path.home() / ".hg1", services[parsed.path], value["traffic_summary"]["start_ms"], now)
                    lookup = {node["instance"]: node for node in value["costs"]["nodes"]}
                    service = services[parsed.path]
                    identities = {"hg": ("run",), "ps": ("instance",), "proxyrack": ("instance",),
                                  "rp": ("salad_instance", "instance"), "earnfm": ("runtime_instance", "instance"),
                                  "tm": ("instance",), "pawns": ("id",), "earnapp": ("id",), "grass": ("id",)}
                    if service == "hg":
                        if value.get("latest") is not None:
                            latest = value["latest"]
                            hg = latest.get("hg") or {}
                            value["latest"] = dict(latest, hg=dict(hg, workers=[dict(row, cost=lookup.get(row.get("run"))) for row in hg.get("workers", [])]))
                    else:
                        field = "nodes" if service == "ps" else "workers"
                        value[field] = [dict(row, cost=next((lookup[row[k]] for k in identities[service] if row.get(k) in lookup), None)) for row in value.get(field, [])]
            if status == 200 and query.get("compact") == ["1"] and not disposition:
                hours = int(query.get("hours", ["24"])[0])
                if hours not in (1, 6, 12, 24, 720):
                    raise ValueError("hours must be 1, 6, 12, 24, or 720")
                value = compact(value, parsed.path, hours)
            body = json.dumps(value, separators=(",", ":")).encode("utf-8")
            self.send_bytes(status, body, "application/json; charset=utf-8", disposition)

        def do_GET(self):  # noqa: N802
            parsed = urlparse(self.path)
            try:
                if parsed.path == "/api/history":
                    with history_lock:
                        result = history_snapshot(Path.home() / ".hg1", parse_qs(parsed.query), fleet_view, history_cache, read_view)
                    service = parse_qs(parsed.query).get("service", [""])[0]
                    costs = cost_snapshot(Path.home() / ".hg1", service, result["start_ms"], result["end_ms"],
                                          [row["group_id"] for row in result["rows"] if row.get("group_id")])
                    lookup = {node["instance"]: node for node in costs["nodes"]}
                    result = dict(result, rows=[dict(row, cost=lookup.get(row.get("instance"))) for row in result["rows"]])
                    self.send_json(200, result)
                    return
                if parsed.path in ("/api/pawns", "/api/grass"):
                    service = parsed.path.rsplit("/", 1)[1]
                    name = {"pawns": "Pawns.app", "earnapp": "EarnApp", "grass": "Grass"}[service]
                    path = Path.home() / ".hg1" / service / "view.json"
                    source = read_view(path) if path.exists() else {"error": "Waiting for " + name + " measurements."}
                    fields = "generated_ms inventory_ms desired running working started_ms total_mb all_recorded_mb received_mb sent_mb basis credited_text earned_text credit_note error".split()
                    result = {field: source.get(field) for field in fields}
                    worker_fields = "id ip country client_status salad_state working mb_per_minute total_mb recorded_ms sample_ms observer_ms sample_expires_ms recorded_duration_ms note error".split()
                    result["workers"] = [{field: row.get(field) for field in worker_fields} for row in source.get("workers", [])]
                    now = int(time.time() * 1000)
                    recent = lambda value: isinstance(value, (int, float)) and 0 <= now - value <= 90000
                    generated = result["generated_ms"]
                    current = (isinstance(generated, (int, float)) and -10000 <= now - generated <= 90000
                               and recent(result["inventory_ms"]))
                    if not current:
                        result["running"] = None
                    for worker in result["workers"]:
                        sample_fresh = (isinstance(worker["sample_expires_ms"], (int, float)) and isinstance(worker["sample_ms"], (int, float))
                                        and worker["sample_ms"] <= now + 10000 and now <= worker["sample_expires_ms"]) if service == "earnapp" else recent(worker["sample_ms"]) and recent(worker["recorded_ms"])
                        if not current or result["error"] or not sample_fresh:
                            worker["working"] = None
                            worker["mb_per_minute"] = None
                        elif service != "earnapp" and worker["salad_state"] != "running":
                            worker["working"] = False
                            worker["mb_per_minute"] = None
                        elif worker["error"] and worker["working"] is True:
                            worker["working"] = False
                    if not current or result["working"] is None or any(row["working"] is None for row in result["workers"]):
                        result["working"] = None
                    else:
                        result["working"] = sum(row["working"] is True for row in result["workers"])
                    result["minutes"] = []
                    for row in source.get("minutes", []):
                        minute = {field: row.get(field) for field in ("minute_ms", "mb", "partial", "estimated", "count", "coverage_complete")}
                        minute["nodes"] = [{field: node.get(field) for field in ("instance", "ip", "country", "mb")} for node in row.get("nodes", [])]
                        result["minutes"].append(minute)
                    self.send_json(200, result)
                    return
                if parsed.path == "/api/proxyrack":
                    from proxyrack import public_snapshot
                    try:
                        result = public_snapshot()
                    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
                        self.send_json(503, {"error": "PR recorder data is not available yet"})
                    else:
                        self.send_json(200, result)
                    return
                if parsed.path == "/api/traffmonetizer":
                    from dashboard.traffmonetizer import snapshot
                    path = Path.home() / ".hg1/traffmonetizer/latest.json"
                    self.send_json(200, snapshot(read_view(path) if path.exists() else None))
                    return
                if parsed.path in ("/api/earnfm", "/ef.json", "/earnfm.json"):
                    path = Path.home()/".hg1/earnfm/view.json"
                    result=read_view(path) if path.exists() else {"error":"EarnFM recorder has not published data yet", "desired":10,"workers":[],"points":[]}
                    self.send_json(200,result)
                    return
                if parsed.path == "/api/repocket":
                    data_dir = Path.home() / ".hg1" / "repocket"
                    result = dict(read_view(data_dir / "view.json"))
                    if "provider" not in result and (data_dir / "provider.json").exists():
                        result["provider"] = read_view(data_dir / "provider.json")
                    if "chart_minutes" not in result and parse_qs(parsed.query).get("chart")==["1"] and (data_dir/"traffic.sqlite3").exists():
                        now=int(time.time()*1000); first=now//60000*60000-1439*60000
                        with closing(sqlite3.connect("file:"+str(data_dir/"traffic.sqlite3")+"?mode=ro",uri=True)) as db:
                            db.execute("BEGIN")
                            raw=[json.loads(row[0]) for row in db.execute("SELECT body FROM events WHERE kind='minute' AND time_ms>=?",(first,))]
                            total=db.execute("SELECT SUM(json_extract(body,'$.rx_bytes')+json_extract(body,'$.tx_bytes')),MIN(json_extract(body,'$.start_ms')) FROM events WHERE kind='minute' AND json_extract(body,'$.rx_bytes')>=0 AND json_extract(body,'$.tx_bytes')>=0").fetchone()
                        records=[]
                        for row in raw:
                            if row.get("rx_bytes") is None or row.get("tx_bytes") is None or row["rx_bytes"]<0 or row["tx_bytes"]<0:continue
                            record={"start_ms":row["start_ms"],"end_ms":row["end_ms"],"rx":row["rx_bytes"],"tx":row["tx_bytes"],"bucket_ms":None,"instance":row["instance"],"machine":row["machine"],"ip":row.get("ip")}
                            bucket=round(row["start_ms"]/60000)*60000
                            if not row.get("partial") and 59000<=row["end_ms"]-row["start_ms"]<=61000 and abs(row["start_ms"]-bucket)<=1000:
                                record.update(start_ms=bucket,end_ms=bucket+60000,bucket_ms=bucket)
                            records.append(record)
                        result["chart_minutes"]=bucket_minutes(records,first,now//60000*60000)
                        for point in result["chart_minutes"]:point["partial"]|=point["count"]<result["desired"]
                        result["total_network_mb"]=total[0]/1e6 if total[0] is not None else None
                        result["test_started_ms"]=total[1]
                    self.send_json(200, result)
                    return
                if parsed.path == "/api/ps1/minutes" and minute_view is not None:
                    query = parse_qs(parsed.query)
                    census = read_view(minute_view.path.parent / "native-census.json")
                    selected = int(query["minute"][0]) if "minute" in query else None
                    if selected is not None and (selected < 0 or selected % 60000):
                        raise ValueError("Invalid selected minute")
                    self.send_json(200, minute_view.minute(census.get("group_id", ""), selected) if selected is not None else minute_view.snapshot(census))
                    return
                if parsed.path in ("/api/fleet-test", "/api/fleet-test/export.json", "/api/fleet-test/export.csv"):
                    archive = parse_qs(parsed.query).get("archive", [None])[0]
                    result = fleet_view.snapshot(archive=archive, include_observations=parsed.path.endswith(".json"), honeygain_only=parse_qs(parsed.query).get("service") == ["hg"])
                    if parsed.path.endswith(".csv"):
                        self.send_bytes(200, fleet_csv(result), "text/csv; charset=utf-8", 'attachment; filename="independent-fleet-test.csv"')
                    else:
                        self.send_json(200, result, 'attachment; filename="independent-fleet-test.json"' if parsed.path.endswith(".json") else "")
                    return
                if parsed.path == "/api/ps1/view" and ps_view is not None:
                    query = parse_qs(parsed.query)
                    start = int(query["start"][0]) if "start" in query else None
                    end = int(query["end"][0]) if "end" in query else None
                    if start is not None and (start < 0 or (end is not None and end <= start)):
                        raise ValueError("Invalid period")
                    result = ps_view.snapshot({}, start, end)
                    provider_path = Path.home() / ".hg1/packetstream/provider.json"
                    result["provider"] = None
                    try:
                        provider = read_view(provider_path)
                        fields = ("observed_ms", "checked_ms", "balance_usd", "balance_text", "rolling_bytes", "days", "scope", "source", "provider_updated_ms", "poll_interval_seconds", "last_changed_ms", "error", "requires_login")
                        result["provider"] = {key: provider[key] for key in fields if key in provider}
                    except (OSError, ValueError, TypeError):
                        result["provider_error"] = "PacketStream account reading is unavailable"
                    self.send_json(200, result)
                    return
                if parsed.path in ("/api/ps1/status", "/api/ps1/history"):
                    if parsed.path.endswith("/history") and int(parse_qs(parsed.query).get("after", ["0"])[0]) < 0:
                        raise ValueError("after must be a non-negative integer")
                    self.send_json(503, {"error": "PS1 recorder is unavailable"})
                    return
                if parsed.path == "/api/status":
                    result = store.status()
                    result.update(status_provider())
                    last_sample_ms = result.get("last_sample_ms")
                    result["source_lag_ms"] = (
                        max(0, int(time.time() * 1000) - int(last_sample_ms))
                        if last_sample_ms is not None
                        else None
                    )
                    self.send_json(200, result)
                    return
                if parsed.path == "/api/boxes":
                    start, end, _bucket = query_window(parse_qs(parsed.query))
                    self.send_json(200, store.query_boxes(start, end, expected_reporters=expected_reporters))
                    return
                if parsed.path == "/api/events":
                    start, end, _bucket = query_window(parse_qs(parsed.query))
                    self.send_json(200, store.query_events(start, end))
                    return
                if parsed.path in ("/api/series", "/api/export.csv", "/api/export.json"):
                    start, end, bucket = query_window(parse_qs(parsed.query))
                    result = store.query_range(start, end, bucket)
                    if parsed.path == "/api/export.csv":
                        self.send_bytes(200, csv_export(result), "text/csv; charset=utf-8", 'attachment; filename="salad-bandwidth.csv"')
                    elif parsed.path == "/api/export.json":
                        self.send_json(200, result, 'attachment; filename="salad-bandwidth.json"')
                    else:
                        self.send_json(200, result)
                    return
                redirects = {"/overview.html": "/overview", "/rp": "/repocket", "/rp.html": "/repocket",
                             "/repocket.html": "/repocket", "/proxyrack.html": "/proxyrack", "/earnfm.html": "/earnfm",
                             "/tm": "/traffmonetizer", "/tm.html": "/traffmonetizer", "/traffmonetizer.html": "/traffmonetizer",
                             "/pawns": "/pawns-app", "/pawns.html": "/pawns-app",
                             "/grass.html": "/grass", "/ef": "/earnfm/details"}
                destination = redirects.get(parsed.path)
                if destination:
                    self.send_response(308)
                    self.send_header("Location", destination + ("?" + parsed.query if parsed.query else ""))
                    self.send_header("Content-Length", "0")
                    self.headers_common()
                    self.end_headers()
                    return
                files = {"/": "index.html", "/index.html": "index.html", "/app.js": "app.js", "/ps1.js": "ps1.js", "/fleet-test.js": "fleet-test.js", "/styles.css": "styles.css"}
                files.update({"/overview": "overview.html", "/earnfm/details": "earnfm.html", "/favicon.svg": "favicon.svg",
                              "/salad-logo.svg": "salad-logo.svg", "/InterVariable.woff2": "InterVariable.woff2",
                              "/JetBrainsMono-Regular.woff2": "JetBrainsMono-Regular.woff2"})
                files.update({path: "index.html" for path in ("/honeygain", "/packetstream", "/proxyrack", "/repocket",
                              "/earnfm", "/traffmonetizer", "/pawns-app", "/grass")})
                filename = files.get(parsed.path)
                if filename is None:
                    self.send_json(404, {"error": "not found"})
                    return
                body, version = read_asset(filename)
                if filename == "index.html":
                    for asset in ("styles.css", "ps1.js", "fleet-test.js"):
                        _, asset_version = read_asset(asset)
                        body = body.replace(('"/' + asset + '"').encode(), ('"/' + asset + '?v=' + asset_version + '"').encode())
                    version = hashlib.sha256(body).hexdigest()
                self.response_etag = '"' + version + '"'
                self.response_cache = "private, max-age=31536000, immutable" if parse_qs(parsed.query).get("v") == [version] else "private, no-cache"
                if self.headers.get("If-None-Match") in (self.response_etag, "W/" + self.response_etag):
                    self.send_response(304)
                    self.headers_common()
                    self.end_headers()
                    return
                content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                self.send_bytes(200, body, content_type + ("; charset=utf-8" if content_type.startswith("text/") or content_type.endswith("javascript") else ""))
            except ValueError as exc:
                self.send_json(400, {"error": str(exc)})
            except FileNotFoundError:
                self.send_json(404, {"error": "dashboard asset not found"})
            except Exception:
                self.send_json(500, {"error": "internal dashboard error"})

        def do_POST(self):  # noqa: N802
            if self.path != "/api/ps1/credited" or ps_view is None:
                self.send_json(404, {"error": "not found"})
                return
            if self.headers.get("X-PS-Token") != ps_view.token or self.headers.get("Origin") != "https://salad.cosmosgeek.org" or self.headers.get_content_type() != "application/json":
                self.send_json(403, {"error": "Dashboard authentication required"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 2048:
                    raise ValueError("Invalid reading size")
                ps_view.ingest(json.loads(self.rfile.read(size)))
                self.send_json(200, {"ok": True})
            except (ValueError, TypeError, KeyError):
                self.send_json(400, {"error": "Invalid provider reading"})

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path.home() / ".hg1")
    args = parser.parse_args()

    store = Store(args.data_dir / "bandwidth.sqlite3", read_only=True)
    ps_runtime = args.data_dir / "packetstream"
    ps_view = PacketStreamView(ps_runtime)
    minute_view = NetworkMinutes(ps_runtime / "minutes.sqlite3", read_only=True)
    expected_reporters = max(1, int(os.environ.get("SALAD_EXPECTED_REPORTERS", "10")))
    handler = make_handler(store, lambda: {"poll_state": "disabled"}, Path(__file__).parent / "static",
                           ps_view, expected_reporters, minute_view=minute_view,
                           trusted_uid=pwd.getpwnam("cloudflared-salad").pw_uid)
    server = DashboardServer(SOCKET_PATH, handler)
    server.daemon_threads = True
    os.chmod(SOCKET_PATH, 0o660)

    def stop_server(_signum, _frame):
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop_server)
    signal.signal(signal.SIGINT, stop_server)
    print(f"dashboard: unix://{SOCKET_PATH}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        Path(SOCKET_PATH).unlink(missing_ok=True)
        minute_view.db.close()
        store.close()


if __name__ == "__main__":
    main()
