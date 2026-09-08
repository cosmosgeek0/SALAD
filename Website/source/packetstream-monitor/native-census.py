#!/usr/bin/env python3
"""Continuously record native PS client acceptance without changing cloud clients."""
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import time
from dashboard.packetstream import period_path, remember_period


def main():
    source = Path(__file__).with_name("audit-client-status.py")
    spec = importlib.util.spec_from_file_location("ps_native_audit", source)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    network_spec = importlib.util.spec_from_file_location("ps_native_network", Path(__file__).with_name("native-network.py"))
    network_module = importlib.util.module_from_spec(network_spec)
    network_spec.loader.exec_module(network_module)
    network = network_module.NetworkObserver(Path(__file__).resolve().parents[1], os.environ["PS_GROUP"], os.environ["PS_EXPECTED_GROUP_ID"])
    target = Path.home()/".hg1/packetstream/native-census.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    periods_file = period_path(target.parent, "hyperlane/default/" + os.environ["PS_GROUP"])
    periods = {p["id"]: p for p in json.loads(periods_file.read_text())} if periods_file.exists() else {}
    for path in sorted(target.parent.glob("status-*.json")):
        try:
            value = json.loads(path.read_text())
            if value.get("name") == os.environ["PS_GROUP"]:
                remember_period(periods, value.get("current_state", {}))
        except (ValueError, OSError):
            pass
    saved_periods = periods_file.read_text() if periods_file.exists() else ""
    last = {}
    while True:
        started = time.monotonic()
        try:
            result = audit.collect()
            remember_period(periods, result["group_state"])
            period_text = json.dumps(list(periods.values()))
            if period_text != saved_periods:
                temporary = periods_file.with_suffix(".tmp")
                temporary.write_text(period_text)
                os.replace(temporary, periods_file)
                saved_periods = period_text
            network.update_members(result["nodes"])
            measurements = network.snapshots()
            for node in result["nodes"]:
                node["network"] = measurements.get(node["instance_id"], {"available": False, "reason": "Waiting for the first minute record"})
                node["ip"] = node["network"].get("ip")
            result["network_available"] = any(node["network"]["available"] for node in result["nodes"])
            result["network_note"] = "Minute records from each container are saved in minutes.sqlite3. Missing records are not zero traffic."
            result["last_success_at"] = result["checked_at"]
            result["poll_interval_seconds"] = 30
            last = result
        except Exception as error:
            result = dict(last, poll_error=type(error).__name__,
                          poll_failed_at=datetime.now(timezone.utc).isoformat(),
                          network_available=False)
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(result, indent=2))
        os.replace(temporary, target)
        time.sleep(max(1, 30-(time.monotonic()-started)))


if __name__ == "__main__":
    main()
