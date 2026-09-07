import json
import os
import signal
import subprocess
import sys
import uuid

email = os.environ.pop("PAWNS_EMAIL")
password = os.environ.pop("PAWNS_PASSWORD")
device = os.environ.get("SALAD_INSTANCE_ID") or str(uuid.uuid4())
payload = {"email": email, "password": password, "identifier": device}
config = 'header = "Content-Type: application/json"\nheader = "X-Locale: EN"\nheader = "X-App-Version: 2.0.0"\nheader = "X-App-OS: Windows"\n'
config += "data-binary = " + json.dumps(json.dumps(payload)) + "\n"
response = subprocess.run(["curl", "-sS", "--max-time", "30", "--config", "-", "--write-out", "\n%{http_code}",
                           "https://api.pawns.app/api/v1/users/tokens"], input=config, text=True, capture_output=True)
raw, status = response.stdout.rsplit("\n", 1)
data = json.loads(raw)
token = data.get("access_token")
if response.returncode or status != "200" or not token:
    message = str(data.get("message", data.get("error", "No access token returned")))
    for secret in (email, password):
        message = message.replace(secret, "[redacted]")
    print("Pawns login failed: HTTP " + status + " " + message, flush=True)
    sys.exit(1)
print("PAWNS_LOGIN authenticated", flush=True)
os.environ.update(PAWNS_ACCESS_TOKEN=token, PAWNS_DEVICE_ID=device)
child = subprocess.Popen(["/usr/lib/wine/wine64", "Z:\\app\\runner.exe"], stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, bufsize=1)
signal.signal(signal.SIGTERM, lambda *_: child.terminate())
signal.signal(signal.SIGINT, lambda *_: child.terminate())
for line in child.stdout:
    for secret in (email, password, token):
        line = line.replace(secret, "[redacted]")
    print(line, end="", flush=True)
    if line.startswith("PAWNS_SDK "):
        event = json.loads(line.removeprefix("PAWNS_SDK "))
        if event.get("name") == "not_running" and event.get("parameters", {}).get("error") == "ip_used":
            child.terminate()
            result = subprocess.run(["curl", "--noproxy", "*", "-sS", "--max-time", "10", "-o", "/dev/null",
                "--write-out", "%{http_code}", "-H", "Metadata: true", "-H", "Content-Type: application/json",
                "--data", '{"reason":"Pawns SDK rejected this IP as already sharing"}',
                "http://169.254.169.254/v1/reallocate"], text=True, capture_output=True)
            print("PAWNS_REALLOCATE reason=ip_used http=" + result.stdout.strip(), flush=True)
            sys.exit(75)
sys.exit(child.wait())
