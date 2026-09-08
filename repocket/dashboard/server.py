#!/usr/bin/env python3
"""Loopback-only API, poller, and static server for the bandwidth dashboard."""

from __future__ import annotations

import argparse
import csv
from http.client import HTTPConnection, HTTPException
import getpass
import io
import json
import sqlite3
from contextlib import closing
import math
import mimetypes
import os
import signal
import subprocess
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from urllib.parse import parse_qs, urlparse

from dashboard.salad_api import SaladLogClient
from dashboard.store import APP_NAMES, Store, parse_time_ms
from dashboard.packetstream import PacketStreamView
from dashboard.fleet_test import FleetTestView, fleet_csv
from dashboard.native_network import NetworkMinutes, saved_minutes, bucket_minutes


HOST = "127.0.0.1"
DEFAULT_PORT = 8787
MAX_POINTS = 2000


def iso_ms(value: int) -> str:
    return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def query_window(query: Dict[str, list]) -> tuple:
    try:
        start = int(query.get("start", [""])[0])
        end = int(query.get("end", [""])[0])
        requested_bucket = int(query.get("bucket", ["1"])[0])
    except (TypeError, ValueError):
        raise ValueError("start, end, and bucket must be integers") from None
    if end <= start:
        raise ValueError("end must be after start")
    if requested_bucket < 1 or requested_bucket > 86400:
        raise ValueError("bucket must be between 1 and 86400 seconds")
    minimum_bucket = max(1, math.ceil((end - start) / 1000 / MAX_POINTS))
    return start, end, max(requested_bucket, minimum_bucket)


def csv_export(series: Dict[str, Any]) -> bytes:
    output = io.StringIO(newline="")
    fields = [
        "time_utc",
        "sample_count",
        "instance_ids",
        "coverage_percent",
        "eth0_rx_bytes_per_second",
        "eth0_tx_bytes_per_second",
        "captured_rx_bytes_per_second",
        "captured_tx_bytes_per_second",
        "unassigned_rx_bytes_per_second",
        "unassigned_tx_bytes_per_second",
    ]
    for app in APP_NAMES:
        fields.extend((f"{app}_rx_bytes_per_second", f"{app}_tx_bytes_per_second"))
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for point in series["points"]:
        row = {
            "time_utc": iso_ms(point["time_ms"]),
            "sample_count": point["sample_count"],
            "instance_ids": ";".join(point["instance_ids"]),
            "coverage_percent": point["coverage_percent"],
            "eth0_rx_bytes_per_second": point["eth0"]["rx_bytes_per_second"],
            "eth0_tx_bytes_per_second": point["eth0"]["tx_bytes_per_second"],
            "captured_rx_bytes_per_second": point["captured"]["rx_bytes_per_second"],
            "captured_tx_bytes_per_second": point["captured"]["tx_bytes_per_second"],
            "unassigned_rx_bytes_per_second": point["unassigned"]["rx_bytes_per_second"],
            "unassigned_tx_bytes_per_second": point["unassigned"]["tx_bytes_per_second"],
        }
        for app in APP_NAMES:
            row[f"{app}_rx_bytes_per_second"] = point["applications"][app]["rx_bytes_per_second"]
            row[f"{app}_tx_bytes_per_second"] = point["applications"][app]["tx_bytes_per_second"]
        writer.writerow(row)
    return output.getvalue().encode("utf-8")


