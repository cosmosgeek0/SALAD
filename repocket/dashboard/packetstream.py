"""Paid-traffic readings and deployment membership for the PS dashboard.

Billing values come only from the authenticated provider page. Interface counters
are used for node identity, never converted into credited traffic.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import secrets
import subprocess
import threading
import time
from urllib.parse import quote


def millis(value):
    if not value:
        return 0
    normalized = re.sub(r"(\.\d{6})\d+", r"\1", value.replace("Z", "+00:00"))
    return int(datetime.fromisoformat(normalized).timestamp() * 1000)


def paid_window(readings, start, end):
    selected = [r for r in readings if start <= r["time_ms"] <= end]
    # Rounded historical display readings must not be mixed with exact provider
    # byte records. Use the newest available measurement basis within the window.
    if selected:
        basis = selected[-1].get("basis", "display_gb")
        selected = [r for r in selected if r.get("basis", "display_gb") == basis]
    result = {"readings": selected, "mb": None, "mb_per_minute": None,
              "first_ms": None, "last_ms": None, "error": None}
    if len(selected) < 2:
        result["error"] = "Two provider readings are needed in this period."
        return result
    first, last = selected[0], selected[-1]
    result.update(first_ms=first["time_ms"], last_ms=last["time_ms"])
    if any(b["gb"] < a["gb"] for a, b in zip(selected, selected[1:])):
        result["error"] = "The provider's rolling counter decreased; this period cannot be measured reliably."
        return result
    amount = round((last["gb"] - first["gb"]) * 1000, 6)
    elapsed = last["time_ms"] - first["time_ms"]
    if elapsed <= 0:
        result["error"] = "The provider readings have no elapsed time."
        return result
    result.update(mb=amount, mb_per_minute=amount * 60000 / elapsed)
    return result


def ordered_nodes(raw_nodes, members, restart_ms, countries):
    newest = {}
    for n in raw_nodes:
        if n["start"] > newest.get(n["machine"], {}).get("start", -1):
            newest[n["machine"]] = n
    rows = []
    for n in raw_nodes:
        current = (n["machine"] in members and newest[n["machine"]]["run"] == n["run"]
                   and n["start"] * 1000 >= restart_ms - 2000)
        receipt_age, source_age = n.get("sample_age_ms"), n.get("source_sample_age_ms")
        sample_source = n.get("sample_source")
        receipt_limit = 25000 if sample_source == "salad_logs_10s" else 15000
        fresh = (n.get("samples", 0) > 0 and isinstance(receipt_age, (int, float)) and 0 <= receipt_age <= receipt_limit
                 and isinstance(source_age, (int, float)) and -15000 <= source_age <= 60000)
        rows.append({"run": n["run"], "machine": n["machine"], "ip": n["ip"],
                     "start_ms": n["start"] * 1000, "current": current,
                     "state": members[n["machine"]] if current else "previous",
                     "observed_network_mb": n.get("mb") if n.get("samples", 0) > 0 else None,
                     "network_sample_age_ms": receipt_age if receipt_age is not None else -1,
                     "network_source_age_ms": source_age,
                     "network_sample_fresh": bool(fresh), "sample_source": sample_source,
                     "source_granularity_seconds": n.get("source_granularity_seconds"),
                     "country": "United States" if countries == ["us"] else " / ".join(countries),
                     "country_source": "Salad deployment placement"})
    for machine, state in members.items():
        if not any(r["machine"] == machine and r["current"] for r in rows):
            rows.append({"run": machine + "/pending", "machine": machine, "ip": "",
                         "start_ms": 0, "current": True, "state": state,
                         "observed_network_mb": None, "network_sample_age_ms": -1,
                         "network_source_age_ms": None, "network_sample_fresh": False,
                         "sample_source": None, "source_granularity_seconds": None,
                         "country": "United States" if countries == ["us"] else " / ".join(countries),
                         "country_source": "Salad deployment placement"})
    return sorted(rows, key=lambda n: (not n["current"], -n["start_ms"], n["machine"]))


class PacketStreamView:
    def __init__(self, runtime: Path, key_provider):
        self.runtime = Path(runtime)
        self.runtime.mkdir(parents=True, exist_ok=True)
        self.key_provider = key_provider
        self.target = {name: os.environ.get(env, "").strip() or fallback for name, env, fallback in (
            ("organization", "PS_ORGANIZATION", "hyperlane"),
            ("project", "PS_PROJECT", "default"), ("group", "PS_GROUP", "ps1"))}
        target_key = "/".join(self.target.values())
        # Retain the original group's history without mixing it into replacement
        # deployments, whose current test must begin at their own start time.
        period_name = ("dashboard-periods.json" if target_key == "hyperlane/default/ps1"
                       else "dashboard-periods-" + quote(target_key, safe="") + ".json")
        self.periods_path = self.runtime / period_name
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.RLock()
        self.metadata = {}
        self.members = {}
        self.metadata_at = 0
        self.error = "Checking Salad deployment…"
        self.periods = {}
        self.last_bridge_ms = 0
        self.stop_event = threading.Event()
        try:
            self.periods = {p["id"]: p for p in json.loads(self.periods_path.read_text())}
        except (ValueError, OSError, KeyError):
            pass
        # These saved snapshots preserve starts/stops already observed before this UI.
        for path in sorted(self.runtime.glob("status-*.json")):
            try:
                value = json.loads(path.read_text())
                if value.get("name") == self.target["group"]:
                    self.remember_period(value)
            except (ValueError, OSError):
                pass

    def remember_period(self, group):
        state = group.get("current_state", {})
        start = millis(state.get("start_time"))
        if not start:
            return
        if state.get("status") == "stopped" and millis(state.get("finish_time")) <= start:
            self.periods.pop(str(start), None)
            return
        item = self.periods.setdefault(str(start), {"id": str(start), "start_ms": start, "end_ms": None})
        if state.get("status") == "stopped":
            finish = millis(state.get("finish_time"))
            if finish > start:
                item["end_ms"] = finish
        for other in self.periods.values():
            if other["start_ms"] < start and other["end_ms"] is None:
                other["end_ms"] = start

    def fetch_metadata(self):
        base = ("https://api.salad.com/api/public/organizations/" + quote(self.target["organization"], safe="")
                + "/projects/" + quote(self.target["project"], safe="")
                + "/containers/" + quote(self.target["group"], safe=""))
        key = self.key_provider()
        def get(path):
            config = "header = " + json.dumps("Salad-Api-Key: " + key) + "\n"
            response = subprocess.run(["/usr/bin/curl", "-sS", "--max-time", "10", "--config", "-",
                                       "--write-out", "\n%{http_code}", path],
                                      input=config, capture_output=True, text=True, timeout=12)
            raw, code = response.stdout.rsplit("\n", 1)
            if response.returncode or code != "200":
                raise ValueError("Salad request failed")
            return json.loads(raw)
        try:
            group, instances = get(base), get(base + "/instances")
            with self.lock:
                self.metadata = {k: group.get(k) for k in ("name", "display_name", "current_state", "country_codes", "version")}
                self.members = {n["machine_id"]: n["state"] for n in instances["instances"]}
                self.metadata_at = int(time.time() * 1000)
                self.error = None
                self.remember_period(group)
                self.periods_path.write_text(json.dumps(list(self.periods.values())))
        except Exception:
            with self.lock:
                self.error = "Salad membership could not be refreshed."

    def run(self):
        while not self.stop_event.is_set():
            self.fetch_metadata()
            self.stop_event.wait(15)

    def readings(self):
        values = {}
        path = self.runtime / "provider-observations.jsonl"
        if not path.exists():
            return []
        for line in path.read_text().splitlines():
            try:
                value = json.loads(line)
                stamp = millis(value.get("recorded_at") or value.get("observed_at"))
                gb = float(value["traffic_sold_gb"])
                if stamp and math.isfinite(gb) and gb >= 0:
                    values[stamp] = {"time_ms": stamp, "gb": gb,
                                     "basis": "provider_bytes" if "provider_bytes" in value else "display_gb"}
            except (KeyError, ValueError, TypeError):
                pass
        return sorted(values.values(), key=lambda r: r["time_ms"])

    def ingest(self, body):
        now = int(time.time() * 1000)
        gb, stamp = float(body["gb"]), int(body["time_ms"])
        provider_bytes = body.get("bytes")
        if provider_bytes is not None:
            if not isinstance(provider_bytes, int) or not 0 <= provider_bytes <= 10**18:
                raise ValueError("Invalid provider bytes")
            gb = provider_bytes / 1e9
        if not math.isfinite(gb) or not 0 <= gb <= 1e9 or abs(now - stamp) > 120000:
            raise ValueError("Invalid provider reading")
        with self.lock:
            self.last_bridge_ms = now
            previous = self.readings()
            if previous and stamp - previous[-1]["time_ms"] < 10000:
                return
            record = {"observed_at": datetime.fromtimestamp(stamp / 1000, timezone.utc).isoformat(),
                      "traffic_sold_gb": gb, "source": "Authenticated PacketStream browser feed"}
            if provider_bytes is not None:
                record["provider_bytes"] = provider_bytes
            with (self.runtime / "provider-observations.jsonl").open("a") as out:
                out.write(json.dumps(record) + "\n")

    def snapshot(self, raw, start=None, end=None):
        now = int(time.time() * 1000)
        with self.lock:
            state = self.metadata.get("current_state", {})
            restart = millis(state.get("start_time"))
            start = restart if start is None else start
            end = now if end is None else end
            readings = self.readings()
            countries = self.metadata.get("country_codes") or ["us"]
            return {"time_ms": now, "target": dict(self.target), "restart_ms": restart, "status": state.get("status", "unknown"),
                    "running_nodes": sum(s == "running" for s in self.members.values()),
                    "membership_age_ms": now - self.metadata_at, "membership_error": self.error,
                    "nodes": ordered_nodes(raw.get("nodes", []), self.members, restart, countries),
                    "periods": sorted(self.periods.values(), key=lambda r: -r["start_ms"]),
                    "billing": paid_window(readings, start, end), "window": {"start_ms": start, "end_ms": end},
                    "recent_billing": paid_window(readings, max(restart, readings[-1]["time_ms"] - 301000), readings[-1]["time_ms"]) if readings else None,
                    "latest_reading": readings[-1] if readings else None,
                    "feed_age_ms": now - self.last_bridge_ms if self.last_bridge_ms else None,
                    "bridge_token": self.token}
