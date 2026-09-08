import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from dashboard.store import Store


APPS = ("packetstream", "proxyrack", "traffmonetizer", "earnfm", "repocket", "bitping", "honeygain")


def iso(epoch_seconds):
    return datetime.fromtimestamp(epoch_seconds, timezone.utc).isoformat().replace("+00:00", "Z")


def log_entry(epoch_seconds, sequence, instance="instance-a", machine="machine-a", rx=100, tx=50):
    applications = {
        name: {
            "attributed_packet_rx_bytes": rx if name == "packetstream" else 0,
            "attributed_packet_tx_bytes": tx if name == "packetstream" else 0,
            "process_count": 1,
            "socket_count": 2,
            "tcp_socket_count": 1,
            "tcp_established_count": 1,
            "udp_socket_count": 1,
            "state": "up",
        }
        for name in APPS
    }
    return {
        "time": iso(epoch_seconds + 0.2),
        "receive_time": iso(epoch_seconds + 0.3),
        "resource": {
            "type": "container",
            "labels": {
                "organization_name": "org",
                "project_name": "default",
                "container_group_name": "honeygain-us-1",
                "container_group_version": "1",
                "instance_id": instance,
                "machine_id": machine,
            },
        },
        "json_log": {
            "kind": "bandwidth_sample",
            "schema_version": 1,
            "sequence": sequence,
            "sample_time": iso(epoch_seconds),
            "instance_id": "payload-instance-must-not-win",
            "machine_id": "payload-machine-must-not-win",
            "interface": "eth0",
            "capture_mode": "total_only",
            "interval_milliseconds": 1000,
            "partial_interval": False,
            "counter_reset": False,
            "eth0": {
                "rx_bytes_total": 100000 + sequence * rx,
                "tx_bytes_total": 50000 + sequence * tx,
                "rx_bytes_delta": rx,
                "tx_bytes_delta": tx,
                "rx_bytes_per_second": rx,
                "tx_bytes_per_second": tx,
            },
            "applications": applications,
            "captured": {"rx_bytes": rx, "tx_bytes": tx},
            "unassigned": {"rx_bytes": 0, "tx_bytes": 0},
            "coverage_percent": 100.0,
        },
    }


def honeygain_event(epoch_seconds, event, instance="instance-a", machine="machine-a", attempt=1, exit_code=0):
    return {
        "time": iso(epoch_seconds),
        "receive_time": iso(epoch_seconds + 0.2),
        "resource": {
            "type": "container",
            "labels": {
                "organization_name": "org",
                "project_name": "default",
                "container_group_name": "honeygain-us-1",
                "container_group_version": "1",
                "instance_id": instance,
                "machine_id": machine,
            },
        },
        "json_log": {
            "kind": "honeygain_event",
            "schema_version": 1,
            "time": iso(epoch_seconds),
            "event": event,
            "client_version": "0.9.0",
            "attempt": attempt,
            "exit_code": exit_code,
        },
    }
class StoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "bandwidth.sqlite3")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_ingest_is_idempotent_and_resource_identity_is_authoritative(self):
        entry = log_entry(1_700_000_000, 1)
        self.assertTrue(self.store.ingest(entry))
        self.assertFalse(self.store.ingest(entry))

        status = self.store.status()
        self.assertEqual(status["sample_count"], 1)
        self.assertEqual(status["latest_instance_id"], "instance-a")
        self.assertNotIn("payload-instance", str(status))
        self.assertEqual(status["source"]["container_group"], "honeygain-us-1")
        self.assertEqual(status["source"]["version"], "1")

    def test_query_reconciles_totals_and_marks_reallocation(self):
        start = 1_700_000_000
        self.store.ingest(log_entry(start, 1, instance="instance-a", rx=100, tx=50))
        self.store.ingest(log_entry(start + 1, 2, instance="instance-a", rx=200, tx=70))
        self.store.ingest(log_entry(start + 2, 1, instance="instance-b", machine="machine-b", rx=300, tx=90))

        result = self.store.query_range(start * 1000, (start + 3) * 1000, 1)
        self.assertEqual(result["totals"]["eth0"], {"rx_bytes": 600, "tx_bytes": 210})
        self.assertEqual(result["totals"]["applications"]["packetstream"], {"rx_bytes": 600, "tx_bytes": 210})
        self.assertEqual(len(result["points"]), 3)
        self.assertEqual([m["instance_id"] for m in result["reallocations"]], ["instance-a", "instance-b"])

    def test_minute_rollup_survives_raw_retention_prune(self):
        old = 1_600_000_020
        self.store.ingest(log_entry(old, 1, rx=120, tx=60))
        self.store.ingest(log_entry(old + 1, 2, rx=180, tx=90))
        self.assertEqual(self.store.rollup(before_ms=(old + 60) * 1000), 2)
        self.assertEqual(self.store.prune(now_ms=(old + 31 * 86400) * 1000), 2)

        result = self.store.query_range(old * 1000, (old + 60) * 1000, 60)
        self.assertEqual(result["totals"]["eth0"], {"rx_bytes": 300, "tx_bytes": 150})
        self.assertEqual(result["points"][0]["sample_count"], 2)

    def test_range_edges_do_not_include_whole_overlapping_rollup_minutes(self):
        for second in range(90):
            self.store.ingest(log_entry(second, second + 1, rx=100, tx=0))
        self.store.rollup(before_ms=90_000)

        result = self.store.query_range(30_000, 90_000, 60)

        self.assertEqual(result["totals"]["eth0"], {"rx_bytes": 6000, "tx_bytes": 0})
        self.assertEqual([point["time_ms"] for point in result["points"]], [30_000])

    def test_unaligned_buckets_do_not_mix_whole_minute_rollups_with_partial_edges(self):
        for second in range(150):
            self.store.ingest(log_entry(second, second + 1, rx=100, tx=0))
        self.store.rollup(before_ms=150_000)

        result = self.store.query_range(30_000, 150_000, 60)

        self.assertEqual([point["time_ms"] for point in result["points"]], [30_000, 90_000])
        self.assertEqual([point["eth0"]["rx_bytes_per_second"] for point in result["points"]], [100, 100])

    def test_partial_late_minute_cannot_overwrite_complete_rollup(self):
        for second in range(60):
            self.store.ingest(log_entry(second, second + 1, rx=100, tx=0))
        self.store.rollup(before_ms=60_000)
        self.store.prune(now_ms=31 * 86400 * 1000)

        self.store.ingest(log_entry(30, 999, rx=999, tx=0))
        self.store.rollup(before_ms=60_000)
        result = self.store.query_range(0, 60_000, 60)

        self.assertEqual(result["totals"]["eth0"], {"rx_bytes": 6000, "tx_bytes": 0})

    def test_query_instances_reports_peak_slowdown_and_missing_samples_per_box(self):
        start = 100
        self.store.ingest(log_entry(start, 1, instance="instance-a", rx=100, tx=50))
        self.store.ingest(log_entry(start + 1, 2, instance="instance-a", rx=200, tx=50))
        self.store.ingest(log_entry(start + 2, 3, instance="instance-a", rx=50, tx=25))
        self.store.ingest(log_entry(start, 1, instance="instance-b", machine="machine-b", rx=10, tx=5))
        self.store.ingest(log_entry(start + 2, 3, instance="instance-b", machine="machine-b", rx=30, tx=15))

        result = self.store.query_boxes(start * 1000, (start + 3) * 1000)
        boxes = {box["instance_id"]: box for box in result["boxes"]}

        self.assertEqual(result["reporter_count"], 2)
        self.assertEqual(boxes["instance-a"]["sample_count"], 3)
        self.assertEqual(boxes["instance-a"]["expected_sample_count"], 3)
        self.assertEqual(boxes["instance-a"]["peak"]["bytes_per_second"], 250)
        self.assertEqual(boxes["instance-a"]["peak"]["time_ms"], (start + 1) * 1000)
        self.assertEqual(boxes["instance-a"]["latest"]["bytes_per_second"], 75)
        self.assertAlmostEqual(boxes["instance-a"]["observed_average"]["bytes_per_second"], 475 / 3)
        self.assertEqual(boxes["instance-a"]["slowdown_ratio"], 1.0)
        self.assertEqual(boxes["instance-a"]["honeygain"]["tcp_socket_count"], 1)
        self.assertEqual(boxes["instance-a"]["honeygain"]["tcp_established_count"], 1)
        self.assertEqual(boxes["instance-a"]["honeygain"]["udp_socket_count"], 1)
        self.assertEqual(
            boxes["instance-a"]["source"],
            {"organization": "org", "project": "default", "container_group": "honeygain-us-1", "version": "1"},
        )
        self.assertEqual(boxes["instance-b"]["expected_sample_count"], 3)
        self.assertEqual(boxes["instance-b"]["missing_sample_count"], 1)
        self.assertAlmostEqual(boxes["instance-b"]["completeness_percent"], 200 / 3)

    def test_native_disconnect_is_recorded_without_claiming_a_version(self):
        connected = honeygain_event(200, "connected")
        raw = {"time": iso(201), "resource": connected["resource"],
               "text_log": "Honeygain service disconnected"}
        self.assertTrue(self.store.ingest(connected))
        self.assertTrue(self.store.ingest(raw))
        self.assertFalse(self.store.ingest(raw))
        self.assertFalse(self.store.ingest(dict(raw, text_log="not Honeygain service disconnected")))
        result = self.store.query_events(199_000, 202_000)
        self.assertEqual([e["event"] for e in result["events"]], ["disconnected", "connected"])
        self.assertEqual(result["events"][0]["client_version"], "")
        self.assertEqual(result["events"][0]["instance_id"], "instance-a")

    def test_structured_disconnect_replaces_legacy_fallback_in_either_arrival_order(self):
        for index, raw_first in enumerate((True, False)):
            structured = honeygain_event(201, "disconnected", instance=f"instance-{index}")
            raw = {"time": iso(201.179), "resource": structured["resource"],
                   "text_log": "Honeygain service disconnected"}
            for entry in ([raw, structured] if raw_first else [structured, raw]):
                self.store.ingest(entry)
        result = self.store.query_events(200_000, 202_000)
        self.assertEqual(result["event_count"], 2)
        self.assertTrue(all(e["client_version"] == "0.9.0" for e in result["events"]))

    def test_honeygain_events_are_sanitized_deduplicated_and_queryable(self):
        connected = honeygain_event(200, "connected")
        overused = honeygain_event(201, "network_overused", instance="instance-b", machine="machine-b")
        device_limit = honeygain_event(201.5, "device_limit_exceeded", instance="instance-c", machine="machine-c")

        self.assertTrue(self.store.ingest(connected))
        self.assertFalse(self.store.ingest(connected))
        self.assertTrue(self.store.ingest(overused))
        self.assertTrue(self.store.ingest(device_limit))

        result = self.store.query_events(199_000, 202_000)
        self.assertEqual(result["event_count"], 3)
        self.assertEqual(result["counts"], {"connected": 1, "device_limit_exceeded": 1, "network_overused": 1})
        self.assertEqual(
            [event["event"] for event in result["events"]],
            ["device_limit_exceeded", "network_overused", "connected"],
        )
        self.assertEqual(result["events"][0]["client_version"], "0.9.0")
        self.assertNotIn("text_log", str(result))

    def test_sparse_application_payload_does_not_expand_unused_apps(self):
        entry = log_entry(250, 1)
        entry["json_log"]["applications"] = {"honeygain": entry["json_log"]["applications"]["honeygain"]}
        self.store.ingest(entry)

        result = self.store.query_range(250_000, 251_000, 1)
        self.assertEqual(set(result["latest_apps"]), {"honeygain"})

    def test_authorization_and_service_start_are_preserved_without_claiming_connection(self):
        self.assertTrue(self.store.ingest(honeygain_event(260, "authenticated")))
        self.assertTrue(self.store.ingest(honeygain_event(261, "service_starting")))
        result = self.store.query_events(259_000, 262_000)
        self.assertEqual(result["counts"], {"authenticated": 1, "service_starting": 1})
        self.assertNotIn("connected", result["counts"])

    def test_query_boxes_uses_one_complete_shared_fleet_second(self):
        self.store.ingest(log_entry(300.1, 1, instance="instance-a", rx=100, tx=50))
        self.store.ingest(log_entry(300.8, 1, instance="instance-b", machine="machine-b", rx=10, tx=5))
        self.store.ingest(log_entry(301, 2, instance="instance-a", rx=200, tx=50))

        result = self.store.query_boxes(300_000, 302_000, expected_reporters=2)
        boxes = {box["instance_id"]: box for box in result["boxes"]}

        self.assertEqual(result["fleet_snapshot_ms"], 300_000)
        self.assertEqual(result["snapshot_reporter_count"], 2)
        self.assertEqual(boxes["instance-a"]["snapshot"]["bytes_per_second"], 150)
        self.assertEqual(boxes["instance-b"]["snapshot"]["bytes_per_second"], 15)

    def test_query_boxes_tolerates_salad_log_delivery_lag_without_hiding_live_boxes(self):
        self.store.ingest(log_entry(100, 1, instance="instance-a", rx=100, tx=50))

        delayed_but_live = self.store.query_boxes(0, 145_000, expected_reporters=1)
        self.assertTrue(delayed_but_live["boxes"][0]["is_live"])

        genuinely_stale = self.store.query_boxes(0, 221_000, expected_reporters=1)
        self.assertFalse(genuinely_stale["boxes"][0]["is_live"])

    def test_query_boxes_start_profile_does_not_change_with_selected_window(self):
        self.store.ingest(log_entry(1, 1, rx=1000, tx=0))
        self.store.ingest(log_entry(601, 2, rx=100, tx=0))
        self.store.ingest(log_entry(602, 3, rx=100, tx=0))

        result = self.store.query_boxes(601_000, 603_000, expected_reporters=1)
        box = result["boxes"][0]

        self.assertEqual(box["first_seen_ms"], 1000)
        self.assertEqual(box["first_5m_average_bytes_per_second"], 1000)
        self.assertEqual(box["last_5m_average_bytes_per_second"], 100)
        self.assertEqual(box["slowdown_ratio"], 0.1)

    def test_exact_interval_bytes_are_separate_from_normalized_rate(self):
        entry = log_entry(700, 1, rx=100, tx=50)
        entry["json_log"]["interval_milliseconds"] = 2000
        entry["json_log"]["partial_interval"] = True
        entry["json_log"]["eth0"]["rx_bytes_delta"] = 200
        entry["json_log"]["eth0"]["tx_bytes_delta"] = 100
        self.store.ingest(entry)

        box = self.store.query_boxes(700_000, 701_000, expected_reporters=1)["boxes"][0]
        self.assertEqual(box["totals"], {"rx_bytes": 200, "tx_bytes": 100})
        self.assertEqual(box["snapshot"]["bytes_per_second"], 150)
        self.assertEqual(box["partial_interval_count"], 1)

    def test_query_boxes_combines_minute_summaries_with_raw_edges(self):
        for second in range(120):
            rate = 1000 if second == 10 else 100
            self.store.ingest(log_entry(second, second + 1, rx=rate, tx=0))
        self.store.raw_retention_days = 0
        self.store.prune(now_ms=60_000)

        box = self.store.query_boxes(0, 120_000, expected_reporters=1)["boxes"][0]

        self.assertEqual(box["sample_count"], 120)
        self.assertEqual(box["totals"], {"rx_bytes": 12_900, "tx_bytes": 0})
        self.assertAlmostEqual(box["observed_average"]["bytes_per_second"], 107.5)
        self.assertEqual(box["peak"], {"bytes_per_second": 1000, "time_ms": 10_000})
        self.assertEqual(box["first_5m_average_bytes_per_second"], 107.5)
        self.assertEqual(box["completeness_percent"], 100.0)


if __name__ == "__main__":
    unittest.main()
