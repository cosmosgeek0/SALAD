"""Retention and source-identity regressions for the fleet memory correction."""
import json
import tempfile
import tracemalloc
import unittest
from pathlib import Path
from unittest.mock import patch

from dashboard.fleet_test import FleetTestView


class FleetMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.path = self.root / "observations.jsonl"
        self.view = FleetTestView(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def read(self, **kwargs):
        rows, invalid, truncated = self.view.ledger(self.path, **kwargs)
        return list(rows), invalid, truncated

    def test_append_partial_invalid_and_repeatable_snapshot(self):
        self.path.write_bytes(b'{"n":1}\ninvalid\n{"n":2')
        rows, invalid, truncated = self.view.ledger(self.path)
        self.assertEqual((list(rows), invalid, truncated), ([{"n": 1}], 2, False))
        with self.path.open("ab") as handle:
            handle.write(b'}\n{"n":3}\n')
        self.assertEqual(self.read(), ([{"n": 1}, {"n": 2}, {"n": 3}], 1, False))
        self.assertEqual(list(rows), [{"n": 1}])
        changed = list(rows)
        changed[0]["n"] = 999
        self.assertEqual(list(rows), [{"n": 1}])
        with patch("dashboard.fleet_test.zlib.compress", side_effect=AssertionError("unchanged ledger rebuilt")):
            self.assertEqual(self.read()[0][-1], {"n": 3})

    def test_prefix_rewrite_truncation_and_replacement_invalidate(self):
        self.path.write_bytes(b'{"n":1}\n')
        self.read()
        self.path.write_bytes(b'{"n":9}\n{"n":2}\n')
        self.assertEqual(self.read()[0], [{"n": 9}, {"n": 2}])
        self.path.write_bytes(b'{"n":3}\n')
        self.assertEqual(self.read()[0], [{"n": 3}])
        other = self.root / "replacement"
        other.write_bytes(b'{"n":4}\n')
        other.replace(self.path)
        self.assertEqual(self.read()[0], [{"n": 4}])

    def test_byte_and_row_limits_precede_decoding(self):
        self.path.write_bytes(b'invalid\n{"n":1}\n{"n":2}\n{"n":3}\n')
        with patch("dashboard.fleet_test.MAX_ROWS", 2), patch("dashboard.fleet_test.json.loads", wraps=json.loads) as decode:
            rows, invalid, truncated = self.view.ledger(self.path)
            self.assertEqual(decode.call_count, 2)
            self.assertEqual((list(rows), invalid, truncated), ([{"n": 2}, {"n": 3}], 0, True))
        with patch("dashboard.fleet_test.MAX_BYTES", 11):
            self.view = FleetTestView(self.root)
            self.assertEqual(self.read(), ([{"n": 3}], 0, True))

    def test_large_encoded_ledger_has_small_retained_and_peak_heap(self):
        # 24 MiB of representative repeated fields, generated on disk. The
        # assertion measures cache+decode memory without materializing all rows.
        record = json.dumps({"workers": [{"machine": "node-" + str(i), "note": "x" * 1000}
                                         for i in range(24)]}).encode() + b"\n"
        with self.path.open("wb") as handle:
            for _ in range(1000):
                handle.write(record)
        tracemalloc.start()
        try:
            rows, invalid, truncated = self.view.ledger(self.path)
            count = sum(1 for _ in rows)
            current, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        self.assertEqual((count, invalid, truncated), (1000, 0, False))
        self.assertLess(current, 3 * 1024 * 1024)
        self.assertLess(peak, 5 * 1024 * 1024)

    def test_archived_lookup_keeps_original_sample_time_and_run(self):
        start = 1_800_000_000_000
        fleet = self.root / "fleet-tests"
        archive = fleet / "archives" / "old"
        archive.mkdir(parents=True)
        source = self.root / "hg-fleet"
        source.mkdir()
        (archive / "current.json").write_text(json.dumps({"id": "old", "started_ms": start,
                                                          "hg": {"desired": 1}, "ps": {}}))
        observations = []
        original = []
        for i in range(2):
            observed = start + i * 60000 + 5000
            original.append({"time_ms": observed, "workers": [{"group": "hg1", "machine": "machine",
                "instance": "runtime", "sample": {"time": "2027-01-15T08:0%d:00.0000000Z" % i,
                "rx_total": i * 1000000, "tx_total": 0}}]})
            observations.append({"experiment_id": "old", "time_ms": observed, "hg": {
                "status_observed_ms": observed, "network_total_bytes": i * 1000000, "workers": [
                    {"group": "hg1", "machine": "machine", "ip": "192.0.2.1", "network_bytes": i * 1000000}]}})
        # The old source is outside the current fleet tail; archives still use it.
        original.extend({"time_ms": start + 3600000 + i, "workers": []} for i in range(10))
        (source / "observations.jsonl").write_text("".join(json.dumps(row) + "\n" for row in original))
        (archive / "observations.jsonl").write_text("".join(json.dumps(row) + "\n" for row in observations))
        view = FleetTestView(fleet)
        with patch("dashboard.fleet_test.MAX_ROWS", 2):
            result = view.snapshot(now_ms=start + 70000, archive="old", include_observations=True, honeygain_only=True)
        workers = [row["hg"]["workers"][0] for row in result["observations"]]
        self.assertEqual([worker["run"] for worker in workers], ["runtime", "runtime"])
        self.assertEqual([worker["sample_ms"] for worker in workers], [start, start + 60000])
        self.assertEqual(sum(row["mb"] or 0 for row in result["hg_minutes"]), 1)


if __name__ == "__main__":
    unittest.main()
