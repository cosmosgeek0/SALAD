"""Read SSH4 logs and provider metrics; publish a credential-free dashboard snapshot."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import time
import threading
import urllib.request
import urllib.error

from control import DATA, GROUP_PATH, api, keychain


def millis(value):
    value = re.sub(r"\.(\d+)", lambda m: "." + (m[1] + "000000")[:6], value, count=1)
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)


def iso(value):
    return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def error_message(error):
    if isinstance(error, urllib.error.HTTPError):
        return "Provider HTTP " + str(error.code)
    return str(error) if isinstance(error, RuntimeError) else type(error).__name__


def database(path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS samples (
          run TEXT, seq INTEGER, instance TEXT, machine TEXT, device TEXT, ip TEXT,
          time_ms INTEGER, start_ms INTEGER, interval_ms REAL, rx INTEGER, tx INTEGER,
          total_rx INTEGER, total_tx INTEGER, state TEXT, status_ms INTEGER,
          client_run INTEGER, native_in TEXT, native_out TEXT, requests INTEGER, error TEXT,
          PRIMARY KEY(run,seq));
        CREATE INDEX IF NOT EXISTS sample_time ON samples(time_ms);
        CREATE INDEX IF NOT EXISTS sample_instance_time ON samples(instance,time_ms DESC,seq DESC);
        CREATE INDEX IF NOT EXISTS sample_run_time ON samples(run,time_ms);
        CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY,time_ms INTEGER,payload TEXT);
        CREATE TABLE IF NOT EXISTS provider (time_ms INTEGER PRIMARY KEY,payload TEXT);
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY,value TEXT);
    """)
    columns = {row[1] for row in db.execute("PRAGMA table_info(samples)")}
    for name, kind in (("received_ms", "INTEGER"), ("log_ms", "INTEGER"), ("status_age_ms", "REAL"),
                       ("statistics_age_ms", "REAL"), ("policy", "TEXT")):
        if name not in columns:
            db.execute("ALTER TABLE samples ADD COLUMN " + name + " " + kind)
    db.commit()
    return db


class LogRequestBudget(RuntimeError):
    pass


def fetch_logs(start, end, request_budget=500, newest_first=False):
    """Yield only complete windows; capped responses are split, never skipped."""
    calls = 0
    deadline = time.monotonic() + 20 if newest_first else None

    def fetch(begin, stop):
        nonlocal calls
        calls += 1
        if calls > request_budget or deadline is not None and time.monotonic() >= deadline:
            raise LogRequestBudget("Log catch-up reached %s requests; completed windows were saved" % request_budget)
        response = api("/log-entries", "POST", {"query": 'resource.type = "container" and resource.labels.project_name = "default" and resource.labels.container_group_name = "tm-test-us" and text_log startswith "TM_V1 "',
            "start_time": iso(begin), "end_time": iso(stop), "page_size": 100, "sort_order": "asc"},
            **({"timeout": max(0.1, min(10, deadline - time.monotonic()))} if newest_first else {}))
        page = response.get("items")
        if not isinstance(page, list):
            raise RuntimeError("Salad returned an invalid log page")
        if len(page) < 100:
            yield stop, page
        else:
            if stop - begin <= 1:
                raise RuntimeError("A capped log millisecond cannot be split; cursor was not advanced")
            middle = (begin + stop) // 2
            if newest_first:
                yield from fetch(middle, stop)
                yield from fetch(begin, middle)
            else:
                yield from fetch(begin, middle)
                yield from fetch(middle, stop)

    yield from fetch(start, end)


