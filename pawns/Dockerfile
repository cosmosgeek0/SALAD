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
HEALTHCHECK --interval=10s --timeout=3s --start-period=30s --retries=3 CMD ["python3", "/app/run.py", "--healthcheck"]
ENTRYPOINT ["python3", "-u", "/app/run.py"]
