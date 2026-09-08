import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import fcntl
import getpass
import ipaddress
import json
import math
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request

from dashboard.native_network import FIELDS, NetworkMinutes, UUID, bucket_minutes
from dashboard.salad_api import SaladLogClient, _iso, _parse_iso

PROVIDER_FRESH_MS = 180000
ERRORS = {
    "ip_used": "Pawns rejected this IP as already sharing.",
    "non_residential_ip": "Pawns rejected this IP as non-residential.",
    "cant_get_free_port": "Pawns could not find a free local port.",
    "cant_open_port": "Pawns could not open its local port.",
    "could_not_mark_peer_alive": "Pawns could not maintain its provider connection.",
    "unauthorized": "Pawns session expired; restarting with a fresh login.",
    "session_expired": "Pawns session expired; restarting with a fresh login.",
    "unsupported_version": "Pawns requires an updated SDK image.",
    "startup_timeout": "Pawns did not start before its connection deadline.",
    "client_exited": "Pawns client exited.",
    "client_output_closed": "Pawns client output closed.",
    "client_suspended": "Pawns client process was suspended.",
    "provider_ip_offline": "Pawns repeatedly reported this IP offline.",
}


class PawnsLogs(SaladLogClient):
    @property
    def query(self):
        return ('resource.type = "container" and resource.labels.project_name = "' + self.project
                + '" and resource.labels.container_group_name = "' + self.container_group
                + '" and text_log startswith "PAWNS_"')


def integer(value):
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 2**53 - 1


def parse_record(item, group_id, received_ms):
    line = item.get("text_log", "")
    prefix, _, text = line.partition(" ")
    kind = prefix.removeprefix("PAWNS_")
    if kind not in ("SAMPLE", "PROVIDER", "RECOVERY"):
        return None
    row = json.loads(text)
    if not isinstance(row, dict) or row.get("group_id") != group_id:
        return None
    if not isinstance(row.get("instance"), str) or not UUID.fullmatch(row["instance"]):
        raise ValueError("Pawns runtime instance identity is invalid")
    if not all(integer(row.get(k)) for k in ("observer", "seq")) or not row["observer"]:
        raise ValueError("Pawns run identity is invalid")
    labels = item.get("resource", {}).get("labels", {})
    row["legacy_instance"] = labels.get("instance_id")
    machine = row.get("machine") or labels.get("machine_id")
    row["machine"] = machine if isinstance(machine, str) and UUID.fullmatch(machine) else None
    row.update(received_ms=received_ms, record_bytes=len(line.encode()) + 1,
               salad_time=item.get("time"), salad_receive_time=item.get("receive_time"))
    if row.get("ip") is not None:
        row["ip"] = str(ipaddress.ip_address(row["ip"]))
    if kind == "SAMPLE":
        if not all(integer(row.get(k)) for k in ("start_ms", "end_ms")) or not row["observer"] <= row["start_ms"] <= row["end_ms"] <= received_ms + 10000:
            raise ValueError("Pawns sample timestamp is invalid")
        if not isinstance(row.get("valid"), bool) or not isinstance(row.get("final"), bool):
            raise ValueError("Pawns sample flags are invalid")
        if row["valid"] and not all(integer(row.get(k)) for k in ("rx", "tx", "total_rx", "total_tx")):
            raise ValueError("Pawns byte counters are invalid")
        row["bucket_ms"] = None
    else:
        if not integer(row.get("time_ms")) or not row["observer"] <= row["time_ms"] <= received_ms + 10000:
            raise ValueError("Pawns event timestamp is invalid")
        if kind == "PROVIDER":
            for key in ("balance_ms", "device_ms"):
                if row.get(key) is not None and (not integer(row[key]) or not row["observer"] <= row[key] <= row["time_ms"]):
                    raise ValueError("Pawns provider timestamp is invalid")
            for key in ("sold_gb", "sharing_usd", "balance_usd"):
                value = row.get(key)
                if value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0):
                    raise ValueError("Pawns provider amount is invalid")
            if row.get("active") is not None and not isinstance(row["active"], bool):
                raise ValueError("Pawns provider status is invalid")
        elif row.get("phase") not in ("requested", "accepted", "failed", "container_exit", "interrupted") or row.get("action") not in ("restart", "reallocate"):
            raise ValueError("Pawns recovery event is invalid")
    return kind, row


def prepare(store):
    store.db.executescript("""
        CREATE TABLE IF NOT EXISTS pawns_events (
            group_id TEXT, instance TEXT, observer INTEGER, kind TEXT, seq INTEGER,
            time_ms INTEGER, data TEXT,
            PRIMARY KEY(group_id,instance,observer,kind,seq));
        CREATE INDEX IF NOT EXISTS pawns_events_time ON pawns_events(group_id,kind,time_ms);
    """)
    store.db.commit()


