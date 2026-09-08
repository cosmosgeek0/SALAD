"""Operate only the SSH4 TraffMonetizer deployment; never print credentials."""
import argparse
import base64
import hashlib
from datetime import datetime, timezone
import getpass
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DATA = Path.home() / ".hg1/traffmonetizer"
ORGANIZATION = "ssh4"
GROUP = "tm-test-us"
GROUP_PATH = "/projects/default/containers/" + GROUP
IMAGE = "docker.io/cosmosgeek0/salad-bandwidth-stack@sha256:d75e26d28fbb9352829eb41440a38b59d5f9d3ecb4967cc0414bb3bbc50f1c2c"


def worker_command():
    source = (Path(__file__).parent / "worker.py").read_bytes()
    encoded = base64.b64encode(source).decode()
    command = ["/bin/sh", "-c", 'umask 077; printf "%s" "$@" | base64 -d > /tmp/tm-worker.py; exec python3 -u /tmp/tm-worker.py', "policy-start"]
    command.extend(encoded[i:i + 900] for i in range(0, len(encoded), 900))
    if len(command) > 100 or any(len(part) > 1000 for part in command):
        raise RuntimeError("Worker exceeds the verified Salad command envelope")
    return command


def keychain(service):
    return subprocess.check_output([str(ROOT / ".runtime/keychain-store"), "--read", "--service",
                                    service, "--account", getpass.getuser()], text=True).strip()


def api(path, method="GET", body=None, timeout=25):
    if not (path == "/projects/default/containers" or path == GROUP_PATH or path.startswith(GROUP_PATH + "/") or path == "/log-entries"):
        raise ValueError("Outside the SSH4 TraffMonetizer scope")
    key = keychain("salad-bandwidth-api")
    media = "application/merge-patch+json" if method == "PATCH" else "application/json"
    config = "header = " + json.dumps("Salad-Api-Key: " + key) + "\nheader = " + json.dumps("Content-Type: " + media) + "\n"
    if body is not None:
        config += "data-binary = " + json.dumps(json.dumps(body)) + "\n"
    result = subprocess.run(["curl", "-sS", "--max-time", str(timeout), "--config", "-", "--request", method,
        "--write-out", "\n%{http_code}", "https://api.salad.com/api/public/organizations/ssh4" + path],
        input=config, capture_output=True, text=True, timeout=timeout + 5)
    raw, status = result.stdout.rsplit("\n", 1)
    if result.returncode == 28:
        raise RuntimeError("Salad " + method + " " + path + " timed out after " + str(round(timeout, 1)) + " seconds")
    if result.returncode or not 200 <= int(status) < 300:
        raise RuntimeError("Salad " + method + " " + path + " returned HTTP " + status)
    return json.loads(raw) if raw.strip() else {}


def safe_group(group):
    return {key: group.get(key) for key in ("id", "name", "version", "replicas", "country_codes", "current_state")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "scale", "update", "status"))
    parser.add_argument("--replicas", type=int, default=10)
    args = parser.parse_args()
    if not 1 <= args.replicas <= 10:
        parser.error("This task is authorized for one through ten workers")
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    record = DATA / "deployment.json"
    if args.action == "create":
        if record.exists() or (DATA / "traffic.sqlite3").exists():
            raise RuntimeError("Existing deployment or history: inspect and restore it; create cannot reset the experiment")
        if any(group["name"] == GROUP for group in api("/projects/default/containers").get("items", [])):
            raise RuntimeError("TraffMonetizer group already exists; inspect it instead")
        from observer import provider_request
        baseline_at = datetime.now(timezone.utc)
        balance = provider_request("/api/app_user/get_balance")["data"]
        days = provider_request("/api/dashboard/get_graph_stat?period=month")
        if datetime.now(timezone.utc).date() != baseline_at.date():
            raise RuntimeError("UTC date changed during baseline capture; retry before creating")
        selected = [day for day in days if day["date"] >= baseline_at.date().isoformat()]
        payload = {"name": GROUP, "display_name": "TM", "replicas": args.replicas,
            "autostart_policy": False, "restart_policy": "always", "country_codes": ["us"],
            "container": {"image": IMAGE, "command": worker_command(), "priority": "batch", "resources": {"cpu": 1, "memory": 1024},
                          "environment_variables": {"TM_TOKEN": keychain("salad-traffmonetizer-token")}}}
        try:
            group = api("/projects/default/containers", "POST", payload)
        except RuntimeError:
            group = api(GROUP_PATH)
            if (group.get("container", {}).get("image") != IMAGE or group.get("container", {}).get("command") != worker_command() or group.get("country_codes") != ["us"]
                    or group.get("container", {}).get("environment_variables", {}).get("TM_TOKEN") != payload["container"]["environment_variables"]["TM_TOKEN"]):
                raise RuntimeError("Uncertain create response did not match this deployment") from None
        saved = {"organization": ORGANIZATION, "project": "default", "group": GROUP, "group_id": group["id"],
                 "image": IMAGE, "started_at": baseline_at.isoformat(), "measurement_started_ms": int(datetime.now(timezone.utc).timestamp() * 1000),
                 "desired_replicas": args.replicas, "provider_baseline_usd": balance["balance"],
                 "provider_baseline_bytes": sum(day["traffic"] for day in selected),
                 "provider_baseline_earned_usd": sum(day["earning"] for day in selected),
                 "provider_baseline_source": "Fresh account API reading before starting this deployment"}
        record.write_text(json.dumps(saved, indent=2))
        record.chmod(0o600)
        api(GROUP_PATH + "/start", "POST")
    else:
        group = api(GROUP_PATH)
        if not record.exists() or json.loads(record.read_text())["group_id"] != group["id"]:
            raise RuntimeError("Deployment identity does not match this task")
        if args.action == "scale":
            if group["container"]["image"] != IMAGE or group.get("pending_change"):
                raise RuntimeError("The runtime image update is still applying; do not expand the old runtime")
            api(GROUP_PATH, "PATCH", {"replicas": args.replicas})
            group = api(GROUP_PATH)
            if group["replicas"] != args.replicas:
                raise RuntimeError("Replica change was not confirmed")
        if args.action == "update":
            api(GROUP_PATH, "PATCH", {"container": {"image": IMAGE, "command": worker_command()}})
            group = api(GROUP_PATH)
            if group["container"]["image"] != IMAGE or group["container"].get("command") != worker_command():
                if group.get("pending_change"):
                    print("Image update accepted and still preparing; verify the applied runtime before scaling.")
                    print(json.dumps(safe_group(group), indent=2))
                    return
                raise RuntimeError("Image update was not confirmed")
            saved = json.loads(record.read_text())
            saved["image"] = IMAGE
            saved["worker_sha256"] = hashlib.sha256((Path(__file__).parent / "worker.py").read_bytes()).hexdigest()
            record.write_text(json.dumps(saved, indent=2))
    print(json.dumps(safe_group(group), indent=2))
    print("instances", json.dumps([{key: value.get(key) for key in ("id", "machine_id", "state", "version", "ready")}
                                   for value in api(GROUP_PATH + "/instances").get("instances", [])]))


if __name__ == "__main__":
    main()
