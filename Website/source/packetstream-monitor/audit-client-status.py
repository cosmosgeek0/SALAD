#!/usr/bin/env python3
"""Read-only native-status census for PS1; never treat absent logs as failure."""
import concurrent.futures
from datetime import datetime, timedelta, timezone
import getpass
import json
import os
from pathlib import Path
import re
import subprocess


def collect():
    root = Path(__file__).resolve().parents[1]
    key = subprocess.check_output([str(root / ".runtime/keychain-store"), "--read", "--service",
                                   "salad-bandwidth-api", "--account", getpass.getuser()], text=True).strip()
    base = "https://api.salad.com/api/public/organizations/hyperlane"
    group = os.environ.get("PS_GROUP", "ps1")
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,61}[a-z0-9]", group):
        raise ValueError("Invalid PacketStream group name")
    now = datetime.now(timezone.utc)

    def api(path, body=None):
        cfg = "header = " + json.dumps("Salad-Api-Key: " + key) + '\nheader = "Content-Type: application/json"\n'
        if body is not None:
            cfg += "data-binary = " + json.dumps(json.dumps(body)) + "\n"
        result = subprocess.run(["curl", "-sS", "--max-time", "20", "--config", "-", "--write-out",
                                 "\n%{http_code}", base + path], input=cfg, text=True, capture_output=True, timeout=25)
        raw, code = result.stdout.rsplit("\n", 1)
        if result.returncode or code != "200":
            raise RuntimeError("Salad read failed HTTP " + code)
        return json.loads(raw)

    deployment = api("/projects/default/containers/" + group)
    expected_id = os.environ.get("PS_EXPECTED_GROUP_ID")
    if expected_id and deployment["id"] != expected_id:
        raise RuntimeError("PacketStream deployment identity changed")
    instances = api("/projects/default/containers/" + group + "/instances")["instances"]

    def one(instance):
        query = ('resource.type = "container" and resource.labels.container_group_name = "' + group + '" and '
                 'resource.labels.machine_id = "' + instance["machine_id"] + '" and text_log contains "Status:"')
        body = {"query": query, "start_time": (now-timedelta(minutes=10)).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                "end_time": now.isoformat(timespec="milliseconds").replace("+00:00", "Z"), "page_size": 100, "sort_order": "desc"}
        row = {"machine": instance["machine_id"], "instance_id": instance["id"], "salad_state": instance["state"],
               "salad_ready": instance.get("ready"), "version": instance["version"], "client_status": None}
        try:
            result = api("/log-entries", body)
            statuses = []
            for item in result.get("items", []):
                text = item.get("text_log", "")
                embedded = re.match(r'PS_NATIVE instance=([^ ]+) ', text)
                recorded_instance = embedded.group(1) if embedded else item.get("resource", {}).get("labels", {}).get("instance_id")
                if recorded_instance != instance["id"]:
                    continue
                match = re.search(r'time="([^" ]+)".*msg="(Status: [^"]+)"', text)
                if match:
                    statuses.append((match.group(1), item.get("time", ""), match.group(2)))
            if statuses:
                at, indexed_at, message = max(statuses)
                state = "running" if message == "Status: PacketStream is running" else "error" if "error" in message.lower() else "unknown"
                row["client_status"] = {"state": state, "message": message, "source_time": at, "indexed_at": indexed_at,
                                         "source": "Salad native client logs; exact current instance"}
            row["returned_log_records"] = len(result.get("items", []))
        except (RuntimeError, subprocess.TimeoutExpired, ValueError):
            row["query_failed"] = True
        return row

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(one, instances))
    for row in rows:
        status = row.get("client_status")
        row["client_status_age_seconds"] = None
        if status:
            row["client_status_age_seconds"] = (now-datetime.fromisoformat(status["source_time"].replace("Z", "+00:00"))).total_seconds()
    result = {"schema_version": 1, "checked_at": now.isoformat(), "group": "hyperlane/default/" + group,
              "group_id": deployment["id"], "group_state": deployment["current_state"], "country_codes": deployment.get("country_codes"), "desired_replicas": deployment["replicas"], "nodes": rows,
              "running_instances": sum(row["salad_state"] == "running" for row in rows),
              "ready_instances": sum(bool(row["salad_ready"]) for row in rows),
              "accepted_clients": sum(row.get("client_status", {}).get("state") == "running" and row["client_status_age_seconds"] is not None and -10 <= row["client_status_age_seconds"] < 600 for row in rows if row.get("client_status")),
              "network_available": False, "network_note": "Plain official client has no network-counter exporter; missing network values are not zero traffic.",
              "limitations": "Up to 100 latest indexed logs per current instance over ten minutes. Missing status is unknown, not zero traffic or rejected."}
    return result


def main():
    root = Path(__file__).resolve().parents[1]
    result = collect()
    path = root / ".runtime/ps1-monitor/independent-test/client-census-latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