def save_event(store, kind, row):
    store.db.execute("""INSERT INTO pawns_events VALUES (?,?,?,?,?,?,?)
        ON CONFLICT(group_id,instance,observer,kind,seq) DO UPDATE SET data=json_set(pawns_events.data,
            '$.salad_time',COALESCE(json_extract(pawns_events.data,'$.salad_time'),json_extract(excluded.data,'$.salad_time')),
            '$.salad_receive_time',COALESCE(json_extract(pawns_events.data,'$.salad_receive_time'),json_extract(excluded.data,'$.salad_receive_time')))
        WHERE (json_extract(pawns_events.data,'$.salad_time') IS NULL AND json_extract(excluded.data,'$.salad_time') IS NOT NULL)
           OR (json_extract(pawns_events.data,'$.salad_receive_time') IS NULL AND json_extract(excluded.data,'$.salad_receive_time') IS NOT NULL)""",
        (row["group_id"], row["instance"], row["observer"], kind, row["seq"], row["time_ms"],
         json.dumps(row, separators=(",", ":"), allow_nan=False)))


def ingest(store, records):
    samples = [row for kind, row in records if kind == "SAMPLE"]
    with store.lock, store.db:
        for row in samples:
            legacy = row.get("legacy_instance") or row["instance"]
            old = store.db.execute("SELECT * FROM minutes WHERE group_id=? AND instance=? AND observer=? AND seq=?",
                (row["group_id"], legacy, row["observer"], row["seq"])).fetchone()
            if old and all(old[k] == row.get(k) for k in FIELDS if k not in ("instance", "machine", "received_ms", "record_bytes", "valid")):
                canonical = (row["group_id"], row["instance"], row["observer"], row["seq"])
                exists = store.db.execute("SELECT 1 FROM minutes WHERE group_id=? AND instance=? AND observer=? AND seq=?", canonical).fetchone()
                if legacy == row["instance"]:
                    store.db.execute("UPDATE minutes SET machine=? WHERE group_id=? AND instance=? AND observer=? AND seq=?", (row["machine"], *canonical))
                elif exists:
                    store.db.execute("UPDATE minutes SET received_ms=MIN(received_ms,?) WHERE group_id=? AND instance=? AND observer=? AND seq=?", (old["received_ms"], *canonical))
                    store.db.execute("DELETE FROM minutes WHERE group_id=? AND instance=? AND observer=? AND seq=?", (row["group_id"], legacy, row["observer"], row["seq"]))
                else:
                    store.db.execute("UPDATE minutes SET instance=?,machine=? WHERE group_id=? AND instance=? AND observer=? AND seq=?",
                        (row["instance"], row["machine"], row["group_id"], legacy, row["observer"], row["seq"]))
    inserted = store.ingest(samples)
    with store.lock, store.db:
        for kind, row in records:
            if kind == "SAMPLE":
                save_event(store, "SAMPLE_SOURCE", {**{k: row[k] for k in
                    ("group_id", "instance", "observer", "seq", "salad_time", "salad_receive_time")},
                    "time_ms": row["end_ms"]})
                detail = {k: row.get(k) for k in ("seq", "sdk_at", "deadline_ms")}
                store.db.execute("""INSERT INTO pawns_events VALUES (?,?,?,'STATUS',0,?,?)
                    ON CONFLICT(group_id,instance,observer,kind,seq) DO UPDATE
                    SET time_ms=excluded.time_ms,data=excluded.data
                    WHERE json_extract(excluded.data,'$.seq')>json_extract(pawns_events.data,'$.seq')""",
                    (row["group_id"], row["instance"], row["observer"], row["end_ms"], json.dumps(detail)))
                if row.get("ip") and row.get("country"):
                    store.db.execute("INSERT OR REPLACE INTO countries VALUES (?,?)", (row["ip"], row["country"]))
            else:
                save_event(store, kind, row)
    return inserted


def latest_event(store, group_id, kind, instance=None, observer=None):
    query = "SELECT data FROM pawns_events WHERE group_id=? AND kind=?"
    params = [group_id, kind]
    if instance is not None:
        query += " AND instance=? AND observer=?"
        params += [instance, observer]
    row = store.db.execute(query + " ORDER BY time_ms DESC,seq DESC LIMIT 1", params).fetchone()
    return json.loads(row[0]) if row else None


