const test = require('node:test');
const assert = require('node:assert/strict');
const {workerState,serviceModel,chartValue} = require('../static/fleet-test.js');
const worker = () => ({state:'running',client_status:'connected',network_bytes:1000000,received_age_ms:1000});
function snapshot() {return {experiment:{hg:{desired:10},ps:{desired:10}},recorder_stale:false,summary:{hg_network_mb:10,hg_gathering_credits:3,ps_network_mb:0,ps_credited_mb:0.005326},latest:{hg:{workers:Array.from({length:10},worker),status_stale:false,network_complete:true,provider_age_ms:1000},ps:{workers:[],network_complete:false,provider_age_ms:1000}}};}
test('ten fresh connected HG clients count as working independently of earnings',()=>{const s=snapshot();const m=serviceModel('hg',s);assert.equal(m.working,10);assert.equal(m.unknown,0);assert.equal(m.networkKnown,true);});
test('Salad running does not confirm a client',()=>{const s=snapshot();s.latest.hg.workers[0].client_status='exited';const m=serviceModel('hg',s);assert.equal(m.working,9);assert.equal(m.unknown,0);assert.equal(m.states[0].label,'Needs attention');});
test('stale or unverified clients are unknown, not working',()=>{for(const field of ['client','receipt','observer','recorder']){const s=snapshot();if(field==='client')s.latest.hg.workers[0].client_status='connected_last_observed_telemetry_unverified';if(field==='receipt')s.latest.hg.workers[0].received_age_ms=120001;if(field==='observer')s.latest.hg.status_stale=true;if(field==='recorder')s.recorder_stale=true;const m=serviceModel('hg',s);assert.ok(m.working<10);assert.ok(m.unknown>0);}});
test('missing inventory and incomplete zero traffic remain unknown',()=>{const m=serviceModel('ps',snapshot());assert.equal(m.workers.length,10);assert.equal(m.working,0);assert.equal(m.unknown,10);assert.equal(m.networkKnown,false);});
test('stale provider values are retained only as historical values',()=>{const s=snapshot();s.latest.ps.provider_age_ms=180001;const m=serviceModel('ps',s);assert.equal(m.earningsKnown,false);assert.equal(m.earnings,0.005326);});
test('a measured fresh zero is valid but absent readings are not zero',()=>{const s=snapshot();s.summary.hg_gathering_credits=0;assert.equal(serviceModel('hg',s).earningsKnown,true);s.summary.hg_gathering_credits=null;assert.equal(serviceModel('hg',s).earningsKnown,false);});
test('PacketStream acceptance and network sample freshness use separate clocks',()=>{const s=snapshot();const w={state:'running',client_status:'accepted',client_status_age_ms:1000,received_age_ms:20000,source_age_ms:1000,sample_source:'salad_logs_10s'};assert.equal(workerState('ps',w,s).working,true);assert.equal(workerState('ps',w,s).networkFresh,true);w.sample_source='gateway_1s';assert.equal(workerState('ps',w,s).networkFresh,false);w.client_status_age_ms=120001;assert.equal(workerState('ps',w,s).working,false);w.source_age_ms=65000;assert.equal(workerState('ps',w,s).networkFresh,false);});
test('an observer error cannot leave a client healthy',()=>{const s=snapshot();s.latest.hg.workers[0].error_code='observer_error';assert.equal(serviceModel('hg',s).working,9);});
test('chart does not turn missing/reset/incomplete zero into measured zero',()=>{assert.equal(chartValue({status:'missing',delta:null}),null);assert.equal(chartValue({status:'counter_reset',delta:4}),null);assert.equal(chartValue({status:'gap',delta:0}),null);assert.equal(chartValue({status:'gap',delta:4}),null);assert.equal(chartValue({status:'incomplete',delta:0}),null);assert.equal(chartValue({status:'complete',delta:0}),0);assert.equal(chartValue({status:'partial',delta:2}),2);});
test('native PacketStream heartbeat uses current census and the native event interval',()=>{const s=snapshot();s.latest.ps.status_age_ms=10000;const w={state:'running',client_status:'running',sample_source:'native_status_only',client_status_age_ms:180000};assert.equal(workerState('ps',w,s).working,true);s.latest.ps.status_age_ms=91000;assert.equal(workerState('ps',w,s).working,false);s.latest.ps.status_age_ms=10000;w.client_status_age_ms=240001;assert.equal(workerState('ps',w,s).working,false);});
test('restart boundary excludes old and straddling intervals in the display',()=>{const {windowStart,displayedIntervals}=require('../static/fleet-test.js');const s={experiment:{started_ms:1000},service_windows:{ps:{start_ms:10000,basis:'deployment_restart'}},timeline:{ps:{provider:[{start_ms:1000,end_ms:9000},{start_ms:9000,end_ms:11000},{start_ms:11000,end_ms:12000}]}}};assert.equal(windowStart('ps',s),10000);assert.deepEqual(displayedIntervals('ps','provider',s),[{start_ms:11000,end_ms:12000}]);});
test('a stale native error is unverified rather than a current failure',()=>{const s=snapshot();s.latest.ps.status_age_ms=10000;const w={state:'running',client_status:'error',error_code:'client_error',sample_source:'native_status_only',client_status_age_ms:300000};const v=workerState('ps',w,s);assert.equal(v.working,false);assert.equal(v.unknown,true);});
test('sysfs sampling keeps the independent native-client heartbeat window',()=>{const s=snapshot();s.latest.ps.status_age_ms=10000;const w={state:'running',client_status:'running',sample_source:'native_sysfs_1s',native_status_only:true,client_status_age_ms:180000,received_age_ms:30000,source_age_ms:40000};const v=workerState('ps',w,s);assert.equal(v.working,true);assert.equal(v.networkFresh,true);w.source_age_ms=61000;assert.equal(workerState('ps',w,s).networkFresh,false);});

