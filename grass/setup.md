# Set up Grass

Keep this folder at `~/Desktop/salad/grass`. On your Mac, open Terminal using Command-Space → Terminal → Return. You need your [SaladCloud account](https://portal.salad.com/) with credit/quota, your [Grass account](https://app.grass.io/dashboard), and access to its sign-in email.

## Prepare the tools

Run:

```sh
python3 --version
curl --version
openssl version
```

Install missing Python from [python.org](https://www.python.org/downloads/macos/). No local Docker installation or Python packages are needed. `repair` uses OpenSSL CMS for the encrypted login transfer; this was measured working with the Mac's LibreSSL 3.3.6 on September 7, 2026.

In Salad, use profile → **API Access** to obtain your API key. Keep it private. [Salad API setup](https://docs.salad.com/container-engine/tutorials/quickstart-api)

Defaults are organization `cosmosgeeketh`, project `default`, group `grass`. For another account, set the names from its Salad URL before running the commands:

```sh
export GRASS_ORGANIZATION="your-organization"
export GRASS_PROJECT="your-project"
export GRASS_GROUP="grass"
```

Skip that block for the existing account.

## Create the container and sign in

```sh
python3 -B "$HOME/Desktop/salad/grass/deploy.py" create
```

Enter the Salad API key at the hidden prompt. For a new group, choose a desktop-access password when asked: the implemented input format is exactly eight English letters/digits, following the image's published [VNC password limit](https://github.com/jlesage/docker-baseimage-gui#vnc-password). Save it in your password manager; it is separate from your Grass login.

The script prints **Portal** and **Desktop** links. It only creates an absent group; repeating `create` reads an existing one without adding replicas. If a request fails, inspect the portal before repeating it.

1. Open **Portal**. Wait for the instance to be **Running / Ready**. Click **Start** if the group is stopped.
2. Open the printed HTTPS **Desktop** link. At **Credentials needed**, enter your desktop password and choose **Submit**.
3. Inside Grass choose **Already have an account? Sign In**, enter your Grass email, then enter the emailed sign-in code.
4. Wait for **Grass is Connected**. Keep this instance running for the next step.

The configured deployment is one US replica, one vCPU, 1024 MiB RAM, batch priority, no GPU, and restart policy `always`. These are this setup's settings, not vendor limits. The community image is pinned by digest in `deploy.py`: [mangup/grassminer](https://hub.docker.com/r/mangup/grassminer). It is a wrapper around Grass Desktop, not an official Grass container. Check Salad's current price before deploying.

## Install native recording and recovery

In Mac Terminal run:

```sh
python3 -B "$HOME/Desktop/salad/grass/deploy.py" repair
```

Enter the Salad API key privately. On first enrollment:

1. The script prints a long **single-line command** and waits. Leave that Terminal process open.
2. Open **Salad → Grass → Instances → the running instance → Terminal**. Paste the entire printed command and press Return.
3. Return to Mac Terminal and press Return.

The command encrypts the existing login. The private decryption key stays only in the running Mac process. The temporary encrypted export deletes itself after the configured five-minute interval. Never copy `store.json`, token values, or Salad environment-variable values into a guide or chat.

The repair command saves the login in the group's private `GRASS_STATE_B64` environment variable, packages `worker.pl` and `bootstrap.sh` into the startup command, and reads the configuration back. Salad rolls out the new container version. Existing country, resources, replica count, desktop password, and image are preserved.

New containers restore the account session while generating their own device identity. Repeating `repair` reuses the saved login and only updates changed native code. It does not ask for a login popup on every replacement. A revoked or expired account session still requires another sign-in; see [Recovery](recovery.md).

## Confirm the complete result

Read **Salad → Instance Logs** for `GRASS_BOOTSTRAP_READY`, `worker_started`, and current `GRASS_SAMPLE_V2` records. The sample must report `replacement_ready: true`, a current process, the current device/IP, and provider health `connected`. Configuration readback or a running process alone is insufficient.

When the AWS recorder is configured, open the [Grass page](https://salad.cosmosgeek.org/#grass). It should show fresh native measurements, provider-confirmed connection, duration, and account Network Points. [Monitoring](monitoring.md) explains the fields and production setup. Closing the viewer leaves Grass running and does not stop Salad charges.
