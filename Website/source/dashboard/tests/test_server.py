import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch
from http.server import ThreadingHTTPServer
from pathlib import Path

from dashboard.server import Poller, make_handler
from dashboard.fleet_test import FleetTestView
from dashboard.salad_api import _parse_iso
from dashboard.store import Store
from dashboard.tests.test_store import honeygain_event, log_entry


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "db.sqlite3")
        self.start = 1_700_000_000
        self.store.ingest(log_entry(self.start, 1))
        static_dir = Path(__file__).resolve().parents[1] / "static"
        self.fleet_dir = Path(self.tmp.name) / "fleet-tests"
        handler = make_handler(self.store, lambda: {"poll_state": "ok"}, static_dir, fleet_view=FleetTestView(self.fleet_dir))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.store.close()
        self.tmp.cleanup()

    def get(self, path):
        with urllib.request.urlopen(self.base + path) as response:
            return response.status, response.headers, response.read()

    def test_status_series_and_exports(self):
        self.store.ingest(honeygain_event(self.start + 1, "connected"))
        status, headers, body = self.get("/api/status")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Cache-Control"], "no-store")
        status_body = json.loads(body)
        self.assertEqual(status_body["sample_count"], 1)
        self.assertGreaterEqual(status_body["source_lag_ms"], 0)

        end = (self.start + 2) * 1000
        status, _, body = self.get(f"/api/series?start={self.start * 1000}&end={end}&bucket=1")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["totals"]["eth0"]["rx_bytes"], 100)

        status, headers, body = self.get(f"/api/export.csv?start={self.start * 1000}&end={end}&bucket=1")
        self.assertEqual(status, 200)
        self.assertIn("text/csv", headers["Content-Type"])
        self.assertIn(b"eth0_rx_bytes_per_second", body)

        status, headers, body = self.get(f"/api/export.json?start={self.start * 1000}&end={end}&bucket=1")
        self.assertEqual(status, 200)
        self.assertIn("attachment", headers["Content-Disposition"])
        self.assertEqual(json.loads(body)["schema_version"], 1)

        status, _, body = self.get(f"/api/events?start={self.start * 1000}&end={end}&bucket=1")
        self.assertEqual(status, 200)
        events = json.loads(body)
        self.assertEqual(events["event_count"], 1)
        self.assertEqual(events["counts"], {"connected": 1})

    def test_invalid_range_is_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.get("/api/series?start=2000&end=1000&bucket=1")
        self.assertEqual(raised.exception.code, 400)

    def test_dashboard_uses_one_panel_and_shared_service_tabs(self):
        status,_,body=self.get("/")
        self.assertEqual(status,200)
        page=body.decode()
        self.assertIn('id="services" role="tablist"',page)
        self.assertIn('id="bandwidthPanel" role="tabpanel"',page)
        self.assertNotIn('target="_blank"',page)
        self.assertLess(page.index('/ps1.js'),page.index('/fleet-test.js'))
        _,_,script=self.get('/fleet-test.js')
        for name in [b'Honeygain',b'PacketStream',b'Proxyrack',b'Repocket',b'EarnFM',b'Traffic Monetizer',b'Pawns.app',b'EarnApp',b'Grass']:
            self.assertIn(name,script)
        self.assertIn(b'6 hours',script)
        self.assertIn(b'12 hours',script)
        self.assertIn(b'24 hours',script)

    def test_new_protocol_views_wait_without_inventing_measurements(self):
        with patch("dashboard.server.Path.home", return_value=Path(self.tmp.name)):
            for service in ("pawns", "earnapp", "grass"):
                status, _, body = self.get("/api/" + service)
                data = json.loads(body)
                self.assertEqual(status, 200)
                self.assertIsNone(data["working"])
                self.assertIsNone(data["total_mb"])
                self.assertEqual(data["workers"], [])
                self.assertIn("Waiting", data["error"])

    def test_new_protocol_views_expose_only_the_agreed_fields(self):
        folder = Path(self.tmp.name) / ".hg1/pawns"
        folder.mkdir(parents=True)
        (folder / "view.json").write_text(json.dumps({"generated_ms": 1000, "working": None,
            "password": "must-not-leak", "workers": [{"id": "current", "working": None, "token": "must-not-leak"}],
            "minutes": [{"minute_ms": 0, "mb": 2, "nodes": [{"instance": "current", "ip": "192.0.2.1", "country": "US", "mb": 2, "token": "must-not-leak"}]}]}))
        with patch("dashboard.server.Path.home", return_value=Path(self.tmp.name)):
            _, _, body = self.get("/api/pawns")
        self.assertNotIn(b"must-not-leak", body)
        data = json.loads(body)
        self.assertEqual(data["minutes"][0]["nodes"][0]["mb"], 2)
        self.assertIsNone(data["working"])

    def test_new_protocol_api_expires_working_and_rates_without_erasing_history(self):
        folder = Path(self.tmp.name) / ".hg1/pawns"
        folder.mkdir(parents=True)
        source = {"generated_ms": 200000, "inventory_ms": 200000, "running": 1, "working": 1, "total_mb": 12,
            "workers": [{"id": "current", "salad_state": "running", "working": True,
                "sample_ms": 200000, "recorded_ms": 200000, "mb_per_minute": 3, "total_mb": 12}]}
        (folder / "view.json").write_text(json.dumps(source))
        with patch("dashboard.server.Path.home", return_value=Path(self.tmp.name)):
            with patch("dashboard.server.time.time", return_value=200):
                _, _, body = self.get("/api/pawns")
                self.assertEqual(json.loads(body)["working"], 1)
            for stale in ("generated_ms", "inventory_ms", "sample_ms", "recorded_ms"):
                value = json.loads(json.dumps(source))
                (value if stale in ("generated_ms", "inventory_ms") else value["workers"][0])[stale] = 100000
                (folder / "view.json").write_text(json.dumps(value))
                with patch("dashboard.server.time.time", return_value=200):
                    _, _, body = self.get("/api/pawns")
                result = json.loads(body)
                self.assertIsNone(result["working"])
                self.assertIsNone(result["workers"][0]["working"])
                self.assertIsNone(result["workers"][0]["mb_per_minute"])
                self.assertEqual(result["total_mb"], 12)
                self.assertEqual(result["workers"][0]["total_mb"], 12)
            source["working"] = None
            source["workers"][0].update(working=None, error="Connection unverified")
            (folder / "view.json").write_text(json.dumps(source))
            with patch("dashboard.server.time.time", return_value=200):
                _, _, body = self.get("/api/pawns")
            result = json.loads(body)
            self.assertIsNone(result["workers"][0]["working"])
            self.assertEqual(result["workers"][0]["mb_per_minute"], 3)

    def test_ps1_proxy_preserves_raw_history_and_cursor(self):
        payload = b'{"cursor":241,"points":[{"seq":240,"seconds":1,"bytes":750000},{"seq":241,"seconds":4,"bytes":2000000}]}'
        connection = MagicMock()
        connection.getresponse.return_value.status = 200
        connection.getresponse.return_value.read.return_value = payload
        with patch("dashboard.server.HTTPConnection", return_value=connection) as connect:
            status, headers, body = self.get("/api/ps1/history?after=239")
        self.assertEqual(status, 200)
        self.assertEqual(body, payload)
        self.assertEqual(headers["Cache-Control"], "no-store")
        connect.assert_called_once_with("127.0.0.1", 8789, timeout=4)
        connection.request.assert_called_once_with("GET", "/api/ps1/history?after=239", headers={"Accept": "application/json"})
        connection.close.assert_called_once()

    def test_fleet_endpoint_exports_only_sanitized_current_experiment(self):
        self.fleet_dir.mkdir()
        start = 1_800_000_000_000
        metadata = {"id": "current-run", "started_ms": start, "ps": {"baseline_provider_bytes": 0}, "hg": {}, "token": "do-not-expose"}
        (self.fleet_dir / "current.json").write_text(json.dumps(metadata))
        row = {"experiment_id": "current-run", "time_ms": start, "ps": {"api_key": "do-not-expose"}, "hg": {}}
        (self.fleet_dir / "observations.jsonl").write_text(json.dumps(row) + "\n")
        for path in ("/api/fleet-test", "/api/fleet-test/export.json", "/api/fleet-test/export.csv"):
            status, headers, body = self.get(path)
            self.assertEqual(status, 200)
            self.assertEqual(headers["Cache-Control"], "no-store")
            self.assertNotIn(b"do-not-expose", body)
            if "export" in path:
                self.assertIn("attachment", headers["Content-Disposition"])
        _, _, body = self.get("/api/fleet-test/export.json")
        self.assertEqual(json.loads(body)["observations"][0]["experiment_id"], "current-run")
        _, _, script = self.get("/fleet-test.js")
        self.assertIn(b"/api/fleet-test", script)
        self.assertIn(b"setInterval(refresh,5000)", script)

    def test_fleet_endpoint_rejects_archive_path_traversal(self):
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.get("/api/fleet-test?archive=..%2F..%2Fsecrets")
        self.assertEqual(raised.exception.code, 400)

    def test_ps1_proxy_reports_offline_without_faking_zero_traffic(self):
        connection = MagicMock()
        connection.request.side_effect = ConnectionRefusedError("private upstream detail")
        with patch("dashboard.server.HTTPConnection", return_value=connection):
            with self.assertRaises(urllib.error.HTTPError) as raised:
                self.get("/api/ps1/status")
        self.assertEqual(raised.exception.code, 503)
        self.assertEqual(json.loads(raised.exception.read()), {"error": "PS1 recorder is unavailable"})
        connection.close.assert_called_once()

    def test_ps1_proxy_rejects_invalid_history_cursor(self):
        for value in ("-1", "nope", "http://example.com"):
            with self.assertRaises(urllib.error.HTTPError) as raised:
                self.get(f"/api/ps1/history?after={value}")
            self.assertEqual(raised.exception.code, 400)

    def test_poller_recovers_a_log_that_arrives_after_the_first_poll(self):
        late_entry = log_entry(30, 1)

        class LateClient:
            calls = 0

            def fetch(self, start, end, page_size=100):
                self.calls += 1
                if self.calls == 1:
                    return []
                sample_time = _parse_iso(late_entry["json_log"]["sample_time"])
                if _parse_iso(start) <= sample_time < _parse_iso(end):
                    return [late_entry]
                return []

        poller = Poller(self.store, LateClient())
        poller.run_once(now_ms=110_000)
        poller.run_once(now_ms=120_000)

        self.assertEqual(self.store.status()["sample_count"], 2)

    def test_new_database_limits_initial_backfill_to_one_minute(self):
        class CaptureClient:
            window = None

            def fetch(self, start, end, page_size=100):
                self.window = (_parse_iso(start), _parse_iso(end))
                return []

        client = CaptureClient()
        poller = Poller(self.store, client, reconcile_horizon_seconds=0)
        poller.run_once(now_ms=2_000_000)

        start, end = client.window
        self.assertEqual((end - start).total_seconds(), 60)

    def test_poller_reconciles_a_late_log_during_continuous_traffic(self):
        normal = [log_entry(second, second, instance=f"normal-{second}") for second in range(650, 731, 10)]
        late = log_entry(610, 610, instance="late-instance")

        class ReconcileClient:
            late_available = False

            def fetch(self, start, end, page_size=100):
                start_time, end_time = _parse_iso(start), _parse_iso(end)
                rows = normal + ([late] if self.late_available else [])
                return [
                    row
                    for row in rows
                    if start_time <= _parse_iso(row["json_log"]["sample_time"]) < end_time
                ]

        client = ReconcileClient()
        poller = Poller(
            self.store,
            client,
            overlap_seconds=30,
            reconcile_horizon_seconds=120,
            reconcile_chunk_seconds=30,
        )
        poller.run_once(now_ms=700_000)
        poller.run_once(now_ms=710_000)
        client.late_available = True
        poller.run_once(now_ms=720_000)

        recovered = self.store.query_range(610_000, 611_000, 1)
        self.assertEqual(recovered["totals"]["eth0"]["rx_bytes"], 100)

    def test_reconciliation_final_check_catches_log_arriving_after_sweep(self):
        normal = [log_entry(second, second, instance=f"normal-{second}") for second in (185, 195, 205, 215)]
        late = log_entry(100, 999, instance="late-after-sweep")

        class ReconcileClient:
            late_available = False

            def fetch(self, start, end, page_size=100):
                start_time, end_time = _parse_iso(start), _parse_iso(end)
                rows = normal + ([late] if self.late_available else [])
                return [
                    row
                    for row in rows
                    if start_time <= _parse_iso(row["json_log"]["sample_time"]) < end_time
                ]

        client = ReconcileClient()
        poller = Poller(
            self.store,
            client,
            interval_seconds=10,
            overlap_seconds=30,
            reconcile_horizon_seconds=120,
            reconcile_chunk_seconds=30,
            reconcile_interval_seconds=10,
        )
        for now_ms in (200_000, 210_000, 220_000):
            poller.run_once(now_ms=now_ms)
        client.late_available = True
        poller.run_once(now_ms=230_000)

        recovered = self.store.query_range(100_000, 101_000, 1)
        self.assertEqual(recovered["totals"]["eth0"]["rx_bytes"], 100)

    def test_one_second_tail_fetch_keeps_reconciliation_on_slower_cadence(self):
        class CaptureClient:
            def __init__(self):
                self.windows = []

            def fetch(self, start, end, page_size=100):
                self.windows.append((_parse_iso(start), _parse_iso(end)))
                return []

        client = CaptureClient()
        poller = Poller(
            self.store,
            client,
            reconcile_horizon_seconds=120,
            reconcile_chunk_seconds=30,
            reconcile_interval_seconds=10,
        )
        for now_ms in range(200_000, 205_000, 1_000):
            poller.run_once(now_ms=now_ms)

        self.assertEqual(poller.interval_seconds, 1)
        self.assertLessEqual(len(client.windows), 7)
        self.assertEqual(poller.status()["tail_fetch_interval_seconds"], 1)
        self.assertEqual(poller.status()["reconcile_interval_seconds"], 10)


if __name__ == "__main__":
    unittest.main()
