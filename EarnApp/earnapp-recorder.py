#!/usr/bin/env python3
"""Record EarnApp traffic, native health, provider credits and recovery outcomes."""
import argparse
import base64
from datetime import datetime, timezone
import fcntl
import getpass
import ipaddress
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get("EARNAPP_DATA_DIR", str(ROOT / "data")))
ORG = os.environ.get("EARNAPP_ORGANIZATION", "cosmosgeeketh")
PROJECT = os.environ.get("EARNAPP_PROJECT", "default")
GROUP = os.environ.get("EARNAPP_GROUP", "earnapp-live")
DEVICE = os.environ.get("EARNAPP_UUID", "sdk-node-f529f336e6a94edaa4c7c4d23fa0d355")
SALAD = "https://api.salad.com/api/public/organizations/" + ORG
HELPER = os.environ.get("SALAD_KEY_HELPER", str(Path.home() / "Library/Application Support/Salad Bandwidth Dashboard/.runtime/keychain-store"))
OFFLINE_MS = 120000
SAMPLE_AGE_MS = 150000


def stamp(value):
    value = re.sub(r"\.(\d+)", lambda m: "." + m.group(1)[:6].ljust(6, "0"), value, count=1)
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)


def iso(value):
    return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def request(url, headers, body=None, method=None, accepted=(200,)):
    config = "".join("header = " + json.dumps(k + ": " + v) + "\n"
                     for k, v in dict({"Content-Type": "application/json"}, **headers).items())
    if body is not None:
        config += "data-binary = " + json.dumps(json.dumps(body)) + "\n"
    reply = subprocess.run(["curl", "-sS", "--max-time", "20", "--config", "-", "--write-out", "\n%{http_code}",
                            "--request", method or ("POST" if body is not None else "GET"), url],
                           input=config, text=True, capture_output=True, timeout=25)
    raw, _, status = reply.stdout.rpartition("\n")
    if reply.returncode or not status.isdigit() or int(status) not in accepted:
        raise RuntimeError(urlsplit(url).hostname + " request failed (HTTP " + (status or "unavailable") + ")")
    return json.loads(raw) if raw.strip() else {}


def read_meta(db, key, default=None):
    row = db.execute("SELECT body FROM meta WHERE key=?", (key,)).fetchone()
    return json.loads(row[0]) if row else default


def save_meta(db, key, body):
    db.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (key, json.dumps(body)))


def fetch_logs(key, start, end):
    query = ('resource.type = "container" and resource.labels.project_name = "' + PROJECT +
             '" and resource.labels.container_group_name = "' + GROUP +
             '" and (text_log startswith "EARNAPP_SAMPLE " or text_log startswith "EARNAPP_EVENT "'
             ' or text_log contains "Failed registration" or text_log contains "EAI_AGAIN" or text_log contains "Registered")')
    rows = request(SALAD + "/log-entries", {"Salad-Api-Key": key},
                   {"query": query, "start_time": iso(start), "end_time": iso(end), "page_size": 100, "sort_order": "asc"})["items"]
    if len(rows) < 100:
        return rows
    if end - start <= 1:
        raise RuntimeError("Salad log page is full at a single timestamp")
    middle = (start + end) // 2
    return fetch_logs(key, start, middle) + fetch_logs(key, middle, end)


