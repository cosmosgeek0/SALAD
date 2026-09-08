"""Collect complete minute records from Salad logs, including replaced instances."""
from datetime import datetime, timedelta, timezone
import getpass
import json
from pathlib import Path
import re
import subprocess
import threading
import time

from dashboard.native_network import NetworkMinutes, parse_minute


def provider_datetime(value):
    value = re.sub(r"\.(\d+)(?=Z$|[+-]\d\d:\d\d$)", lambda m: "." + (m[1] + "000000")[:6], value)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class NetworkObserver:
    def __init__(self, app_root, group, group_id, data_dir=None):
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,61}[a-z0-9]", group):
            raise ValueError("Invalid PacketStream group")
        self.group, self.group_id = group, group_id
        self.key = subprocess.check_output(
            [str(app_root / ".runtime/keychain-store"), "--read", "--service",
             "salad-bandwidth-api", "--account", getpass.getuser()], text=True).strip()
        self.store = NetworkMinutes((data_dir or Path.home() / ".hg1/packetstream") / "minutes.sqlite3")
        self.members = []
        self.lock = threading.Lock()
        threading.Thread(target=self.run, daemon=True).start()

    def request(self, path, body=None):
        config = "header = " + json.dumps("Salad-Api-Key: " + self.key) + '\nheader = "Content-Type: application/json"\n'
        if body is not None:
            config += "data-binary = " + json.dumps(json.dumps(body)) + "\n"
        response = subprocess.run(
            ["curl", "-sS", "--max-time", "20", "--config", "-", "--write-out", "\n%{http_code}",
             "https://api.salad.com/api/public/organizations/hyperlane" + path],
            input=config, text=True, capture_output=True, timeout=25)
        raw, code = response.stdout.rsplit("\n", 1)
        if response.returncode or code != "200":
            raise RuntimeError("Salad log request HTTP " + code)
        return json.loads(raw)

    def update_members(self, nodes):
        with self.lock:
            self.members = [node["instance_id"] for node in nodes]

    def snapshots(self):
        now = int(time.time() * 1000)
        latest = self.store.latest(self.group_id)
        with self.lock:
            members = list(self.members)
        result = {}
        for instance in members:
            row = latest.get(instance)
            if not row or not row["valid"]:
                continue
            seconds = (row["end_ms"] - row["start_ms"]) / 1000
            result[instance] = {
                "available": True, "source": "sysfs-minute-via-salad-logs",
                "observer": row["observer"], "time_ms": row["end_ms"], "received_ms": row["received_ms"],
                "ip": row["ip"], "observed_rx_bytes": row["total_rx"], "observed_tx_bytes": row["total_tx"],
                "observed_total_bytes": row["total_rx"] + row["total_tx"],
                "source_age_seconds": (now - row["end_ms"]) / 1000,
                "receipt_age_seconds": (now - row["received_ms"]) / 1000,
                "last_interval_seconds": seconds, "last_delta_bytes": row["rx"] + row["tx"],
                "bytes_per_second": (row["rx"] + row["tx"]) / seconds if seconds > 0 else None,
                "nominal_interval_ms": 60000, "samples": row["seq"] + 1}
        return result

    def poll(self):
        group = self.request("/projects/default/containers/" + self.group)
        if group.get("id") != self.group_id:
            raise RuntimeError("PacketStream deployment identity changed")
        now = datetime.now(timezone.utc)
        saved = self.store.collector_status(self.group_id)
        cursor = provider_datetime(saved["cursor"]) if saved.get("cursor") else now
        start = min(cursor, now) - timedelta(minutes=10)
        calls = 0

        def fetch(begin, end):
            nonlocal calls
            calls += 1
            if calls > 512:
                raise RuntimeError("Minute log catch-up has too many pages")
            body = {
                "query": 'resource.type = "container" and resource.labels.project_name = "default" and '
                         'resource.labels.container_group_name = "' + self.group + '" and text_log startswith "PS_MINUTE_V"',
                "start_time": begin.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                "end_time": end.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                "page_size": 100, "sort_order": "asc"}
            items = self.request("/log-entries", body).get("items")
            if not isinstance(items, list):
                raise RuntimeError("Invalid Salad log response")
            if len(items) < 100:
                return items
            if end - begin <= timedelta(milliseconds=1):
                raise RuntimeError("Too many minute records share a pagination timestamp")
            middle = begin + (end - begin) / 2
            return fetch(begin, middle) + fetch(middle, end)

        items = fetch(start, now)
        records = [parse_minute(item, self.group_id) for item in items]
        invalid = sum(row is None for row in records)
        inserted = self.store.ingest([row for row in records if row is not None])
        self.store.collector_status(self.group_id, now.isoformat(),
                                    "Invalid minute records: " + str(invalid) if invalid else None, inserted)

    def lookup_countries(self):
        with self.store.lock:
            ips = [r[0] for r in self.store.db.execute(
                "SELECT DISTINCT ip FROM minutes WHERE ip IS NOT NULL AND ip NOT IN (SELECT ip FROM countries) LIMIT 100")]
        if not ips:
            return
        response = subprocess.run(["curl", "-fsS", "--max-time", "8", "-H", "Content-Type: application/json",
                                   "--data-binary", "@-", "https://api.country.is/"],
                                  input=json.dumps(ips), text=True, capture_output=True, timeout=10)
        if response.returncode:
            return
        countries = json.loads(response.stdout)
        with self.store.lock, self.store.db:
            for row in countries:
                country = row.get("country")
                if row.get("ip") in ips and (country is None or re.fullmatch(r"[A-Z]{2}", country)):
                    self.store.db.execute("INSERT OR REPLACE INTO countries VALUES (?,?)", (row["ip"], country))

    def run(self):
        while True:
            began = time.monotonic()
            try:
                self.poll()
                self.lookup_countries()
            except Exception as error:
                saved = self.store.collector_status(self.group_id)
                cursor = saved.get("cursor") or datetime.now(timezone.utc).isoformat()
                message = str(error) if isinstance(error, RuntimeError) else type(error).__name__
                self.store.collector_status(self.group_id, cursor, message)
                print("PS minute recording failed:", message, flush=True)
            time.sleep(max(1, 15 - (time.monotonic() - began)))