def ingest(db, items):
    with db:
        for item in items:
            text = item.get("text_log", "")
            if not text.startswith("TM_V1 "):
                continue
            kind = instance = "unknown"
            try:
                record = json.loads(text[6:])
                kind = record["kind"]
                instance, machine = record["instance"], record["machine"]
                labels = item.get("resource", {}).get("labels", {})
                if any(labels.get(key) not in (None, expected) for key, expected in
                       (("organization_name", "ssh4"), ("project_name", "default"), ("container_group_name", "tm-test-us"))):
                    raise ValueError("Unexpected log origin")
                if labels.get("machine_id") not in (None, machine):
                    raise ValueError("Runtime machine differs from log origin")
                received = millis(item["receive_time"]) if item.get("receive_time") else None
                log_ms = millis(item["time"]) if item.get("time") else None
                run = instance + "/" + str(record["observer_start_ms"])
                if kind == "batch":
                    rows = record["samples"]
                elif kind == "sample":
                    rows = [[record["seq"], record["time_ms"], record["start_ms"], record["interval_ms"],
                        record["rx_bytes"], record["tx_bytes"], record["total_rx_bytes"], record["total_tx_bytes"],
                        record["state"], record["status_ms"], record["client_run"], record["connected"], record["accepting"]]]
                else:
                    event_id = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
                    record.update(received_ms=received, log_ms=log_ms)
                    db.execute("INSERT OR REPLACE INTO events VALUES (?,?,?)",
                               (event_id, record["time_ms"], json.dumps(record, sort_keys=True)))
                    continue
                policy = json.dumps(record["policy"]) if isinstance(record.get("policy"), dict) else None
                for row in rows:
                    if len(row) not in (13, 15) or not math.isfinite(row[3]) or row[3] <= 0:
                        raise ValueError("Invalid measurement interval")
                    if any(value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0) for value in row[4:8]):
                        raise ValueError("Invalid traffic counter")
                    state = row[8]
                    if state not in ("starting", "connected", "disconnected", "reallocating", "stopped") or state == "connected" and not (row[11] and row[12]):
                        raise ValueError("Invalid client state")
                    status_age = row[13] if len(row) == 15 else row[1] - row[9] if row[9] is not None else None
                    statistics_age = row[14] if len(row) == 15 else None
                    if any(age is not None and (isinstance(age, bool) or not isinstance(age, (int, float)) or not math.isfinite(age) or age < 0)
                           for age in (status_age, statistics_age)):
                        raise ValueError("Invalid client reply age")
                    values = (run, row[0], instance, machine, record.get("device"), record.get("ip"), row[1], row[2], row[3],
                         row[4], row[5], row[6], row[7], state, row[9], row[10], record.get("native_inbound"),
                         record.get("native_outgoing"), record.get("native_requests"), record.get("error"),
                         received, log_ms, status_age, statistics_age, policy)
                    inserted = db.execute("INSERT OR IGNORE INTO samples VALUES (" + ",".join("?" for _ in values) + ")", values)
                    if not inserted.rowcount:
                        old = db.execute("SELECT * FROM samples WHERE run=? AND seq=?", (run, row[0])).fetchone()
                        if tuple(old)[:20] != values[:20]:
                            raise ValueError("Conflicting duplicate sample " + str(row[0]))
                        if old["received_ms"] is None and received is not None:
                            db.execute("UPDATE samples SET received_ms=?,log_ms=?,status_age_ms=? WHERE run=? AND seq=?",
                                       (received, log_ms, status_age, run, row[0]))
            except (KeyError, ValueError, TypeError) as error:
                raise RuntimeError("TM record " + str(instance) + "/" + str(kind) + ": " + str(error)) from None



def save_cursor(db, cursor):
    db.execute("""INSERT INTO meta VALUES ('cursor',?) ON CONFLICT(key) DO UPDATE SET
                  value=CAST(MAX(CAST(meta.value AS INTEGER),CAST(excluded.value AS INTEGER)) AS TEXT)""", (str(cursor),))
    db.commit()