def provider_read(db):
    now = int(time.time() * 1000)
    if now - read_meta(db, "provider_check", {}).get("checked_ms", 0) < 60000:
        return
    credit_error = status_error = None
    try:
        if os.environ.get("EARNAPP_COOKIE"):
            session = {"cookie": os.environ["EARNAPP_COOKIE"], "xsrf_token": os.environ["EARNAPP_XSRF_TOKEN"]}
        else:
            session = json.loads(subprocess.check_output(
                [HELPER, "--read", "--service", "earnapp-read-session", "--account", getpass.getuser()],
                text=True, stderr=subprocess.PIPE))
        headers = {"Cookie": session["cookie"], "xsrf-token": session["xsrf_token"], "X-Requested-With": "XMLHttpRequest"}
    except Exception:
        with db:
            save_meta(db, "provider_check", {"checked_ms": now, "credit_error": "Saved EarnApp session unavailable",
                                           "status_error": "Saved EarnApp session unavailable"})
        return
    try:
        devices = request("https://earnapp.com/dashboard/api/devices", headers)
        device = next((d for d in devices if d["uuid"] == DEVICE), None)
        if device is None:
            raise RuntimeError("The saved EarnApp device is absent from the signed-in account")
        safe = {"uuid": DEVICE, "observed_ms": int(time.time() * 1000), "earned_total": device["earned_total"],
                "usage_ms": device["total_uptime"], "ips": device["ips"],
                "rate": device.get("rate"), "billing": device.get("billing")}
        if any(type(safe[k]) not in (int, float) or not 0 <= safe[k] < 2**53 for k in ("earned_total", "usage_ms")):
            raise RuntimeError("Invalid EarnApp provider amount")
        with db:
            db.execute("INSERT OR IGNORE INTO provider VALUES (?,?,?)", (DEVICE, safe["observed_ms"], json.dumps(safe)))
    except Exception as exc:
        credit_error = str(exc) if isinstance(exc, RuntimeError) else "Provider credit reading failed: " + type(exc).__name__
    try:
        if credit_error:
            raise RuntimeError("Device membership not verified: " + credit_error)
        statuses = request("https://earnapp.com/dashboard/api/device_statuses?appid=earnapp&version=1.664.512",
                           headers, {"devices": [{"uuid": DEVICE}]})
        if not isinstance(statuses, dict) or "error" in statuses:
            raise RuntimeError("Invalid EarnApp status response")
        status = statuses.get(DEVICE)
        if status is not None and status is not False and status != 0 and not isinstance(status, list):
            raise RuntimeError("Invalid EarnApp device status")
        since = status[0] if isinstance(status, list) and status else None
        if since and (type(since) not in (int, float) or not 0 < since < 2**53):
            raise RuntimeError("Invalid EarnApp online time")
        with db:
            save_meta(db, "provider_status", {"uuid": DEVICE, "observed_ms": int(time.time() * 1000),
                                            "online": bool(since), "online_since_ms": since or None})
    except Exception as exc:
        status_error = str(exc) if isinstance(exc, RuntimeError) else "Provider status reading failed: " + type(exc).__name__
    with db:
        save_meta(db, "provider_check", {"checked_ms": now, "credit_error": credit_error, "status_error": status_error})


def record_event(db, row, received_ms, source="native"):
    identity = (row["group_id"], row["instance"], row["observer"], source, row["seq"])
    body = json.dumps(row, sort_keys=True)
    old = db.execute("SELECT body FROM events WHERE group_id=? AND instance=? AND observer=? AND source=? AND seq=?", identity).fetchone()
    if old:
        if json.loads(old[0]) != row:
            raise RuntimeError("Conflicting EarnApp event with the same run and sequence")
    else:
        db.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?)",
                   identity + (row["time_ms"], row["kind"], body, received_ms))
    if row["kind"] not in ("requested", "accepted", "request_failed", "fallback"):
        return
    key = "recovery:" + row["group_id"] + ":" + row["instance"] + ":" + str(row["observer"])
    recovery = read_meta(db, key, {"instance": row["instance"], "machine": row["machine"], "observer": row["observer"],
                                  "origin": source, "first_event_ms": row["time_ms"], "attempts": 0})
    if row["kind"] == "requested":
        recovery.setdefault("requested_ms", row["time_ms"])
    recovery["attempts"] = db.execute("SELECT COUNT(*) FROM events WHERE group_id=? AND instance=? AND observer=? AND kind='requested'", identity[:3]).fetchone()[0]
    latest = json.loads(db.execute("SELECT body FROM events WHERE group_id=? AND instance=? AND observer=? AND source=? "
                                  "AND kind IN ('requested','accepted','request_failed','fallback') ORDER BY seq DESC LIMIT 1", identity[:4]).fetchone()[0])
    if source == recovery.get("updated_source", recovery["origin"]) or latest["time_ms"] >= recovery.get("updated_ms", 0):
        recovery.update(state=latest["kind"], reason=latest["reason"], updated_ms=latest["time_ms"],
                        updated_source=source, updated_seq=latest["seq"],
                        http_status=latest.get("http_status"), error=latest.get("error"))
        if latest["kind"] == "accepted":
            recovery["accepted_ms"] = latest["time_ms"]
    save_meta(db, key, recovery)


