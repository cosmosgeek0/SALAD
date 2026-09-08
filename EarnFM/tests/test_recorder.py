"""Offline accounting and recovery-ledger checks; no credentials or HTTP calls."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('recorder', ROOT/'scripts/earnfm-recorder.py')
recorder = importlib.util.module_from_spec(spec); spec.loader.exec_module(recorder)
INSTANCE = '11111111-1111-1111-1111-111111111111'
MACHINE = '22222222-2222-2222-2222-222222222222'
NOW = 1800000000000
TARGET = {'id': 'group', 'created_at': recorder.iso(NOW-600000), 'measurement_started_ms': NOW-600000, 'desired': 1}


def item(seq=1, **extra):
    row = dict(kind='earnfm_sample', revision=2, run=INSTANCE+'/run', seq=seq, instance=INSTANCE,
               machine=MACHINE, start_ms=NOW-90000, end_ms=NOW-30000, rx=101, tx=203,
               total_rx=101, total_tx=203, state='running', valid=1, final=0, ip='192.0.2.1', country='US')
    row.update(extra)
    return {'json_log': row, 'time': recorder.iso(NOW-29000), 'receive_time': recorder.iso(NOW-28000),
            'resource': {'labels': {'container_group_id': 'group', 'machine_id': MACHINE}}}


class RecorderTests(unittest.TestCase):
    def setUp(self):
        self.original_clock=recorder.time.time;recorder.time.time=lambda:NOW/1000
        work = ROOT/'.work'; work.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=work)
        self.path = Path(self.temp.name)/'traffic.sqlite3'
        self.db = recorder.database(self.path)

    def tearDown(self):
        self.db.close(); self.temp.cleanup();recorder.time.time=self.original_clock

    def test_interval_conservation_and_source_clocks(self):
        row = recorder.parse_record(item(), TARGET, NOW)
        self.assertEqual(recorder.ingest(self.db, [row, row]), 1)
        self.assertEqual(tuple(self.db.execute('SELECT SUM(rx),SUM(tx),SUM(duration_ms),MAX(estimated) FROM minute_cache').fetchone()), (101,203,60000,1))
        detail = json.loads(self.db.execute('SELECT body FROM sample_details').fetchone()[0])
        self.assertEqual((detail['log_time_ms'],detail['received_ms'],detail['recorded_ms']), (NOW-29000,NOW-28000,NOW))
        bad = dict(row, rx=102, total_rx=102)
        with self.assertRaisesRegex(RuntimeError, 'Conflicting'): recorder.ingest(self.db, [bad])
        self.assertEqual(self.db.execute('SELECT rx FROM samples').fetchone()[0], 101)

    def test_migration_preserves_original_samples(self):
        row = recorder.parse_record(item(), TARGET, NOW)
        recorder.ingest(self.db, [row])
        self.db.execute('DELETE FROM minute_cache'); self.db.execute("DELETE FROM collector WHERE name='minute_cache_version'"); self.db.commit(); self.db.close()
        self.db = recorder.database(self.path)
        self.assertEqual(tuple(self.db.execute('SELECT COUNT(*),SUM(rx+tx) FROM samples').fetchone()), (1,304))
        self.assertEqual(self.db.execute('SELECT SUM(rx+tx) FROM minute_cache').fetchone()[0],304)

    def test_retired_contributor_keeps_ip_and_duration(self):
        row = recorder.parse_record(item(), TARGET, NOW); recorder.ingest(self.db, [row])
        original = recorder.time.time; recorder.time.time = lambda: NOW/1000
        try:
            out = recorder.snapshot(self.db, TARGET, [], NOW, {})
            node = out['history_nodes'][out['points'][0]['contributions'][0][0]]
            self.assertEqual((node['instance'], node['ip']), (INSTANCE,'192.0.2.1'))
            self.assertEqual(sum(p['mb'] for p in out['points']), .000304)
            inv = [{'id':INSTANCE,'machine_id':MACHINE,'state':'running'}]
            current = recorder.snapshot(self.db, TARGET, inv, NOW, {})['workers'][0]
            self.assertEqual(current['recorded_duration_ms'],60000)
            self.assertFalse(current['provider_online'])
        finally: recorder.time.time = original

    def test_zero_and_invalid_counter_are_distinct(self):
        zero = recorder.parse_record(item(rx=0,tx=0,total_rx=0,total_tx=0), TARGET, NOW)
        recorder.ingest(self.db,[zero]); self.assertEqual(self.db.execute('SELECT SUM(rx+tx) FROM minute_cache').fetchone()[0],0)
        bad = item(seq=2,valid=0); recorder.ingest(self.db,[recorder.parse_record(bad,TARGET,NOW)])
        self.assertEqual(self.db.execute('SELECT SUM(duration_ms) FROM minute_cache').fetchone()[0],60000)

    def test_group_identity_rejected(self):
        bad=item();bad['resource']['labels']['container_group_id']='other'
        with self.assertRaises(ValueError): recorder.parse_record(bad,TARGET,NOW)

    def test_capped_queries_split_and_keep_cursor_on_error(self):
        calls=[]; original=recorder.request
        def request(path, body):
            calls.append(body)
            a,b=recorder.millis(body['start_time']),recorder.millis(body['end_time'])
            self.assertNotIn('machine_id',body['query'])
            return {'items':[{}]*100 if b-a>150000 else []}
        recorder.request=request
        try:
            result=recorder.collect(self.db,TARGET,NOW)
            self.assertTrue(result['caught_up']);self.assertGreater(len(calls),1)
            saved=self.db.execute("SELECT value FROM collector WHERE name='cursor'").fetchone()[0]
            recorder.request=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('HTTP 503'))
            with self.assertRaises(RuntimeError):recorder.collect(self.db,TARGET,NOW+60000)
            self.assertEqual(self.db.execute("SELECT value FROM collector WHERE name='cursor'").fetchone()[0],saved)
        finally:recorder.request=original

    def test_malformed_or_conflicting_record_does_not_block_other_workers(self):
        original=recorder.request; original_clock=recorder.time.time; recorder.time.time=lambda: NOW/1000
        try:
            a=item(); backward=item(seq=2,start_ms=NOW-1000,end_ms=NOW-2000,valid=0)
            b=item(seq=3,start_ms=NOW-2000,end_ms=NOW-1000,rx=5,tx=9,total_rx=106,total_tx=212)
            null_time=item(seq=4); null_time['time']=None
            recorder.request=lambda *args,**kwargs: {'items':[a,backward,null_time,None,[],b]}
            out=recorder.collect(self.db,TARGET,NOW)
            self.assertEqual((out['inserted'],out['rejected']),(2,4))
            self.assertEqual(self.db.execute('SELECT COUNT(*) FROM rejected_records').fetchone()[0],4)
            conflict=item(rx=102,total_rx=102)
            recorder.request=lambda *args,**kwargs: {'items':[conflict,b]}
            out=recorder.collect(self.db,TARGET,NOW+1000)
            self.assertEqual((out['inserted'],out['rejected']),(0,1))
            self.assertEqual(self.db.execute('SELECT rx FROM samples WHERE seq=1').fetchone()[0],101)
            self.assertEqual(self.db.execute("SELECT value FROM collector WHERE name='cursor'").fetchone()[0],str(NOW+1000))
        finally:recorder.request=original;recorder.time.time=original_clock

    def test_counter_observation_failure_visible_until_success(self):
        bad=item(kind='earnfm_event',time_ms=NOW-40000,event_seq=1,action='observer_error',reason='counter_unavailable')
        recorder.ingest(self.db,[recorder.parse_record(bad,TARGET,NOW)])
        inv=[{'id':INSTANCE,'machine_id':MACHINE,'state':'running'}]
        worker=recorder.snapshot(self.db,TARGET,inv,NOW,{})['workers'][0]
        self.assertIn('counter unavailable',worker['error']);self.assertIsNone(worker['kb_per_second'])
        self.assertEqual(worker['observation_error']['received_ms'],NOW-28000)
        recorder.ingest(self.db,[recorder.parse_record(item(),TARGET,NOW)])
        worker=recorder.snapshot(self.db,TARGET,inv,NOW,{})['workers'][0]
        self.assertIsNone(worker['observation_error']);self.assertEqual(worker['error'],'')
        recorder.ingest(self.db,[recorder.parse_record(item(seq=2,start_ms=NOW-2000,end_ms=NOW-1000,valid=0),TARGET,NOW)])
        recorder.ingest(self.db,[recorder.parse_record(bad,TARGET,NOW)])
        worker=recorder.snapshot(self.db,TARGET,inv,NOW,{})['workers'][0]
        self.assertIsNone(worker['observation_error'])

    def test_event_source_time_bounded_without_rejecting_future_retry(self):
        for future in (NOW+3600000,2**53-1):
            bad=item(kind='earnfm_event',time_ms=future,event_seq=1,action='observer_error',reason='counter_unavailable')
            with self.assertRaises(ValueError):recorder.parse_record(bad,TARGET,NOW)
        valid=item(kind='earnfm_event',time_ms=NOW,event_seq=1,action='cooldown_started',reason='rate_limited',retry_at_ms=NOW+86400000)
        self.assertEqual(recorder.parse_record(valid,TARGET,NOW)['event']['retry_at_ms'],NOW+86400000)

    def test_last_provider_ip_is_preserved_separately_from_current_confirmation(self):
        recorder.remember_provider_devices(self.db,{'observed_ms':NOW-30000,'devices':[{'instance':INSTANCE,'ip':'192.0.2.9'}]})
        recorder.remember_provider_devices(self.db,{'observed_ms':NOW,'devices':[]})
        inv=[{'id':INSTANCE,'machine_id':MACHINE,'state':'running'}]
        w=recorder.snapshot(self.db,TARGET,inv,NOW,{'observed_ms':NOW,'devices':[]})['workers'][0]
        self.assertEqual((w['last_provider_ip'],w['last_provider_seen_ms']),('192.0.2.9',NOW-30000))
        self.assertIsNone(w['ip']);self.assertFalse(w['provider_online'])

    def test_skewed_salad_clock_does_not_hide_fresh_recorded_traffic(self):
        source=item();source['receive_time']=recorder.iso(NOW-217000)
        row=recorder.parse_record(source,TARGET,NOW-1000);recorder.ingest(self.db,[row])
        inv=[{'id':INSTANCE,'machine_id':MACHINE,'state':'running'}]
        provider={'observed_ms':NOW,'devices':[{'instance':INSTANCE,'ip':'192.0.2.1'}]}
        original=recorder.time.time;recorder.time.time=lambda:NOW/1000
        try:
            w=recorder.snapshot(self.db,TARGET,inv,NOW,provider)['workers'][0]
            self.assertTrue(w['provider_online']);self.assertAlmostEqual(w['kb_per_second'],304/60000)
            self.assertEqual(w['received_ms'],NOW-217000);self.assertIn('187s',w['telemetry_note'])
            # Re-querying the same source record cannot refresh its first receipt.
            recorder.ingest(self.db,[dict(row,_detail=dict(row['_detail'],recorded_ms=NOW+180000))])
            recorder.time.time=lambda:(NOW+180000)/1000
            w=recorder.snapshot(self.db,TARGET,inv,NOW,provider)['workers'][0]
            self.assertFalse(w['provider_online']);self.assertIsNone(w['kb_per_second'])
            self.assertEqual(w['recorded_ms'],NOW-1000)
        finally:recorder.time.time=original


if __name__=='__main__': unittest.main()
