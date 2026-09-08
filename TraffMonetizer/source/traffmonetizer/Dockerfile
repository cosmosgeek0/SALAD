FROM traffmonetizer/cli_v2@sha256:6dbf8e75cc93e25131e2e701b1d478b3ccbf89212636b08d629621c270f0c966 AS vendor
FROM python:3.12-alpine@sha256:b64631e04e4920160c50fbe8d8df828f7f35f06f425cb44aa09bca53e708a35a
COPY --from=vendor /usr/local/bin/cli /usr/local/bin/cli
COPY worker.py /usr/local/bin/tm-worker.py
WORKDIR /usr/local/bin
ENTRYPOINT ["python3", "-u", "/usr/local/bin/tm-worker.py"]