def ingest(db, items, group_id, received_ms):
    for item in items:
        labels = item.get("resource", {}).get("labels", {})
        line = item.get("text_log", "")
        prefix = next((p for p in ("EARNAPP_SAMPLE ", "EARNAPP_EVENT ") if line.startswith(p)), None)
        if prefix is None:
            message = ("EarnApp registration failed" if "Failed registration" in line else
                       "EarnApp DNS lookup failed (EAI_AGAIN)" if "EAI_AGAIN" in line else None)
            if message or "Registered" in line:
                at = stamp(item["time"])
                key = "client:" + group_id + ":" + labels.get("machine_id", "")
                if at >= read_meta(db, key, {}).get("time_ms", 0):
                    save_meta(db, key, {"time_ms": at, "error": message, "registered": message is None,
                                       "log_instance": labels.get("instance_id")})
            continue
        row = json.loads(line[len(prefix):])
        if row["group_id"] != group_id:
            continue
        if not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", row["instance"]) or row["machine"] != labels.get("machine_id"):
            raise RuntimeError("Invalid EarnApp runtime identity or machine mismatch")
        fields = ("observer", "seq", "time_ms") if prefix == "EARNAPP_EVENT " else ("observer", "seq", "start_ms", "end_ms", "raw_rx", "raw_tx")
        for field in fields:
            if type(row[field]) is not int or not 0 <= row[field] < 2**53:
                raise RuntimeError("Invalid EarnApp counter or timestamp: " + field)
        if prefix == "EARNAPP_EVENT ":
            if not 0 < row["time_ms"] <= received_ms + 60000:
                raise RuntimeError("Invalid EarnApp event time")
            record_event(db, row, received_ms)
            continue
        if row.get("valid", True) and not 0 < row["start_ms"] <= row["end_ms"] <= received_ms + 60000:
            raise RuntimeError("Invalid EarnApp source interval")
        if row.get("valid", True) and any(type(row[k]) is not int or not 0 <= row[k] < 2**53 for k in ("rx", "tx")):
            raise RuntimeError("Invalid EarnApp interval bytes")
        if "event_seq" in row and (type(row["event_seq"]) is not int or not -1 <= row["event_seq"] < 2**53):
            raise RuntimeError("Invalid EarnApp sample event sequence")
        geo = row.get("geo") or {}
        row["ip"] = str(ipaddress.ip_address(geo["ip"])) if geo.get("ip") else None
        row["country"] = geo.get("country") if re.fullmatch("[A-Z]{2}", geo.get("country") or "") else None
        row["log_instance"] = labels.get("instance_id")
        row["log_version"] = labels.get("container_group_version")
        row["log_time_ms"] = stamp(item["time"])
        body = json.dumps(row, sort_keys=True)
        identity = (group_id, row["instance"], row["observer"], row["seq"])
        old = db.execute("SELECT body FROM samples WHERE group_id=? AND instance=? AND observer=? AND seq=?", identity).fetchone()
        if old and old[0] != body:
            raise RuntimeError("Conflicting EarnApp record with the same run and sequence")
        db.execute("INSERT OR IGNORE INTO samples VALUES (?,?,?,?,?,?,?,?)",
                   identity + (row["start_ms"], row["end_ms"], body, received_ms))


