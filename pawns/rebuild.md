# Build or recover the Pawns image

[Start here](README.md) · [Next: deployment setup](setup.md)

## Use the published image

For the shortest recovery path, paste this entire image reference into Salad's **Image Name** field and follow [Setup](setup.md):

```text
docker.io/cosmosgeek0/salad-bandwidth-stack@sha256:f86d4ea5dba3a17f9914f86140856e74b72ceb7bd77327dd4fcfc1b529f206b6
```

This exact image was built, pushed and read back in the Pawns group's version 13 configuration on September 7, 2026. That verifies publication and configuration; use [Setup's current-instance checks](setup.md#verify-the-current-deployment) to verify a new deployment. The image includes the SDK supervisor, telemetry and health-check command. It still needs your Pawns credentials and Salad's explicit liveness probe.

The reference identifies immutable image content while that public image remains available. If it is unavailable, rebuild from the saved source below. You do not need Docker Desktop or a Docker Hub account when using the published image directly.

## Before opening Terminal

You need this folder's `Dockerfile`, `runner.c` and `run.py`, an internet connection, a Docker Hub account and Docker Desktop running. On a Mac, install [Docker Desktop](https://docs.docker.com/desktop/setup/install/mac-install/) for the chip shown in **Apple menu → About This Mac**.

If the folder was deleted, restore your complete copy into `Desktop/salad/pawns`. The source is stored in ordinary files here; there is no source-code dump to extract from Markdown.

On a Mac, open **Applications → Utilities → Terminal**. Paste one command block at a time and press **Return**. Keep the same Terminal window open through the upload.

```sh
cd "$HOME/Desktop/salad/pawns"
docker info
```

If `cd` fails, restore the folder before continuing. If `docker` is missing, finish installing Docker Desktop and reopen Terminal. If the Docker daemon is unavailable, start Docker Desktop.

## Build and upload

In [Docker Hub](https://hub.docker.com/), create a repository named **salad-pawns** and select **Public**. The image contains the program; your Pawns password is entered in Salad later.

Sign into Docker Hub and complete its browser instructions:

```sh
docker login
```

After login succeeds, paste this prompt:

```sh
printf 'Your Docker Hub username: '
IFS= read -r PAWNS_DOCKER_USER
```

Type your Docker Hub username and press **Return**. Enter the username, not an email address or password. Then paste:

```sh
PAWNS_IMAGE="$PAWNS_DOCKER_USER/salad-pawns:consumer"
docker build --platform linux/amd64 --tag "$PAWNS_IMAGE" .
```

Keep `--platform linux/amd64` on Apple silicon too; it matches the measured Salad runtime. The `.dockerignore` allows only the cloud launcher's source files into the build context.

Wait for a successful build. If it fails, use [Troubleshooting](troubleshooting.md) before uploading. Then run:

```sh
docker push "$PAWNS_IMAGE"
```

After the push succeeds, print the tag to paste into Salad:

```sh
printf 'docker.io/%s\n' "$PAWNS_IMAGE"
```

Use the actual printed value. Docker also prints a `sha256:...` digest after pushing; to pin that build, use `docker.io/YOUR_USERNAME/salad-pawns@sha256:THE_REPORTED_DIGEST` with your actual username and complete reported digest. Continue to [Setup](setup.md).

## Recovery details

The Dockerfile pins the measured Debian base and verifies the downloaded installer and SDK checksums. A vendor change at the download URL can stop a future build. Preserve those checks and investigate a mismatch as described in [Troubleshooting](troubleshooting.md).

A source recovery still needs your provider accounts, credentials and available internet downloads. Preserve the complete `data` directory separately from source-only copies if you also want the old local measurements; see [Website and data](website.md).