const unified = require('../static/fleet-test.js');
test('unified services use hashes and provide six, twelve and twenty-four hour windows', () => {
  assert.equal(unified.SERVICES.length, 9);
  assert.ok(unified.SERVICES.every(s=>s.hash.startsWith('#')));
  for(const hours of [6,12,24]){
    const bars=unified.periodMinutes([{minute_ms:1800000000000,mb:0}],hours,1800000000010);
    assert.equal(bars.length,hours*60);
    assert.equal(bars.at(-1).mb,0);
    assert.equal(bars[0].mb,null);
  }
});
test('network bytes do not become invented earnings', () => {
  const model=unified.normalize('rp',{generated_ms:1000,desired:10,workers:[],minutes:[],total_network_mb:500},1000);
  assert.equal(model.total,500);
  assert.equal(model.earned,'Not reported');
});
test('ProxyRack parser failure makes working clients unverified', () => {
  const model=unified.normalize('proxyrack',{generated_ms:1000,requested:10,cloud_error:'timestamp parse failed',workers:[{name:'one',provider_online:true,provider_status:'Online: 192.0.2.1',provider_age_ms:0,sample_age_ms:0,mb_per_minute:3}],minutes:[]},1000);
  assert.equal(model.working,null);
  assert.equal(model.nodes[0].status,'Unverified');
  assert.equal(model.nodes[0].rate,null);
});
test('TM provider credits remain separate from network totals', () => {
  const model=unified.normalize('tm',{generated_ms:1000,recorded:{rx:60000000,tx:40000000},deployment:{desired_replicas:10},workers:[],minutes:[],credited:{credited_bytes:25000000,credited_usd:0.0025,fresh:true},errors:{}},1000);
  assert.equal(model.total,100);
  assert.equal(model.credited,'25 MB');
  assert.equal(model.earned,'$0.0025');
});
test('new feeds retain unavailable values and current evidence expires',()=>{
  for(const service of ['pawns','earnapp','grass']){
    const missing=unified.normalize(service,{},100000);
    assert.equal(missing.working,null);assert.equal(missing.desired,null);assert.equal(missing.total,null);
    assert.match(missing.notice,/Waiting/);assert.equal(missing.earned,'Not reported');
    const data={generated_ms:100000,inventory_ms:100000,desired:1,running:1,working:null,total_mb:12,
      workers:[{id:'node',salad_state:'running',client_status:'unverified',working:null,sample_ms:100000,recorded_ms:100000,total_mb:12}],minutes:[]};
    assert.equal(unified.normalize(service,data,100000).working,null);
    data.working=1;Object.assign(data.workers[0],{client_status:'running',working:true,mb_per_minute:3});
    assert.equal(unified.normalize(service,data,100000).working,1);
    const stale=unified.normalize(service,data,200001);
    assert.equal(stale.working,null);assert.equal(stale.total,12);assert.equal(stale.nodes[0].rate,null);
    data.generated_ms=200001;data.inventory_ms=200001;
    assert.equal(unified.normalize(service,data,200001).nodes[0].working,false);
    data.workers[0].sample_ms=200001;data.workers[0].recorded_ms=200001;data.workers[0].salad_state='stopped';
    const stopped=unified.normalize(service,data,200001);
    assert.equal(stopped.working,0);assert.equal(stopped.nodes[0].rate,null);
  }
});
test('new minute feeds keep real zeroes, gaps and ranked contributor details',()=>{
  const model=unified.normalize('pawns',{generated_ms:1000,inventory_ms:1000,desired:1,running:0,working:0,
    minutes:[{minute_ms:0,mb:2,partial:true,estimated:true,count:2,nodes:[{instance:'a',ip:'192.0.2.1',country:'US',mb:0},{instance:'b',ip:'192.0.2.2',country:'US',mb:2}]},{minute_ms:60000,mb:0,count:1,nodes:[{instance:'a',ip:'192.0.2.1',country:'US',mb:0}]}]},1000);
  assert.equal(model.minutes[1].mb,0);assert.equal(model.minutes[0].nodes[0].instance,'b');
  assert.equal(unified.periodMinutes(model.minutes,1,120000)[59].mb,null);
});