def stamp(value):
    return datetime.fromtimestamp(value / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def snapshot(store, group, instances, inventory_ms, now, error=None):
    group_id = group.get("id", "")
    fresh_inventory = inventory_ms is not None and 0 <= now - inventory_ms <= 90000
    latest = store.latest(group_id)
    with store.lock, store.db:
        totals = store.db.execute("SELECT SUM(rx+tx),MIN(start_ms) FROM minutes WHERE group_id=? AND valid=1 AND seq>0", (group_id,)).fetchone()
        first = now // 60000 * 60000 - 1439 * 60000
        rows = store.db.execute("SELECT m.*,c.country FROM minutes m LEFT JOIN countries c ON m.ip=c.ip WHERE group_id=? AND valid=1 AND seq>0 AND end_ms>=? ORDER BY end_ms", (group_id, first)).fetchall()
        minutes = bucket_minutes(rows, first, now // 60000 * 60000)
        workers = []
        request = latest_event(store, group_id, "RECOVERY")
        recovered = latest_event(store, group_id, "RECOVERED")
        pending = request and request["phase"] != "interrupted" and not (recovered and recovered["previous_instance"] == request["instance"] and recovered["previous_observer"] == request["observer"])
        for instance in instances:
            row = latest.get(instance["id"])
            fresh_sample = bool(row and 0 <= now - row["end_ms"] <= 90000 and 0 <= now - row["received_ms"] <= 90000)
            known = fresh_inventory and fresh_sample and not error
            state = row["state"] if known else None
            provider = latest_event(store, group_id, "PROVIDER", instance["id"], row["observer"]) if row else None
            provider_fresh = bool(provider and provider.get("device_ms") and 0 <= now - provider["device_ms"] <= PROVIDER_FRESH_MS and provider.get("ip") == row["ip"])
            detail = latest_event(store, group_id, "STATUS", instance["id"], row["observer"]) if row else None
            measured = store.db.execute("SELECT SUM(rx+tx),SUM(end_ms-start_ms) FROM minutes WHERE group_id=? AND instance=? AND observer=? AND valid=1 AND seq>0",
                (group_id, instance["id"], row["observer"])).fetchone() if row else (None, None)
            country = store.db.execute("SELECT country FROM countries WHERE ip=?", (row["ip"],)).fetchone() if row else None
            native_ok = known and state == "running" and instance.get("state") == "running" and not row["final"] and not row["error"]
            working = bool(native_ok and provider_fresh and provider.get("active") is True) if known else None
            message = ERRORS.get(row["error"], row["error"]) if known else error or "Waiting for a current Pawns sample."
            label = {"not_running": "Disconnected", "restarting": "Restarting", "login_error": "Login unavailable"}.get(state, state)
            if known and row["error"] == "unsupported_version":
                label = "Update required"
            if native_ok:
                if not provider_fresh or provider.get("active") is None:
                    working = None
                    label = "Provider status unavailable"
                    message = provider.get("error") if provider else "Waiting for Pawns to confirm this IP."
                elif provider["active"]:
                    label = "connected"
                else:
                    label = "Provider offline"
                    message = "Pawns reports this IP offline; persistent absence triggers automatic replacement."
            elif known and detail and detail.get("deadline_ms") and state == "not_running":
                message = (message + " " if message else "") + "Automatic replacement deadline: " + stamp(detail["deadline_ms"]) + "."
            rate = (row["rx"] + row["tx"]) * 60000 / (row["end_ms"] - row["start_ms"]) / 1e6 if known and row["valid"] and row["seq"] > 0 and row["end_ms"] > row["start_ms"] and not row["final"] else None
            workers.append({"id": instance["id"], "ip": row["ip"] if row else None,
                "country": country[0] if country else None, "client_status": label, "salad_state": instance.get("state"),
                "working": working, "mb_per_minute": rate if instance.get("state") == "running" else None,
                "total_mb": measured[0] / 1e6 if measured[0] is not None else None,
                "recorded_duration_ms": measured[1],
                "observer_ms": row["observer"] if row else None,
                "recorded_ms": row["received_ms"] if row else None, "sample_ms": row["end_ms"] if row else None,
                "error": message})
            if working and pending and group.get("replicas") == 1 and len(instances) == 1 and row["observer"] > request["time_ms"]:
                known_machines = row["machine"] and request.get("machine")
                outcome = ("replacement_confirmed" if row["machine"] != request["machine"] else "restart_confirmed") if known_machines else "healthy_run_placement_unknown"
                save_event(store, "RECOVERED", {"group_id": group_id, "instance": instance["id"], "observer": row["observer"],
                    "seq": 0, "time_ms": now, "phase": outcome, "previous_instance": request["instance"],
                    "previous_machine": request.get("machine"), "previous_observer": request["observer"],
                    "machine": row["machine"], "ip": row["ip"], "reason": request["reason"],
                    "request_time_ms": request["time_ms"], "request_phase": request["phase"]})
            elif working and group.get("replicas") == 1 and len(instances) == 1 and not latest_event(store, group_id, "RECOVERED", instance["id"], row["observer"]):
                previous = store.db.execute("SELECT instance,machine,observer FROM minutes WHERE group_id=? AND observer<? ORDER BY observer DESC,end_ms DESC LIMIT 1",
                                            (group_id, row["observer"])).fetchone()
                if previous:
                    known_machines = previous["machine"] and row["machine"]
                    change = ("new_machine_observed" if previous["machine"] != row["machine"] else "restart_observed") if known_machines else "healthy_run_placement_unknown"
                    save_event(store, "RUN_CHANGE", {"group_id": group_id, "instance": instance["id"], "observer": row["observer"],
                        "seq": 0, "time_ms": now, "started_ms": row["observer"], "machine": row["machine"],
                        "previous_instance": previous["instance"], "previous_machine": previous["machine"],
                        "previous_observer": previous["observer"], "phase": change})
        provider = latest_event(store, group_id, "PROVIDER")
        account = provider.get("account_id") if provider else None
        balance_row = store.db.execute("""SELECT data FROM pawns_events
            WHERE group_id=? AND kind='PROVIDER' AND json_extract(data,'$.account_id')=?
            AND json_extract(data,'$.balance_ms') IS NOT NULL ORDER BY time_ms DESC LIMIT 1""", (group_id, account)).fetchone()
        balance = json.loads(balance_row[0]) if balance_row else None
        credited = earned = None
        note = "Network RX + TX includes relay traffic and overhead. Row totals and recorded time belong to the current run; the chart and total retain previous runs. "
        if balance:
            fresh_balance = 0 <= now - balance["balance_ms"] <= PROVIDER_FRESH_MS
            suffix = "" if fresh_balance else " (stale)"
            if balance.get("sold_gb") is not None:
                credited = format(Decimal(str(balance["sold_gb"])), "f") + " GB account total" + suffix
            if balance.get("sharing_usd") is not None:
                earned = "$" + format(Decimal(str(balance["sharing_usd"])), "f") + " account sharing" + suffix
            note += "Provider snapshot at " + stamp(balance["balance_ms"]) + ". These totals are account-wide, not earnings attributed to this worker or the chart period. "
            readings = store.db.execute("""SELECT data FROM pawns_events WHERE group_id=? AND kind='PROVIDER'
                AND json_extract(data,'$.account_id')=? AND json_extract(data,'$.sold_gb') IS NOT NULL
                AND json_extract(data,'$.balance_ms') IS NOT NULL ORDER BY json_extract(data,'$.balance_ms'),time_ms,seq""", (group_id, account))
            baseline = previous_balance = None
            for reading in readings:
                reading = json.loads(reading[0])
                if baseline is None or Decimal(str(reading["sold_gb"])) < Decimal(str(previous_balance["sold_gb"])):
                    baseline = reading
                previous_balance = reading
            if baseline and balance.get("sold_gb") is not None and balance["balance_ms"] > baseline["balance_ms"]:
                delta = Decimal(str(balance["sold_gb"])) - Decimal(str(baseline["sold_gb"]))
                note += ("Recorded sold-traffic change since " + stamp(baseline["balance_ms"]) + ": " + format(delta, "f") + " GB. ") if delta >= 0 else "Provider sold-traffic counter decreased; no credited delta is asserted. "
            elif baseline:
                note += "Provider baseline saved; awaiting a later reading. "
        else:
            note += "Waiting for an actual Pawns provider balance; unavailable credits are not zero. "
        if provider and provider.get("error"):
            note += "Latest provider check: " + provider["error"] + ". "
        note += "Recovery runs inside the container: rejected IPs, client exit and suspension trigger replacement; startup/disconnection and repeated provider-offline observations have a configured 120-second deadline. A separate liveness probe checks the supervisor. "
        if provider and provider.get("idle_state"):
            if provider["idle_state"] in ("observing", "idle"):
                note += "Idle observation: " + format(provider["idle_elapsed_ms"] / 60000, ".1f") + " min without provider sold-traffic progress as of " + stamp(provider["time_ms"]) + "; this is the account's sole active IP. "
            else:
                note += "Idle observation is waiting for fresh, attributable single-IP provider evidence. "
            note += "A healthy connected node remains running when traffic or earnings are low. "
        recovered = latest_event(store, group_id, "RECOVERED")
        if recovered and (not request or recovered["time_ms"] >= request["time_ms"]):
            note += "Last confirmed recovery request: " + recovered["phase"].replace("_", " ") + " at " + stamp(recovered["time_ms"]) + " after " + recovered["reason"] + "."
        elif request and request["phase"] == "interrupted":
            note += "Recovery retries were interrupted by shutdown at " + stamp(request["time_ms"]) + "."
        elif request:
            note += "Last recovery request: " + request["action"] + " " + request["phase"] + " at " + stamp(request["time_ms"]) + " (" + request["reason"] + "); a healthy result has not yet been confirmed."
        change = latest_event(store, group_id, "RUN_CHANGE")
        if change and (not recovered or change["time_ms"] > recovered["time_ms"]):
            note += " Latest runtime change: " + change["phase"].replace("_", " ") + " at " + stamp(change["time_ms"]) + "; its cause was not reported by the workload."
    known_workers = fresh_inventory and not error and all(w["working"] is not None for w in workers)
    return {"generated_ms": now, "inventory_ms": inventory_ms, "desired": group.get("replicas"),
        "running": sum(w["salad_state"] == "running" for w in workers) if fresh_inventory else None,
        "working": sum(w["working"] is True for w in workers) if known_workers else None,
        "started_ms": totals[1], "total_mb": totals[0] / 1e6 if totals[0] is not None else None,
        "credited_text": credited, "earned_text": earned, "credit_note": note,
        "error": error or ("Waiting for current Pawns measurements." if not any(w["client_status"] for w in workers) else None),
        "workers": workers, "minutes": minutes}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--data-dir", type=Path, default=Path.home() / ".hg1/pawns")
    parser.add_argument("--organization", default="cosmosgeeketh")
    parser.add_argument("--project", default="default")
    parser.add_argument("--group", default="pawns")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    args.data_dir.mkdir(parents=True, exist_ok=True)
    lock = (args.data_dir / "observer.lock").open("w")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    key = subprocess.check_output([str(args.app_root / ".runtime/keychain-store"), "--read", "--service", "salad-bandwidth-api", "--account", getpass.getuser()], text=True).strip()
    client = PawnsLogs(args.organization, args.project, args.group, lambda: key)
    store = NetworkMinutes(args.data_dir / "traffic.sqlite3")
    prepare(store)
    base = "https://api.salad.com/api/public/organizations/" + args.organization + "/projects/" + args.project + "/containers/" + args.group
    group, instances, inventory_ms = {}, [], None
    while True:
        began = time.monotonic()
        error = None
        try:
            inventory = []
            for suffix in ("", "/instances"):
                req = urllib.request.Request(base + suffix, headers={"Salad-Api-Key": key, "User-Agent": "salad-bandwidth-dashboard/1"})
                with urllib.request.urlopen(req, timeout=25) as response:
                    inventory.append(json.load(response))
            group, instances = inventory[0], inventory[1]["instances"]
            inventory_ms = int(time.time() * 1000)
            now = datetime.now(timezone.utc)
            saved = store.collector_status(group["id"])
            cursor = _parse_iso(saved["cursor"]) if saved.get("cursor") else now
            items = client.fetch(_iso(min(cursor, now) - timedelta(minutes=10)), _iso(now))
            received_ms = int(time.time() * 1000)
            records, rejected = [], 0
            for item in items:
                try:
                    record = parse_record(item, group["id"], received_ms)
                    if record is not None:
                        records.append(record)
                except (ValueError, TypeError, KeyError, AttributeError):
                    rejected += 1
            if rejected:
                print("Pawns collector: rejected " + str(rejected) + " malformed records; valid records continue.", flush=True)
            inserted = ingest(store, records)
            store.collector_status(group["id"], _iso(now), inserted=inserted)
        except Exception as exc:
            error = "Salad HTTP " + str(exc.code) if isinstance(exc, urllib.error.HTTPError) else type(exc).__name__ + ": " + str(exc)
            error = error.replace(key, "[redacted]") if key else error
            print("Pawns collector: " + error, flush=True)
        view = snapshot(store, group, instances, inventory_ms, int(time.time() * 1000), error)
        target = args.data_dir / "view.json"
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(view, separators=(",", ":"), allow_nan=False))
        os.replace(temporary, target)
        if args.once:
            print(json.dumps({k: view[k] for k in ("generated_ms", "desired", "running", "working", "total_mb", "error")}))
            return
        time.sleep(max(1, 15 - (time.monotonic() - began)))


if __name__ == "__main__":
    main()
