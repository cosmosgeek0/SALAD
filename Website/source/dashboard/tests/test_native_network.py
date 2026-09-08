import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from dashboard.native_network import NetworkMinutes, parse_minute

START = 1_800_000_000_000
MACHINE = '11111111-1111-1111-1111-111111111111'
INSTANCE = '22222222-2222-2222-2222-222222222222'
OTHER = '44444444-4444-4444-4444-444444444444'
GROUP = 'test-group'


def sample(seq, amount, instance=INSTANCE, **changes):
    values = dict(instance=instance, machine=MACHINE, observer=START, seq=seq,
                  start_ms=START + max(0, seq-1)*60000, end_ms=START+seq*60000,
                  rx=amount, tx=0, total_rx=amount, total_tx=0, ip='192.0.2.1',
                  state='running', error='none', final=0, bucket_ms=START+max(0, seq-1)*60000)
    values.update(changes)
    return {'text_log': 'PS_MINUTE_V2 ' + ' '.join(f'{k}={v}' for k,v in values.items())}


class NativeNetworkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = NetworkMinutes(Path(self.tmp.name)/'minutes.sqlite3')
        self.now = START+130000
        self.census = {'group_id': GROUP, 'desired_replicas': 2,
                       'checked_at': datetime.fromtimestamp(self.now/1000,timezone.utc).isoformat(),
                       'nodes': [{'machine': MACHINE, 'instance_id': i, 'salad_state': 'running'} for i in (INSTANCE,OTHER)]}

    def tearDown(self):
        self.store.db.close()
        self.tmp.cleanup()

    def ingest(self,*items):
        return self.store.ingest([parse_minute(i,GROUP,self.now) for i in items])

    def view(self, **kwargs):
        return self.store.snapshot(self.census, now_ms=self.now, **kwargs)

    def test_common_minutes_contributions_totals_and_replay(self):
        items = [sample(0,0),sample(1,60000000),sample(2,1500000,total_rx=61500000),sample(2,2500000,OTHER)]
        self.assertEqual(self.ingest(*items),4)
        self.assertEqual(self.ingest(*items),0)
        result=self.view()
        self.assertEqual([b['mb'] for b in result['candles'] if b['mb'] is not None], [60,4])
        detail=self.store.minute(GROUP,START+60000)
        self.assertEqual(detail['mb'],4)
        self.assertEqual(sum(n['mb'] for n in detail['nodes']),4)
        self.assertEqual(result['nodes'][0]['total_mb'],61.5)
        self.assertEqual(result['nodes'][0]['latest_mb_per_minute'],1.5)
        self.assertEqual(result['nodes'][0]['status'],'Running')
        self.assertEqual(result['disk']['total_records'],4)
        self.assertEqual(result['disk']['total_record_bytes'],sum(len(i['text_log'].encode())+1 for i in items))
        first=self.store.minute(GROUP,START)
        self.assertEqual(first['nodes'][0]['mb'],60)
        self.assertEqual(len(first['nodes']),1)

    def test_missing_and_conflicting_records_are_not_zero(self):
        self.ingest(sample(1,1000000),sample(1,2000000),sample(3,0))
        result=self.view()
        self.assertEqual([b['mb'] for b in result['candles'][-3:]], [None,None,0])
        self.assertIsNone(self.store.minute(GROUP,START+60000)['mb'])
        self.assertTrue(result['nodes'][0]['has_gaps'])

    def test_selected_minute_includes_reallocated_contributor(self):
        self.ingest(sample(1,4000000,final=1),sample(1,7000000,OTHER))
        self.census['nodes']=self.census['nodes'][1:]
        result=self.view()
        detail=self.store.minute(GROUP,START)
        self.assertEqual(detail['mb'],11)
        self.assertEqual(sum(n['mb'] for n in detail['nodes']),11)
        self.assertEqual(len(result['nodes']),1)
        self.assertEqual(result['nodes'][0]['instance'],OTHER)

    def test_bad_component_does_not_break_candle_contribution_sum(self):
        self.ingest(sample(1,1000000,end_ms=START+30000),sample(2,2000000,start_ms=START+30000,end_ms=START+60000,bucket_ms=START))
        self.ingest(sample(2,9000000,start_ms=START+30000,end_ms=START+60000,bucket_ms=START))
        result=self.view()
        detail=self.store.minute(GROUP,START)
        self.assertEqual(detail['mb'],1)
        self.assertEqual(detail['nodes'][0]['mb'],1)
        self.assertTrue(next(b for b in result['candles'] if b['minute_ms']==START)['partial'])

    def test_unaligned_legacy_and_delayed_intervals_are_marked_estimated(self):
        delayed=sample(1,1000000,end_ms=START+61000)
        legacy=sample(2,2000000);legacy['text_log']=legacy['text_log'].replace('PS_MINUTE_V2','PS_MINUTE_V1').split(' bucket_ms=')[0]
        self.ingest(delayed,legacy)
        measured=[b for b in self.view()['candles'] if b['mb'] is not None]
        self.assertTrue(measured)
        self.assertTrue(all(b['estimated'] for b in measured))
        self.assertAlmostEqual(sum(b['mb'] for b in measured),3)
        self.assertEqual(self.view()['nodes'][0]['total_mb'],2)

    def test_large_history_gap_is_bounded_and_stale_status_is_explicit(self):
        self.ingest(sample(1,1000000),sample(10000,1000000))
        result=self.view()
        self.assertEqual(len(result['candles']),1440)
        self.now += 300000
        result=self.view()
        self.assertFalse(result['inventory_fresh'])
        self.assertEqual(result['nodes'][0]['status'],'Status feed stale')

    def test_baseline_has_no_bar_and_zero_interval_is_measured(self):
        self.ingest(sample(0,0))
        self.assertTrue(all(b['mb'] is None for b in self.view()['candles']))
        self.ingest(sample(1,0))
        self.assertEqual(self.store.minute(GROUP,START)['mb'],0)


    def test_full_day_top_twenty_countries_and_stopped_client(self):
        self.ingest(sample(1,1000000,final=1))
        result=self.view()
        self.assertEqual(result['nodes'][0]['status'],'Stopped')
        self.assertEqual(result['running'],0)
        self.assertEqual(len(result['candles']),1440)
        self.assertEqual(result['candles'][-1]['minute_ms']-result['candles'][0]['minute_ms'],1439*60000)
        for i in range(30):
            self.ingest(sample(1,(i+1)*1000000,instance=f'{i:08x}-aaaa-aaaa-aaaa-aaaaaaaaaaaa',ip=f'192.0.2.{i+1}'))
        with self.store.db:self.store.db.execute("INSERT INTO countries VALUES ('192.0.2.30','US')")
        detail=self.store.minute(GROUP,START)
        self.assertEqual(len(detail['nodes']),20)
        self.assertEqual(detail['nodes'][0]['mb'],30)
        self.assertEqual(detail['nodes'][0]['country'],'US')
        self.assertEqual(detail['count'],31)
        self.assertEqual(detail['mb'],466)

    def test_snapshot_read_transaction_keeps_concurrent_collector_consistent(self):
        self.ingest(sample(1,1000000))
        writer=NetworkMinutes(self.store.path)
        original=self.store.latest
        def interleave(group):
            rows=original(group)
            writer.ingest([parse_minute(sample(2,5000000,total_rx=6000000),GROUP,self.now)])
            return rows
        self.store.latest=interleave
        result=self.view()
        self.assertEqual(result['nodes'][0]['total_mb'],1)
        self.assertIsNone(result['candles'][-2]['mb'])
        self.store.latest=original
        self.assertEqual(self.view()['nodes'][0]['total_mb'],6)
        writer.db.close()

if __name__ == '__main__': unittest.main()