def make_handler(store: Store, status_provider: Callable[[], Dict[str, Any]], static_dir: Path, ps_view=None, expected_reporters: int = 10, fleet_view=None, minute_view=None):
    static_dir = Path(static_dir)
    fleet_view = fleet_view or FleetTestView(Path(os.environ.get("FLEET_TEST_DIR", str(Path.home() / ".hg1" / "fleet-tests"))))

    class Handler(BaseHTTPRequestHandler):
        server_version = "SaladBandwidthDashboard/1"

        def log_message(self, *_args):
            return

        def headers_common(self) -> None:
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")

        def send_bytes(self, status: int, body: bytes, content_type: str, disposition: str = "") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            if disposition:
                self.send_header("Content-Disposition", disposition)
            self.headers_common()
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, status: int, value: Any, disposition: str = "") -> None:
            body = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
            self.send_bytes(status, body, "application/json; charset=utf-8", disposition)

        def do_GET(self):  # noqa: N802
            parsed = urlparse(self.path)
            try:
                if parsed.path == "/api/proxyrack":
                    result = json.loads((Path.home() / ".hg1/proxyrack/view.json").read_text())
                    path=Path.home()/".hg1/proxyrack/traffic.sqlite3"
                    result["minutes"] = saved_minutes(path, group_id=result["group_id"])
                    if path.exists():
                        with closing(sqlite3.connect("file:"+str(path)+"?mode=ro",uri=True)) as db:
                            amount=db.execute("SELECT SUM(rx+tx) FROM minutes WHERE valid=1 AND seq>0 AND group_id=?",(result["group_id"],)).fetchone()[0]
                        result["total_recorded_mb"]=amount/1e6 if amount is not None else None
                    self.send_json(200, result)
                    return
                if parsed.path == "/api/traffmonetizer":
                    from dashboard.traffmonetizer import snapshot
                    result = snapshot()
                    path = Path.home()/".hg1/traffmonetizer/traffic.sqlite3"
                    if path.exists() and parse_qs(parsed.query).get("chart")==["1"]:
                        now=int(time.time()*1000); first=now//60000*60000-1439*60000
                        test_start=result.get("deployment",{}).get("measurement_started_ms",0)
                        points={}
                        with closing(sqlite3.connect("file:"+str(path)+"?mode=ro",uri=True)) as db:
                            db.row_factory=sqlite3.Row; db.execute("BEGIN")
                            rows=db.execute("""SELECT CAST(time_ms/60000 AS INTEGER)*60000 minute,run,instance,machine,ip,
                                SUM(rx+tx)/1e6 mb,
                                SUM(time_ms-MAX(start_ms,CAST(time_ms/60000 AS INTEGER)*60000)) coverage_ms,
                                SUM(MAX(0,CAST(time_ms/60000 AS INTEGER)*60000-start_ms)) previous_coverage_ms
                                FROM samples WHERE time_ms>=? AND start_ms>=? AND rx IS NOT NULL AND tx IS NOT NULL
                                GROUP BY minute,run,instance,machine,ip ORDER BY minute""",(first,test_start)).fetchall()
                            total=db.execute("SELECT SUM(rx) rx,SUM(tx) tx,COUNT(*) samples,MIN(time_ms) first_ms,MAX(time_ms) last_ms FROM samples WHERE start_ms>=? AND rx IS NOT NULL AND tx IS NOT NULL",(test_start,)).fetchone()
                            result["recorded"]=dict(total)
                        for row in rows:
                            point=points.setdefault(row["minute"],{"minute_ms":row["minute"],"mb":0,"nodes":[],"duration_ms":0})
                            point["mb"]+=row["mb"];point["duration_ms"]+=row["coverage_ms"]
                            previous=points.get(row["minute"]-60000)
                            if previous is not None: previous["duration_ms"]+=row["previous_coverage_ms"]
                            point["nodes"].append({"instance":row["instance"],"ip":row["ip"],"mb":row["mb"]})
                        for point in points.values():
                            point["count"]=len(point["nodes"])
                            point["nodes"]=sorted(point["nodes"],key=lambda n:-n["mb"])[:20]
                            point["partial"]=point.pop("duration_ms")<result.get("deployment",{}).get("desired_replicas",10)*60000
                        result["chart_minutes"]=list(points.values())
                    self.send_json(200,result)
                    return
                if parsed.path == "/api/earnfm":
                    path = static_dir/"earnfm.json"
                    result=json.loads(path.read_text()) if path.exists() else {"error":"EarnFM recorder has not published data yet", "desired":10,"workers":[],"points":[]}
                    self.send_json(200,result)
                    return
                if parsed.path == "/api/repocket":
                    data_dir = Path.home() / ".hg1" / "repocket"
                    result = json.loads((data_dir / "view.json").read_text())
                    if "provider" not in result and (data_dir / "provider.json").exists():
                        result["provider"] = json.loads((data_dir / "provider.json").read_text())
                    if "chart_minutes" not in result and parse_qs(parsed.query).get("chart")==["1"] and (data_dir/"traffic.sqlite3").exists():
                        now=int(time.time()*1000); first=now//60000*60000-1439*60000
                        with closing(sqlite3.connect("file:"+str(data_dir/"traffic.sqlite3")+"?mode=ro",uri=True)) as db:
                            db.execute("BEGIN")
                            raw=[json.loads(row[0]) for row in db.execute("SELECT body FROM events WHERE kind='minute' AND time_ms>=?",(first,))]
                            total=db.execute("SELECT SUM(json_extract(body,'$.rx_bytes')+json_extract(body,'$.tx_bytes')),MIN(json_extract(body,'$.start_ms')) FROM events WHERE kind='minute' AND json_extract(body,'$.rx_bytes')>=0 AND json_extract(body,'$.tx_bytes')>=0").fetchone()
                        records=[]
                        for row in raw:
                            if row.get("rx_bytes") is None or row.get("tx_bytes") is None or row["rx_bytes"]<0 or row["tx_bytes"]<0:continue
                            record={"start_ms":row["start_ms"],"end_ms":row["end_ms"],"rx":row["rx_bytes"],"tx":row["tx_bytes"],"bucket_ms":None,"instance":row["instance"],"machine":row["machine"],"ip":row.get("ip")}
                            bucket=round(row["start_ms"]/60000)*60000
                            if not row.get("partial") and 59000<=row["end_ms"]-row["start_ms"]<=61000 and abs(row["start_ms"]-bucket)<=1000:
                                record.update(start_ms=bucket,end_ms=bucket+60000,bucket_ms=bucket)
                            records.append(record)
                        result["chart_minutes"]=bucket_minutes(records,first,now//60000*60000)
                        for point in result["chart_minutes"]:point["partial"]|=point["count"]<result["desired"]
                        result["total_network_mb"]=total[0]/1e6 if total[0] is not None else None
                        result["test_started_ms"]=total[1]
                    self.send_json(200, result)
                    return
                if parsed.path == "/api/ps1/minutes" and minute_view is not None:
                    query = parse_qs(parsed.query)
                    census = json.loads((minute_view.path.parent / "native-census.json").read_text())
                    selected = int(query["minute"][0]) if "minute" in query else None
                    if selected is not None and (selected < 0 or selected % 60000):
                        raise ValueError("Invalid selected minute")
                    self.send_json(200, minute_view.minute(census.get("group_id", ""), selected) if selected is not None else minute_view.snapshot(census))
                    return
                if parsed.path in ("/api/fleet-test", "/api/fleet-test/export.json", "/api/fleet-test/export.csv"):
                    archive = parse_qs(parsed.query).get("archive", [None])[0]
                    result = fleet_view.snapshot(archive=archive, include_observations=parsed.path.endswith(".json"), honeygain_only=parse_qs(parsed.query).get("service") == ["hg"])
                    if parsed.path.endswith(".csv"):
                        self.send_bytes(200, fleet_csv(result), "text/csv; charset=utf-8", 'attachment; filename="independent-fleet-test.csv"')
                    else:
                        self.send_json(200, result, 'attachment; filename="independent-fleet-test.json"' if parsed.path.endswith(".json") else "")
                    return
                if parsed.path == "/api/ps1/view" and ps_view is not None:
                    query = parse_qs(parsed.query)
                    start = int(query["start"][0]) if "start" in query else None
                    end = int(query["end"][0]) if "end" in query else None
                    if start is not None and (start < 0 or (end is not None and end <= start)):
                        raise ValueError("Invalid period")
                    raw = {}
                    connection = HTTPConnection("127.0.0.1", 8789, timeout=4)
                    try:
                        connection.request("GET", "/api/ps1/status")
                        response = connection.getresponse()
                        if response.status == 200:
                            raw = json.loads(response.read())
                    except (OSError, HTTPException, ValueError):
                        pass
                    finally:
                        connection.close()
                    self.send_json(200, ps_view.snapshot(raw, start, end))
                    return
                if parsed.path in ("/api/ps1/status", "/api/ps1/history"):
                    # Fixed loopback target; browser input cannot select an upstream.
                    target = parsed.path
                    if parsed.path.endswith("/history"):
                        after = int(parse_qs(parsed.query).get("after", ["0"])[0])
                        if after < 0:
                            raise ValueError("after must be a non-negative integer")
                        target += f"?after={after}"
                    connection = HTTPConnection("127.0.0.1", 8789, timeout=4)
                    try:
                        connection.request("GET", target, headers={"Accept": "application/json"})
                        upstream = connection.getresponse()
                        body = upstream.read()
                        if upstream.status != 200:
                            self.send_json(503, {"error": f"PS1 recorder returned HTTP {upstream.status}"})
                        else:
                            self.send_bytes(200, body, "application/json; charset=utf-8")
                    except (OSError, HTTPException):
                        self.send_json(503, {"error": "PS1 recorder is unavailable"})
                    finally:
                        connection.close()
                    return
                if parsed.path == "/api/status":
                    result = store.status()
                    result.update(status_provider())
                    last_sample_ms = result.get("last_sample_ms")
                    result["source_lag_ms"] = (
                        max(0, int(time.time() * 1000) - int(last_sample_ms))
                        if last_sample_ms is not None
                        else None
                    )
                    self.send_json(200, result)
                    return
                if parsed.path == "/api/boxes":
                    start, end, _bucket = query_window(parse_qs(parsed.query))
                    self.send_json(200, store.query_boxes(start, end, expected_reporters=expected_reporters))
                    return
                if parsed.path == "/api/events":
                    start, end, _bucket = query_window(parse_qs(parsed.query))
                    self.send_json(200, store.query_events(start, end))
                    return
                if parsed.path in ("/api/series", "/api/export.csv", "/api/export.json"):
                    start, end, bucket = query_window(parse_qs(parsed.query))
                    result = store.query_range(start, end, bucket)
                    if parsed.path == "/api/export.csv":
                        self.send_bytes(200, csv_export(result), "text/csv; charset=utf-8", 'attachment; filename="salad-bandwidth.csv"')
                    elif parsed.path == "/api/export.json":
                        self.send_json(200, result, 'attachment; filename="salad-bandwidth.json"')
                    else:
                        self.send_json(200, result)
                    return
                files = {"/": "index.html", "/index.html": "index.html", "/app.js": "app.js", "/ps1.js": "ps1.js", "/fleet-test.js": "fleet-test.js", "/styles.css": "styles.css"}
                files.update({"/rp": "repocket.html", "/repocket": "repocket.html", "/repocket.html": "repocket.html"})
                files.update({"/proxyrack": "proxyrack.html", "/proxyrack.html": "proxyrack.html"})
                files.update({"/ef": "earnfm.html", "/earnfm": "earnfm.html", "/earnfm.html": "earnfm.html", "/ef.json": "earnfm.json", "/earnfm.json": "earnfm.json"})
                files.update({alias:"index.html" for path in ("/proxyrack","/rp","/repocket","/earnfm","/traffmonetizer","/tm") for alias in (path,path+".html")})
                filename = files.get(parsed.path)
                if filename is None:
                    self.send_json(404, {"error": "not found"})
                    return
                body = (static_dir / filename).read_bytes()
                content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                self.send_bytes(200, body, content_type + ("; charset=utf-8" if content_type.startswith("text/") or content_type.endswith("javascript") else ""))
            except ValueError as exc:
                self.send_json(400, {"error": str(exc)})
            except FileNotFoundError:
                self.send_json(404, {"error": "dashboard asset not found"})
            except Exception:
                self.send_json(500, {"error": "internal dashboard error"})

        def do_POST(self):  # noqa: N802
            if self.path != "/api/ps1/credited" or ps_view is None:
                self.send_json(404, {"error": "not found"})
                return
            if self.headers.get("X-PS-Token") != ps_view.token or self.headers.get("Origin", "http://127.0.0.1:8787") != "http://127.0.0.1:8787":
                self.send_json(403, {"error": "Local dashboard authentication required"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 2048:
                    raise ValueError("Invalid reading size")
                ps_view.ingest(json.loads(self.rfile.read(size)))
                self.send_json(200, {"ok": True})
            except (ValueError, TypeError, KeyError):
                self.send_json(400, {"error": "Invalid provider reading"})

    return Handler


class Poller:
    def __init__(
        self,
        store: Store,
        client: SaladLogClient,
        interval_seconds: int = 1,
        overlap_seconds: int = 2,
        settlement_seconds: int = 10,
        initial_lookback_seconds: int = 60,
        reconcile_horizon_seconds: int = 3600,
        reconcile_chunk_seconds: int = 60,
        reconcile_interval_seconds: int = 10,
    ):
        self.store = store
        self.client = client
        self.interval_seconds = interval_seconds
        self.overlap_ms = overlap_seconds * 1000
        self.settlement_ms = settlement_seconds * 1000
        self.initial_lookback_ms = initial_lookback_seconds * 1000
        self.reconcile_horizon_ms = reconcile_horizon_seconds * 1000
        self.reconcile_chunk_ms = reconcile_chunk_seconds * 1000
        self.reconcile_interval_ms = reconcile_interval_seconds * 1000
        self._reconcile_cursor_ms: Optional[int] = None
        self._next_reconcile_ms: Optional[int] = None
        self._last_reconcile_start_ms: Optional[int] = None
        self._last_reconcile_end_ms: Optional[int] = None
        self._last_reconcile_final_start_ms: Optional[int] = None
        self._last_reconcile_final_end_ms: Optional[int] = None
        self.stop_event = threading.Event()
        self._lock = threading.Lock()
        self._status: Dict[str, Any] = {"poll_state": "starting"}
        self._maintenance_at = 0.0

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._status)

    def run_once(self, now_ms: Optional[int] = None) -> int:
        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        settled_end_ms = max(0, now_ms - self.settlement_ms)
        watermark = self.store.watermark_ms()
        start_ms = max(
            0,
            (watermark - self.overlap_ms)
            if watermark is not None
            else settled_end_ms - self.initial_lookback_ms,
        )
        try:
            entries = self.client.fetch(iso_ms(start_ms), iso_ms(settled_end_ms), page_size=100)
            reconcile_due = self._next_reconcile_ms is None or now_ms >= self._next_reconcile_ms
            if (
                reconcile_due
                and self.reconcile_horizon_ms > 0
                and self.reconcile_chunk_ms > 0
                and self.reconcile_interval_ms > 0
            ):
                self._next_reconcile_ms = now_ms + self.reconcile_interval_ms
                reconcile_floor = max(0, settled_end_ms - self.reconcile_horizon_ms)
                reconcile_limit = max(reconcile_floor, settled_end_ms - self.overlap_ms)
                reconcile_slice_ms = max(1000, self.reconcile_chunk_ms // 2)
                if self._reconcile_cursor_ms is None:
                    self._reconcile_cursor_ms = reconcile_floor
                if self._reconcile_cursor_ms < reconcile_floor or self._reconcile_cursor_ms >= reconcile_limit:
                    self._reconcile_cursor_ms = reconcile_floor
                reconcile_start_ms = self._reconcile_cursor_ms
                reconcile_end_ms = min(reconcile_start_ms + reconcile_slice_ms, reconcile_limit)
                if reconcile_end_ms > reconcile_start_ms:
                    entries.extend(
                        self.client.fetch(iso_ms(reconcile_start_ms), iso_ms(reconcile_end_ms), page_size=100)
                    )
                    self._reconcile_cursor_ms = (
                        reconcile_floor if reconcile_end_ms >= reconcile_limit else reconcile_end_ms
                    )
                    self._last_reconcile_start_ms = reconcile_start_ms
                    self._last_reconcile_end_ms = reconcile_end_ms

                # Every event-time slice receives a final check as it reaches the
                # configured lateness horizon. This prevents a log that arrived
                # just after the rolling sweep from aging out unseen.
                final_start_ms = reconcile_floor
                final_end_ms = min(final_start_ms + reconcile_slice_ms, reconcile_limit)
                if final_end_ms > final_start_ms and (final_start_ms, final_end_ms) != (
                    reconcile_start_ms,
                    reconcile_end_ms,
                ):
                    entries.extend(self.client.fetch(iso_ms(final_start_ms), iso_ms(final_end_ms), page_size=100))
                if final_end_ms > final_start_ms:
                    self._last_reconcile_final_start_ms = final_start_ms
                    self._last_reconcile_final_end_ms = final_end_ms
            inserted = self.store.ingest_many(entries)
            next_watermark = settled_end_ms if entries else (watermark if watermark is not None else start_ms)
            self.store.record_poll(next_watermark, inserted, now_ms=now_ms)
            if time.monotonic() >= self._maintenance_at:
                self.store.rollup()
                self.store.prune(now_ms=now_ms)
                self._maintenance_at = time.monotonic() + 3600
            with self._lock:
                self._status = {
                    "poll_state": "ok",
                    "last_fetch_count": len(entries),
                    "last_insert_count": inserted,
                    "settled_through_ms": settled_end_ms,
                    "reconcile_start_ms": self._last_reconcile_start_ms,
                    "reconcile_end_ms": self._last_reconcile_end_ms,
                    "reconcile_final_start_ms": self._last_reconcile_final_start_ms,
                    "reconcile_final_end_ms": self._last_reconcile_final_end_ms,
                    "tail_fetch_interval_seconds": self.interval_seconds,
                    "tail_overlap_seconds": self.overlap_ms // 1000,
                    "settlement_seconds": self.settlement_ms // 1000,
                    "reconcile_interval_seconds": self.reconcile_interval_ms // 1000,
                }
            return inserted
        except Exception as exc:
            safe_error = f"{type(exc).__name__}: {exc}"
            self.store.record_poll(watermark or start_ms, 0, error=safe_error, now_ms=now_ms)
            with self._lock:
                self._status = {"poll_state": "error", "poll_error": safe_error[:500]}
            return 0

    def run(self) -> None:
        while not self.stop_event.is_set():
            self.run_once()
            self.stop_event.wait(self.interval_seconds)

    def stop(self) -> None:
        self.stop_event.set()


def key_provider(helper: Path) -> str:
    environment_key = os.environ.get("SALAD_API_KEY", "").strip()
    if environment_key:
        return environment_key
    result = subprocess.run(
        [str(helper), "--read", "--service", "salad-bandwidth-api", "--account", getpass.getuser()],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.decode("utf-8").strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--data-dir", type=Path, default=Path.home() / ".salad-bandwidth-monitor")
    parser.add_argument("--no-poll", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    helper = repo_root / ".runtime" / "keychain-store"
    store = Store(args.data_dir / "bandwidth.sqlite3")
    poller: Optional[Poller] = None
    if not args.no_poll:
        client = SaladLogClient(
            os.environ.get("SALAD_ORGANIZATION", "cosmosgeeketh"),
            os.environ.get("SALAD_PROJECT", "default"),
            os.environ.get("SALAD_CONTAINER_GROUP", "honeygain-canary"),
            lambda: key_provider(helper),
        )
        poller = Poller(store, client)
        threading.Thread(target=poller.run, name="salad-log-poller", daemon=True).start()

    status = poller.status if poller else (lambda: {"poll_state": "disabled"})
    ps_runtime = Path(os.environ.get("PS_MONITOR_DIR", str(args.data_dir / "packetstream")))
    ps_view = PacketStreamView(ps_runtime, lambda: key_provider(helper))
    minute_view = NetworkMinutes(ps_runtime / "minutes.sqlite3")
    threading.Thread(target=ps_view.run, name="ps-deployment-metadata", daemon=True).start()
    expected_reporters = max(1, int(os.environ.get("SALAD_EXPECTED_REPORTERS", "10")))
    server = ThreadingHTTPServer((HOST, args.port), make_handler(store, status, Path(__file__).parent / "static", ps_view, expected_reporters, minute_view=minute_view))

    def stop_server(_signum, _frame):
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop_server)
    signal.signal(signal.SIGINT, stop_server)
    print(f"dashboard: http://{HOST}:{args.port}", flush=True)
    try:
        server.serve_forever()
    finally:
        ps_view.stop_event.set()
        if poller:
            poller.stop()
        server.server_close()
        minute_view.db.close()
        store.close()


if __name__ == "__main__":
    main()
