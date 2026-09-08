import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from dashboard.fleet_test import FleetTestView, rate_buckets, rate_timeline, timestamp_ms, honeygain_minutes


START = 1_800_000_000_000
MACHINE = "11111111-1111-1111-1111-111111111111"
INSTANCE = "22222222-2222-2222-2222-222222222222"
REPLACEMENT = "33333333-3333-3333-3333-333333333333"


def observation(seconds, paid_mb, network_mb=None, *, experiment="test-one", complete=True):
    return {
        "experiment_id": experiment, "time_ms": START + seconds * 1000,
        "ps": {"provider_bytes": paid_mb * 1_000_000,
               "provider_observed_ms": START + seconds * 1000,
               "network_total_bytes": (network_mb if network_mb is not None else paid_mb * 2) * 1_000_000,
               "network_observed_ms": START + seconds * 1000,
               "network_complete": complete, "running": 10, "reporting": 10,
               "workers": [{"machine": "ps-worker", "client_status": "unknown", "state": "running"}]},
        "hg": {"provider_gathering_credits": seconds / 60,
               "provider_observed_ms": START + seconds * 1000,
               "workers": [{"device": "hg-01", "state": "running", "client_status": "unknown"}]},
    }


class FleetTestRates(unittest.TestCase):
    def test_honeygain_minute_estimates_preserve_interval_bytes_and_identity(self):
        rows=[]
        for seconds,total in [(20,100_000_000),(140,220_000_000)]:
            rows.append({"time_ms":START+seconds*1000,"hg":{"status_observed_ms":START+seconds*1000,
                "workers":[{"group":"hg1","machine":MACHINE,"ip":"192.0.2.1","network_bytes":total,"received_age_ms":0}]}})
        bars=honeygain_minutes(rows,START,START+180000)
        measured=[b for b in bars if b["mb"] is not None]
        self.assertEqual(len(bars),1440)
        self.assertEqual([b["mb"] for b in measured],[40,60,20])
        self.assertEqual(sum(b["mb"] for b in measured),120)
        self.assertTrue(all(b["estimated"] for b in measured))
        self.assertTrue(all(b["nodes"][0]["ip"]=="192.0.2.1" for b in measured))
        rows[-1]["hg"]["workers"][0]["ip"]="192.0.2.2"
        self.assertTrue(all(b["mb"] is None for b in honeygain_minutes(rows,START,START+180000)))

    def test_honeygain_does_not_bridge_an_ip_that_returns_later(self):
        rows=[{"time_ms":START+t*1000,"hg":{"status_observed_ms":START+t*1000,"workers":[{"machine":MACHINE,"ip":ip,"network_bytes":t*1_000_000,"received_age_ms":0}]}} for t,ip in [(0,"192.0.2.1"),(80,"192.0.2.2"),(160,"192.0.2.1")]]
        self.assertTrue(all(b["mb"] is None for b in honeygain_minutes(rows,START,START+180000)))

    def test_honeygain_missing_gap_and_counter_reset_are_not_estimated_traffic(self):
        for second,value in [(240,2_000_000),(60,500_000),(60,None)]:
            rows=[{"time_ms":START+t*1000,"hg":{"status_observed_ms":START+t*1000,
                "workers":[{"machine":MACHINE,"network_bytes":n,"received_age_ms":0}]}} for t,n in [(0,1_000_000),(second,value)]]
            self.assertTrue(all(b["mb"] is None for b in honeygain_minutes(rows,START,START+300000)))

    def test_honeygain_popup_returns_twenty_largest_contributors(self):
        rows=[]
        for second in (0,60):
            rows.append({"time_ms":START+second*1000,"hg":{"status_observed_ms":START+second*1000,
                "workers":[{"machine":str(i),"ip":"192.0.2."+str(i),"network_bytes":i*1_000_000*second/60,"received_age_ms":0} for i in range(1,31)]}})
        bar=next(b for b in honeygain_minutes(rows,START,START+60000) if b["mb"] is not None)
        self.assertEqual(bar["count"],30)
        self.assertEqual(bar["mb"],465)
        self.assertEqual(len(bar["nodes"]),20)
        self.assertEqual(bar["nodes"][0]["mb"],30)

    def test_salad_restart_timestamp_accepts_seven_fractional_digits(self):
        self.assertEqual(timestamp_ms("2026-09-06T15:57:21.5157715+00:00"), 1788710241515)

    def test_timeline_uses_distinct_source_times_and_actual_elapsed_seconds(self):
        rows = [observation(0, 1, 2), observation(20, 3, 8), observation(50, 3, 20)]
        rows[-1]["ps"]["provider_observed_ms"] = START + 20_000
        timeline, truncated = rate_timeline(rows, START, START + 50_000)
        self.assertFalse(truncated)
        self.assertEqual(len(timeline["ps"]["provider"]), 1)
        self.assertEqual(timeline["ps"]["provider"][0]["per_second"], 100_000)
        self.assertEqual([p["per_second"] for p in timeline["ps"]["network"]], [300_000, 400_000])
        self.assertEqual(timeline["ps"]["network"][-1]["end_ms"], START + 50_000)

    def test_timeline_preserves_gaps_resets_and_partial_network_activity(self):
        rows = [observation(s, paid, s, complete=s != 360) for s, paid in ((0, 100), (60, 101), (300, 104), (360, 2))]
        timeline, _ = rate_timeline(rows, START, START + 360_000)
        paid = timeline["ps"]["provider"]
        self.assertEqual([p["status"] for p in paid], ["complete", "gap", "counter_reset"])
        self.assertIsNone(paid[1]["per_second"])
        self.assertEqual(paid[1]["delta"], 3_000_000)
        self.assertIsNone(paid[2]["per_second"])
        self.assertIsNone(paid[2]["delta"])
        partial = timeline["ps"]["network"][-1]
        self.assertEqual(partial["status"], "incomplete")
        self.assertFalse(partial["complete"])
        self.assertEqual(partial["per_second"], 1_000_000)
        self.assertTrue(all(p["complete"] for p in timeline["hg"]["provider"]))

    def test_timeline_has_no_fabricated_timestamps_or_prebaseline_hg_earnings(self):
        rows = [observation(s, s) for s in (0, 60, 120)]
        for row in rows:
            row["ps"]["network_observed_ms"] = None
            row["ps"]["provider_observed_ms"] = START - 1000
        timeline, _ = rate_timeline(rows, START, START + 120_000, START + 60_000)
        self.assertEqual(timeline["ps"]["network"], [])
        self.assertEqual(timeline["ps"]["provider"], [])
        self.assertEqual(len(timeline["hg"]["provider"]), 1)
        self.assertEqual(timeline["hg"]["provider"][0]["start_ms"], START + 60_000)

    def test_records_rate_fall_without_calling_network_earnings(self):
        rows = [observation(s, s / 10 if s <= 600 else 60 + (s - 600) / 20) for s in range(0, 1201, 60)]
        buckets = rate_buckets(rows, START, START + 1200_000)
        self.assertEqual(len(buckets), 2)
        self.assertAlmostEqual(buckets[0]["ps_credited"]["delta"], 60)
        self.assertAlmostEqual(buckets[1]["ps_credited"]["delta"], 30)
        self.assertEqual(buckets[0]["ps_network"]["delta"], 120)
        self.assertEqual(buckets[1]["ps_credited"]["change_percent"], -50)
        self.assertEqual(buckets[0]["hg_credits"]["delta"], 10)
        self.assertEqual(buckets[0]["ps_credited"]["status"], "complete")

    def test_counter_reset_is_unknown_not_negative_earning(self):
        rows = [observation(s, s if s < 300 else s - 300) for s in range(0, 601, 60)]
        value = rate_buckets(rows, START, START + 600_000)[0]["ps_credited"]
        self.assertEqual(value["status"], "counter_reset")
        self.assertIsNone(value["delta"])
        self.assertIsNone(value["per_10_min"])

    def test_gap_has_no_claimed_ten_minute_rate(self):
        rows = [observation(s, s / 10) for s in [0, 60, 540, 600]]
        value = rate_buckets(rows, START, START + 600_000)[0]["ps_credited"]
        self.assertEqual(value["delta"], 60)
        self.assertEqual(value["status"], "gap")
        self.assertIsNone(value["per_10_min"])

    def test_missing_network_workers_do_not_become_full_fleet_zero(self):
        rows = [observation(s, 0, complete=s != 300) for s in range(0, 601, 60)]
        value = rate_buckets(rows, START, START + 600_000)[0]["ps_network"]
        self.assertEqual(value["status"], "incomplete")
        self.assertIsNone(value["per_10_min"])
        self.assertEqual(value["delta"], 0)

    def test_stale_provider_observation_is_not_a_new_zero_earning_sample(self):
        rows = [observation(s, 42) for s in range(0, 601, 60)]
        for row in rows:
            row["ps"]["provider_observed_ms"] = START - 60_000
        value = rate_buckets(rows, START, START + 600_000)[0]["ps_credited"]
        self.assertEqual(value["status"], "missing")
        self.assertIsNone(value["delta"])

    def test_honeygain_network_remains_separate_from_credits(self):
        rows = [observation(s, s / 10) for s in range(0, 601, 60)]
        for row in rows:
            row["hg"].update(network_total_bytes=(row["time_ms"] - START) * 200,
                             network_observed_ms=row["time_ms"], network_complete=True)
        bucket = rate_buckets(rows, START, START + 600_000)[0]
        self.assertEqual(bucket["hg_network"]["delta"], 120)
        self.assertEqual(bucket["hg_credits"]["delta"], 10)

    def test_five_minute_hg_readings_are_expected_but_ps_readings_are_gapped(self):
        bucket = rate_buckets([observation(s, s / 10) for s in [0, 300, 600]], START, START + 600_000)[0]
        self.assertEqual(bucket["hg_credits"]["status"], "complete")
        self.assertEqual(bucket["ps_credited"]["status"], "gap")

    def test_missing_first_or_last_minute_stays_partial(self):
        for times in (range(60, 601, 60), range(0, 541, 60)):
            value = rate_buckets([observation(s, s / 10) for s in times], START, START + 600_000)[0]["ps_credited"]
            self.assertEqual(value["status"], "partial")
            self.assertIsNone(value["per_10_min"])


class FleetTestFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "fleet-tests"
        self.root.mkdir()
        self.current = {"id": "test-one", "started_ms": START, "status": "measuring",
                        "phase": "baseline", "ps": {"desired": 10, "baseline_provider_bytes": 100_000_000,
                                                     "organization": "test-org", "group": "ps-current"},
                        "hg": {"desired": 10}, "api_key": "secret-not-for-browser"}
        (self.root / "current.json").write_text(json.dumps(self.current))

    def tearDown(self):
        self.tmp.cleanup()

    def write_rows(self, rows):
        (self.root / "observations.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    def write_census(self, restarted, observed, instance=INSTANCE, group="test-org/default/ps-current"):
        def stamp(seconds):
            return datetime.fromtimestamp(START / 1000 + seconds, timezone.utc).isoformat()
        directory = self.root.parent / "packetstream"
        directory.mkdir(exist_ok=True)
        census = {"group": group, "checked_at": stamp(observed), "last_success_at": stamp(observed),
                  "group_state": {"status": "running", "start_time": stamp(restarted)},
                  "nodes": [{"machine": MACHINE, "instance_id": instance,
                             "client_status": {"state": "running", "message": "private-census-message"}}]}
        (directory / "native-census.json").write_text(json.dumps(census))

    def ps_row(self, seconds, paid, network=0, instance=INSTANCE):
        row = observation(seconds, paid, network)
        row["ps"]["status_observed_ms"] = row["time_ms"]
        row["ps"]["workers"][0].update(machine=MACHINE, run=MACHINE + "/" + instance,
            client_status="running", client_status_age_ms=0, sample_source="native_status_only",
            network_bytes=network * 1_000_000, source_age_ms=0)
        return row

    def test_native_minute_observer_suffix_matches_current_census(self):
        row = self.ps_row(610, 110, 999)
        row["ps"]["workers"][0]["run"] += "/1800000600000"
        row["ps"]["workers"][0]["sample_source"] = "native_minutes"
        self.write_rows([row])
        self.write_census(600, 610)
        result = FleetTestView(self.root).snapshot(now_ms=START + 611_000)
        self.assertEqual(result["latest"]["ps"]["inventory_status"], "matched")
        self.assertEqual(result["latest"]["ps"]["workers"][0]["sample_source"], "native_minutes")

    def test_restart_window_rebases_account_and_network_without_crossing_restart(self):
        rows = [self.ps_row(s, paid, network) for s, paid, network in ((0, 100, 200), (590, 110, 220), (610, 111, 230), (670, 113, 234))]
        self.write_rows(rows)
        self.write_census(600, 670)
        result = FleetTestView(self.root).snapshot(now_ms=START + 671_000)
        window = result["service_windows"]["ps"]
        self.assertEqual(window["start_ms"], START + 600_000)
        self.assertEqual(window["basis"], "native_restart")
        self.assertFalse(window["stale"])
        self.assertEqual(window["provider_baseline_ms"], START + 610_000)
        self.assertEqual(result["summary"]["ps_credited_mb"], 2)
        self.assertEqual(result["summary"]["ps_network_mb"], 4)
        for metric in ("provider", "network"):
            self.assertEqual(len(result["timeline"]["ps"][metric]), 1)
            self.assertEqual(result["timeline"]["ps"][metric][0]["start_ms"], START + 610_000)
        self.assertEqual(result["latest"]["ps"]["workers"][0]["network_interval"]["start_ms"], START + 610_000)
        self.assertEqual(result["service_windows"]["hg"]["start_ms"], START)
        self.assertNotIn("private-census-message", json.dumps(result))

    def test_new_run_earnings_require_two_distinct_fresh_reset_free_readings(self):
        for scenario in ("pre_restart", "one_reading", "reset", "stale_provider", "stale_census"):
            with self.subTest(scenario=scenario):
                rows = [self.ps_row(590, 110), self.ps_row(610, 111), self.ps_row(670, 113)]
                now = 671
                if scenario == "pre_restart":
                    for row in rows[1:]:
                        row["ps"].update(provider_observed_ms=START + 590_000, provider_bytes=110_000_000)
                elif scenario == "one_reading":
                    rows[-1]["ps"].update(provider_observed_ms=START + 610_000, provider_bytes=111_000_000)
                elif scenario == "reset":
                    rows[-1]["ps"]["provider_bytes"] = 1_000_000
                elif scenario == "stale_provider":
                    now = 900
                elif scenario == "stale_census":
                    now = 770
                self.write_rows(rows)
                self.write_census(600, 670 if scenario == "stale_census" else now)
                result = FleetTestView(self.root).snapshot(now_ms=START + now * 1000)
                self.assertIsNone(result["summary"]["ps_credited_mb"])

    def test_newer_census_hides_replaced_instances_until_the_ledger_catches_up(self):
        self.write_rows([self.ps_row(610, 111, 1)])
        self.write_census(600, 615, instance=REPLACEMENT)
        result = FleetTestView(self.root).snapshot(now_ms=START + 616_000)
        ps = result["latest"]["ps"]
        self.assertEqual(ps["inventory_status"], "awaiting_current_run")
        self.assertEqual(len(ps["workers"]), 10)
        self.assertTrue(all(w["state"] == "unknown" and not w.get("run") for w in ps["workers"]))
        self.assertIsNone(ps["running"])
        self.assertFalse(ps["network_complete"])
        self.assertTrue(any("Older container rows are hidden" in w for w in result["warnings"]))

    def test_restart_does_not_reuse_an_earlier_event_or_worker_counter(self):
        rows = [self.ps_row(590, 110, 100), self.ps_row(610, 111, 200)]
        rows[-1]["ps"]["workers"][0]["client_status_age_ms"] = 20_000
        self.write_rows(rows)
        self.write_census(600, 610)
        result = FleetTestView(self.root).snapshot(now_ms=START + 611_000)
        worker = result["latest"]["ps"]["workers"][0]
        self.assertEqual(worker["client_status"], "unknown")
        self.assertTrue(worker["client_status_stale"])
        self.assertIsNone(worker["network_interval"]["per_second"])

    def test_wrong_target_census_and_older_membership_do_not_replace_newer_ledger(self):
        self.write_rows([self.ps_row(620, 111, instance=REPLACEMENT)])
        self.write_census(600, 615, group="other-org/default/ps-current")
        result = FleetTestView(self.root).snapshot(now_ms=START + 621_000)
        self.assertEqual(result["service_windows"]["ps"]["start_ms"], START)
        self.assertTrue(result["service_windows"]["ps"]["stale"])
        self.assertEqual(result["latest"]["ps"]["workers"][0]["run"], MACHINE + "/" + REPLACEMENT)
        self.write_census(600, 615)
        result = FleetTestView(self.root).snapshot(now_ms=START + 621_000)
        self.assertEqual(result["latest"]["ps"]["workers"][0]["run"], MACHINE + "/" + REPLACEMENT)

    def test_archives_keep_test_window_and_original_baseline_after_a_live_restart(self):
        archive = self.root / "archives" / "test-one"
        archive.mkdir(parents=True)
        (archive / "current.json").write_text(json.dumps(self.current))
        rows = [self.ps_row(s, paid) for s, paid in ((0, 100), (590, 110), (610, 111), (670, 113))]
        (archive / "observations.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        self.write_census(600, 670, instance=REPLACEMENT)
        result = FleetTestView(self.root).snapshot(now_ms=START + 671_000, archive="test-one")
        self.assertEqual(result["service_windows"]["ps"]["start_ms"], START)
        self.assertEqual(result["service_windows"]["ps"]["basis"], "test")
        self.assertEqual(result["summary"]["ps_credited_mb"], 13)
        self.assertEqual(len(result["timeline"]["ps"]["provider"]), 3)
        self.assertEqual(result["latest"]["ps"]["workers"][0]["run"], MACHINE + "/" + INSTANCE)

    def test_current_snapshot_ignores_prior_run_and_allowlists_secrets(self):
        prior = observation(0, 999, experiment="old-test")
        good = observation(60, 102)
        good["ps"]["password"] = "secret-password"
        good["ps"]["workers"][0]["token"] = "secret-token"
        good["errors"] = ["failure contains secret-password"]
        self.write_rows([prior, observation(0, 100), good])
        result = FleetTestView(self.root).snapshot(now_ms=START + 70_000)
        self.assertEqual(result["observation_count"], 2)
        self.assertEqual(result["summary"]["ps_credited_mb"], 2)
        self.assertEqual(result["latest"]["ps"]["workers"][0]["client_status"], "unknown")
        self.assertNotIn("secret", json.dumps(result))
        self.assertEqual(len(result["latest"]["ps"]["workers"]), 10)

    def test_bad_tail_and_stopped_recorder_are_visible(self):
        self.write_rows([observation(0, 100)])
        with (self.root / "observations.jsonl").open("a") as handle:
            handle.write('{"partial":')
        result = FleetTestView(self.root).snapshot(now_ms=START + 300_000)
        self.assertTrue(result["recorder_stale"])
        self.assertEqual(result["invalid_lines"], 1)
        self.assertTrue(result["warnings"])

    def test_hg_worker_error_codes_are_allowlisted(self):
        cases = [(code, code) for code in (
            "device_limit", "device_already_active", "network_overused", "network_unusable", "authorization_error")]
        cases += [(None, None), ("", None),
                  ("RuntimeError: https://example.invalid/?token=private-value-not-for-browser", "observer_error"),
                  ("device_limit: private-value-not-for-browser", "observer_error"),
                  ({"message": "private-value-not-for-browser"}, "observer_error")]
        for raw_error, expected in cases:
            with self.subTest(raw_error=raw_error):
                row = observation(0, 100)
                row["hg"]["workers"][0]["error"] = raw_error
                self.write_rows([row])
                result = FleetTestView(self.root).snapshot(now_ms=START + 10_000, include_observations=True)
                for source in (result["latest"], result["observations"][0]):
                    worker = source["hg"]["workers"][0]
                    self.assertEqual(worker["error_code"], expected)
                    self.assertNotIn("error", worker)
                self.assertNotIn("private-value-not-for-browser", json.dumps(result))

    def test_ps_errors_and_native_census_age_are_sanitized_independently(self):
        cases = [(None, None), ("", None),
                 ("PacketStream allows packeting from 1 client per IP address. private-value-not-for-browser", "duplicate_ip"),
                 ("one client per IP private-value-not-for-browser", "client_error"),
                 ({"message": "private-value-not-for-browser"}, "client_error")]
        for raw_error, expected in cases:
            with self.subTest(raw_error=raw_error):
                row = observation(90, 100)
                row["ps"]["status_observed_ms"] = START
                row["ps"]["workers"][0].update(run="instance-a", sample_source="native_status_only",
                    client_status="running", client_status_age_ms=30_000, error=raw_error)
                self.write_rows([row])
                result = FleetTestView(self.root).snapshot(now_ms=START + 100_000, include_observations=True)
                ps = result["latest"]["ps"]
                worker = ps["workers"][0]
                self.assertFalse(result["recorder_stale"])
                self.assertEqual(ps["status_age_ms"], 100_000)
                self.assertTrue(ps["status_stale"])
                self.assertTrue(ps["native_status_only"])
                self.assertEqual(worker["client_status"], "running")
                self.assertEqual(worker["client_status_age_ms"], 40_000)
                self.assertTrue(worker["client_status_stale"])
                self.assertEqual(worker["run"], "instance-a")
                self.assertEqual(worker["error_code"], expected)
                self.assertNotIn("error", worker)
                self.assertEqual(result["observations"][0]["ps"]["workers"][0]["client_status_age_ms"], 30_000)
                self.assertNotIn("private-value-not-for-browser", json.dumps(result))

    def test_native_event_age_does_not_add_the_census_age_again(self):
        row = observation(300, 100)
        row["ps"]["status_observed_ms"] = START + 280_000
        row["ps"]["workers"][0].update(sample_source="native_status_only", client_status_age_ms=180_000)
        self.write_rows([row])
        for recorder_age in (0, 2000):
            with self.subTest(recorder_age=recorder_age):
                result = FleetTestView(self.root).snapshot(now_ms=START + 300_000 + recorder_age)
                ps = result["latest"]["ps"]
                self.assertEqual(ps["status_age_ms"], 20_000 + recorder_age)
                self.assertEqual(ps["workers"][0]["client_status_age_ms"], 180_000 + recorder_age)
                self.assertFalse(ps["status_stale"])
                self.assertFalse(ps["workers"][0]["client_status_stale"])

    def test_native_client_event_has_its_own_four_minute_cutoff(self):
        for event_age, expected_stale in ((230_000, False), (231_000, True)):
            with self.subTest(event_age=event_age):
                row = observation(300, 100)
                row["ps"]["status_observed_ms"] = START + 300_000
                row["ps"]["workers"][0].update(sample_source="native_status_only", client_status_age_ms=event_age)
                self.write_rows([row])
                result = FleetTestView(self.root).snapshot(now_ms=START + 310_000)
                self.assertFalse(result["latest"]["ps"]["status_stale"])
                self.assertEqual(result["latest"]["ps"]["workers"][0]["client_status_stale"], expected_stale)

    def test_worker_rates_use_sample_times_without_mutating_ledger_ages(self):
        rows = [observation(s, 100) for s in (0, 30, 60)]
        for row, ps_bytes, hg_bytes in zip(rows, (100, 160, 220), (500, 800, 1100)):
            row["ps"]["status_observed_ms"] = row["time_ms"]
            row["ps"]["workers"][0].update(run="instance-a", network_bytes=ps_bytes, source_age_ms=1000, received_age_ms=500)
            row["hg"]["status_observed_ms"] = row["time_ms"]
            row["hg"]["workers"][0].update(network_bytes=hg_bytes, received_age_ms=5000)
        self.write_rows(rows)
        result = FleetTestView(self.root).snapshot(now_ms=START + 61_000, include_observations=True)
        ps = result["latest"]["ps"]["workers"][0]
        hg = result["latest"]["hg"]["workers"][0]
        self.assertEqual(ps["network_interval"]["per_second"], 2)
        self.assertEqual(ps["network_interval"]["end_ms"], START + 59_000)
        self.assertEqual(hg["network_interval"]["per_second"], 10)
        self.assertEqual(hg["network_interval"]["end_ms"], START + 55_000)
        self.assertEqual(ps["source_age_ms"], 2000)
        self.assertEqual(result["observations"][-1]["ps"]["workers"][0]["source_age_ms"], 1000)

    def test_worker_restart_gap_reset_and_stale_samples_have_unknown_rates(self):
        for run, seconds, current_bytes, now_seconds, expected in (
            ("new-instance", 60, 200, 61, "missing"),
            ("same-instance", 60, 50, 61, "counter_reset"),
            ("same-instance", 240, 200, 241, "gap"),
            ("same-instance", 60, 200, 121, "stale"),
            ("same-instance", 60, None, 61, "missing"),
        ):
            with self.subTest(expected=expected):
                rows = [observation(0, 100), observation(seconds, 100)]
                rows[0]["ps"]["workers"][0].update(run="same-instance", network_bytes=100, source_age_ms=0)
                rows[1]["ps"]["workers"][0].update(run=run, network_bytes=current_bytes, source_age_ms=0)
                self.write_rows(rows)
                result = FleetTestView(self.root).snapshot(now_ms=START + now_seconds * 1000)
                interval = result["latest"]["ps"]["workers"][0]["network_interval"]
                self.assertEqual(interval["status"], expected)
                self.assertIsNone(interval["per_second"])
                self.assertFalse(interval["complete"])

    def test_fresh_recorder_does_not_hide_a_stale_honeygain_observer(self):
        row = observation(300, 100)
        row["hg"]["status_observed_ms"] = START
        row["hg"]["workers"][0]["received_age_ms"] = 2000
        row["ps"]["workers"][0]["network_bytes"] = 9_000_000
        row["ps"]["workers"][0]["received_age_ms"] = 1000
        self.write_rows([row])
        result = FleetTestView(self.root).snapshot(now_ms=START + 310_000)
        self.assertFalse(result["recorder_stale"])
        self.assertTrue(result["latest"]["hg"]["status_stale"])
        self.assertEqual(result["latest"]["hg"]["status_age_ms"], 310_000)
        self.assertEqual(result["latest"]["hg"]["workers"][0]["received_age_ms"], 312_000)
        self.assertEqual(result["latest"]["ps"]["workers"][0]["received_age_ms"], 11_000)
        self.assertEqual(result["latest"]["ps"]["workers"][0]["network_bytes"], 9_000_000)
        self.assertTrue(any("observer" in warning for warning in result["warnings"]))

    def test_hg_explicit_baseline_excludes_startup_credits(self):
        self.current["hg"].update(baseline_provider_gathering_credits=181.73,
                                  baseline_provider_observed_ms=START + 300_000,
                                  baseline_started_ms=START + 300_000)
        (self.root / "current.json").write_text(json.dumps(self.current))
        rows = [observation(s, 100) for s in (0, 300, 600)]
        for row, credits in zip(rows, (169.74, 181.73, 187.33)):
            row["hg"]["provider_gathering_credits"] = credits
        rows[-1]["ps"]["accepted"] = 7
        rows[-1]["ps"]["workers"][0].update(sample_source="salad_logs_10s", source_granularity_seconds=10, last_interval_seconds=10)
        self.write_rows(rows)
        result = FleetTestView(self.root).snapshot(now_ms=START + 610_000)
        self.assertAlmostEqual(result["summary"]["hg_gathering_credits"], 5.6)
        self.assertEqual(result["latest"]["ps"]["accepted"], 7)
        self.assertEqual(result["latest"]["ps"]["workers"][0]["sample_source"], "salad_logs_10s")
        self.write_rows(rows[:2])
        result = FleetTestView(self.root).snapshot(now_ms=START + 310_000)
        self.assertIsNone(result["summary"]["hg_gathering_credits"])
        rows[-1]["hg"]["provider_gathering_credits"] = 20
        self.write_rows(rows)
        self.assertIsNone(FleetTestView(self.root).snapshot(now_ms=START + 610_000)["summary"]["hg_gathering_credits"])

    def test_archive_selection_cannot_escape_archive_directory(self):
        view = FleetTestView(self.root)
        for name in ["../current.json", "/tmp", "a/b", ".."]:
            with self.assertRaises(ValueError):
                view.snapshot(archive=name)

    def test_saved_experiment_archive_is_readable(self):
        archive = self.root / "archives" / "test-one"
        archive.mkdir(parents=True)
        (archive / "current.json").write_text(json.dumps(self.current))
        (archive / "observations.jsonl").write_text(json.dumps(observation(0, 100)) + "\n")
        result = FleetTestView(self.root).snapshot(now_ms=START + 60_000, archive="test-one")
        self.assertEqual(result["experiment"]["id"], "test-one")
        self.assertTrue(result["archived"])
        self.assertEqual(result["archives"][0]["id"], "test-one")


if __name__ == "__main__":
    unittest.main()