def minute_points(rows, now):
    points = {}
    for row in rows:
        start, end = row["start_ms"], row["end_ms"]
        if row["seq"] == 0 or end <= start or not row.get("valid", True):
            continue
        for minute in range(max(start // 60000 * 60000, now // 60000 * 60000 - 1439 * 60000),
                            min((end - 1) // 60000 * 60000, now // 60000 * 60000) + 1, 60000):
            overlap = min(end, minute + 60000) - max(start, minute)
            if overlap <= 0:
                continue
            point = points.setdefault(minute, {"minute_ms": minute, "mb": 0, "estimated": False, "nodes": {}})
            amount = (row["rx"] + row["tx"]) / 1e6 * overlap / (end - start)
            point["mb"] += amount
            point["estimated"] |= start < minute or end > minute + 60000
            key = (row["instance"], row["observer"], row["ip"])
            node = point["nodes"].setdefault(key, {"instance": row["instance"], "ip": row["ip"], "country": row["country"],
                                                  "mb": 0, "duration_ms": 0})
            node["mb"] += amount
            node["duration_ms"] += overlap
    for point in points.values():
        nodes = list(point["nodes"].values())
        point.update(partial=point["minute_ms"] + 60000 > now or any(n["duration_ms"] < 60000 for n in nodes),
                     count=len(nodes), nodes=[{k: v for k, v in n.items() if k != "duration_ms"} for n in nodes])
    return list(points.values())


def snapshot(db, inventory, error):
    now = int(time.time() * 1000)
    group_id = inventory.get("group_id")
    records = db.execute("SELECT body FROM samples WHERE group_id=? AND end_ms>=? ORDER BY end_ms,seq",
                         (group_id, now - 86400000)).fetchall()
    rows = [json.loads(r[0]) for r in records]
    valid = "seq>0 AND COALESCE(json_extract(body,'$.valid'),1)=1"
    summaries = db.execute("SELECT instance,observer,SUM(json_extract(body,'$.rx')+json_extract(body,'$.tx')),"
                           "SUM(end_ms-start_ms),MIN(start_ms) FROM samples WHERE group_id=? AND " + valid +
                           " GROUP BY instance,observer", (group_id,)).fetchall()
    summaries = {(r[0], r[1]): r[2:] for r in summaries}
    totals = db.execute("SELECT SUM(json_extract(body,'$.rx')),SUM(json_extract(body,'$.tx')),MIN(start_ms) "
                        "FROM samples WHERE group_id=? AND " + valid, (group_id,)).fetchone()
    total_mb = (totals[0] + totals[1]) / 1e6 if totals[0] is not None else None
    saved = db.execute("SELECT body FROM provider WHERE uuid=? ORDER BY observed_ms DESC LIMIT 1", (DEVICE,)).fetchone()
    provider = json.loads(saved[0]) if saved else {}
    status = read_meta(db, "provider_status", {})
    checks = read_meta(db, "provider_check", {})
    status_fresh = not checks.get("status_error", checks.get("error")) and status.get("uuid") == DEVICE and 0 <= now - status.get("observed_ms", 0) <= SAMPLE_AGE_MS
    fresh_inventory = 0 <= now - inventory.get("inventory_ms", 0) <= 90000 and not error
    workers = []
    for member in inventory.get("workers", []):
        record = db.execute("SELECT body,received_ms FROM samples WHERE group_id=? AND instance=? ORDER BY observer DESC,seq DESC LIMIT 1",
                            (group_id, member["id"])).fetchone()
        row = dict(json.loads(record[0]), recorded_ms=record[1]) if record else None
        event_record = db.execute("SELECT body FROM events WHERE group_id=? AND instance=? AND source='native' "
                                  "ORDER BY observer DESC,seq DESC LIMIT 1", (group_id, member["id"])).fetchone()
        event = json.loads(event_record[0]) if event_record else None
        if row and event:
            if event["observer"] > row["observer"]:
                row = None
            elif event["observer"] < row["observer"] or (
                    event["seq"] <= row["event_seq"] if "event_seq" in row else
                    event["time_ms"] <= row["end_ms"] or event["kind"] == "registered"):
                event = None
        observer = row["observer"] if row else event["observer"] if event else None
        expires = row["end_ms"] + SAMPLE_AGE_MS if row else None
        fresh = row is not None and row["end_ms"] <= now + 10000 and now <= expires
        state = row.get("state") if row else None
        native_error = row.get("error") if row and row.get("error") not in (None, "none") else None
        final = bool(row and row.get("final"))
        if event:
            state = {"error": "dns_error", "client_exited": "stopped", "requested": "reallocating",
                     "accepted": "reallocating", "request_failed": "reallocating", "fallback": "reallocating"}.get(event["kind"], event["kind"])
            native_error = None if state in ("starting", "registered") else event["reason"]
            final |= state in ("stopped", "reallocating")
        if row and state is None:
            legacy = read_meta(db, "client:" + group_id + ":" + member["machine_id"], {})
            if legacy.get("log_instance") == member["id"] and legacy.get("time_ms", 0) >= row["observer"] and legacy.get("error"):
                native_error = legacy["error"]
        geo = row if row else (event.get("geo") or {}) if event else {}
        ip, country = geo.get("ip"), geo.get("country")
        health_fresh = fresh or bool(event and event["time_ms"] <= now + 10000 and now <= event["time_ms"] + SAMPLE_AGE_MS)
        running_process = bool(fresh and row["process"] == "earnapp" and not final)
        native_registered = bool(running_process and state == "registered" and not native_error)
        description = {"starting": "Registering EarnApp", "registered": "Native registered",
                       "country_unverified": "Country lookup failed; retrying",
                       "dns_error": "DNS lookup failed; retrying", "reallocating": "Reallocating", "stopped": "Stopped"}.get(state)
        description = description or ("Process running; provider connection unverified" if running_process else
                                      "Traffic observation stale" if row else "Waiting for first native sample")
        working = False if final or native_error or member["state"] not in ("creating", "running") else None
        registered_at = row.get("registered_ms", 0) if row else 0
        if event and event["kind"] == "registered":
            registered_at = event["time_ms"]
        provider_current = status_fresh and status.get("observed_ms", 0) >= registered_at - 10000
        if fresh_inventory and fresh and member["state"] in ("creating", "running") and not final and not native_error and provider_current:
            if native_registered and status["online"]:
                description, working = "Native registered; provider online", True
            elif status["online"] is False and running_process:
                description, working = "Provider reports device offline", False
        if native_registered and not status_fresh:
            description = "Native registered; provider status unavailable"
        if country and country != "US":
            description, working, native_error = "Non-US IP; replacement required", False, "country_not_us"
        if not fresh_inventory or not health_fresh:
            working = None
        period = row["end_ms"] - row["start_ms"] if row else 0
        summary = summaries.get((member["id"], row["observer"])) if row else None
        workers.append({"id": member["id"], "machine": member["machine_id"], "ip": ip,
                        "country": country, "client_status": description,
                        "salad_state": member["state"], "working": working, "native_state": state, "native_registered": native_registered,
                        "mb_per_minute": (row["rx"] + row["tx"]) / 1e6 * 60000 / period if fresh and not final and row.get("valid", True) and row["seq"] and period > 0 else None,
                        "total_mb": summary[0] / 1e6 if summary else None,
                        "recorded_duration_ms": summary[1] if summary else None,
                        "recorded_ms": row["recorded_ms"] if row else None, "sample_ms": row["end_ms"] if row else None,
                        "observer_ms": observer, "sample_expires_ms": expires,
                        "registered_ms": registered_at, "client_pid": row.get("client_pid") if row else None,
                        "deadline_ms": row.get("deadline_ms") if row else None, "final": final,
                        "error": native_error, "note": None})
    minutes = minute_points(rows, now)
    for point in minutes:
        point["partial"] |= point["count"] < inventory.get("desired", 0)
    note = ("Provider device totals cover every IP used by this UUID. " +
            ("Last credit observation " + iso(provider["observed_ms"]) + ". " if provider else "Credit reading unavailable. ") +
            "Provider credited bandwidth is not reported; no per-GB conversion is published. Network totals include all captured countries and retained runs.")
    if checks.get("credit_error"):
        note += " Credit refresh error: " + checks["credit_error"] + "."
    if checks.get("status_error", checks.get("error")):
        note += " Status refresh error: " + checks.get("status_error", checks.get("error")) + "."
    return {"generated_ms": now, "inventory_ms": inventory.get("inventory_ms"), "group_id": group_id,
            "desired": inventory.get("desired"), "running": sum(w["salad_state"] == "running" for w in workers) if fresh_inventory else None,
            "working": sum(w["working"] is True for w in workers) if fresh_inventory and all(w["working"] is not None for w in workers) else None,
            "started_ms": totals[2], "total_mb": total_mb, "all_recorded_mb": total_mb,
            "received_mb": totals[0] / 1e6 if totals[0] is not None else None,
            "sent_mb": totals[1] / 1e6 if totals[1] is not None else None,
            "credited_text": None,
            "earned_text": "$" + format(provider["earned_total"], ".3f") + " device total" if provider else None,
            "credit_note": note, "provider_observed_ms": provider.get("observed_ms"),
            "basis": "Recorded container RX + TX across retained runs and countries. Includes overhead; excludes traffic before the first counter baseline, including setup downloads. Source intervals are split into estimated minute contributions.",
            "error": error, "workers": workers, "minutes": minutes}


def recover(db, view, key, enabled=True):
    now = int(time.time() * 1000)
    group_id = view["group_id"]
    if not group_id:
        return
    workers = view["workers"]
    current_ids = {w["id"] for w in workers}
    with db:
        for worker in workers:
            seen_key = "seen:" + group_id + ":" + worker["id"]
            if read_meta(db, seen_key) is None:
                save_meta(db, seen_key, {"time_ms": now})
        histories = db.execute("SELECT key,body FROM meta WHERE key GLOB ?", ("recovery:" + group_id + ":*",)).fetchall()
        for rec_key, body in histories:
            recovery = json.loads(body)
            if recovery.get("verified_ms") or recovery.get("replacement_lost_ms") or recovery["instance"] in current_ids:
                continue
            if not recovery.get("replacement_instance"):
                candidates = [w for w in workers if read_meta(db, "seen:" + group_id + ":" + w["id"])["time_ms"] >= recovery["first_event_ms"]]
                if len(candidates) == 1:
                    replacement = candidates[0]
                    recovery.update(replacement_instance=replacement["id"], replacement_machine=replacement["machine"], replacement_seen_ms=now)
            replacement = next((w for w in workers if w["id"] == recovery.get("replacement_instance")), None)
            if replacement and replacement["working"] is True:
                recovery["verified_ms"] = now
            elif recovery.get("replacement_instance") and not replacement and not view["error"]:
                recovery["replacement_lost_ms"] = now
            save_meta(db, rec_key, recovery)
    saved = db.execute("SELECT body FROM provider WHERE uuid=? ORDER BY observed_ms DESC LIMIT 1", (DEVICE,)).fetchone()
    provider = json.loads(saved[0]) if saved else {}
    checks, status = read_meta(db, "provider_check", {}), read_meta(db, "provider_status", {})
    fresh_view = not view["error"] and 0 <= now - (view["inventory_ms"] or 0) <= 90000 and len(workers) == 1
    for worker in workers:
        if not worker["observer_ms"] or worker["native_state"] is None:
            worker["note"] = "Waiting for the supervised client and its first source sample."
            continue
        policy_key = "policy:" + group_id + ":" + worker["id"] + ":" + str(worker["observer_ms"])
        policy = read_meta(db, policy_key, {})
        reason = None
        meter_fresh = worker["sample_ms"] is not None and worker["sample_ms"] <= now + 10000 and now <= worker["sample_expires_ms"] and not worker["final"]
        credit_fresh = not checks.get("credit_error", checks.get("error")) and provider.get("uuid") == DEVICE and 0 <= now - provider.get("observed_ms", 0) <= SAMPLE_AGE_MS and provider["observed_ms"] >= worker["observer_ms"] - 10000
        status_fresh = not checks.get("status_error", checks.get("error")) and status.get("uuid") == DEVICE and 0 <= now - status.get("observed_ms", 0) <= SAMPLE_AGE_MS and status.get("observed_ms", 0) >= worker["registered_ms"] - 10000
        native_ok = worker["native_registered"] and not worker["error"] and worker["salad_state"] == "running"
        if not (fresh_view and meter_fresh and native_ok and status_fresh):
            policy.pop("offline_since_ms", None)
        if fresh_view and meter_fresh and native_ok:
            if status_fresh and status["online"] is False:
                policy.setdefault("offline_since_ms", status["observed_ms"])
                if status["observed_ms"] - policy["offline_since_ms"] >= OFFLINE_MS:
                    reason = "provider_offline"
            elif status_fresh and status["online"]:
                policy.pop("offline_since_ms", None)
            if credit_fresh:
                before = policy.get("earned_total")
                usage = policy.get("usage_ms")
                if before is None or provider["earned_total"] != before or provider["usage_ms"] != usage:
                    policy["credit_progress_ms"] = provider["observed_ms"]
                policy.update(earned_total=provider["earned_total"], usage_ms=provider["usage_ms"],
                              provider_observed_ms=provider["observed_ms"])
        with db:
            save_meta(db, policy_key, policy)
        if worker["error"] or worker["native_state"] != "registered":
            worker["note"] = "Native supervisor handles this state; its recovery events are retained."
        elif worker["salad_state"] != "running":
            worker["note"] = "Provider recovery paused while Salad is " + worker["salad_state"] + "."
        elif not fresh_view or not meter_fresh:
            worker["note"] = "Automatic provider recovery paused: current inventory or native sample is unavailable."
        elif policy.get("offline_since_ms") and status_fresh:
            remaining = max(0, OFFLINE_MS - (status["observed_ms"] - policy["offline_since_ms"]))
            worker["note"] = "Provider offline; US replacement due in " + str((remaining + 999) // 1000) + " s."
        elif not credit_fresh:
            worker["note"] = "Provider credits unavailable; healthy client stays running."
        elif policy.get("credit_progress_ms"):
            elapsed = max(0, provider["observed_ms"] - policy["credit_progress_ms"])
            worker["note"] = "Provider credits unchanged for " + str(elapsed // 60000) + " min; healthy client stays running."
        rec_key = "recovery:" + group_id + ":" + worker["id"] + ":" + str(worker["observer_ms"])
        previous = read_meta(db, rec_key)
        if previous:
            worker["note"] = "US replacement request " + previous["state"] + " · " + previous["reason"]
        if not reason or not enabled or not fresh_view or not meter_fresh:
            continue
        if previous and (previous["origin"] == "native" or previous.get("accepted_ms") or previous["attempts"] >= 3 or now - previous["updated_ms"] < 15000):
            continue
        sequence = db.execute("SELECT COALESCE(MAX(seq),-1)+1 FROM events WHERE group_id=? AND instance=? AND observer=? AND source='recorder'",
                              (group_id, worker["id"], worker["observer_ms"])).fetchone()[0]
        action = {"group_id": group_id, "instance": worker["id"], "machine": worker["machine"],
                  "observer": worker["observer_ms"], "seq": sequence, "time_ms": now,
                  "kind": "requested", "reason": reason, "http_status": None}
        with db:
            record_event(db, action, now, "recorder")
        try:
            request(SALAD + "/projects/" + PROJECT + "/containers/" + GROUP + "/instances/" + worker["id"] + "/reallocate",
                    {"Salad-Api-Key": key}, method="POST", accepted=(202,))
            action.update(kind="accepted", http_status=202)
        except Exception as exc:
            action.update(kind="request_failed", error=str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__)
        action.update(seq=sequence+1, time_ms=int(time.time()*1000))
        with db:
            record_event(db, action, action["time_ms"], "recorder")
        worker["note"] = "US replacement request " + ("accepted" if action["kind"] == "accepted" else "failed: " + action["error"]) + " · " + reason
    history = [json.loads(row[0]) for row in db.execute("SELECT body FROM meta WHERE key GLOB ?", ("recovery:" + group_id + ":*",))]
    view["recoveries"] = sorted(history, key=lambda r: r["first_event_ms"], reverse=True)[:20]
    view["credit_note"] += " Recovery policy: native exit/registration failure requests replacement; native connection/DNS deadline 120 s; provider offline 120 s. Low traffic or unchanged credits do not replace a healthy client."
    if view["recoveries"]:
        latest = view["recoveries"][0]
        view["credit_note"] += " Last recovery: " + latest["reason"] + " · " + latest["state"] + " at " + iso(latest["updated_ms"]) + "."
        if latest.get("error"):
            view["credit_note"] += " " + latest["error"] + "."
        if latest.get("verified_ms"):
            view["credit_note"] += " Replacement " + latest["replacement_instance"][:8] + " verified online at " + iso(latest["verified_ms"]) + "."
        elif latest.get("replacement_lost_ms"):
            view["credit_note"] += " Its replacement departed before it could be verified online."
        elif latest.get("replacement_seen_ms"):
            view["credit_note"] += " Replacement " + latest["replacement_instance"][:8] + " observed; native/provider confirmation pending."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="collect and report once without issuing recovery requests")
    parser.add_argument("--startup", action="store_true", help="print the complete Salad bash command")
    parser.add_argument("--command", action="store_true", help="print the Salad command array using the PacketStream transport")
    parser.add_argument("--connect-provider", action="store_true", help="save existing EarnApp request credentials in Keychain")
    args = parser.parse_args()
    if args.startup:
        print((ROOT / "startup.sh").read_text(), end="")
        return
    if args.command:
        encoded = base64.b64encode((ROOT / "startup.sh").read_bytes()).decode()
        print(json.dumps(["/bin/bash", "-c", 'printf "%s" "$@" | base64 -d > /tmp/earnapp-supervisor.sh; exec /bin/bash /tmp/earnapp-supervisor.sh',
                          "earnapp-supervisor", *[encoded[i:i+900] for i in range(0, len(encoded), 900)]]))
        return
    if args.connect_provider:
        session = {"cookie": getpass.getpass("EarnApp request Cookie header: "),
                   "xsrf_token": getpass.getpass("EarnApp request xsrf-token header: ")}
        subprocess.run([HELPER, "--service", "earnapp-read-session", "--account", getpass.getuser()],
                       input=json.dumps(session), text=True, check=True, stdout=subprocess.DEVNULL)
        print("EarnApp account session saved")
        return
    os.umask(0o077)
    DATA.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DATA / "traffic.sqlite3", timeout=10)
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""CREATE TABLE IF NOT EXISTS samples (
        group_id TEXT, instance TEXT, observer INTEGER, seq INTEGER, start_ms INTEGER, end_ms INTEGER,
        body TEXT, received_ms INTEGER, PRIMARY KEY(group_id,instance,observer,seq));
        CREATE INDEX IF NOT EXISTS sample_time ON samples(group_id,end_ms);
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, body TEXT);
        CREATE TABLE IF NOT EXISTS provider (uuid TEXT,observed_ms INTEGER,body TEXT,PRIMARY KEY(uuid,observed_ms));
        CREATE TABLE IF NOT EXISTS events (group_id TEXT,instance TEXT,observer INTEGER,source TEXT,seq INTEGER,
        time_ms INTEGER,kind TEXT,body TEXT,received_ms INTEGER,PRIMARY KEY(group_id,instance,observer,source,seq));""")
    lock = (DATA / "recorder.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    key = os.environ.get("SALAD_API_KEY", "").strip()
    if not key:
        key = subprocess.check_output([HELPER, "--read", "--service", "salad-bandwidth-api",
                                       "--account", getpass.getuser()], text=True).strip()
    path = "/projects/" + PROJECT + "/containers/" + GROUP
    while True:
        began = time.monotonic()
        inventory = read_meta(db, "inventory", {})
        error = None
        try:
            group = request(SALAD + path, {"Salad-Api-Key": key})
            if group["container"]["environment_variables"].get("EARNAPP_UUID") != DEVICE:
                raise RuntimeError("EarnApp saved device identity changed")
            if group.get("country_codes") != ["us"] or group["replicas"] != 1:
                raise RuntimeError("EarnApp requires the configured US-only single-device deployment")
            members = request(SALAD + path + "/instances", {"Salad-Api-Key": key})["instances"]
            now = int(time.time() * 1000)
            inventory = {"group_id": group["id"], "desired": group["replicas"], "inventory_ms": now, "workers": members}
            with db:
                save_meta(db, "inventory", inventory)
            cursor = read_meta(db, "cursor:" + group["id"], now)
            items = fetch_logs(key, max(0, min(cursor, now) - 600000), now)
            with db:
                ingest(db, items, group["id"], int(time.time() * 1000))
                save_meta(db, "cursor:" + group["id"], now)
        except Exception as exc:
            error = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
        provider_read(db)
        view = snapshot(db, inventory, error)
        recover(db, view, key, enabled=not args.once)
        temporary = DATA / "view.json.tmp"
        temporary.write_text(json.dumps(view, allow_nan=False, separators=(",", ":")))
        os.replace(temporary, DATA / "view.json")
        if args.once:
            print(json.dumps({k: view[k] for k in ("inventory_ms", "running", "working", "total_mb", "all_recorded_mb", "error")}))
            return
        if error:
            print(error, flush=True)
        time.sleep(max(1, 15 - (time.monotonic() - began)))


if __name__ == "__main__":
    main()