def collect_current(db, deployment, cursor, now):
    """Read newest leaves first and adapt dense live windows; history fills gaps."""
    saved = db.execute("SELECT value FROM meta WHERE key='live_window_ms'").fetchone()
    window = int(saved[0]) if saved else 45000
    start = max(millis(deployment["started_at"]), now - window)
    count = 0
    try:
        for completed, page in fetch_logs(start, now, request_budget=5, newest_first=True):
            ingest(db, page)
            count += len(page)
    except LogRequestBudget:
        db.execute("INSERT OR REPLACE INTO meta VALUES ('live_window_ms',?)", (str(max(1, window // 2)),))
        db.commit()
        return cursor
    if start <= cursor:
        cursor = max(cursor, now)
        save_cursor(db, cursor)
    if count < 25 and window < 45000:
        db.execute("INSERT OR REPLACE INTO meta VALUES ('live_window_ms',?)", (str(min(45000, window * 2)),))
        db.commit()
    return cursor


def collect_history(db, deployment, cursor, now):
    """At most one minute of history per cycle, with its own durable progress."""
    began = millis(deployment["started_at"])
    if cursor < now - 45000:
        saved_window = db.execute("SELECT value FROM meta WHERE key='history_window_ms'").fetchone()
        window = int(saved_window[0]) if saved_window else 60000
        try:
            for completed, page in fetch_logs(cursor, min(now, cursor + window), request_budget=3):
                ingest(db, page)
                cursor = max(cursor, completed)
                save_cursor(db, cursor)
        except LogRequestBudget:
            db.execute("INSERT OR REPLACE INTO meta VALUES ('history_window_ms',?)", (str(max(1, window // 2)),))
            db.commit()
            raise
        db.execute("INSERT OR REPLACE INTO meta VALUES ('history_window_ms',?)", (str(min(60000, window * 2)),))
        db.commit()
        return cursor
    saved = db.execute("SELECT value FROM meta WHERE key='reconcile'").fetchone()
    state = json.loads(saved[0]) if saved else None
    if not state or state["cursor"] >= state["end"] and now >= state["next_ms"]:
        state = {"cursor": max(began, now - 600000), "end": now, "next_ms": now + 300000, "window_ms": 60000}
        db.execute("INSERT OR REPLACE INTO meta VALUES ('reconcile',?)", (json.dumps(state),))
        db.commit()
    if state["cursor"] >= state["end"]:
        return cursor
    window = state.get("window_ms", 60000)
    try:
        for completed, page in fetch_logs(state["cursor"], min(state["end"], state["cursor"] + window), request_budget=3):
            ingest(db, page)
            state["cursor"] = max(state["cursor"], completed)
            db.execute("INSERT OR REPLACE INTO meta VALUES ('reconcile',?)", (json.dumps(state),))
            db.commit()
    except LogRequestBudget:
        state["window_ms"] = max(1, window // 2)
        db.execute("INSERT OR REPLACE INTO meta VALUES ('reconcile',?)", (json.dumps(state),))
        db.commit()
        raise
    state["window_ms"] = min(60000, window * 2)
    db.execute("INSERT OR REPLACE INTO meta VALUES ('reconcile',?)", (json.dumps(state),))
    db.commit()
    return cursor


def provider_request(path):
    if path not in ("/api/app_user/get_balance", "/api/dashboard/get_graph_stat?period=month"):
        raise ValueError("Provider request is outside the read-only metrics scope")
    request = urllib.request.Request("https://data.traffmonetizer.com" + path,
        headers={"Authorization": "Bearer " + keychain("salad-traffmonetizer-session"), "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=15) as response:
        result = json.load(response)
        refreshed = response.headers.get("Authorization", "")
    if refreshed.startswith("Bearer "):
        from control import ROOT
        import getpass
        subprocess.run([str(ROOT / ".runtime/keychain-store"), "--service", "salad-traffmonetizer-session",
            "--account", getpass.getuser()], input=refreshed[7:], text=True, capture_output=True, check=True)
    return result


def provider_reading(deployment):
    balance = provider_request("/api/app_user/get_balance")["data"]
    days = provider_request("/api/dashboard/get_graph_stat?period=month")
    start_day = deployment["started_at"][:10]
    selected = [day for day in days if day["date"] >= start_day]
    return {"observed_ms": int(time.time() * 1000), "balance_usd": balance["balance"],
            "balance_change_usd": balance["balance"] - deployment["provider_baseline_usd"],
            "credited_bytes": sum(day["traffic"] for day in selected) - deployment.get("provider_baseline_bytes", 0),
            "credited_usd": sum(day["earning"] for day in selected) - deployment.get("provider_baseline_earned_usd", 0),
            "requests": sum(day["requestsCount"] for day in selected), "days": selected,
            "source": "TraffMonetizer authenticated dashboard API", "scope": "Provider account totals less the saved ten-worker test baseline. Account balance is separate."}


def read_snapshot(db, deployment, members, errors, chart_minutes=None, inventory_ms=None, chart_generated_ms=None):
    now = int(time.time() * 1000)
    test_start = deployment.get("measurement_started_ms", millis(deployment["started_at"]))
    inventory_fresh = inventory_ms is not None and 0 <= now - inventory_ms <= 90000
    current = []
    for member in members:
        row = db.execute("SELECT * FROM samples WHERE instance=? ORDER BY time_ms DESC,seq DESC LIMIT 1", (member["id"],)).fetchone()
        value = dict(row) if row else {"instance": member["id"], "machine": member["machine_id"], "state": "awaiting_sample"}
        age = now - value["time_ms"] if row else None
        received_age = now - value["received_ms"] if row and value.get("received_ms") is not None else None
        status_age = value.get("status_age_ms")
        statistics_age = value.get("statistics_age_ms")
        value.update(salad_state=member["state"], sample_age_ms=age, receipt_age_ms=received_age,
                     fresh=age is not None and -5000 <= age <= 45000 and received_age is not None and -5000 <= received_age <= 45000,
                     policy=json.loads(value["policy"]) if value.get("policy") else None,
                     source_receipt_difference_ms=value["log_ms"] - value["received_ms"] if row and value.get("log_ms") is not None and value.get("received_ms") is not None else None)
        value["statistics_fresh"] = bool(value["fresh"] and statistics_age is not None and 0 <= statistics_age + max(0, age) <= 60000)
        value["connection_fresh"] = bool(value["statistics_fresh"] and status_age is not None and 0 <= status_age + max(0, age) <= 60000)
        if not value["statistics_fresh"]:
            reason = "Native statistics reply age is missing" if statistics_age is None else "Native statistics reply is stale or unverified"
            value["error"] = "; ".join(filter(None, (value.get("error"), reason)))
        measured = db.execute("SELECT SUM(rx) rx,SUM(tx) tx,SUM(interval_ms) duration FROM samples WHERE instance=? AND start_ms>=? AND rx IS NOT NULL AND tx IS NOT NULL", (member["id"], test_start)).fetchone()
        value.update(test_rx=measured["rx"], test_tx=measured["tx"], test_duration_ms=measured["duration"],
                     raw_mb_per_minute=None, native_recent_bytes=None, native_recent_requests=None, native_recent_ms=None)
        if row:
            end = value["time_ms"]
            recent = db.execute("SELECT SUM(rx+tx) bytes,SUM(interval_ms) duration FROM samples WHERE run=? AND time_ms>? AND time_ms<=? AND start_ms>=? AND rx IS NOT NULL AND tx IS NOT NULL",
                                (value["run"], end - 60000, end, test_start)).fetchone()
            if recent["duration"]:
                value["raw_mb_per_minute"] = recent["bytes"] / 1e6 * 60000 / recent["duration"]
            base = db.execute("SELECT time_ms,native_in,native_out,requests FROM samples WHERE run=? AND client_run=? AND time_ms>=? AND time_ms<=? AND native_in IS NOT NULL AND native_out IS NOT NULL AND requests IS NOT NULL ORDER BY seq LIMIT 1",
                              (value["run"], value["client_run"], max(test_start, end - 900000), end)).fetchone()
            if base and end > base["time_ms"]:
                before = [base[key] for key in ("native_in", "native_out", "requests")]
                after = [value[key] for key in ("native_in", "native_out", "requests")]
                if all(str(number).isdigit() for number in before + after):
                    deltas = [int(last) - int(first) for first, last in zip(before, after)]
                    if min(deltas) >= 0:
                        value.update(native_recent_bytes=deltas[0] + deltas[1], native_recent_requests=deltas[2],
                                     native_recent_ms=end - base["time_ms"])
        if not value["statistics_fresh"]:
            value.update(native_recent_bytes=None, native_recent_requests=None, native_recent_ms=None)
        value["working"] = bool(inventory_fresh and not errors.get("recorder") and value["connection_fresh"] and value["state"] == "connected" and member["state"] == "running")
        current.append(value)
    totals = db.execute("SELECT SUM(rx) rx,SUM(tx) tx,COUNT(*) samples,MIN(time_ms) first_ms,MAX(time_ms) last_ms FROM samples WHERE start_ms>=? AND rx IS NOT NULL AND tx IS NOT NULL", (test_start,)).fetchone()
    if chart_minutes is None:
        chart_generated_ms = now
        first = now // 60000 * 60000 - 1439 * 60000
        minutes = {}
        # The counter read fits inside the following monotonic interval. A wall span
        # exceeding both intervals (plus 1 ms timestamp rounding) proves a clock discontinuity.
        rows = db.execute("""WITH intervals AS (
                                SELECT *, CAST(time_ms/60000 AS INTEGER)*60000 minute,
                                       CASE WHEN time_ms-start_ms>interval_ms+1
                                            AND time_ms-start_ms>interval_ms+(SELECT following.interval_ms FROM samples following
                                                WHERE following.run=samples.run AND following.seq=samples.seq+1)+1
                                            THEN interval_ms+1 ELSE time_ms-start_ms END duration_ms
                                FROM samples WHERE time_ms>=? AND start_ms>=? AND rx IS NOT NULL AND tx IS NOT NULL),
                            coverage AS (
                                SELECT *, MIN(duration_ms,time_ms-MAX(start_ms,minute)) covered_ms FROM intervals)
                            SELECT minute,run,instance,machine,ip,SUM(rx+tx)/1e6 mb,
                                   SUM(covered_ms) coverage_ms,
                                   SUM(MIN(60000,MAX(0,duration_ms-covered_ms))) previous_coverage_ms,
                                   MAX(start_ms<minute) estimated
                            FROM coverage GROUP BY minute,run,instance,machine,ip ORDER BY minute""", (first, test_start)).fetchall()
        for row in rows:
            minute = minutes.setdefault(row["minute"], {"minute_ms": row["minute"], "mb": 0, "nodes": [], "duration_ms": 0, "estimated": False})
            minute["mb"] += row["mb"]
            minute["duration_ms"] += row["coverage_ms"]
            minute["estimated"] |= bool(row["estimated"])
            previous = minutes.get(row["minute"] - 60000)
            if previous is not None:
                previous["duration_ms"] += row["previous_coverage_ms"]
                previous["estimated"] |= bool(row["estimated"])
            minute["nodes"].append({"instance": row["instance"], "ip": row["ip"], "mb": row["mb"]})
        for minute in minutes.values():
            minute["count"] = len(minute["nodes"])
            minute["nodes"] = sorted(minute["nodes"], key=lambda row: -row["mb"])[:20]
            minute["partial"] = minute.pop("duration_ms") < deployment.get("desired_replicas", 10) * 60000
        chart_minutes = list(minutes.values())
    provider_row = db.execute("SELECT payload FROM provider ORDER BY time_ms DESC LIMIT 1").fetchone()
    provider = json.loads(provider_row[0]) if provider_row else None
    if provider:
        provider["age_ms"] = now - provider["observed_ms"]
        provider["fresh"] = provider["age_ms"] <= 180000 and not errors.get("provider")
    events = [json.loads(row[0]) for row in db.execute("SELECT payload FROM events WHERE json_extract(payload,'$.kind') NOT IN ('client_log') ORDER BY time_ms DESC LIMIT 20")]
    actions = {}
    for event in [json.loads(row[0]) for row in db.execute("SELECT payload FROM events WHERE json_extract(payload,'$.kind') IN ('reallocate','reallocate_result') ORDER BY time_ms DESC LIMIT 100")]:
        key = (event.get("instance"), event.get("observer_start_ms"))
        action = actions.setdefault(key, {"instance": key[0], "observer_start_ms": key[1]})
        if event["kind"] == "reallocate":
            action.update(time_ms=event["time_ms"], reason=event.get("reason"), machine=event.get("machine"))
        elif "accepted" not in action:
            action.update(accepted=event.get("accepted"), http_status=event.get("http_status"), attempt=event.get("attempt"))
    members_ids = {member["id"] for member in members}
    restored = inventory_fresh and len(current) == deployment.get("desired_replicas", 10) and all(row["working"] for row in current)
    recovery = []
    confirmations = []
    for action in actions.values():
        if "time_ms" not in action:
            continue
        confirmation_key = "recovery:" + action["instance"] + "/" + str(action["observer_start_ms"])
        confirmed = db.execute("SELECT value FROM meta WHERE key=?", (confirmation_key,)).fetchone()
        if not confirmed and restored and action["instance"] not in members_ids:
            confirmations.append((confirmation_key, str(now)))
            confirmed = (str(now),)
        action["fleet_confirmed_ms"] = int(confirmed[0]) if confirmed else None
        action["outcome"] = ("fleet_restored" if confirmed else "request_failed" if action.get("accepted") is False else "awaiting_response" if action.get("accepted") is not True else
                             "inventory_unverified" if not inventory_fresh else "awaiting_retirement" if action["instance"] in members_ids else
                             "fleet_restored" if restored else "replacement_pending")
        recovery.append(action)
    recovery.sort(key=lambda action: action["time_ms"], reverse=True)
    return {"_confirmations": confirmations, "schema_version": 2, "provider": "traffmonetizer", "title": "TM", "generated_ms": now,
            "deployment": deployment, "recorded": dict(totals), "workers": current,
            "inventory_ms": inventory_ms, "inventory_fresh": inventory_fresh,
            "running": sum(row["salad_state"] == "running" for row in current) if inventory_fresh else None,
            "working": sum(row["working"] for row in current) if inventory_fresh and not errors.get("recorder") else None,
            "chart_minutes": chart_minutes, "chart_generated_ms": chart_generated_ms, "recent_recovery": recovery[:5],
            "credited": provider, "events": events, "errors": errors,
            "measurement": "Raw interface RX and TX measured every second inside each container. Transported in ten-sample batches. Credited traffic comes separately from the provider account API."}


def snapshot(db, *args, **kwargs):
    # One consistent read while the maintenance connection can ingest older logs.
    db.execute("SAVEPOINT published_view")
    try:
        result = read_snapshot(db, *args, **kwargs)
    except Exception:
        db.execute("ROLLBACK TO published_view")
        db.execute("RELEASE published_view")
        raise
    db.execute("RELEASE published_view")
    for confirmation in result.pop("_confirmations"):
        db.execute("INSERT OR IGNORE INTO meta VALUES (?,?)", confirmation)
    db.commit()
    return result


def maintain_history(deployment, stop):
    db = database(DATA / "traffic.sqlite3")
    provider_at = 0
    try:
        while not stop.is_set():
            began = time.monotonic()
            try:
                saved = json.loads((DATA / "deployment.json").read_text())
                if saved["group_id"] != deployment["group_id"]:
                    raise RuntimeError("Saved deployment identity changed")
                if api(GROUP_PATH)["id"] != deployment["group_id"]:
                    raise RuntimeError("Deployment identity changed")
                if time.monotonic() >= provider_at:
                    try:
                        reading = provider_reading(saved)
                        db.execute("INSERT OR REPLACE INTO provider VALUES (?,?)", (reading["observed_ms"], json.dumps(reading)))
                        db.execute("DELETE FROM meta WHERE key='provider_error'")
                    except Exception as error:
                        db.execute("INSERT OR REPLACE INTO meta VALUES ('provider_error',?)", (error_message(error),))
                    db.commit()
                    provider_at = time.monotonic() + 60
                cursor_row = db.execute("SELECT value FROM meta WHERE key='cursor'").fetchone()
                cursor = int(cursor_row[0]) if cursor_row else millis(saved["started_at"])
                collect_history(db, saved, cursor, int(time.time() * 1000))
                db.execute("DELETE FROM meta WHERE key='history_error'")
            except Exception as error:
                db.execute("INSERT OR REPLACE INTO meta VALUES ('history_error',?)", (error_message(error),))
            db.commit()
            stop.wait(max(1, 15 - (time.monotonic() - began)))
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    os.umask(0o077)
    DATA.mkdir(parents=True, exist_ok=True)
    lock = (DATA / "observer.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    deployment = json.loads((DATA / "deployment.json").read_text())
    db = database(DATA / "traffic.sqlite3")
    cursor_row = db.execute("SELECT value FROM meta WHERE key='cursor'").fetchone()
    cursor = int(cursor_row[0]) if cursor_row else millis(deployment["started_at"])
    members = []
    inventory_ms = None
    chart_generated_ms = None
    maintenance_stop = threading.Event()
    if not args.once:
        threading.Thread(target=maintain_history, args=(deployment, maintenance_stop), daemon=True).start()
    chart_minutes, chart_at = None, 0
    while True:
        began = time.monotonic()
        now = int(time.time() * 1000)
        errors = {}
        try:
            current_deployment = json.loads((DATA / "deployment.json").read_text())
            if current_deployment["group_id"] != deployment["group_id"]:
                raise RuntimeError("Saved deployment identity changed")
            deployment = current_deployment
            group = api(GROUP_PATH)
            if group["id"] != deployment["group_id"]:
                raise RuntimeError("Deployment identity changed")
            members = api(GROUP_PATH + "/instances")["instances"]
            inventory_ms = int(time.time() * 1000)
            cursor_row = db.execute("SELECT value FROM meta WHERE key='cursor'").fetchone()
            cursor = int(cursor_row[0]) if cursor_row else cursor
            cursor = collect_current(db, deployment, cursor, int(time.time() * 1000))
        except Exception as error:
            errors["recorder"] = error_message(error)
            cursor_row = db.execute("SELECT value FROM meta WHERE key='cursor'").fetchone()
            cursor = int(cursor_row[0]) if cursor_row else cursor
        for key in ("history", "provider"):
            error = db.execute("SELECT value FROM meta WHERE key=?", (key + "_error",)).fetchone()
            if error:
                errors[key] = error[0]
        refresh_chart = time.monotonic() >= chart_at
        result = snapshot(db, deployment, members, errors, None if refresh_chart else chart_minutes, inventory_ms, chart_generated_ms)
        if refresh_chart:
            chart_minutes, chart_at = result["chart_minutes"], time.monotonic() + 60
            chart_generated_ms = result["chart_generated_ms"]
        result["cycle_seconds"] = round(time.monotonic() - began, 3)
        temporary = DATA / "latest.tmp"
        temporary.write_text(json.dumps(result, separators=(",", ":")))
        os.replace(temporary, DATA / "latest.json")
        print(json.dumps({"time_ms": result["generated_ms"], "running": result["running"], "working": result["working"], "samples": result["recorded"]["samples"], "errors": errors}), flush=True)
        if args.once:
            break
        time.sleep(max(1, 15 - (time.monotonic() - began)))


if __name__ == "__main__":
    main()
