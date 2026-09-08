#!/usr/bin/env python3
"""Start only the PS1 recorder on macOS, without starting Docker or other apps."""
import getpass
import json
import os
from pathlib import Path
import subprocess
import sys
import runpy


def main():
    root = Path(__file__).resolve().parent
    target_file = Path.home()/".hg1/packetstream/observer-target.json"
    if target_file.exists():
        target = json.loads(target_file.read_text())
        if target.get("mode") == "native-census":
            os.environ["PS_GROUP"] = target["group"]
            os.environ["PS_EXPECTED_GROUP_ID"] = target["group_id"]
            runpy.run_path(str(root/"packetstream-monitor/native-census.py"), run_name="__main__")
            return
    helper = root / ".runtime/keychain-store"
    key = subprocess.check_output([str(helper), "--read", "--service", "salad-bandwidth-api",
                                   "--account", getpass.getuser()], text=True).strip()
    if not key:
        raise RuntimeError("Salad credential is unavailable")
    config = "header = " + json.dumps("Salad-Api-Key: " + key) + "\n"
    result = subprocess.run(["/usr/bin/curl", "-sS", "--max-time", "20", "--config", "-",
                             "--write-out", "\n%{http_code}",
                             "https://api.salad.com/api/public/organizations/hyperlane/projects/default/containers/ps1"],
                            input=config, text=True, capture_output=True, timeout=25)
    raw, code = result.stdout.rsplit("\n", 1)
    if result.returncode or code != "200":
        raise RuntimeError("PS1 configuration could not be read")
    group = json.loads(raw)
    if group.get("id") != "1c7c9cbd-0cc2-4f10-a1ad-76f56d7492ba":
        raise RuntimeError("PS1 deployment identity changed")
    env = group["container"]["environment_variables"]
    if env.get("CID") != "8ExP" or len(env.get("PS_STREAM_TOKEN", "")) < 32:
        raise RuntimeError("PS1 recorder configuration changed")
    data = Path.home() / ".hg1/packetstream/network"
    data.mkdir(parents=True, exist_ok=True)
    child_env = os.environ.copy()
    child_env.update(SALAD_API_KEY=key, PS_STREAM_TOKEN=env["PS_STREAM_TOKEN"],
                     PS_ORGANIZATION="hyperlane", PS_GROUP="ps1")
    executable = str(root / "ps1-collector")
    print("Starting native PS1 device recorder on 127.0.0.1:8789", flush=True)
    os.execve(executable, [executable, "-data", str(data), "-listen", "127.0.0.1:8789"], child_env)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Never emit the provider response or credentials into service logs.
        print("PS1 native recorder could not start:", type(exc).__name__, file=sys.stderr)
        sys.exit(1)
