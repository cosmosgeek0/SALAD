"use strict";
(() => {
  const valid = value => typeof value === "number" && Number.isFinite(value);
  const num = (value, digits = 3) => valid(value) ? value.toLocaleString(undefined, {maximumFractionDigits: digits}) : "Unknown";
  const fresh = (age, limit) => valid(age) && age >= 0 && age <= limit;
  const CLIENTS = {running: "Accepted", error: "Client error", accepted: "Accepted", connected: "Connected", exited: "Client exited", device_limit: "Device limit", device_already_active: "Device already active", network_overused: "Network overused", network_unusable: "Network unusable", authorization_error: "Authorization failed", connected_last_observed_telemetry_stale: "Connection unverified", connected_last_observed_telemetry_unverified: "Connection unverified", starting: "Starting", waiting: "Waiting", rejected: "Rejected", unknown: "Unknown", unverified: "Unverified", disconnected: "Disconnected", reallocating: "Reallocating"};
  const ERRORS = {device_limit: "Provider device limit reached.", device_already_active: "Provider reports this device is already active.", network_overused: "Provider reports this network is overused.", network_unusable: "Provider cannot use this network.", authorization_error: "Provider authorization failed.", observer_error: "Observer could not verify this container.", disconnected: "Client disconnected; automatic reallocation after 2 minutes without recovery."};
  function workerState(service, worker, data) {
    const source = data.latest?.[service] || {};
    const native = service === "ps" && (worker.native_status_only === true || ["native_status_only", "native_sysfs_1s", "sysfs_via_salad_logs_1s"].includes(worker.sample_source));
    const observerFresh = !data.recorder_stale && (service !== "hg" || !source.status_stale) && (!native || fresh(source.status_age_ms, 90000));
    const clientFresh = observerFresh && fresh(service === "hg" ? worker.received_age_ms : worker.client_status_age_ms, native ? 240000 : 120000);
    const knownState = ["running", "stopped", "stopping", "pending", "starting", "allocating", "creating", "deploying", "failed", "succeeded"].includes(worker.state);
    const client = CLIENTS[worker.client_status] || "Unknown";
    const accepted = service === "hg" ? worker.client_status === "connected" : ["accepted", "running"].includes(worker.client_status);
    const bad = ["error", "exited", "device_limit", "device_already_active", "network_overused", "network_unusable", "authorization_error", "rejected"].includes(worker.client_status);
    const working = clientFresh && worker.state === "running" && accepted && !worker.error_code;
    const knownFailure = observerFresh && ((knownState && worker.state !== "running") || (clientFresh && (bad || Boolean(worker.error_code) && worker.error_code !== "observer_error")));
    const networkFresh = observerFresh && (service === "hg" ? fresh(worker.received_age_ms, 120000) : fresh(worker.received_age_ms, ["native_sysfs_1s", "sysfs_via_salad_logs_1s"].includes(worker.sample_source) ? 45000 : worker.sample_source === "salad_logs_10s" ? 25000 : 15000) && valid(worker.source_age_ms) && worker.source_age_ms >= -15000 && worker.source_age_ms <= 60000);
    return {working, unknown: !working && !knownFailure, client, networkFresh, observerFresh, clientFresh,
      label: working ? "Working" : knownFailure ? "Needs attention" : "Unknown",
      tone: working ? "ok" : knownFailure ? "bad" : "warn"};
  }
  function serviceModel(service, data) {
    const source = data.latest?.[service] || {};
    const desired = Math.min(50, data.experiment?.[service]?.desired || 10);
    const workers = [...(source.workers || [])];
    while (workers.length < desired) workers.push({state: "unknown", client_status: "unknown"});
    const states = workers.map(worker => workerState(service, worker, data));
    const providerFresh = !data.recorder_stale && fresh(source.provider_age_ms, service === "hg" ? 360000 : 180000);
    const earnings = data.summary?.[service === "hg" ? "hg_gathering_credits" : "ps_credited_mb"];
    const network = data.summary?.[`${service}_network_mb`];
    const networkKnown = !data.recorder_stale && (service !== "hg" || !source.status_stale) && source.network_complete === true && states.length >= desired && states.every(s => s.networkFresh) && valid(network);
    return {source, desired, workers, states, working: states.filter(s => s.working).length, unknown: states.filter(s => s.unknown).length,
      providerFresh, earnings, earningsKnown: providerFresh && valid(earnings), network, networkKnown};
  }
  function chartValue(metric) {
    if (!metric || !valid(metric.delta) || ["counter_reset", "gap"].includes(metric.status) || (metric.status === "incomplete" && metric.delta === 0)) return null;
    return metric.delta;
  }
  function windowStart(service, data) {
    const value = data.service_windows?.[service]?.start_ms;
    return valid(value) ? value : data.experiment?.started_ms;
  }
  function displayedIntervals(service, kind, data) {
    const start = windowStart(service, data);
    return (data.timeline?.[service]?.[kind] || []).filter(p => !valid(start) || p.start_ms >= start);
  }
  const SERVICES=[
    {id:'hg',hash:'#hg1',name:'Honeygain',url:'/api/fleet-test?service=hg'},
    {id:'ps',hash:'#ps1',name:'PacketStream',url:'/api/ps1/minutes'},
    {id:'proxyrack',hash:'#proxyrack',name:'Proxyrack',url:'/api/proxyrack'},
    {id:'rp',hash:'#rp',name:'Repocket',url:'/api/repocket?chart=1'},
    {id:'earnfm',hash:'#earnfm',name:'RFM',url:'/api/earnfm'},
    {id:'tm',hash:'#tm',name:'Traffic Monetizer',url:'/api/traffmonetizer?chart=1'}
  ];
  const shown=(value,digits=3)=>valid(value)?num(value,digits):'—';
  const mb=value=>valid(value)?shown(value)+' MB':'Not reported';
  const usd=value=>valid(value)?'$'+shown(value,6):'Not reported';
  const diff=(end,start)=>valid(end)&&valid(start)&&end>=start?end-start:null;
  const normalizeMinute=(time,amount,nodes=[],partial=false,estimated=false)=>({minute_ms:time,mb:valid(amount)?amount:null,partial,estimated,count:nodes.length,nodes:[...nodes].sort((a,b)=>b.mb-a.mb).slice(0,20)});
  function normalize(service,d,now=Date.now(),billing=null){
    const result={at:now,statusFresh:true,name:SERVICES.find(s=>s.id===service)?.name,desired:10,running:null,working:0,total:null,start:null,source:d.generated_ms,credited:'Not reported',earned:'Not reported',creditNote:'',notice:'',nodes:[],minutes:[],estimated:false};
    const delay=valid(d.generated_ms)?now-d.generated_ms:Infinity,recordingFresh=delay>=-10000&&delay<=90000;
    if(service==='hg'){
      const m=serviceModel('hg',d),s=m.source;
      result.desired=m.desired;result.running=s.running;result.working=m.working;result.total=valid(s.network_total_bytes)?s.network_total_bytes/1e6:m.network;result.start=windowStart('hg',d);result.source=s.status_observed_ms;result.minutes=d.hg_minutes||[];result.estimated=true;result.statusFresh=Boolean(d.latest?.hg)&&!d.recorder_stale&&!s.status_stale;
      const intervals=displayedIntervals('hg','provider',d).filter(p=>valid(p.per_second)&&chartValue(p)!==null),credits=intervals.length?intervals.reduce((sum,p)=>sum+p.delta,0):null;
      result.credited=valid(credits)?shown(credits)+' credits':'Not reported';result.earned=valid(credits)?shown(credits)+' credits':'Not reported';
      result.creditNote='Honeygain gathering credits from recorded intervals'+(m.providerFresh?'':'; provider reading is stale');
      if(d.recorder_stale||s.status_stale)result.notice='Honeygain recorder or client status is stale.';
      result.nodes=m.workers.map((w,i)=>({id:w.machine||w.group||String(i),ip:w.ip,status:m.states[i].clientFresh?m.states[i].client:'Unverified',salad:w.state,working:m.states[i].working,
        rate:m.states[i].networkFresh&&valid(w.network_interval?.per_second)?w.network_interval.per_second*60/1e6:null,total:valid(w.network_bytes)?w.network_bytes/1e6:null,
        duration:diff(w.network_last_ms,w.network_first_ms),age:w.received_age_ms,error:ERRORS[w.error_code]||''}));
    }else if(service==='ps'){
      result.desired=d.desired||10;result.running=(d.nodes||[]).filter(n=>n.salad_state==='running').length;result.working=d.running;result.total=d.total_mb;result.start=d.started_ms;result.source=valid(d.inventory_age_ms)?d.time_ms-d.inventory_age_ms:null;result.minutes=d.candles||[];result.estimated=result.minutes.some(m=>m.estimated);result.statusFresh=d.inventory_fresh;
      result.notice=d.collector?.error||(!d.inventory_fresh?'PacketStream inventory is stale.':'');
      result.nodes=(d.nodes||[]).map(n=>({id:n.instance,ip:n.ip,status:n.status,salad:n.salad_state,working:n.status==='Running',rate:n.metrics_fresh?n.latest_mb_per_minute:null,total:n.total_mb,duration:valid(n.elapsed_seconds)?n.elapsed_seconds*1000:null,age:n.sample_age_ms,error:n.error||''}));
      const readings=(billing?.billing?.readings||[]).filter(r=>valid(r.time_ms)&&valid(d.started_ms)&&r.time_ms>=d.started_ms&&valid(r.gb));
      if(readings.length>=2&&readings.every((r,i)=>!i||r.gb>=readings[i-1].gb))result.credited=mb((readings.at(-1).gb-readings[0].gb)*1000);
      result.creditNote=readings.length<2?'PacketStream has no provider baseline and follow-up for this recording. Earnings are not reported.':'Provider credited traffic comes from account readings; earnings are not reported.';
      if(!valid(billing?.feed_age_ms)||billing.feed_age_ms>180000)result.creditNote+=' Provider feed is stale.';
    }else if(service==='proxyrack'){
      result.desired=d.requested||10;result.running=recordingFresh&&!d.cloud_error?(d.workers||[]).filter(w=>w.salad_state?.toLowerCase()==='running').length:null;result.total=valid(d.total_recorded_mb)?d.total_recorded_mb:d.network_mb;result.start=Date.parse(d.started_at);result.minutes=(d.minutes||[]).map(m=>({...m,partial:m.partial||m.count<(d.requested||10)}));result.estimated=result.minutes.some(m=>m.estimated);result.statusFresh=recordingFresh&&!d.cloud_error;
      result.credited=mb(d.credited_mb);result.creditNote='Cached PR credited bandwidth includes replaced replicas. Readings available for '+(d.credited_devices||0)+'/'+result.desired+' current devices. Network RX + TX counts both sides of relayed traffic and includes overhead.'+(d.balance?' Account balance '+d.balance+' covers the whole account.':'')+' Earnings for this group are not reported. Connection status comes from registered client logs; provider API checks are paced below its five requests/minute limit.';
      result.notice=d.cloud_error||(!recordingFresh?'Proxyrack recorder is stale.':'');
      result.nodes=(d.workers||[]).map(w=>{
        const networkFresh=recordingFresh&&!d.cloud_error&&valid(w.sample_age_ms)&&fresh(w.sample_age_ms+delay,150000),ip=w.provider_status?.match(/(?:Online|Offline):\s*(\S+)/i)?.[1];
        const connected=networkFresh&&w.fresh&&!w.client_error&&w.client_state==='running'&&w.salad_state?.toLowerCase()==='running';
        return {id:w.name,ip,status:connected?'Connected':w.client_error==='registration_pending'?'Registration pending':w.status||'Unverified',salad:w.salad_state,working:connected,rate:networkFresh&&w.fresh?w.mb_per_minute:null,total:w.network_mb,duration:null,age:valid(w.sample_age_ms)?w.sample_age_ms+delay:null,error:w.client_error||w.provider_error||''};
      });result.working=result.nodes.filter(n=>n.working).length;
    }else if(service==='rp'){
      const inventoryFresh=recordingFresh&&valid(d.inventory_ms)&&fresh(now-d.inventory_ms,90000)&&!d.error;
      result.desired=d.desired||10;result.running=inventoryFresh?d.running:null;result.total=d.total_network_mb;result.start=d.test_started_ms;result.source=d.inventory_ms||d.generated_ms;result.statusFresh=inventoryFresh;
      result.notice=d.error||(!recordingFresh?'Repocket recorder is stale.':!inventoryFresh?'Repocket inventory is stale.':'');
      result.nodes=(d.workers||[]).filter(w=>w.current!==false).map((w,i)=>{
        const native=inventoryFresh&&w.native_fresh===true&&fresh(now-w.source_ms,90000),network=native&&w.network_fresh===true&&fresh(now-w.last_end_ms,150000),policy=w.policy;
        const policyFresh=native&&w.diagnostics_fresh===true&&fresh(now-policy?.checked_ms,90000),notes=[];
        let status=inventoryFresh&&w.salad_state&&w.salad_state!=='running'?w.salad_state:native?w.status:'Unverified';
        if(status==='connected')status='Connected (control)';
        if(w.reason&&w.reason!=='Waiting for fresh native evidence')notes.push(w.reason);
        if(policyFresh&&policy.state==='observing')notes.push('Observing '+shown(policy.observed_ms/60000,1)+'/10 min');
        else if(policyFresh&&policy.state==='keeping')notes.push('Keeping: '+shown(policy.target_bytes/1e6)+' MB target traffic / 10 min');
        else if(status==='reallocating')notes.push('Replacement requested');
        else if(w.salad_state==='running')notes.push('Recovery decision unverified');
        if(policyFresh){const errors=Object.entries(policy.errors||{}).filter(([,n])=>n>0).sort((a,b)=>b[1]-a[1]).slice(0,2);if(errors.length)notes.push(errors.map(([name,n])=>name+': '+n).join('; '));}
        return {id:w.salad_instance||w.instance||'awaiting-'+i,ip:w.ip,status,salad:w.salad_state,working:native&&w.phase==='connected'&&w.salad_state==='running',rate:network?w.last_mb_per_minute:null,total:w.total_mb,duration:w.recorded_ms,age:diff(now,w.source_ms),error:notes.join(' · ')};
      });
      result.working=inventoryFresh&&valid(d.connected)?result.nodes.filter(n=>n.working).length:null;
      result.minutes=d.chart_minutes||[];
      const provider=d.provider,providerFresh=provider&&!provider.error&&fresh(now-provider.observed_ms,180000);
      if(providerFresh){result.earned=provider.today_earned_text||provider.earned_text||'Not reported';result.credited=provider.today_traffic_text||provider.traffic_text||'Not reported';}
      result.creditNote='RP records original source, Salad receipt and recorder receipt times. Network totals include both directions and overhead; provider credits are separate account readings. '+(providerFresh?'Provider observed '+new Date(provider.observed_ms).toLocaleString():provider?.observed_ms?'Provider reading unavailable now; last observed '+new Date(provider.observed_ms).toLocaleString()+' ('+(provider.today_traffic_text||provider.traffic_text||'traffic unavailable')+' / '+(provider.today_earned_text||provider.earned_text||'earnings unavailable')+').':'Provider credit feed has not supplied a reading.');
      result.creditNote+=' '+shown(d.record_count,0)+' records · '+mb(d.database_bytes/1e6)+' on disk · '+shown(d.saved_bytes_last_minute/1000)+' KB saved in the last minute.';
      if(d.legacy_receipt_unknown)result.creditNote+=' '+shown(d.legacy_receipt_unknown,0)+' historical records have unknown receipt times.';
      if(d.invalid_records)result.creditNote+=' '+shown(d.invalid_records,0)+' invalid/conflicting records are excluded from measured totals.';
      const action=d.recent_recovery?.[0];if(action)result.creditNote+=' Recovery '+(action.ip||'worker')+': '+({old_instance_removed:'old machine left inventory',accepted:'Salad accepted request; removal not yet verified',request_failed:'request failed',requested:'request sent'}[action.result]||'unverified')+' · '+action.reason+'. Fleet now '+shown(result.working,0)+'/'+result.desired+' confirmed. New instances are confirmed from fresh native records.';
    }else if(service==='tm'){
      result.desired=d.deployment?.desired_replicas||10;result.running=recordingFresh&&!d.stale?d.running:null;result.working=recordingFresh&&!d.stale?d.working||0:0;result.total=valid(d.recorded?.rx)&&valid(d.recorded?.tx)?(d.recorded.rx+d.recorded.tx)/1e6:null;result.start=d.deployment?.measurement_started_ms||Date.parse(d.deployment?.started_at);result.source=d.generated_ms;result.statusFresh=recordingFresh&&!d.stale&&!d.errors?.recorder;
      result.credited=mb(d.credited?.credited_bytes/1e6);result.earned=usd(d.credited?.credited_usd);result.creditNote=(d.credited?.scope||'TM provider account figures')+(d.credited?.fresh?'':'; provider reading is stale');
      result.notice=Object.values(d.errors||{}).join(' · ')||(!recordingFresh||d.stale?'Traffic Monetizer recorder is stale.':'');
      result.nodes=(d.workers||[]).map(w=>{const recent=recordingFresh&&!d.stale&&fresh(now-w.time_ms,45000);return {id:w.instance,ip:w.ip,status:recent?w.state:'Unverified',salad:w.salad_state,working:recent&&w.working,rate:recent?w.raw_mb_per_minute:null,total:valid(w.test_rx)&&valid(w.test_tx)?(w.test_rx+w.test_tx)/1e6:null,duration:w.test_duration_ms,age:diff(now,w.time_ms),error:[w.error,valid(w.native_recent_bytes)?'Relay observed: '+mb(w.native_recent_bytes/1e6)+' / '+shown(w.native_recent_requests,0)+' requests over '+shown(w.native_recent_ms/60000,1)+' min':'Relay window not yet measured'].filter(Boolean).join('; ')};});
      result.working=result.nodes.filter(n=>n.working).length;
      result.minutes=d.chart_minutes||(d.minutes||[]).map(m=>normalizeMinute(m.time_ms,(m.rx_bytes+m.tx_bytes)/1e6,(m.workers||[]).map(w=>({instance:w.instance,ip:w.ip||(d.workers||[]).find(n=>n.run===w.run)?.ip,mb:(w.rx+w.tx)/1e6})),m.samples<result.desired*60));
    }else if(service==='earnfm'){
      result.desired=d.desired||10;result.running=recordingFresh?(d.workers||[]).filter(w=>w.salad_state==='running').length:null;result.total=d.total_mb;result.start=d.test_started_ms;result.source=d.inventory_ms||d.generated_ms;result.statusFresh=recordingFresh&&!d.error;result.notice=d.error||(!recordingFresh?'RFM recorder is stale.':'');
      result.nodes=(d.workers||[]).map(w=>{
        const recent=recordingFresh&&!d.error&&fresh(now-w.sample_ms,90000),providerFresh=fresh(now-d.provider?.observed_ms,180000)&&!d.provider?.error;
        const runtime=w.runtime_instance||w.instance,present=Array.isArray(d.provider?.devices)?d.provider.devices.some(device=>device.instance===runtime):w.provider_online===true?true:null;
        const working=recent&&!w.final&&w.client_state==='running'&&w.salad_state==='running'&&providerFresh&&present===true;
        let status=w.client_state;
        if(w.salad_state&&w.salad_state!=='running')status=w.salad_state;
        else if(!recent)status='Unverified';
        else if(w.client_state==='reallocating')status='Reallocating';
        else if(w.final)status='Stopped';
        else if(w.client_state==='running')status=!providerFresh?'Provider status unavailable':present===false?'Provider offline':working?'Connected':'Awaiting provider confirmation';
        return {id:runtime,ip:w.ip,status,salad:w.salad_state,working,rate:recent&&!w.final&&valid(w.kb_per_second)?w.kb_per_second*.06:null,total:w.total_mb,duration:null,age:diff(now,w.sample_ms),error:w.error||(w.client_state==='rate_limited'?'Provider cooldown':!providerFresh&&d.provider?.error?d.provider.error:'')};
      });result.working=result.nodes.filter(n=>n.working).length;
      result.minutes=(d.points||[]).map(m=>normalizeMinute(m.time_ms,m.mb,Object.entries(m.by_instance||{}).map(([id,amount])=>({instance:id,ip:(d.workers||[]).find(w=>(w.runtime_instance||w.instance)===id)?.ip,country:(d.workers||[]).find(w=>(w.runtime_instance||w.instance)===id)?.country,mb:amount})),m.partial));
      result.earned=usd(d.provider?.earned);result.credited=mb(d.provider?.credited_mb);result.creditNote='EarnFM gross account balance change and credited traffic since its recorded baseline'+(valid(d.provider?.baseline_ms)?' · '+new Date(d.provider.baseline_ms).toLocaleString():'')+(!fresh(now-d.provider?.observed_ms,180000)||d.provider?.error?' · provider reading is stale':'')+'.';
    }
    result.estimated=result.estimated||result.minutes.some(m=>m.estimated);
    if(result.statusFresh){
      for(const node of result.nodes){
        const state=node.salad?.toLowerCase();
        if(['allocating','downloading','creating','stopping','stopped'].includes(state)){
          node.status=state[0].toUpperCase()+state.slice(1);node.working=false;node.rate=null;
          if(['allocating','downloading','creating'].includes(state))node.error='Waiting for the client to start on this machine.';
        }
      }
      result.working=result.nodes.filter(node=>node.working).length;
      while(result.nodes.length<result.desired)result.nodes.push({id:service+'-pending-'+result.nodes.length,pending:true,status:'Awaiting inventory',working:false,error:'No machine listed in the latest inventory.'});
    }
    if(!result.statusFresh){result.working=null;result.running=null;result.nodes=result.nodes.map(n=>({...n,working:false,status:"Unverified",stale:true,rate:null}));}
    return result;
  }
  function periodMinutes(minutes,hours,now=Date.now()){
    const end=Math.floor(now/60000)*60000,start=end-(hours*60-1)*60000,byTime=new Map(minutes.map(m=>[m.minute_ms,m]));
    return Array.from({length:hours*60},(_,i)=>byTime.get(start+i*60000)||{minute_ms:start+i*60000,mb:null,partial:true,count:0,nodes:[]});
  }
  if(typeof module!=='undefined'&&module.exports){module.exports={workerState,serviceModel,chartValue,windowStart,displayedIntervals,normalize,periodMinutes,SERVICES};return;}
  const el=id=>document.getElementById(id),make=(tag,text,cls)=>{const n=document.createElement(tag);if(text!=null)n.textContent=text;if(cls)n.className=cls;return n;};
  const duration=ms=>!valid(ms)?'—':Math.floor(ms/3600000)+'h '+Math.floor(ms%3600000/60000)+'m';
  const age=ms=>!valid(ms)?'—':ms<60000?shown(ms/1000,0)+'s':shown(ms/60000,1)+'m';
  const nodeLabel=n=>n.pending?'Unassigned':n.ip?window.bandwidthCountries.name(n)+' · '+n.ip:n.id?.slice(0,12)||'IP unavailable';
  const statusNames={unverified:'Status not received',unknown:'Awaiting client status','checking client':'Awaiting client status',stale:'Monitor delayed','status feed stale':'Monitor delayed',rate_limited:'Provider cooldown',connection_error:'Connection failed',reallocating:'Reallocating',awaiting_sample:'Awaiting first sample','online / running':'Connected'};
  const aliases={'/proxyrack':'proxyrack','/rp':'rp','/repocket':'rp','/earnfm':'earnfm','/traffmonetizer':'tm','/tm':'tm'};
  let active=SERVICES.find(s=>s.hash===location.hash)||SERVICES.find(s=>s.id===aliases[location.pathname.replace(/\.html$/,'')])||SERVICES[1],hours=24,data=null,model=null,busy=false,generation=0,billing=null,billingPending=false,billingChecked=0;
  const buttons=new Map();el('services').replaceChildren();
  for(const service of SERVICES){const button=make('button',service.name);button.id='tab-'+service.id;button.setAttribute('role','tab');button.setAttribute('aria-controls','bandwidthPanel');button.onclick=()=>select(service);buttons.set(service.id,button);el('services').append(button);}
  const panel=el('bandwidthPanel');
  panel.innerHTML='<div id="totals" class="summary-line"></div><p id="notice" class="notice hidden" role="status"></p>'+
    '<div class="chart-controls"><h2 id="chartTitle">Network traffic</h2><label>Show <select id="hours" aria-label="Time range"><option value="1">1 hour</option><option value="6">6 hours</option><option value="12">12 hours</option><option value="24" selected>24 hours</option></select></label></div>'+
    '<div class="ps-chart"><div id="chartScroll" class="ps-chart-scroll"><canvas id="trafficChart" tabindex="0" role="img"></canvas></div><div id="minutePopup" class="ps-popup hidden" role="tooltip"></div></div>'+
    '<p id="chartNote" class="source-note"></p><div class="table-scroll"><table class="container-table"><thead><tr><th>Country / IP</th><th>Client</th><th>Salad</th><th>MB/min</th><th>Recorded MB</th><th>Recorded time</th><th>Last sample</th><th>Error / note</th></tr></thead><tbody id="workerRows"></tbody></table></div><p id="creditNote" class="source-note"></p>';
  const chart=window.createMinuteChart({canvas:el('trafficChart'),scroll:el('chartScroll'),popup:el('minutePopup'),active:()=>true,readMinute:async minute=>{
    if(active.id==='ps')return read('/api/ps1/minutes?minute='+minute);
    return model?.minutes.find(m=>m.minute_ms===minute)||{minute_ms:minute,mb:null,count:0,nodes:[]};
  }});
  async function read(url){const response=await fetch(url,{cache:'no-store',signal:AbortSignal.timeout(10000)});if(!response.ok){const error=await response.json().catch(()=>({}));throw new Error(typeof error.error==='string'?error.error:'HTTP '+response.status);}return response.json();}
  function render(){
    if(!model)return;
    const bars=periodMinutes(model.minutes,hours),measured=bars.filter(b=>valid(b.mb)),estimated=measured.some(b=>b.estimated);
    let amount=measured.length?measured.reduce((sum,b)=>sum+b.mb,0):null;
    const totals=el('totals');totals.replaceChildren();
    for(const [label,value] of [['Clients confirmed',shown(model.working,0)+'/'+model.desired+' · '+shown(model.running,0)+' containers running'],[active.id==='tm'?'Network RX + TX':'Total recorded',mb(model.total)],['Last '+hours+(hours===1?' hour':' hours'),(estimated?'≈ ':'')+mb(amount)],['Provider credited / earned',model.credited===model.earned?model.earned:model.credited+' · '+(model.earned==='Not reported'?'earnings not reported':model.earned)],['Elapsed',duration(diff(Date.now(),model.start))]]){const item=make('span',label+': ');item.append(make('strong',value));totals.append(item);}
    el('notice').textContent=model.notice;el('notice').classList.toggle('hidden',!model.notice);
    el('chartTitle').textContent=active.name+' · MB per minute';
    el('chartNote').textContent='Hover or click a bar for the top 20 IPs, countries and MB. '+(model.estimated?'≈ Minute estimates from saved counter intervals. ':'')+'Blank = no measurement; amber = partial coverage. Network traffic includes overhead.'+(active.id==='tm'?' TM row rates average the latest observed minute. Relay notes show client counter increases, not per-worker paid earnings.':'');
    const body=el('workerRows');body.replaceChildren();
    for(const n of model.nodes){const row=make('tr'),id=make('td',nodeLabel(n));id.title=n.pending?'':n.id||'';row.dataset.instance=n.id;row.append(id,make('td',statusNames[n.status?.toLowerCase()]||n.status||'Awaiting client status',n.working?'ok':n.error?'bad':'stale'),make('td',(n.salad||'—')+(n.stale?' (last seen)':'')),make('td',shown(n.rate)),make('td',shown(n.total)),make('td',duration(n.duration)),make('td',age(valid(n.age)?n.age+Math.max(0,Date.now()-model.at):null)),make('td',n.error||''));body.append(row);}
    const countryModel=model;
    window.bandwidthCountries.lookup(model.nodes.filter(n=>!n.pending)).then(()=>{
      if(model!==countryModel)return;
      for(let i=0;i<countryModel.nodes.length;i++)if(body.rows[i])body.rows[i].cells[0].textContent=nodeLabel(countryModel.nodes[i]);
    });
    if(!model.nodes.length){const row=make('tr'),cell=make('td','Waiting for the recorder to publish its container inventory.');cell.colSpan=8;row.append(cell);body.append(row);}
    el('creditNote').textContent=model.creditNote;
    el('connection').textContent=active.name+' · status '+age(diff(Date.now(),model.source))+' old';
    el('connection').classList.toggle('bad',Boolean(model.notice));
    chart.update({time_ms:Date.now(),candles:bars});
  }
  async function refresh(){
    if(busy)return;busy=true;const ticket=generation,service=active;
    try{const result=await read(service.url);if(ticket!==generation)return;data=result;model=normalize(service.id,data,Date.now(),billing);render();}
    catch(e){if(ticket===generation){if(model){if(service.id==='rp'&&data)model=normalize('rp',data,Date.now(),billing);model.notice='Cannot refresh '+service.name+'. Last saved values are shown.';model.working=null;model.running=null;model.nodes=model.nodes.map(n=>({...n,working:false,status:'Unverified',stale:true,rate:null}));render();}else{model=normalize(service.id,{});model.nodes=[];model.working=null;model.running=null;model.notice='Waiting for '+service.name+' recorder: '+e.message;render();}}}
    finally{if(ticket===generation)busy=false;}
    if(service.id==='ps'&&!billingPending&&Date.now()-billingChecked>60000){billingPending=true;billingChecked=Date.now();read('/api/ps1/view').then(value=>{billing=value;if(active.id==='ps'&&data){const credit=normalize('ps',data,Date.now(),billing);if(model){model.credited=credit.credited;model.earned=credit.earned;model.creditNote=credit.creditNote;render();}}}).catch(()=>{}).finally(()=>{billingPending=false;});}
  }
  function select(service,changeHash=true){
    active=service;generation++;busy=false;data=null;model=null;chart.hide();chart.update({time_ms:Date.now(),candles:periodMinutes([],hours)});
    for(const item of SERVICES){const yes=item.id===service.id;buttons.get(item.id).setAttribute('aria-selected',String(yes));buttons.get(item.id).tabIndex=yes?0:-1;}
    panel.setAttribute('aria-labelledby','tab-'+service.id);if(changeHash)history.replaceState(null,'','/'+service.hash);document.title=service.name+' · Bandwidth test';
    el('connection').textContent=service.name+' · loading';el('totals').textContent='Loading '+service.name+' readings…';el('workerRows').replaceChildren();el('creditNote').textContent='';el('notice').classList.add('hidden');el('chartTitle').textContent=service.name+' · MB per minute';el('chartNote').textContent='Hover or click a minute for its contributors.';refresh();
  }
  el('hours').onchange=()=>{hours=Number(el('hours').value);chart.hide();if(model)render();else chart.update({time_ms:Date.now(),candles:periodMinutes([],hours)});};
  el('services').addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();const index=SERVICES.indexOf(active),next=event.key==='Home'?0:event.key==='End'?SERVICES.length-1:(index+(event.key==='ArrowLeft'?-1:1)+SERVICES.length)%SERVICES.length;select(SERVICES[next]);buttons.get(active.id).focus();});
  window.addEventListener('hashchange',()=>select(SERVICES.find(s=>s.hash===location.hash)||SERVICES[1],false));
  select(active);setInterval(refresh,5000);
})();
