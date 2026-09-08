from pathlib import Path
import importlib.util,json,tempfile
root=Path(__file__).resolve().parents[1];s=importlib.util.spec_from_file_location('rp',root/'repocket-monitor/observe.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
with tempfile.TemporaryDirectory(dir=root) as directory:
 m.DATA=Path(directory);gid='33333333-3333-3333-3333-333333333333';dep={'id':gid,'replicas':1};db=m.database(gid)
 at=1788800040000;began=at-600000;machine='11111111-1111-1111-1111-111111111111';iid='22222222-2222-2222-2222-222222222222'
 base={'service':'repocket','format':2,'revision':11,'group_id':gid,'machine':machine,'instance':iid,'run':iid+':'+str(began),'started_ms':began,'time_ms':at,'seq':1,'kind':'minute','start_ms':at-60000,'end_ms':at,'elapsed_ms':60000,'rx_bytes':1000000,'tx_bytes':2000000,'phase':'connected','ip':'203.0.113.1','diagnostics':{'time_ms':at},'policy':{'checked_ms':at,'state':'keeping'},'valid':True}
 def add(item): return m.insert(db,[{'text_log':'RP_MON '+json.dumps(item)}],gid,at+30000)
 instances=[{'id':iid,'machine_id':machine,'state':'running','update_time':m.stamp(at)}]
 def view():return m.snapshot(db,dep,{'replicas':1},instances,at+30000,{'inventory_ms':at+30000},{})
 add(base);w=view()['workers'][0];assert w['native_fresh'] and w['run']==base['run'] and w['last_mb_per_minute']==3,w
 add({**base,'seq':2,'time_ms':at+15000,'kind':'tick'})
 add({**base,'seq':3,'time_ms':at+20000,'end_ms':at+20000,'start_ms':at,'elapsed_ms':20000,'valid':False,'rx_bytes':None,'tx_bytes':None,'counter_error':'reset'})
 w=view()['workers'][0];assert w['native_fresh'] and not w['network_fresh'] and w['last_mb_per_minute'] is None,w
 with db:db.execute('DELETE FROM events')
 add({**base,'partial':True,'final':True,'start_ms':at-60000,'end_ms':at-500,'elapsed_ms':59500})
 bars=view()['chart_minutes'];assert len(bars)==1 and bars[0]['partial'] and bars[0]['estimated'] and bars[0]['mb']==3,bars
 with db:db.execute('DELETE FROM events')
 add({**base,'kind':'tick','time_ms':at-300000})
 newer='44444444-4444-4444-4444-444444444444';new_start=at-45000
 add({**base,'kind':'tick','instance':newer,'run':newer+':'+str(new_start),'started_ms':new_start,'time_ms':at+20000})
 instances[0]['update_time']=m.stamp(at-30000)
 w=view()['workers'][0];assert w['native_fresh'] and w['instance']==newer,w
 print('PASS exact runtime survives inventory update; stale exact permits newer guarded fallback; reset clears rate; final partial preserves bytes.')
# A 59m25s late record is reconsidered only after its full one-hour allowance.
source=600000;arrives=source+3565000;state={};captured=False
for now in range(0,source+3660000,30000):
 window=m.final_window(state,0,now)
 if window:
  if now>=arrives and window[0]<=source<=window[1]:captured=True
  state['final_through_ms']=window[1]
assert captured
# Simulated failed reads do not mutate progress; a restart catches up with bounded windows.
saved=state.copy();failed=m.final_window(state,0,now+300000);assert state==saved
for later in range(now+300000,now+900000,30000):
 window=m.final_window(state,0,later);assert window[1]-window[0]<=120000
 state['final_through_ms']=window[1]
assert state['final_through_ms']>=later-3600000
print('PASS near-hour delayed log, cursor preservation after failure, bounded outage catch-up.')
# Beginning-of-capture outage must preserve a pending final cursor even before 1h.
state={};captured=False
for now in range(0,9000000,30000):
 if 3000000<=now<4500000:continue
 window=m.final_window(state,0,now)
 if window:
  if now>=4165000 and window[0]<=600000<=window[1]:captured=True
  state['final_through_ms']=window[1]
assert captured
print('PASS initial pre-hour final cursor survives a 50–75 minute recorder outage.')
