FROM golang:1.26.8-alpine@sha256:ce864e7223ac17b1775e6fd0b4c0db580c2eb50e7953a427916379e4b92a1628 AS build
WORKDIR /src
ADD https://codeload.github.com/mysteriumnetwork/node/tar.gz/c45527af1ea80300ae3d9c92bd37255335b6140d /tmp/node.tar.gz
RUN tar -xzf /tmp/node.tar.gz --strip-components=1 -C /src && rm /tmp/node.tar.gz
RUN sed -i '/func (c \*client) ConfigureDevice(cfg wgcfg.DeviceConfig) error {/a\    mtu := cfg.MTU\n    if mtu == 0 {\n        mtu = device.DefaultMTU\n    }' services/wireguard/endpoint/netstack-provider/client.go \
 && sed -i 's/cfg.DNSPort, device.DefaultMTU)/cfg.DNSPort, mtu)/' services/wireguard/endpoint/netstack-provider/client.go \
 && gofmt -w services/wireguard/endpoint/netstack-provider/client.go
RUN CGO_ENABLED=0 GOMAXPROCS=2 GOMEMLIMIT=1GiB GOTOOLCHAIN=local GOTELEMETRY=off go build -p 2 -trimpath -tags netgo \
 -ldflags="-s -w -X github.com/mysteriumnetwork/node/metadata.Version=1.39.5 -X github.com/mysteriumnetwork/node/metadata.BuildBranch=salad-mtu -X github.com/mysteriumnetwork/node/metadata.BuildCommit=c45527af-mtu -X github.com/mysteriumnetwork/node/metadata.BuildNumber=32001741886" \
 -o /myst ./cmd/mysterium_node
FROM mysteriumnetwork/myst@sha256:4a7f312c8b8bec4fa249d6e916a9e2b0c4987f50a5e4d9f72b71efd10bbcd1cf
COPY --from=build /myst /usr/bin/myst
COPY --from=build /src /usr/share/mysterium/source
COPY --chmod=755 start.sh /usr/local/bin/mysterium-start.sh
ENTRYPOINT ["/usr/local/bin/mysterium-start.sh"]
CMD []
