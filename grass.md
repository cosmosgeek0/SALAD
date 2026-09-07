# Run Grass on Salad from scratch

**Live-tested on September 7, 2026:** this setup launched the Grass Linux desktop app on a US Salad node. Both the app and the Grass account showed Connected, and Grass reported 100% Network Quality. That proved connection; it did not prove profitable traffic.

Keep a copy of this file. You can recreate the deployment with it even if the other local files and the old Salad container are deleted. You still need your accounts, account access, Salad credit/quota, and the image to remain available on Docker Hub. No existing project scripts, Docker installation, or local credential helper are needed.

### What was actually verified

Verification date: September 7, 2026.

- **Live:** the original API creation, desktop access, email-code login, and Grass connection succeeded with the settings below.
- **Live:** this file's exact command ran from an empty folder in a real terminal, found the existing deployment, hid the API-key input, and created no local files. Docker Hub still served the pinned Linux/AMD64 image.
- **Simulated:** the command's fresh-create path, repeat-run path, failed creation, invalid credentials/password input, and creation followed by an error response behaved as expected.

The audit did not delete and rebuild the live node. It did not prove automatic login after replacement, future earnings, or that another machine will receive the same IP or Network Quality score.

## 1. Have these ready

- A [SaladCloud account](https://portal.salad.com/), an organization and a project, with credit and room for a new replica.
- Your [Grass account](https://app.grass.io/dashboard) and access to its email inbox. Use your existing account.
- A Mac with Terminal, Python 3 and `curl`. Open Terminal using Spotlight: press Command-Space, type **Terminal**, then press Return.

Check the local tools by pasting these commands into Terminal:

```sh
python3 --version
curl --version
```

If Python is missing, install Python 3 from [python.org](https://www.python.org/downloads/macos/), reopen Terminal, and check again. No Python packages are required. The launch block below is for Mac/Linux terminals, not Windows PowerShell.

In Salad, click your profile at the top right, then **API Access**, and copy your API key. This key lets the command create your container. Keep it private. [Salad's instructions](https://docs.salad.com/container-engine/tutorials/quickstart-api)

Choose and save a separate desktop-access password in your password manager: **exactly eight random English letters or digits** for this setup. This is the VNC password, not your Grass password. VNC's published password limit is eight characters. [Image-base documentation](https://github.com/jlesage/docker-baseimage-gui#vnc-password)

## 2. Create the container

The following block uses the configuration that worked in the live test. It deploys a prebuilt community image containing the Grass desktop app; the image is maintained by `mangup`, not Grass.

The image digest below pins the exact inspected image, whose installed package metadata reported Grass Desktop 7.6.1. It is not a promise that this version will remain current forever. [Image publisher](https://hub.docker.com/r/mangup/grassminer)

Our organization is `cosmosgeeketh` and project is `default`. For another account, change `ORG` and `PROJECT` below to the names in your Salad page URL. Leave `NAME` as `grass` to create one Grass deployment.

**Paste the entire block into Terminal, including the final `PY`, and press Return.** It asks privately for the Salad API key and, only when creating a new container, your chosen desktop-access password. Nothing appears while you type or paste those secrets; press Return after each.

```sh
python3 -B - <<'PY'
import getpass
import json
import subprocess

ORG = "cosmosgeeketh"
PROJECT = "default"
NAME = "grass"
IMAGE = "docker.io/mangup/grassminer@sha256:92b9f50fc784f69d3f8dd49f84e670d55e30dd5f6eb58b57e0381bb55b6b6302"
BASE = f"https://api.salad.com/api/public/organizations/{ORG}/projects/{PROJECT}/containers"
PORTAL = f"https://portal.salad.com/organizations/{ORG}/projects/{PROJECT}/containers/{NAME}"
key = getpass.getpass("Paste your Salad API key, then press Return: ").strip()
if not key:
    raise SystemExit("No API key entered. Nothing created.")

def request(path, method="GET", body=None):
    config = "header = " + json.dumps("Salad-Api-Key: " + key) + "\n"
    config += 'header = "Content-Type: application/json"\n'
    if body is not None:
        config += "data-binary = " + json.dumps(json.dumps(body)) + "\n"
    result = subprocess.run(
        ["curl", "-sS", "--max-time", "30", "--config", "-",
         "--request", method, "--write-out", "\n%{http_code}", BASE + path],
        input=config, text=True, capture_output=True, timeout=35)
    if result.returncode:
        raise SystemExit("Request failed. Check the portal before repeating: " + PORTAL)
    raw, status = result.stdout.rsplit("\n", 1)
    return int(status), json.loads(raw) if raw.strip() else {}

status, group = request("/" + NAME)
if status == 404:
    password = getpass.getpass("Your new desktop-access password: ")
    if len(password) != 8 or not password.isascii() or not password.isalnum():
        raise SystemExit("Use exactly eight English letters or digits. Nothing created.")
    payload = {
        "name": NAME, "display_name": "Grass", "replicas": 1,
        "autostart_policy": True, "restart_policy": "always", "country_codes": ["us"],
        "container": {
            "image": IMAGE, "priority": "batch",
            "resources": {"cpu": 1, "memory": 1024},
            "environment_variables": {
                "SECURE_CONNECTION": "0", "WEB_AUTHENTICATION": "0",
                "VNC_PASSWORD": password}},
        "networking": {"auth": False, "protocol": "http", "port": 5800,
                       "load_balancer": "least_number_of_connections"}}
    created, _ = request("", "POST", payload)
    status, group = request("/" + NAME)
    if status != 200:
        raise SystemExit(f"Create returned HTTP {created}; readback HTTP {status}. Check: {PORTAL}")
    print("Creation confirmed by reading the group back from Salad.")
elif status == 200:
    print("The group already exists. Its configuration and password were not changed.")
else:
    raise SystemExit(f"Salad returned HTTP {status}. Check your API key, organization and project.")

if group.get("container", {}).get("image") != IMAGE:
    raise SystemExit("That name belongs to a different image. Inspect it in the portal; nothing overwritten.")
print("Portal:", PORTAL)
print("Current group state:", group["current_state"]["status"])
print("Grass desktop:", "https://" + group["networking"]["dns"])
print("If the group is Stopped, open its portal page and click Start.")
print("Creation is not a connection test. Complete the login and checks below.")
PY
```

The launch block creates the group only when its name is absent. Running it again finds the existing group; it does not reset it or create another replica. It does not save your API key or passwords in local files.

The measured successful configuration was CPU-only, one replica, one vCPU, 1 GB RAM, US location, and Lowest/batch priority. The portal quoted **$0.005 per running hour** for that configuration on the test date. Calculated at continuous operation, that is **$0.12 per day**; check current pricing before running it again.

## 3. Wait for Salad, then sign into Grass

1. Open the **Portal** link printed by the command.
2. Watch **Instances**. Allocation, downloading and creating are preparation states. Wait until the instance says **Running** and **Ready**. If the group is **Stopped**, click **Start**.
3. Open the printed **Grass desktop** link. The page may be titled **DockerApp**; that is the desktop viewer used by this image.
4. At **Credentials needed**, enter the desktop-access password you chose above, then click **Submit**.
5. Inside the Grass app, choose **Already have an account? Sign In**. Do not create another account for this node.
6. Enter your Grass account email and click **Continue**. Enter the code sent to that inbox and click **Sign In**. This is the login route that worked in the live test.
7. Wait for **Grass is Connected**. Check its **Network Quality** reading.

The tested access path is browser HTTPS through Salad's gateway to the container's HTTP listener. `SECURE_CONNECTION=0` and `WEB_AUTHENTICATION=0` are intentional for that path; access to the desktop is still protected by `VNC_PASSWORD`. Always open the generated **https://...salad.cloud** link. Do not publish a raw HTTP/VNC port elsewhere or remove its password.

If you forgot the desktop password, open the group in Salad, select **Deployment Details → View Environment Variables → Show**, and read `VNC_PASSWORD` privately. Never paste it into chat or this file.

## 4. Confirm what is working

Open [your Grass dashboard](https://app.grass.io/dashboard) and refresh it after login. It may briefly show Guest while loading your account.

- **Salad Running/Ready:** the container is up.
- **Grass is Connected:** the client has connected.
- **Your Networks:** the new IP should appear as Connected. The original test IP was `172.2.201.58`; a replacement machine can have a different IP. Do not hard-code that address.
- **Uptime Points increasing:** Grass is recording availability.
- **Network Points increasing after daily crediting:** Grass has credited bandwidth use. Connected status and Uptime Points alone do not prove paid traffic or profit.

Published Grass guidance says Network Points are credited after a daily calculation rather than continuously. There is no separate switch to activate them. [Point reporting](https://www.grass.io/learn/grass-points-stopped-increasing-a-troubleshooting-checklist/)

After login, you can close Terminal and the desktop-viewer browser tab. Grass runs on Salad, not on your Mac. Hosting charges continue until you stop the group.

## 5. If something interrupts the setup

| What you see | What to do |
|---|---|
| The command reports an HTTP error | Check the organization/project names, API key, Salad credit and quota. Open the portal before repeating a create attempt. A group may have been created even if a response failed. |
| The desktop link fails while Salad is allocating/downloading | Wait for the instance to become Running/Ready, then reload the desktop page. A link existing does not mean the app is ready yet. |
| The viewer says Reconnecting or shows a `clipboardPasteFrom` error | Reload the viewer and enter its desktop password again. This happened during the live test; it did not require recreating the node. |
| Typing or pasting lands in the viewer's Clipboard box | Click directly inside the Grass form. Verify the email displayed before continuing. If text is wrong, use Home, Shift-End, then Backspace to clear that field and type again. |
| Grass shows its sign-in page again after replacement | Sign in again with the same Grass account. This setup does not automatically transfer a login to a replacement machine. |

For an actual client failure, open **Salad group → Instances → the machine → Instance Logs** and read the error. Restarting or reallocating is not a fix for an unfinalized Network Points counter.

## 6. Stop costs, or rebuild after deletion

To stop hosting charges for this deployment, open its Salad group, click **Stop**, and confirm the group becomes **Stopped** with no running instances. Closing your browser does not stop billing.

If the group still exists, use **Start** on its page to run it again. If the group was deleted, repeat the launch block, choose a new desktop-access password, and sign into Grass again. Use the newly printed desktop URL: the old URL is not a recovery dependency.

Salad's container filesystem is ephemeral. Saved Grass login data inside the container is not guaranteed to survive replacement. This guide recreates the setup; it does not back up your account, password or session. [Salad storage behavior](https://docs.salad.com/container-engine/explanation/core-concepts/overview#persistent-storage)

For this project, the group page is [cosmosgeeketh / default / grass](https://portal.salad.com/organizations/cosmosgeeketh/projects/default/containers/grass). The working desktop URL at the original test was [the Grass desktop](https://lemon-panzanella-p0q3zxydhqzwc9pq.salad.cloud/). Use the launch block's output after any rebuild.
