# Rebuild the Mysterium image

[Guide index](README.md)

Use the published image in [setup](setup.md#create-the-deployment) for normal deployment. To rebuild it, install [Docker](https://docs.docker.com/get-started/get-docker/) and open your terminal in this `mysterium` folder. Keep [Dockerfile](Dockerfile) and [start.sh](start.sh) together.

The Dockerfile builds the MTU-corrected binary from pinned upstream source and installs the startup script. No account key or node identity is included at build time. The compiler and build cache are excluded from the final image; the modified upstream source and license are retained in `/usr/share/mysterium/source`.

Use a Docker Hub repository you control, replacing the placeholder:

```sh
myst_image='YOUR_DOCKERHUB_USERNAME/mysterium:registration'
docker build --platform linux/amd64 -t "$myst_image" .
docker run --rm --platform linux/amd64 --network none --entrypoint /usr/bin/myst "$myst_image" --version
docker run --rm --platform linux/amd64 --network none --entrypoint /bin/sh "$myst_image" -c 'sha256sum /usr/bin/myst /usr/local/bin/mysterium-start.sh'
docker login
docker push "$myst_image"
docker image inspect "$myst_image" --format '{{index .RepoDigests 0}}'
```

Copy the pushed `repository@sha256:...` into `IMAGE` in [setup](setup.md#create-the-deployment). Preserve the startup command, readiness probe, required environment secret, and chosen country restriction (currently GB) from that guide.

Measured local image hashes for this build:

| File inside image | SHA-256 |
| --- | --- |
| `/usr/bin/myst` | `884d0c81c00298a9f78eb37deaf41bfebfa56a6f479900adabc922394413a0cf` |
| `/usr/local/bin/mysterium-start.sh` | `3df1691bf1c8e4632a913d54b5cbf7d713706687f9558eea627fa5308ac9cafa` |

The binary reports version `1.39.5`, branch `salad-mtu`, and commit `c45527af-mtu`. The startup script is a separate source file, so its hash and the image digest identify the registration behavior.
