# Pawns app — rebuild and run on Salad in the United States

Keep a copy of this file somewhere outside the project too. It contains the complete source and instructions needed to recreate this deployment after the other project files or its Docker image are deleted. The build downloads its operating-system packages and the official Pawns SDK from the internet; you supply your own accounts and passwords.

The computer prepares and uploads a Docker image. Salad runs that image on a US machine. Once Salad is running it, your computer does not need to stay on.

## What this runs

The successful implementation uses the native SDK bundled in the **official Pawns Windows consumer application**, running through Wine inside a Linux container. Wine supplies the Windows runtime. A small launcher signs into the ordinary Pawns consumer account and gives the returned token to that SDK.

**A separate partner/developer API key was not needed for the measured working deployment.** The original `iproyal/pawns-cli` image and tested older releases rejected login with `authenticate user failed (please use SDK)`. Use the image built below; its login path is different.

Historical measured proof, September 7, 2026: the SDK reported `running` on Salad, Pawns displayed the same device as **Active**, and an IP lookup executed inside that container returned `45.47.50.142`, Liverpool, New York, country `US`. This is a past verification, not a promise that this IP or instance still exists. Follow the live verification steps below after every deployment.

## What you need

- A Mac with an internet connection. The Terminal commands below also use ordinary Bash-compatible syntax on Linux. On Windows, use a Linux terminal through WSL rather than PowerShell for these commands.
- [Docker Desktop](https://docs.docker.com/desktop/setup/install/mac-install/) installed and running. On a Mac, choose the download for Apple silicon or Intel to match **Apple menu → About This Mac**.
- A [Docker Hub account](https://hub.docker.com/) and permission to create a public image repository in it. Docker Hub stores the image so Salad can download it.
- A [SaladCloud account](https://portal.salad.com/organizations), billing set up, and access to the organization/project where it will run. Running containers incur Salad charges; inspect the portal's current estimate before deploying.
- An ordinary [Pawns account](https://dashboard.pawns.app/internet-sharing) with its Pawns email and password. These are different from your Docker Hub or Salad credentials. A browser already being signed in does not supply the container's password.

The steps below reproduce the measured configuration: **one replica, one vCPU, 1 GB memory, US only**. They do not scale it to a fleet.

## Prepare Terminal

On your Mac, open **Applications → Utilities → Terminal**. Paste a command block into Terminal, then press **Return**. Do not copy the surrounding Markdown backticks. Keep the same Terminal window open through building and uploading.

Open Docker Desktop and wait until its engine is running. Check it:

```sh
docker info
```

If Terminal says `docker: command not found`, finish installing Docker Desktop and open a new Terminal window. If it cannot connect to the Docker daemon, start Docker Desktop before continuing.

Create/open the Desktop project folder:

```sh
mkdir -p "$HOME/Desktop/salad"
cd "$HOME/Desktop/salad"
```

## Recreate all source files

Paste this entire block into Terminal. It creates the `pawns` folder and writes its complete Dockerfile, C bridge and Python launcher. It overwrites those three files if they already exist; use it when restoring this documented implementation.

No existing code, old chat, private helper program, saved API token, or previously built image is needed for this block.

```sh
mkdir -p pawns
cat > pawns/Dockerfile <<'PAWNS_DOCKERFILE'
FROM debian:trixie-slim@sha256:d7e12182ce18b85b93007c1dedf31f2d29e01ccf3182cc4017c709b6259bc132 AS build
RUN apt-get update && apt-get install -y --no-install-recommends gcc-mingw-w64-x86-64-posix curl ca-certificates 7zip
WORKDIR /build
RUN curl -fsSL --max-time 120 'https://cdn.pawns.app/download/app/releases/windows/latest/Pawns%20Setup.exe' -o installer.exe \
    && echo '222a36ac1970c2c30acef5403fc7eacef16c48c71b3585cbc1ee3eb92789c3ea  installer.exe' | sha256sum -c - \
    && 7z e installer.exe '$PLUGINSDIR/app-64.7z' \
    && 7z e app-64.7z resources/app.asar.unpacked/resources/libpawns/libpawns.dll \
    && echo 'ae96cb849ab0903883eac5059db283660b56ba725f185749a994dd6ea63a3ebb  libpawns.dll' | sha256sum -c -
COPY runner.c .
RUN x86_64-w64-mingw32-gcc runner.c -Os -s -o runner.exe

FROM debian:trixie-slim@sha256:d7e12182ce18b85b93007c1dedf31f2d29e01ccf3182cc4017c709b6259bc132
RUN apt-get update && apt-get install -y --no-install-recommends wine64 python3 curl ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build /build/runner.exe /build/libpawns.dll /app/
COPY run.py .
ENV WINEDEBUG=-all WINEARCH=win64 WINEPREFIX=/tmp/pawns-wine
ENTRYPOINT ["python3", "-u", "/app/run.py"]
PAWNS_DOCKERFILE

cat > pawns/runner.c <<'PAWNS_RUNNER_C'
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef void (*Initialize)(const char *, const char *, const char *, const char *, const char *);
typedef void (*Start)(const char *, void (*)(char *));

static void report(char *data) {
    printf("PAWNS_SDK %s\n", data);
    fflush(stdout);
}

int main(void) {
    HMODULE library = LoadLibraryA("Z:\\app\\libpawns.dll");
    if (!library) {
        fprintf(stderr, "SDK load failed: Windows error %lu\n", GetLastError());
        return 1;
    }
    Initialize initialize = (Initialize)GetProcAddress(library, "Initialize");
    Start start = (Start)GetProcAddress(library, "StartMainRoutine");
    if (!initialize || !start || !getenv("PAWNS_ACCESS_TOKEN") || !getenv("PAWNS_DEVICE_ID")) return 1;
    initialize("pawnsapp-gui", "2.0.0", getenv("PAWNS_DEVICE_ID"), "windows", "https://bootstrap.pawns.app");
    start(getenv("PAWNS_ACCESS_TOKEN"), report);
    Sleep(INFINITE);
}
PAWNS_RUNNER_C

cat > pawns/run.py <<'PAWNS_RUN_PY'
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
PAWNS_RUN_PY
```

The files have these jobs:

| File | What it does |
|---|---|
| `pawns/Dockerfile` | Downloads the official Windows installer, verifies its checksum, extracts and verifies the SDK DLL, compiles the bridge, and packages everything with Wine and Python. |
| `pawns/runner.c` | `main()` loads the official SDK and starts it; `report()` prints its status callbacks. The process waits while the SDK works. |
| `pawns/run.py` | Reads the Pawns credentials from environment variables, signs in, starts the SDK through Wine, redacts credentials from its output, forwards shutdown, and requests a new Salad machine after an `ip_used` rejection. |

The source is the measured working implementation. The installer URL and hashes pin the official package tested for this version. If the vendor changes that download, the checksum check stops the build; see the troubleshooting section instead of deleting the checks.

## Build and upload your own image

In Docker Hub, choose **Create repository**. Name it `salad-pawns` and make it **Public**. This image contains the program and public SDK, not your Pawns password. Your Pawns login is entered in Salad later.

In the same Terminal window, sign into Docker Hub and follow its browser sign-in instructions:

```sh
docker login
```

Continue only after Docker confirms the login succeeded. Set the image name by entering your **Docker Hub username** when prompted. Do not enter an email address, password, or the literal word `YOUR_USERNAME`:

```sh
printf 'Your Docker Hub username: '
IFS= read -r PAWNS_DOCKER_USER
```

Type your username, press **Return**, and only then paste the next block. It names and builds the image. Keep `--platform linux/amd64` even if your Mac has an Apple chip: this is the platform used by the verified Salad runtime.

```sh
PAWNS_IMAGE="$PAWNS_DOCKER_USER/salad-pawns:consumer"
docker build --platform linux/amd64 --tag "$PAWNS_IMAGE" ./pawns
```

Wait for the command to finish successfully and return to the prompt. If it reports an error, resolve that error before uploading. Then upload:

```sh
docker push "$PAWNS_IMAGE"
```

After a successful push, print the image reference you will paste into Salad:

```sh
printf 'docker.io/%s\n' "$PAWNS_IMAGE"
```

It will look like `docker.io/YOUR_DOCKER_HUB_USERNAME/salad-pawns:consumer`, with your real Docker Hub username. Use the actual line Terminal printed.

The historically verified deployment used this immutable image reference; it is a useful reference if that image still exists, but rebuilding from this file does not depend on it:

```text
docker.io/cosmosgeek0/salad-bandwidth-stack@sha256:8ab6172cf1b34045f5ec75b5f50eacd5b31815ecc9e72fd6ef531767c35f021b
```

## Deploy in Salad — US only

For the original owner's account, the target is [cosmosgeeketh → Default → Container Groups](https://portal.salad.com/organizations/cosmosgeeketh/projects/default/containers). Another operator should choose an organization and project they own or are authorized to use.

If a group called **pawns** already exists, open it first. To update that existing group, stop it, wait until its instances are gone, choose **Edit**, apply the settings below, save, then start it. Do not create a second group with the same job merely because the local source folder was deleted.

If the group was deleted, choose **Deploy a Container Group → Custom Container Group → Get Started**, then follow these screens:

1. **Cloud:** select **SaladCloud Community — CPU only**.
2. **Resources:** set **1 vCPU** and **1 GB memory**. Leave the default shared memory and no additional disk reservation. This matches the verified workload.
3. **Allowed Countries:** click **Edit** and select **United States only**. Remove any other selections. The summary must not say **All**. The underlying verified setting is `country_codes: ["us"]`; an empty list allows arbitrary countries. [Salad's country-setting reference](https://docs.salad.com/reference/saladcloud-api/container-groups/get-container-group).
4. **Container Configuration:** enter the settings in the table below. Click **Configure** inside each editor to save its entries.
5. **Networking:** leave **Container Gateway** disabled. The client uses outgoing connections; this setup needs no public HTTP port.
6. **Health Probes & Logging:** leave the additional probes and external logging disabled, as in the verified deployment. Native container logs are available in Salad. Enable **Autostart container group once image is pulled** if offered.
7. Recheck **United States only** and the current cost estimate. Click **Deploy**. If the prepared group ends up **Stopped**, click **Start**.

| Setting | Enter/select |
|---|---|
| Container Group Name | `pawns` |
| Image Name | The `docker.io/.../salad-pawns:consumer` reference printed after your successful push |
| Registry | **Public Registry** |
| Replicas | `1` |
| Environment variable key | `PAWNS_EMAIL` |
| Its value | Your actual Pawns account email, without quotes or an `-email=` prefix |
| Another environment variable key | `PAWNS_PASSWORD` |
| Its value | Your actual Pawns account password, without surrounding quotes or a `-password=` prefix |
| Command | **Empty / None Configured** — remove any old command override |
| GPU | None — use the CPU-only cloud |

**Do not put passwords in this Markdown file, the Dockerfile, a Docker build command, or an image tag.** Enter them only as runtime environment variables in your Salad group. The launcher constructs JSON, so leave special characters in the password unchanged.

The tested group uses the CPU batch priority and `restart_policy: "always"`. Retain the CPU-only/default restart configuration. Do not copy the old CLI command `/pawns-cli -email=... -password=...` into this new image: leaving Command empty runs the Python launcher built into it.

## Verify that it really works

A group can say **Running** while its client has failed. Check all of the following.

**Container:** open **pawns → Instances**. A current instance should be **Running / Ready**. Allocating, downloading and creating are preparation states, not proof that Pawns is sharing.

**Client:** copy the current instance's **Machine ID** from its details. Open **Container Logs**, put that ID in the **Machine Id** filter, and inspect messages after this instance started. Refresh the query. The successful run produced these messages; timestamp values will differ:

```text
PAWNS_LOGIN authenticated
PAWNS_SDK {"happened_at":"...","name":"starting","parameters":{}}
PAWNS_SDK {"happened_at":"...","name":"running","parameters":{}}
```

`authenticated` means login succeeded. The SDK's `running` callback is the additional evidence that it accepted the sharing connection. Read later messages too: a later `not_running` changes that status.

**Country:** click the current instance and open its **Terminal**. Wait for **Successfully Connected**, paste this command, then press **Return**:

```sh
curl -fsS --max-time 15 https://ipinfo.io/json
```

The response must report `"country": "US"`. Note the `ip` value. This is an IP-geolocation lookup from inside the running container, not your Mac's location. Do not use Salad's SSH relay address as the worker's sharing IP.

**Provider:** sign into [Pawns → Internet Sharing](https://dashboard.pawns.app/internet-sharing), click **Refresh**, and find that same IP marked **Active**. The device is displayed as **windows**, because it is the official Windows SDK running through Wine. Old test devices can remain listed as Inactive.

If the IP is not US, stop the group, correct **Allowed Countries** to United States only, then restart and repeat the check. Do not accept a non-US Active device as a successful deployment.

These checks verify connection and placement. They do not measure paid bandwidth or profit; use Pawns' credited earnings for those, rather than assuming all container network bytes are billable.

## If something goes wrong

| What you see | What to do |
|---|---|
| `authenticate user failed (please use SDK)` | This was the old CLI's observed failure. Verify that Salad uses the image built by this guide, Command is empty, and the environment keys are `PAWNS_EMAIL` and `PAWNS_PASSWORD`. The guide's consumer login endpoint successfully authenticated the tested account. |
| `Pawns login failed: HTTP ...` | Read the actual error. Recheck the Pawns account credentials in Salad; a saved browser session alone does not verify the password. Stop a repeatedly failing group before correcting it. Do not post its password or tokens in chat/logs. |
| SDK `not_running` with `"error":"ip_used"` | The assigned public IP is already sharing through Pawns. This code requests a replacement through Salad IMDS and prints `PAWNS_REALLOCATE reason=ip_used http=...`. A successful HTTP response confirms the request, not that the replacement has finished. Watch the new instance and repeat verification. If no replacement follows, use **Instances → Reallocate** for that failed instance. |
| Long **Allocating** state | Keep US-only selected. Inspect **System Events** for progress or a stated failure. A stop/start retry was used during the measured US deployment; allocation still depended on Salad finding a machine. Do not change countries to All to make it start sooner. |
| **Downloading / Creating** | Wait for the image to finish downloading and the process to start; check System Events. This is not a Pawns authentication result. |
| Local Mac runtime exits with `rosetta error: invalid gdt selector index 5` | This occurred while attempting to run the Windows SDK in an emulated AMD64 container on Apple silicon. Building there succeeded; the same SDK ran successfully on Salad's AMD64 machine. Use the Mac for building and Salad for running, as this guide does. |
| Wine prints `XDG_RUNTIME_DIR is invalid` or a `syswow64/rundll32.exe` warning | These warnings occurred in a run that subsequently reached SDK `running`. Determine success from the SDK's latest state and the matching Active device, not from these warnings alone. |
| Build reports a checksum mismatch | The downloaded vendor artifact differs from the pinned package. Verify the official current package, native library and interface before updating the hashes/source. Do not simply remove the checksum checks and assume the replacement behaves identically. |
| Push is denied | Sign into the Docker Hub account that owns the username in `PAWNS_IMAGE`, and verify its `salad-pawns` repository is Public. Repeat the failed push after correcting access. |

Recovery evidence is deliberately precise: an `ip_used` rejection was observed, and **manual reallocation** led to a working node. Automatic handling was then added and independently reviewed. The final successful test did not trigger `ip_used`, so automatic replacement was not itself demonstrated in that run.

## Stop the deployment

In Salad, open **pawns**, click **Stop**, and wait until the group is **Stopped** and no instances are running. Closing your browser or quitting Docker Desktop does not stop a cloud container. Keep the stopped group if you want to reuse its settings; use **Start** when you want it running again.

## Keep this recoverable

Keep this Markdown file backed up outside the Desktop folder. The source-creation block is the complete local-program backup. A future rebuild still uses your provider accounts and downloads the pinned official installer and Debian packages.

Before trusting a restored deployment, repeat the four checks: current instance running, latest SDK status running, in-container US IP, and the same IP Active in Pawns. Never substitute an old screenshot, old IP address or old successful log for the current instance.
