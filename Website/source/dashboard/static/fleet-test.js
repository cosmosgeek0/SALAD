"use strict";
(() => {
  const valid = value => typeof value === "number" && Number.isFinite(value);
  const formats = new Map();
  const num = (value, digits = 3) => {
    if (!valid(value)) return "Unknown";
    if (!formats.has(digits)) formats.set(digits, new Intl.NumberFormat(undefined, {maximumFractionDigits: digits}));
    return formats.get(digits).format(value);
  };
  const responseAge = (data, now) => {
    const source=data.latest?.hg;
    const at=valid(source?.status_observed_ms)&&valid(source?.status_age_ms)?source.status_observed_ms+source.status_age_ms:data.generated_ms;
    return valid(at)?Math.max(0,now-at):0;
  };
  const fresh = (age, limit) => valid(age) && age >= 0 && age <= limit;
  const CLIENTS = {running: "Accepted", error: "Client error", accepted: "Accepted", connected: "Connected", exited: "Client exited", device_limit: "Device limit", device_already_active: "Device already active", network_overused: "Network overused", network_unusable: "Network unusable", authorization_error: "Authorization failed", connected_last_observed_telemetry_stale: "Connection unverified", connected_last_observed_telemetry_unverified: "Connection unverified", starting: "Starting", waiting: "Waiting", rejected: "Rejected", unknown: "Unknown", unverified: "Unverified", disconnected: "Disconnected", reallocating: "Reallocating"};
  const ERRORS = {device_limit: "Provider device limit reached.", device_already_active: "Provider reports this device is already active.", network_overused: "Provider reports this network is overused.", network_unusable: "Provider cannot use this network.", authorization_error: "Provider authorization failed.", observer_error: "Observer could not verify this container.", disconnected: "Client disconnected; automatic reallocation after 2 minutes without recovery."};
  function workerState(service, worker, data, now=Date.now()) {
    const elapsed=responseAge(data,now);
    const source = data.latest?.[service] || {};
    const native = service === "ps" && (worker.native_status_only === true || ["native_status_only", "native_sysfs_1s", "sysfs_via_salad_logs_1s"].includes(worker.sample_source));
    const observerFresh = !data.recorder_stale && (service !== "hg" || !source.status_stale && fresh(now-source.status_observed_ms,120000)) && (!native || fresh(source.status_age_ms, 90000));
    const clientFresh = observerFresh && fresh(service === "hg" ? (valid(worker.received_age_ms)?worker.received_age_ms+elapsed:null) : worker.client_status_age_ms, native ? 240000 : 120000);
    const knownState = ["running", "stopped", "stopping", "pending", "starting", "allocating", "creating", "deploying", "failed", "succeeded"].includes(worker.state);
    const client = CLIENTS[worker.client_status] || "Unknown";
    const accepted = service === "hg" ? worker.client_status === "connected" : ["accepted", "running"].includes(worker.client_status);
    const bad = ["error", "exited", "device_limit", "device_already_active", "network_overused", "network_unusable", "authorization_error", "rejected"].includes(worker.client_status);
    const working = clientFresh && worker.state === "running" && accepted && !worker.error_code;
    const knownFailure = observerFresh && ((knownState && worker.state !== "running") || (clientFresh && (bad || Boolean(worker.error_code) && worker.error_code !== "observer_error")));
    const networkFresh = observerFresh && (service === "hg" ? fresh(valid(worker.received_age_ms)?worker.received_age_ms+elapsed:null, 120000) : fresh(worker.received_age_ms, ["native_sysfs_1s", "sysfs_via_salad_logs_1s"].includes(worker.sample_source) ? 45000 : worker.sample_source === "salad_logs_10s" ? 25000 : 15000) && valid(worker.source_age_ms) && worker.source_age_ms >= -15000 && worker.source_age_ms <= 60000);
    return {working, unknown: !working && !knownFailure, client, networkFresh, observerFresh, clientFresh,
      label: working ? "Working" : knownFailure ? "Needs attention" : "Unknown",
      tone: working ? "ok" : knownFailure ? "bad" : "warn"};
  }
  function serviceModel(service, data, now=Date.now()) {
    const source = data.latest?.[service] || {};
    const desired = valid(data.experiment?.[service]?.desired) ? data.experiment[service].desired : null;
    const workers = [...(source.workers || [])];
    while (workers.length < desired) workers.push({state: "unknown", client_status: "unknown"});
    const states = workers.map(worker => workerState(service, worker, data, now));
    const providerFresh = !data.recorder_stale && fresh(valid(source.provider_age_ms)?source.provider_age_ms+responseAge(data,now):null, service === "hg" ? 360000 : 180000);
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
    {id:'hg',path:'/honeygain',hash:'#hg1',name:'Honeygain',url:'/api/fleet-test?service=hg'},
    {id:'ps',path:'/packetstream',hash:'#ps1',name:'PacketStream',url:'/api/ps1/minutes'},
    {id:'proxyrack',path:'/proxyrack',hash:'#proxyrack',name:'Proxyrack',url:'/api/proxyrack'},
    {id:'rp',path:'/repocket',hash:'#rp',name:'Repocket',url:'/api/repocket?chart=1'},
    {id:'earnfm',path:'/earnfm',hash:'#earnfm',name:'EarnFM',url:'/api/earnfm'},
    {id:'tm',path:'/traffmonetizer',hash:'#tm',name:'TraffMonetizer',url:'/api/traffmonetizer?chart=1'},
    {id:'pawns',path:'/pawns-app',hash:'#pawns',name:'Pawns.app',url:'/api/pawns'},
    {id:'grass',path:'/grass',hash:'#grass',name:'Grass',url:'/api/grass'}
  ];
  const aliases={'/rp':'rp','/tm':'tm','/pawns':'pawns'};
  function pageService(path,hash){const clean=path.replace(/\/$/,'').replace(/\.html$/,'');return SERVICES.find(s=>s.hash===hash)||SERVICES.find(s=>s.path===clean||s.id===aliases[clean]);}
  const shown=(value,digits=3)=>valid(value)?num(value,digits):'—';
  const mb=(value,digits=3)=>valid(value)?shown(value,digits)+' MB':'Not reported';
  const usd=value=>valid(value)?'$'+shown(value,6):'Not reported';
  const prNumber=value=>!valid(value)?'—':value>0&&value<0.000001?value.toExponential(2):shown(value,value>0&&value<0.01?6:3);
  const prMB=value=>valid(value)?prNumber(value)+' MB':'Not reported';
  const diff=(end,start)=>valid(end)&&valid(start)&&end>=start?end-start:null;
  const normalizeMinute=(time,amount,nodes=[],partial=false,estimated=false)=>({minute_ms:time,mb:valid(amount)?amount:null,partial,estimated,count:nodes.length,nodes:[...nodes].sort((a,b)=>b.mb-a.mb).slice(0,20)});
  function normalize(service,d,now=Date.now(),billing=null){
    if(Array.isArray(d.chart_nodes))for(const key of ['hg_minutes','candles','minutes','chart_minutes'])for(const minute of d[key]||[])if(Array.isArray(minute.contributions)&&!minute.nodes)minute.nodes=minute.contributions.map(([index,amount])=>({...d.chart_nodes[index],mb:amount}));
    const result={at:now,statusFresh:true,name:SERVICES.find(s=>s.id===service)?.name,desired:null,running:null,working:0,total:null,start:null,source:d.generated_ms,credited:'Not reported',earned:'Not reported',creditNote:'',notice:'',nodes:[],minutes:[],estimated:false};
    const delay=valid(d.generated_ms)?now-d.generated_ms:Infinity,recordingFresh=delay>=-10000&&delay<=90000;
    if(service==='hg'){
      const m=serviceModel('hg',d,now),s=m.source;
      result.desired=m.desired;result.running=s.running;result.working=m.working;result.total=valid(s.network_total_bytes)?s.network_total_bytes/1e6:m.network;result.start=windowStart('hg',d);result.source=s.status_observed_ms;result.minutes=d.hg_minutes||[];result.estimated=true;result.statusFresh=Boolean(d.latest?.hg)&&!d.recorder_stale&&!s.status_stale&&fresh(now-s.status_observed_ms,120000)&&fresh(valid(d.recorder_age_ms)?d.recorder_age_ms+responseAge(d,now):null,180000);
      const intervals=displayedIntervals('hg','provider',d).filter(p=>valid(p.per_second)&&chartValue(p)!==null),credits=intervals.length?intervals.reduce((sum,p)=>sum+p.delta,0):null;
      result.credited=valid(credits)?shown(credits)+' credits':'Not reported';result.earned=valid(credits)?shown(credits)+' credits':'Not reported';
      result.creditNote='Honeygain gathering credits from recorded intervals'+(m.providerFresh?'':'; provider reading is stale');
      if(!result.statusFresh)result.notice='Honeygain recorder or client status is stale.';
      result.nodes=m.workers.map((w,i)=>({id:w.run||w.machine||w.group||String(i),ip:w.ip,country:w.country,status:m.states[i].clientFresh?m.states[i].client:'Unverified',salad:w.state,working:m.states[i].working,
        rate:m.states[i].networkFresh&&valid(w.network_interval?.per_second)?w.network_interval.per_second*60/1e6:null,total:valid(w.network_bytes)?w.network_bytes/1e6:null,
        duration:diff(w.network_last_ms,w.network_first_ms),age:valid(w.received_age_ms)?w.received_age_ms+responseAge(d,now):null,error:[ERRORS[w.error_code],w.recovery_note].filter(Boolean).join(' · ')}));
    }else if(service==='ps'){
      result.desired=valid(d.desired)?d.desired:null;result.running=(d.nodes||[]).filter(n=>n.salad_state==='running').length;result.working=d.running;result.total=d.total_mb;result.start=d.started_ms;result.source=valid(d.inventory_age_ms)?d.time_ms-d.inventory_age_ms:null;result.minutes=d.candles||[];result.estimated=result.minutes.some(m=>m.estimated);result.statusFresh=d.inventory_fresh&&fresh(now-result.source,120000);
      result.notice=d.collector?.error||(!result.statusFresh?'PacketStream inventory is stale.':'');
      result.nodes=(d.nodes||[]).map(n=>({id:n.instance,ip:n.ip,country:n.country,status:n.status,salad:n.salad_state,working:n.status==='Running',rate:n.metrics_fresh&&valid(n.sample_age_ms)&&fresh(n.sample_age_ms+Math.max(0,now-d.time_ms),150000)?n.latest_mb_per_minute:null,total:n.total_mb,duration:valid(n.elapsed_seconds)?n.elapsed_seconds*1000:null,age:valid(n.sample_age_ms)?n.sample_age_ms+Math.max(0,now-d.time_ms):null,error:n.error||''}));
      const provider=billing?.provider,providerFresh=provider&&!provider.error&&fresh(now-provider.observed_ms,180000);
      result.credited=valid(provider?.rolling_bytes)?mb(provider.rolling_bytes/1e6):'Not reported';
      result.balance=valid(provider?.balance_usd)?usd(provider.balance_usd):'Not reported';
      if(!providerFresh){if(result.credited!=='Not reported')result.credited+=' (stale)';if(result.balance!=='Not reported')result.balance+=' (stale)';}
      result.creditNote='PacketStream account balance and rolling 14-day traffic. Neither is an interval earning.'+(provider?.observed_ms?' Observed '+new Date(provider.observed_ms).toLocaleString()+'.':'')+(!providerFresh?' Provider reading is stale or unavailable.':'');
    }else if(service==='proxyrack'){
      const inventoryFresh=recordingFresh&&valid(d.inventory_ms)&&now-d.inventory_ms>=-10000&&now-d.inventory_ms<=90000&&!d.cloud_error;
      result.desired=valid(d.requested)?d.requested:null;result.running=inventoryFresh?(d.workers||[]).filter(w=>w.salad_state==='running').length:null;
      result.total=valid(d.total_recorded_mb)?d.total_recorded_mb:d.network_mb;result.start=Date.parse(d.started_at);result.source=valid(d.inventory_ms)?d.inventory_ms:null;result.recorder=d.generated_ms;
      result.minutes=(d.minutes||[]).map(m=>({...m,partial:m.partial||m.count<result.desired}));result.statusFresh=inventoryFresh;
      result.credited=valid(d.provider_bandwidth_value)?String(d.provider_bandwidth_value):'Not reported';result.earned=d.balance!=null&&d.balance!==''?String(d.balance)+(valid(d.balance_checked_ms)&&now-d.balance_checked_ms>=-10000&&now-d.balance_checked_ms<=900000&&!d.balance_error?'':' (stale)'):'Not reported';result.creditNote=(recordingFresh?'':'Last saved: ')+(d.credit_note||'Waiting for PR provider and recovery observations.');
      result.notice=d.cloud_error||(!recordingFresh?'PR recorder is stale.':!inventoryFresh?'PR inventory is stale.':d.backfilling?'PR is backfilling retained history; totals are incomplete until catch-up finishes.':'');
      result.nodes=(d.workers||[]).map(w=>{
        const sourceAge=valid(w.last_sample_ms)?now-w.last_sample_ms:null;
        const recent=inventoryFresh&&valid(sourceAge)&&sourceAge>=-10000&&sourceAge<=150000;
        return {id:w.instance||w.name,ip:w.ip,country:w.country,status:recent?(w.status||'Unverified'):'Unverified',salad:w.salad_state,
          working:recent&&w.connected===true&&w.salad_state==='running',rate:recent&&w.fresh&&w.salad_state==='running'?w.mb_per_minute:null,total:w.network_mb,
          duration:w.recorded_duration_ms,age:sourceAge,receivedAge:valid(w.recorded_ms)?now-w.recorded_ms:null,error:(recent?'':'Last saved: ')+(w.status_note||'Waiting for the recorded recovery policy.')};
      });result.working=result.nodes.filter(n=>n.working).length;
    }else if(service==='rp'){
      const inventoryFresh=recordingFresh&&valid(d.inventory_ms)&&fresh(now-d.inventory_ms,90000)&&!d.error;
      result.desired=valid(d.desired)?d.desired:null;result.running=inventoryFresh?d.running:null;result.total=d.total_network_mb;result.start=d.test_started_ms;result.source=d.inventory_ms||d.generated_ms;result.statusFresh=inventoryFresh;
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
        return {id:w.salad_instance||w.instance||'awaiting-'+i,ip:w.ip,country:w.country,status,salad:w.salad_state,working:native&&w.phase==='connected'&&w.salad_state==='running',rate:network?w.last_mb_per_minute:null,total:w.total_mb,duration:w.recorded_ms,age:diff(now,w.source_ms),error:notes.join(' · ')};
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
      result.desired=valid(d.deployment?.desired_replicas)?d.deployment.desired_replicas:null;result.running=d.inventory_fresh?d.running:null;result.total=valid(d.recorded?.rx)&&valid(d.recorded?.tx)?(d.recorded.rx+d.recorded.tx)/1e6:null;result.start=d.deployment?.measurement_started_ms||Date.parse(d.deployment?.started_at);result.source=d.inventory_ms;result.statusFresh=recordingFresh&&!d.stale&&d.inventory_fresh&&fresh(now-d.inventory_ms,90000)&&!d.errors?.recorder;
      const paidFresh=d.credited?.fresh&&fresh(now-d.credited.observed_ms,180000);
      result.credited=mb(valid(d.credited?.credited_bytes)?d.credited.credited_bytes/1e6:null);result.earned=usd(d.credited?.credited_usd);
      if(d.credited&&!paidFresh){result.credited+=' (stale)';result.earned+=' (stale)';}
      result.creditNote=(d.credited?.scope||'TM provider account figures')+(paidFresh?'':' Provider reading is stale or unavailable.');
      result.notice=Object.values(d.errors||{}).join(' · ')||(!recordingFresh||d.stale?'Traffic Monetizer recorder is stale.':!d.inventory_fresh?'Salad inventory is stale.':'');
      result.nodes=(d.workers||[]).map(w=>{
        const recent=recordingFresh&&!d.stale&&w.fresh&&fresh(now-w.time_ms,45000)&&fresh(now-w.received_ms,45000),connected=recent&&w.connection_fresh,notes=[];
        if(w.error)notes.push(w.error);
        if(!recent)notes.push(w.received_ms?'Measurement or receipt is stale':'Receipt time has not been recorded');
        if(valid(w.source_receipt_difference_ms)&&Math.abs(w.source_receipt_difference_ms)>30000)notes.push('Source/receipt time differ by '+shown(w.source_receipt_difference_ms/1000,0)+'s');
        if(recent&&valid(w.native_recent_bytes))notes.push('Relay observed: '+mb(w.native_recent_bytes/1e6)+' / '+shown(w.native_recent_requests,0)+' requests over '+shown(w.native_recent_ms/60000,1)+' min');
        const policy=w.policy;
        if(recent&&policy){notes.push(policy.state==='reallocating'?'Automatic replacement requested':policy.state==='stopped'?'Client stopped':policy.state==='waiting_connection'?'Connection recovery: '+shown(policy.unavailable_seconds,1)+'/'+shown(policy.failure_limit_seconds,0)+' unavailable seconds':policy.reallocate_on_idle===false?'Automatic failure recovery active':valid(policy.payload_remaining_seconds)?'No-payload replacement in '+shown(Math.max(0,policy.payload_remaining_seconds-Math.max(0,now-w.time_ms)/1000)/60,1)+' min if payload remains unchanged':'Recovery policy is incomplete');}
        else notes.push('Recovery policy has no fresh reading');
        return {id:w.instance,ip:w.ip,country:w.country,status:connected?w.state:'Unverified',salad:w.salad_state,working:connected&&w.working,rate:recent?w.raw_mb_per_minute:null,total:valid(w.test_rx)&&valid(w.test_tx)?(w.test_rx+w.test_tx)/1e6:null,duration:w.test_duration_ms,age:diff(now,w.time_ms),error:notes.join('; ')};
      });
      result.working=result.nodes.filter(n=>n.working).length;
      result.minutes=d.chart_minutes||[];
      const action=d.recent_recovery?.[0];
      if(action){const outcomes={request_failed:'request failed; container exit fallback',awaiting_response:'awaiting IMDS response',inventory_unverified:'replacement outcome unverified',awaiting_retirement:'accepted; old instance still listed',replacement_pending:'old instance left; replacement fleet pending',fleet_restored:'old instance left; full fleet confirmed'};result.creditNote+=' Last recovery: '+new Date(action.time_ms).toLocaleString()+' · '+action.instance.slice(0,8)+' · '+action.reason+(action.http_status?' · IMDS HTTP '+action.http_status:action.accepted===false?' · IMDS request failed':'')+' · '+(outcomes[action.outcome]||action.outcome)+(valid(action.fleet_confirmed_ms)?' at '+new Date(action.fleet_confirmed_ms).toLocaleString():'')+'.';}
      if(valid(d.chart_generated_ms))result.creditNote+=' Chart recorded through '+new Date(d.chart_generated_ms).toLocaleTimeString()+'.';
    }else if(service==='earnfm'){
      const inventoryFresh=recordingFresh&&fresh(now-d.inventory_ms,90000),providerFresh=!d.provider?.error&&fresh(now-(d.provider?.devices_observed_ms??d.provider?.observed_ms),180000);
      result.desired=valid(d.desired)?d.desired:null;result.running=inventoryFresh?(d.workers||[]).filter(w=>w.salad_state==='running').length:null;result.total=d.total_mb;result.start=d.test_started_ms;result.source=d.inventory_ms;result.statusFresh=inventoryFresh&&!d.error;result.notice=d.error||(!recordingFresh?'EarnFM recorder is stale.':!inventoryFresh?'EarnFM inventory is stale.':'');
      if(d.collection?.rejected)result.notice+=(result.notice?' · ':'')+shown(d.collection.rejected,0)+' malformed telemetry records saved separately; valid recording continues.';
      result.nodes=(d.workers||[]).map(w=>{
        const recent=inventoryFresh&&!d.error&&fresh(now-w.sample_ms,90000)&&fresh(now-w.recorded_ms,90000),h=w.health||{},runtime=w.runtime_instance||w.instance;
        const present=Array.isArray(d.provider?.devices)?d.provider.devices.some(device=>device.instance===runtime):w.provider_online===true?true:null;
        const working=recent&&!w.final&&w.client_state==='running'&&w.salad_state==='running'&&providerFresh&&present===true;
        const names={authorization_error:'Account key rejected',provider_rejected:'Provider rejected',starting:'Starting',connecting:'Connecting',connection_error:'Connection errors',rate_limited:'Provider cooldown',observer_unknown:'Connection unverified',retrying:'Restarting',awaiting_sample:'Awaiting first sample'};
        let status=names[w.client_state]||w.client_state,notes=[];
        if(w.salad_state&&w.salad_state!=='running')status=w.salad_state;
        else if(!recent)status='Unverified';
        else if(w.client_state==='reallocating')status='Reallocating';
        else if(w.final)status='Stopped';
        else if(w.client_state==='running')status=!providerFresh?'Provider status unavailable':present===false?'Provider offline':working?'Provider online':'Awaiting provider confirmation';
        if(w.error)notes.push(w.error);
        if(w.telemetry_note)notes.push(w.telemetry_note);
        if(!w.ip&&w.last_provider_ip&&valid(w.last_provider_seen_ms))notes.push('Last provider IP observed '+new Date(w.last_provider_seen_ms).toLocaleString());
        if(recent&&valid(h.retry_at_ms)&&h.retry_at_ms>now)notes.push('Retry '+new Date(h.retry_at_ms).toLocaleString());
        if(recent&&h.error&&h.error!=='none')notes.push(h.error.replaceAll('_',' '));
        if(recent&&h.activity_min_bytes===0&&w.client_state==='running')notes.push('No traffic-based restart');
        if(recent&&h.activity_observing===0&&h.activity_min_bytes!==0&&w.client_state==='running')notes.push('Activity check starts after 60 seconds of control connection warmup');
        if(recent&&h.activity_observing!==0&&h.activity_window_ms&&valid(h.activity_min_bytes)&&h.activity_min_bytes>0&&w.client_state==='running')notes.push('Activity check '+shown(h.activity_elapsed_ms/60000,1)+'/'+shown(h.activity_window_ms/60000,0)+' min: '+mb(h.activity_bytes/1e6)+' RX + TX; below '+mb(h.activity_min_bytes/1e6)+' restarts once, then replaces after another full low window');
        if(!providerFresh&&d.provider?.error)notes.push(d.provider.error);
        return {id:runtime,ip:w.ip||(w.last_provider_ip?w.last_provider_ip+' (last seen)':null),country:w.country,status,salad:w.salad_state,working,rate:recent&&!w.final&&valid(w.kb_per_second)&&w.salad_state==='running'?w.kb_per_second*.06:null,total:w.total_mb,duration:w.recorded_duration_ms,age:diff(now,w.sample_ms),error:notes.join(' · ')};
      });result.working=result.nodes.filter(n=>n.working).length;
      result.minutes=(d.points||[]).map(m=>{
        const nodes=Array.isArray(m.contributions)?m.contributions.map(([index,amount])=>({...d.history_nodes?.[index],mb:amount})):Object.entries(m.by_instance||{}).map(([id,amount])=>({instance:id,ip:(d.workers||[]).find(w=>(w.runtime_instance||w.instance)===id)?.ip,country:(d.workers||[]).find(w=>(w.runtime_instance||w.instance)===id)?.country,mb:amount}));
        return normalizeMinute(m.time_ms,m.mb,nodes,m.partial,m.estimated);
      });
      const creditFresh=!d.provider?.error&&fresh(now-d.provider?.observed_ms,180000);
      result.earned=usd(d.provider?.earned);result.credited=mb(d.provider?.credited_mb);
      if(!creditFresh){if(result.earned!=='Not reported')result.earned+=' (stale)';if(result.credited!=='Not reported')result.credited+=' (stale)';}
      result.creditNote='Recorded traffic is interface RX + TX, including relay crossings and overhead. Provider online confirms the device listing, not paid traffic. Credits and gross balance change cover the EarnFM account since '+(valid(d.provider?.baseline_ms)?new Date(d.provider.baseline_ms).toLocaleString():'its saved baseline')+'; per-device earnings are not reported.';
      if(valid(d.provider?.observed_ms))result.creditNote+=' Provider observation: '+new Date(d.provider.observed_ms).toLocaleString()+(creditFresh?'':' (stale)')+'.';
      if(d.provider_history?.observations)result.creditNote+=' '+shown(d.provider_history.observations,0)+' provider observations saved.';
      const action=d.recent_recovery?.[0];
      if(action)result.creditNote+=' Latest recovery: '+(action.machine?.slice(0,8)||'worker')+' · '+new Date(action.time_ms).toLocaleString()+' · '+action.action.replaceAll('_',' ')+' ('+action.reason.replaceAll('_',' ')+')'+(action.http_status?' · HTTP '+action.http_status:'')+(action.action==='reallocate_accepted'?' · '+(inventoryFresh?(action.old_instance_present?'old allocation still present':'old allocation removed; current provider-confirmed fleet '+result.working+'/'+result.desired):'inventory stale; removal unverified'):'')+'.';
    }else if(['pawns','earnapp','grass'].includes(service)){
      const inventoryFresh=recordingFresh&&valid(d.inventory_ms)&&fresh(now-d.inventory_ms,90000);
      result.desired=valid(d.desired)?d.desired:null;result.running=valid(d.running)?d.running:null;result.working=valid(d.working)?d.working:null;
      result.total=valid(d.total_mb)?d.total_mb:null;result.start=d.started_ms;result.source=d.inventory_ms;result.statusFresh=inventoryFresh;
      result.credited=d.credited_text||'Not reported';result.earned=d.earned_text||'Not reported';result.creditNote=d.credit_note||'Provider credited traffic and earnings have not been reported.';
      if(service==='earnapp'){result.basis=d.basis||'';result.received=valid(d.received_mb)?d.received_mb:null;result.sent=valid(d.sent_mb)?d.sent_mb:null;}
      if(!recordingFresh){if(result.credited!=='Not reported')result.credited+=' (stale)';if(result.earned!=='Not reported')result.earned+=' (stale)';}
      result.notice=d.error||(!valid(d.generated_ms)?'Waiting for '+result.name+' measurements.':!recordingFresh?result.name+' recorder is stale.':!inventoryFresh?result.name+' inventory is stale.':'');
      result.nodes=(d.workers||[]).map(w=>{
        const recent=inventoryFresh&&!d.error&&(service==='earnapp'?valid(w.sample_expires_ms)&&valid(w.sample_ms)&&w.sample_ms<=now+10000&&now<=w.sample_expires_ms:valid(w.sample_ms)&&fresh(now-w.sample_ms,90000)&&valid(w.recorded_ms)&&fresh(now-w.recorded_ms,90000));
        return {id:w.id,ip:w.ip,country:w.country,unknown:service==='pawns'&&(w.working===null||!recent),status:recent?(service==='pawns'?(w.client_status==='running'?'SDK running':CLIENTS[w.client_status]||w.client_status):w.client_status):'Unverified',salad:w.salad_state,
          working:recent&&w.working===true&&(service==='earnapp'||w.salad_state==='running')&&!w.error,
          rate:recent&&(service==='earnapp'||w.salad_state==='running')&&valid(w.mb_per_minute)?w.mb_per_minute:null,total:w.total_mb,duration:valid(w.recorded_duration_ms)?w.recorded_duration_ms:service==='earnapp'?diff(w.sample_ms,w.observer_ms):null,age:valid(w.sample_ms)?diff(now,w.sample_ms):null,error:w.error||'',note:w.note||''};
      });
      result.minutes=(d.minutes||[]).map(m=>({...m,nodes:[...(m.nodes||[])].sort((a,b)=>b.mb-a.mb).slice(0,20)}));
    }
    result.estimated=result.estimated||result.minutes.some(m=>m.estimated);
    if(result.statusFresh){
      for(const node of result.nodes){
        if(service==='proxyrack')continue;
        const state=node.salad?.toLowerCase();
        if(service==='earnapp'&&state==='creating')continue;
        if(['allocating','downloading','creating','stopping','stopped'].includes(state)){
          node.status=state[0].toUpperCase()+state.slice(1);node.working=false;node.rate=null;
          if(['allocating','downloading','creating'].includes(state))node.error='Waiting for the client to start on this machine.';
        }
      }
      if(result.working!==null)result.working=result.nodes.filter(node=>node.working).length;
      while(result.nodes.length<result.desired)result.nodes.push({id:service+'-pending-'+result.nodes.length,pending:true,status:'Awaiting inventory',working:false,error:'No machine listed in the latest inventory.'});
    }
    if(!result.statusFresh){result.working=null;result.running=null;result.nodes=result.nodes.map(n=>({...n,working:false,status:"Unverified",stale:true,rate:null}));}
    result.providerMetrics=d.provider_metrics||null;result.trafficSummary=d.traffic_summary||null;result.costs=d.costs||null;
    const sourceNodes=service==='hg'?d.latest?.hg?.workers:service==='ps'?d.nodes:d.workers,costById=new Map();
    for(const worker of sourceNodes||[])if(worker.cost)for(const key of ['id','run','instance','salad_instance','runtime_instance','machine','group','name'])if(worker[key])costById.set(worker[key],worker.cost);
    for(const node of result.nodes)node.cost=costById.get(node.id)||null;
    return result;
  }
  function periodMinutes(minutes,hours,now=Date.now()){
    const end=Math.floor(now/60000)*60000,start=end-(hours*60-1)*60000,byTime=new Map(minutes.map(m=>[m.minute_ms,m]));
    return Array.from({length:hours*60},(_,i)=>byTime.get(start+i*60000)||{minute_ms:start+i*60000,mb:null,partial:true,count:0,nodes:[]});
  }
  if(typeof module!=='undefined'&&module.exports){module.exports={workerState,serviceModel,chartValue,windowStart,displayedIntervals,normalize,periodMinutes,SERVICES,pageService,prNumber,prMB};return;}
  const el=id=>document.getElementById(id);
  const displayMB=window.formatBandwidth;
  const make=(tag,text,cls)=>{const node=document.createElement(tag);if(text!=null)node.textContent=text;if(cls)node.className=cls;return node;};
  const duration=ms=>!valid(ms)?'Not recorded':ms<60000?shown(ms/1000,0)+'s':Math.floor(ms/3600000)+'h '+Math.floor(ms%3600000/60000)+'m';
  const age=ms=>!valid(ms)?'Unknown':ms<60000?shown(ms/1000,0)+'s':ms<3600000?shown(ms/60000,1)+'m':shown(ms/3600000,1)+'h';
  const date=ms=>valid(ms)?new Date(ms).toLocaleString([], {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}):'Not recorded';
  const providerPeriod=period=>{if(typeof period==='string')return period;if(!period)return '';const dates=[period.first_date||(period.start_approximate?'≈ ':'')+date(period.start_ms),period.last_date||date(period.end_ms)].filter(value=>value&&value!=='Not recorded');return [period.kind?.replaceAll('_',' '),dates.join(' – '),period.timezone,period.stage!=null?'Stage '+period.stage:'',period.epoch,valid(period.covered_ms)?duration(period.covered_ms)+' observed':'',period.partial?'partial':''].filter(Boolean).join(' · ');};
  const buttons=new Map(),feeds=window.bandwidthData,read=feeds.read;
  let warmed=false;
  let active=pageService(location.pathname,location.hash);
  if(!active){location.replace('/overview');return;}
  history.replaceState(null,'',active.path+location.search);
  let hours=24,data=null,model=null,busy=false,generation=0,billing=null,billingPending=false,billingChecked=0;
  let historyVisible=false,historyData=null,historyOffset=0,historyTicket=0,historyRequest=null,historyTimer=null;
  const panel=el('bandwidthPanel');
  panel.innerHTML=`
    <div class="page-head"><h1 id="serviceTitle"></h1><div class="page-actions"><span id="connection" role="status"></span><button id="refresh" class="quiet-button" aria-label="Refresh" title="Refresh"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 11a9 9 0 0 1 15-6l3 3M21 3v5h-5M21 13a9 9 0 0 1-15 6l-3-3M3 21v-5h5"/></svg></button></div></div>
    <div id="totals" class="metrics" aria-label="Service measurements"></div>
    <section class="panel chart-panel corners" aria-labelledby="chartTitle">
      <div class="panel-head"><h2 id="chartTitle">Traffic</h2><span id="chartUnit" class="panel-subtitle">MB</span><div class="chart-controls"><div class="chart-legend"><span><i class="legend-key"></i>Network</span><span id="earnedLegend"><i class="legend-key earned"></i>Credited —</span></div><details id="hours" class="range-control"><summary id="hoursLabel" aria-haspopup="listbox" aria-controls="hoursOptions"><span>24h</span><svg viewBox="0 0 16 16" aria-hidden="true"><path d="m4 6 4 4 4-4"/></svg></summary><div id="hoursOptions" role="listbox" aria-label="Time range"><button type="button" role="option" data-hours="1" aria-selected="false">1 hour</button><button type="button" role="option" data-hours="6" aria-selected="false">6 hours</button><button type="button" role="option" data-hours="12" aria-selected="false">12 hours</button><button type="button" role="option" data-hours="24" aria-selected="true">24 hours</button></div></details></div></div>
      <div class="traffic-layout"><div class="ps-chart"><div id="chartScroll" class="ps-chart-scroll"><svg id="trafficChart" tabindex="0" role="img"></svg></div><div id="minutePopup" class="ps-popup hidden" role="tooltip"></div></div></div>
      
    </section>
    <section class="panel corners" aria-label="Node records">
      <div class="node-head"><div class="view-tabs nav nav-tabs" role="tablist" aria-label="Node views"><button class="nav-link active" id="currentTab" role="tab" aria-selected="true" aria-controls="currentView">Current nodes</button><button class="nav-link" id="breakdownTab" role="tab" aria-selected="false" aria-controls="breakdownView" tabindex="-1">IP breakdown</button><button class="nav-link" id="historyTab" role="tab" aria-selected="false" aria-controls="historyView" tabindex="-1">IP history</button></div><span id="nodeCount" class="view-count" role="status">—</span></div>
      <div id="breakdownView" role="tabpanel" aria-labelledby="breakdownTab" hidden><div class="table-scroll"><table class="breakdown-table"><thead><tr><th>IP</th><th>Country</th><th>Client</th><th>State</th><th class="numeric">Peak MB/min</th><th class="numeric">Period MB</th><th>Minutes</th></tr></thead><tbody id="ipBreakdown"></tbody></table></div><div class="table-foot"><span id="ipPageCount"></span><nav aria-label="IP pages"><ul class="pagination pagination-sm"><li class="page-item"><button class="page-link" id="ipPrevious" disabled>Previous</button></li><li class="page-item"><button class="page-link" id="ipNext" disabled>Next</button></li></ul></nav></div></div><div id="currentView" role="tabpanel" aria-labelledby="currentTab">
        <div class="table-scroll" tabindex="0" aria-label="Current node measurements"><table class="container-table"><thead><tr><th scope="col">IP</th><th scope="col">Country</th><th scope="col">Client</th><th scope="col">State</th><th scope="col" class="numeric">MB/min</th><th scope="col" class="numeric">Recorded MB</th><th scope="col">Duration</th></tr></thead><tbody id="workerRows"></tbody></table></div>
      </div>
      <div id="historyView" role="tabpanel" aria-labelledby="historyTab" hidden>
        <div class="history-controls"><label class="search-field">Find an IP or node<input id="historySearch" type="search" placeholder="Search recorded IP, instance or run" autocomplete="off"></label><label>Period<select id="historyHours"><option value="all" selected>All recorded history</option><option value="selected">Chart period</option></select></label><label>Test<select id="historyTest"><option value="current">Current test</option></select></label><label>Sort by<select id="historySort"><option value="last_seen">Last seen · newest</option><option value="total_mb">Contribution · highest</option></select></label></div>
        <p id="historyNote" class="history-note" role="status">Reading recorded IP history…</p>
        <div class="table-scroll" tabindex="0" aria-label="Historical node contributions"><table class="history-table"><thead><tr><th scope="col">IP</th><th scope="col">Country</th><th scope="col">Client</th><th scope="col">State</th><th scope="col" class="numeric">Avg MB/min</th><th scope="col" class="numeric">Period MB</th><th scope="col">Duration</th></tr></thead><tbody id="historyRows"></tbody></table></div>
        <div class="table-foot"><span id="historyCount"></span><nav aria-label="History pages"><ul class="pagination pagination-sm"><li class="page-item"><button class="page-link" id="historyPrevious" disabled>Previous</button></li><li class="page-item"><button class="page-link" id="historyNext" disabled>Next</button></li></ul></nav></div>
      </div>
      <details class="provider-note"><summary>Details</summary><p id="notice" class="notice hidden"></p><p id="elapsed" class="source-note"></p><p id="currentNote" class="source-note"></p><p id="chartNote" class="source-note"></p><p id="creditNote" class="source-note"></p><p id="costNote" class="source-note"></p><a id="earnfmDetail" href="/earnfm/details" hidden>EarnFM detailed records and download</a><details id="originalProvider" hidden><summary>Original provider values</summary><pre id="providerRaw"></pre></details></details>
    </section>
    <dialog id="recordDetail" class="detail-dialog" aria-labelledby="detailTitle"><div class="dialog-head"><div><h2 id="detailTitle">IP record</h2><p id="detailSubtitle"></p></div><button id="closeDetail" aria-label="Close record details">Close</button></div><div id="detailBody" class="dialog-body"></div></dialog>`;
  for(const node of panel.querySelectorAll('button:not(.page-link):not(.nav-link)'))node.classList.add('btn','btn-outline-secondary','btn-sm');
  for(const node of panel.querySelectorAll('select'))node.classList.add('form-select','form-select-sm');
  for(const node of panel.querySelectorAll('input'))node.classList.add('form-control','form-control-sm');
  for(const node of panel.querySelectorAll('table'))node.classList.add('table','table-sm','table-hover');
  for(const [i,service]of SERVICES.entries()){const button=make('button',null,'btn btn-outline-secondary btn-sm'),mark=make('span',['HG','PS','PR','RP','EF','TM','PA','EA','GR'][i],'service-mark');mark.setAttribute('aria-hidden','true');mark.innerHTML=window.serviceIcon(mark.textContent);button.append(mark,make('span',service.name,'service-name'));button.setAttribute('aria-label',service.name);button.title=service.name;button.id='tab-'+service.id;button.setAttribute('role','tab');button.setAttribute('aria-controls','bandwidthPanel');button.onclick=()=>select(service);buttons.set(service.id,button);el('services').append(button);}
  el('services').onkeydown=event=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End'].includes(event.key))return;event.preventDefault();const index=SERVICES.indexOf(active),next=event.key==='Home'?0:event.key==='End'?SERVICES.length-1:(index+(['ArrowLeft','ArrowUp'].includes(event.key)?SERVICES.length-1:1))%SERVICES.length;select(SERVICES[next]);buttons.get(active.id).focus();};
  const chart=window.createMinuteChart({plot:el('trafficChart'),breakdown:el('ipBreakdown'),pageCount:el('ipPageCount'),previous:el('ipPrevious'),next:el('ipNext'),scroll:el('chartScroll'),popup:el('minutePopup'),active:()=>true,unit:el('chartUnit')});
  function identityCell(node,includeCountry=true){
    const cell=make('td');cell.append(window.bandwidthNodes.label(node,includeCountry));
    if(node.id&&!node.pending)cell.title=node.id;return cell;
  }
  function emptyRow(body,text){body.replaceChildren();const row=make('tr'),cell=make('td',text,'empty-cell');cell.colSpan=body.closest('table').tHead.rows[0].cells.length;row.append(cell);body.append(row);}
  function metric(label,value,unit,note,cls=''){
    if(value==='—'||value==='≈ —'){value='Not reported';unit='';}
    const card=make('div',null,'metric card '+cls),valueNode=make('div',value,'metric-value');if(unit)valueNode.append(make('span',unit,'metric-unit'));
    card.title=note;card.append(make('p',label,'metric-label'),valueNode);return card;
  }
  function render(){
    if(!model)return;
    const bars=periodMinutes(model.minutes,hours,valid(model.trafficSummary?.end_ms)?model.trafficSummary.end_ms-1:Date.now()),measured=bars.filter(b=>valid(b.mb)),estimated=measured.some(b=>b.estimated);
    const networkNumber=displayMB;
    const t=model.trafficSummary||{},p=model.providerMetrics||{},observed=p.observed_period||{},comparison=t.provider_comparison||{},rates=model.nodes.filter(n=>!n.pending).map(n=>n.rate).filter(valid),partialRate=rates.length!==t.containers_total,currentRate=model.statusFresh&&rates.length?rates.reduce((sum,n)=>sum+n,0):null;
    const balanceChange=active.id==='earnfm',moneyValue=balanceChange?observed.balance_change_usd:observed.earned_usd,moneyWindow=balanceChange?observed.balance_window:observed.earned_window;
    const providerNumber=value=>shown(value,6),providerStale=valid(p.observed_ms)&&!feeds.providerFresh(active.id,p);
    const isEarnApp=active.id==='earnapp',matched=t.earnings_comparison||{},effective=isEarnApp?matched.usd_per_recorded_gb:p.effective_usd_per_gb,effectiveUnit=isEarnApp?'USD/recorded GB':'USD/GB';
    const effectiveText=(isEarnApp&&valid(effective)&&(matched.partial||matched.estimated)?'≈ ':'')+shown(effective,4);
    const effectiveNote=isEarnApp?(matched.basis||'Matching earnings and traffic observations unavailable')+' · '+providerPeriod(matched)+' · '+shown(matched.earned_usd,6)+' USD / '+shown(matched.measured_mb)+' recorded MB · '+(matched.provider_scope||'device')+' / '+(matched.traffic_scope||'recorded fleet'):(p.scope||'Unknown scope')+' · '+providerPeriod(p.window);
    el('totals').replaceChildren(metric('Containers',(model.statusFresh&&fresh(Date.now()-t.inventory_ms,active.id==='hg'||active.id==='ps'?120000:90000)&&valid(t.containers_running)?shown(t.containers_running,0):valid(t.inventory_ms)?'Stale':'Not reported')+' / '+shown(t.containers_total,0),'',shown(model.working,0)+' confirmed clients'),metric('Current rate'+(valid(currentRate)&&partialRate?' · partial':''),valid(currentRate)?displayMB(currentRate):model.statusFresh?'Waiting':'Stale',valid(currentRate)?'MB/min':'',rates.length+' / '+shown(t.containers_total,0)+' containers have fresh native rates'+(partialRate?'; sum of available fresh rates while other rates are unavailable':'')),metric('Measured · 24h',(t.last_24h_partial||t.estimated?'≈ ':'')+displayMB(t.last_24h_mb),'MB','Recorded last-day chart intervals'),hours===24?metric('Average rate',(t.average_partial?'≈ ':'')+displayMB(t.average_mb_per_minute),'MB/min',t.average_basis||'Completed observed minutes'):metric('Measured · '+hours+'h',(t.partial||t.estimated?'≈ ':'')+displayMB(t.selected_mb),'MB','Selected-period chart intervals'),metric('Credited'+(providerStale?' · stale':model.cached?' · saved':''),(observed.credited_window?.partial?'≈ ':'')+displayMB(observed.credited_mb),'MB',(p.missing||p.changes_error||p.error||p.scope)+' · observed changes · '+providerPeriod(observed.credited_window)),metric((balanceChange?'Balance change':p.usd_conversion?'USD equivalent':'Earned')+(providerStale?' · stale':model.cached?' · saved':''),(moneyWindow?.partial?'≈ ':'')+providerNumber(moneyValue),'USD',(p.missing||p.changes_error||p.error||p.scope)+' · observed changes · '+providerPeriod(moneyWindow)+(p.usd_conversion?' · '+(p.usd_conversion.basis||String(p.usd_conversion.credits_per_usd)+' credits per USD')+' · '+p.usd_conversion.source:'')),isEarnApp?metric('Provider rate'+(providerStale?' · stale':''),shown(p.monthly_rate_usd,2),'USD/month','Provider-reported device rate for qualifying usage · observed '+date(p.observed_ms)):metric('Credit / measured %',(valid(comparison.ratio_percent)&&(comparison.estimated||comparison.partial)?'≈ ':'')+shown(comparison.ratio_percent,1),'',(comparison.basis||'Unavailable')+' · '+providerPeriod(comparison)+' · '+shown(comparison.credited_mb)+' credited MB / '+shown(comparison.measured_mb)+' measured MB'),balanceChange?metric('Account balance',providerNumber(p.balance_usd),'USD','Provider bandwidth balance · observed '+date(p.observed_ms)):metric('Effective rate'+(isEarnApp&&providerStale?' · stale':''),effectiveText,effectiveUnit,effectiveNote));
    el('totals').classList.add('overview-metrics');
    el('notice').textContent=model.notice;el('notice').classList.toggle('hidden',!model.notice);
    el('elapsed').textContent=valid(model.start)?'Test window starts '+date(model.start)+' · '+duration(diff(Date.now(),model.start))+' elapsed':'Recording start has not been reported';
    
    el('earnedLegend').lastChild.textContent=model.providerMetrics?.intervals?.some(p=>valid(p.credited_mb))?'Credited':'Credited —';el('earnedLegend').title='Provider counter changes shown when observed; their posting time is unknown.';
    el('chartNote').textContent=(estimated?'≈ Estimated minute allocation.':'')+' Network traffic includes overhead.'+(active.id==='earnapp'?' EarnApp has not reported credited traffic in MB; network MB is separate from earnings. '+model.basis:'');
    const costs=model.costs;el('costNote').textContent=costs?'Salad running time: '+shown(costs.running_minutes,1)+' node-minutes · Estimated cost: '+usd(costs.estimated_usd)+' · '+providerPeriod(costs.window)+(costs.partial?' · Partial coverage':'')+' · '+costs.basis+(costs.errors?.length?' · '+costs.errors.join('; '):''):'Salad runtime and cost have not been reported.';el('earnfmDetail').hidden=active.id!=='earnfm';
    const body=el('workerRows');body.replaceChildren();
    for(const n of model.nodes){
      const row=make('tr'),client=make('td'),status=window.bandwidthNodes.status(n),state=make('td',window.bandwidthNodes.state(n));
      client.append(make('span',status,'status-pill '+(status==='Online'?'online':'')));client.title=[n.status,n.error,n.note].filter(Boolean).join(' · ');state.title=n.stale?'Last recorded: '+(n.salad||'Unknown'):n.salad||'';
      const durationCell=make('td',duration(n.duration));durationCell.title=(valid(n.age)?'Last source sample '+age(n.age)+' ago':'Source sample unavailable')+(n.cost?' · Salad running '+duration(valid(n.cost.running_minutes)?n.cost.running_minutes*60000:null)+' · Estimated Salad cost '+usd(n.cost.estimated_usd)+(n.cost.partial?' · Partial coverage':''):'');
      row.append(identityCell(n,false),make('td',window.bandwidthCountries.name(n)),client,state,make('td',active.id==='earnfm'?shown(n.rate,valid(n.rate)&&n.rate>0&&n.rate<.001?6:3):networkNumber(n.rate),'numeric'),make('td',networkNumber(n.total),'numeric'),durationCell);body.append(row);
    }
    if(!model.nodes.length)emptyRow(body,'No current nodes');
    const renderedModel=model;
    window.bandwidthCountries.lookup(model.nodes.filter(n=>!n.pending)).then(()=>{
      if(model!==renderedModel)return;
      for(let i=0;i<renderedModel.nodes.length;i++)if(body.rows[i])body.rows[i].cells[1].textContent=window.bandwidthCountries.name(renderedModel.nodes[i]);
    });
    el('currentNote').textContent=!data?'No inventory has been received.':model.statusFresh?'Current inventory · source observed '+date(model.source):'Current state is unverified · showing last recorded identities';
    el('creditNote').textContent=model.creditNote+(active.id==='proxyrack'?' Account balance: '+model.earned+' · '+date(data?.balance_checked_ms):'');if(model.providerMetrics){const p=model.providerMetrics,t=model.trafficSummary||{};el('creditNote').textContent=model.creditNote+' '+[p.scope,providerPeriod(p.window),'Observed '+date(p.observed_ms),'Average '+shown(t.average_mb_per_minute)+' MB/min','Peak '+shown(t.peak_mb_per_minute)+' MB/min','Credit / measured '+(t.provider_comparison?.estimated||t.provider_comparison?.partial?'≈ ':'')+shown(t.provider_comparison?.ratio_percent,1)+'% ('+shown(t.provider_comparison?.credited_mb)+' credited MB / '+shown(t.provider_comparison?.measured_mb)+' measured MB; '+providerPeriod(t.provider_comparison)+'; '+(t.provider_comparison?.provider_scope||'unknown provider scope')+' / '+(t.provider_comparison?.traffic_scope||'unknown traffic scope')+')','Effective '+effectiveText+' '+effectiveUnit+(isEarnApp?' · '+effectiveNote:''),isEarnApp?'Provider rate '+shown(p.monthly_rate_usd,2)+' USD/month':'',p.raw?.account_balance_credits!=null?'Account balance '+p.raw.account_balance_credits+' credits · observed '+date(p.raw.account_balance_observed_ms):'Account balance '+shown(p.balance_usd)+' USD','Credited observation window: '+providerPeriod(p.observed_period?.credited_window),(active.id==='earnfm'?'Balance-change observation window: ':'Earned observation window: ')+providerPeriod(active.id==='earnfm'?p.observed_period?.balance_window:p.observed_period?.earned_window),'Account-source totals: '+shown(p.credited_mb)+' MB / '+shown(active.id==='earnfm'?p.balance_change_usd:p.earned_usd)+(active.id==='earnfm'?' USD balance change':' USD'),p.error,p.missing].filter(Boolean).join(' · ');}
    el('originalProvider').hidden=!model.providerMetrics?.raw;el('providerRaw').textContent=model.providerMetrics?.raw?JSON.stringify(model.providerMetrics.raw,null,2):'';
    updateClock(false);
    chart.update({key:active.id+':'+hours,time_ms:Date.now(),candles:bars,nodes:model.nodes,postings:model.providerMetrics?.intervals||[],usdConversion:model.providerMetrics?.usd_conversion});renderHistoryClients();updateNodeCount();
  }
  function updateClock(recheck=true){
    if(!model)return;
    const now=Date.now();
    if(recheck&&data){
      const current=normalize(active.id,{...data,hg_minutes:[],candles:[],minutes:[],chart_minutes:[],points:[],timeline:{}},now,billing);
      const changed=current.statusFresh!==model.statusFresh||current.running!==model.running||current.working!==model.working||current.nodes.length!==model.nodes.length||current.nodes.some((node,i)=>['status','working','rate','stale','unknown'].some(key=>node[key]!==model.nodes[i]?.[key]))||feeds.providerFresh(active.id,model.providerMetrics,now)!==feeds.providerFresh(active.id,model.providerMetrics,model.at);
      if(changed){
        model={...model,at:now,statusFresh:current.statusFresh,running:current.running,working:current.working,nodes:current.nodes,notice:model.cached?model.notice:current.notice};
        render();return;
      }
    }
    const current=model.statusFresh&&fresh(now-model.source,active.id==='hg'||active.id==='ps'?120000:90000),node=el('connection');
    const text=(model.cached?'Error · ':current?'':'Stale · ')+'Updated '+feeds.age(feeds.updated(active,hours),now)+' · Source '+feeds.age(model.source,now);
    if(node.textContent!==text)node.textContent=text;
    node.title=model.notice||'Updated: last successful website fetch. Source: original inventory observation.';node.className=current&&!model.notice?'ok':'bad';
  }
  function restoreView(service,range){
    const ticket=generation;
    feeds.restore(service,range).then(value=>{
      if(ticket!==generation||data||!value)return;
      const failure=model?.cached?model.notice:null;data=value;model=failure?savedModel(service,data):normalize(service.id,data,Date.now(),billing);if(failure)model.notice=failure.replace('No readings are available.','Saved measurements are shown.');render();
    });
  }
  function savedModel(service,payload){
    const value=normalize(service.id,payload,Date.now(),billing);value.cached=true;return value;
  }
  async function refresh(force=true){
    if(busy)return;
    busy=true;const ticket=generation,service=active,range=hours;el('refresh').disabled=true;
    try{
      const result=await feeds.load(service,range,force);
      if(ticket!==generation)return;if(result!==data){data=result;model=normalize(service.id,data,Date.now(),billing);render();}else updateClock();
      if(!warmed){warmed=true;for(const next of SERVICES)if(next!==service)feeds.restore(next,range).then(()=>feeds.load(next,range,false)).catch(()=>{});}
    }catch(error){
      if(ticket!==generation)return;
      model=savedModel(service,data||{});if(!data)model.nodes=[];model.notice='Cannot refresh '+service.name+': '+error.message+(data?' Saved measurements are shown.':' No readings are available.');render();
    }finally{if(ticket===generation){busy=false;el('refresh').disabled=false;}}
    if(service.id==='ps'&&!billingPending&&Date.now()-billingChecked>60000){
      billingPending=true;billingChecked=Date.now();
      read('/api/ps1/view').then(value=>{billing=value;if(active.id==='ps'&&data&&model){const credit=normalize('ps',data,Date.now(),billing);model.credited=credit.credited;model.earned=credit.earned;model.balance=credit.balance;model.creditNote=credit.creditNote;render();}}).catch(()=>{}).finally(()=>{billingPending=false;});
    }
  }
  function updateNodeCount(){
    const kind=historyVisible?'history':el('breakdownView').hidden?'current':'breakdown';
    const count=kind==='history'?historyData?.total:kind==='breakdown'?chart.count():data&&model?model.nodes.filter(n=>!n.pending).length:null;
    const node=el('nodeCount'),text=shown(count,0);if(node.textContent!==text)node.textContent=text;
    node.setAttribute('aria-label',text+' '+(kind==='history'?'history records':kind==='breakdown'?'contributor records':'current nodes'));
  }
  function showNodeView(view){
    historyVisible=view==='history';for(const name of ['breakdown','current','history']){const selected=name===view;el(name+'View').hidden=!selected;el(name+'Tab').setAttribute('aria-selected',String(selected));el(name+'Tab').classList.toggle('active',selected);el(name+'Tab').tabIndex=selected?0:-1;}
    if(historyVisible)loadHistory();else{historyRequest?.abort();historyTicket++;}updateNodeCount();
  }
  function renderHistoryClients(){
    if(!historyVisible||!historyData)return;
    for(const [i,record]of historyData.rows.entries()){
      const current=record.current===true?model?.nodes.find(n=>!n.pending&&n.ip===record.ip&&n.id===record.instance):null;
      const status=window.bandwidthNodes.status(current),pill=el('historyRows').rows[i].cells[2].firstElementChild;
      pill.textContent=status;pill.className='status-pill '+(status==='Online'?'online':'');
    }
  }
  async function loadHistory(){
    if(!historyVisible)return;historyRequest?.abort();historyRequest=new AbortController();const ticket=++historyTicket,service=active;
    historyData=null;emptyRow(el('historyRows'),'Loading recorded IP contributions…');el('historyCount').textContent='';el('historyNote').textContent='Reading saved IP records…';el('historyRows').setAttribute('aria-busy','true');el('historyPrevious').disabled=true;el('historyNext').disabled=true;updateNodeCount();
    const query=new URLSearchParams({service:service.id,hours:el('historyHours').value==='all'?'all':String(hours),test:el('historyTest').value,q:el('historySearch').value.trim(),sort:el('historySort').value,offset:String(historyOffset),limit:'50'});
    try{
      const result=await read('/api/history?'+query,historyRequest.signal);if(ticket!==historyTicket)return;historyData=result;
      const selection=el('historyTest').value;el('historyTest').replaceChildren();
      for(const test of result.tests||[]){const option=make('option',test.label+(test.archived?' · archived':''));option.value=test.id;el('historyTest').append(option);}
      if(!el('historyTest').options.length){const option=make('option','Current test');option.value='current';el('historyTest').append(option);}
      if([...el('historyTest').options].some(o=>o.value===selection))el('historyTest').value=selection;else el('historyTest').value=result.test?.id||'current';
      const period=el('historyHours').value==='all'?'All recorded history':'Last '+hours+' hours';
      el('historyNote').textContent=period+' · '+(result.test?.label||'Current test')+(result.test?.archived?' · Archived test':'')+'. '+(result.coverage_note||'Coverage has not been reported.')+(valid(result.source_ms)?' Source observed '+date(result.source_ms)+'.':'');
      const body=el('historyRows');body.replaceChildren();
      for(const record of result.rows||[]){
        const row=make('tr'),identity=make('td'),client=make('td'),button=make('button',null,'record-link');
        button.append(window.bandwidthNodes.label(record,false));button.setAttribute('aria-label','View record for '+(record.ip||record.instance||'unknown IP'));button.onclick=()=>showRecord(record,result);identity.append(button);
        client.append(make('span',null,'status-pill'));
        const average=valid(record.total_mb)&&valid(record.duration_ms)&&record.duration_ms>0?record.total_mb*60000/record.duration_ms:null,prefix=record.estimated?'≈ ':'';
        const amount=make('td',prefix+displayMB(record.total_mb),'numeric');if(record.partial)amount.append(make('span','Partial coverage','cell-subtitle'));
        row.append(identity,make('td',record.country||'Not recorded'),client,make('td',record.lifecycle||'Unknown'),make('td',prefix+displayMB(average),'numeric'),amount,make('td',duration(record.duration_ms)));body.append(row);
      }
      renderHistoryClients();
      if(!result.rows?.length)emptyRow(body,'No recorded IPs match this period and search. Try all recorded history or another test.');
      el('historyCount').textContent=(result.rows?.length?shown(historyOffset+1,0)+'–'+shown(historyOffset+result.rows.length,0):'0')+' of '+shown(result.total,0)+' records · period contributions';
      el('historyPrevious').disabled=historyOffset===0;el('historyNext').disabled=!result.has_more;
    }catch(error){if(ticket!==historyTicket)return;historyData=null;emptyRow(el('historyRows'),'History could not be loaded. Use Refresh to try again.');el('historyNote').textContent='History unavailable: '+error.message;el('historyCount').textContent='No history response';}
    finally{if(ticket===historyTicket){el('historyRows').removeAttribute('aria-busy');updateNodeCount();}}
  }
  function showRecord(record,result){
    el('detailTitle').textContent=record.ip||'IP not recorded';el('detailSubtitle').textContent=(record.country||'Country not recorded')+' · '+(record.lifecycle||'Lifecycle unknown');
    const body=el('detailBody'),grid=make('dl',null,'detail-grid');body.replaceChildren(grid);
    const fields=[['Period contribution',mb(record.total_mb,6)],['Recorded time in period',duration(record.duration_ms)],['First sample used for period',valid(record.first_seen_ms)?new Date(record.first_seen_ms).toLocaleString():'Not recorded'],['Last sample used for period',valid(record.last_seen_ms)?new Date(record.last_seen_ms).toLocaleString():'Not recorded'],['Test',(result.test?.label||'Unknown')+(result.test?.archived?' · archived':'')],['Saved samples',shown(record.samples,0)],['Group',record.group_id||record.group],['Instance',record.instance],['Machine',record.machine],['Run',record.run],['Coverage',[record.partial?'Partial':'',record.estimated?'Estimated interval allocation':''].filter(Boolean).join(' · ')||'See source coverage note']];
    if('run_first_observed_ms' in record)fields.push(['First retained run observation',valid(record.run_first_observed_ms)?new Date(record.run_first_observed_ms).toLocaleString():'Not recorded'],['Last retained run observation',valid(record.run_last_observed_ms)?new Date(record.run_last_observed_ms).toLocaleString():'Not recorded']);
    if(record.cost)fields.push(['Salad running time in period',duration(valid(record.cost.running_minutes)?record.cost.running_minutes*60000:null)],['Estimated Salad cost',usd(record.cost.estimated_usd)],['Cost scope',record.cost.scope+(record.cost.partial?' · Partial coverage':'')]);
    for(const [label,value]of fields){const item=make('div',null,['Group','Instance','Machine','Run'].includes(label)?'full':'');item.append(make('dt',label),make('dd',value==null?'Not recorded':String(value),['Group','Instance','Machine','Run'].includes(label)?'mono':''));grid.append(item);}
    body.append(make('p',(result.coverage_note||'Coverage has not been reported.')+' Provider credit per IP is not reported. Account totals are kept separate.','dialog-note'));
    el('recordDetail').showModal();
  }
  function clearDetails(){el('costNote').textContent='';el('providerRaw').textContent='';el('originalProvider').hidden=true;el('earnfmDetail').hidden=active.id!=='earnfm';el('creditNote').textContent='Waiting for provider and measurement notes.';}
  function select(service,changePath=true){
    if(service===active&&model)return;
    historyRequest?.abort();historyTicket++;generation++;busy=false;active=service;chart.hide();el('recordDetail').close();
    data=feeds.get(service,hours)||null;model=data?normalize(service.id,data,Date.now(),billing):null;historyData=null;historyOffset=0;
    el('historyTest').replaceChildren(Object.assign(make('option','Current test'),{value:'current'}));el('historySearch').value='';
    panel.setAttribute('aria-label',service.name);if(changePath&&location.pathname!==service.path)history.pushState(null,'',service.path);document.title='Salad · '+service.name;
    el('serviceTitle').textContent=service.name;for(const item of SERVICES){const chosen=item.id===service.id;buttons.get(item.id).setAttribute('aria-selected',String(chosen));buttons.get(item.id).classList.toggle('active',chosen);buttons.get(item.id).tabIndex=chosen?0:-1;}el('connection').textContent='Loading…';el('connection').className='';
    if(model){render();}else{
      clearDetails();
      el('totals').classList.add('overview-metrics');el('totals').replaceChildren(...['Containers','Current rate','Measured · 24h',hours===24?'Average rate':'Measured · '+hours+'h','Credited','Earned',service.id==='earnapp'?'Provider rate':'Credit / measured %','Effective rate'].map(label=>metric(label,'\u00a0','','Reading measurements')));
      emptyRow(el('workerRows'),'Loading '+service.name+' inventory…');el('notice').classList.add('hidden');el('nodeCount').textContent='—';el('elapsed').textContent='Reading saved measurements…';el('currentNote').textContent='Reading current inventory…';chart.update({time_ms:Date.now(),candles:periodMinutes([],hours),loading:true});
    }
    if(!data)restoreView(service,hours);refresh(false);if(historyVisible)loadHistory();
  }
  function selectHours(value){hours=value;el('hoursLabel').firstElementChild.textContent=hours+'h';el('hours').open=false;for(const option of el('hoursOptions').children)option.setAttribute('aria-selected',String(Number(option.dataset.hours)===hours));el('hoursLabel').focus({preventScroll:true});data=feeds.get(active,hours)||null;model=data?normalize(active.id,data,Date.now(),billing):null;chart.hide();generation++;busy=false;if(model)render();else{clearDetails();chart.update({time_ms:Date.now(),candles:periodMinutes([],hours),loading:true});for(const value of el('totals').querySelectorAll('.metric-value'))value.firstChild.textContent='—';el('earnedLegend').lastChild.textContent='Credited —';}updateNodeCount();if(!data)restoreView(active,hours);refresh(false);historyOffset=0;if(historyVisible)loadHistory();}
  for(const option of el('hoursOptions').children)option.onclick=()=>selectHours(Number(option.dataset.hours));
  el('hours').onkeydown=event=>{const options=[...el('hoursOptions').children],index=options.indexOf(document.activeElement);if(event.key==='Escape'){event.preventDefault();el('hours').open=false;el('hoursLabel').focus();}else if(['ArrowDown','ArrowUp','Home','End'].includes(event.key)){event.preventDefault();el('hours').open=true;const next=event.key==='Home'?0:event.key==='End'?options.length-1:index<0?options.findIndex(o=>Number(o.dataset.hours)===hours):(index+(event.key==='ArrowDown'?1:options.length-1))%options.length;options[next].focus();}};
  el('hours').addEventListener('focusout',event=>{if(!el('hours').contains(event.relatedTarget))el('hours').open=false;});
  document.addEventListener('pointerdown',event=>{if(!el('hours').contains(event.target))el('hours').open=false;});
  el('refresh').onclick=()=>{refresh();if(historyVisible)loadHistory();};
  const nodeViews=['current','breakdown','history'];
  for(const [index,name]of nodeViews.entries()){
    el(name+'Tab').onclick=()=>showNodeView(name);
    el(name+'Tab').onkeydown=event=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();const next=event.key==='Home'?0:event.key==='End'?2:(index+(event.key==='ArrowLeft'?2:1))%3;showNodeView(nodeViews[next]);el(nodeViews[next]+'Tab').focus();}};
  }
  for(const id of ['historyHours','historyTest','historySort'])el(id).onchange=()=>{historyOffset=0;loadHistory();};
  el('historySearch').oninput=()=>{clearTimeout(historyTimer);historyOffset=0;historyTimer=setTimeout(loadHistory,250);};
  el('historyPrevious').onclick=()=>{historyOffset=Math.max(0,historyOffset-50);loadHistory();};el('historyNext').onclick=()=>{if(historyData?.has_more){historyOffset+=50;loadHistory();}};
  el('closeDetail').onclick=()=>el('recordDetail').close();
  document.querySelector('.skip-link')?.addEventListener('click',event=>{event.preventDefault();panel.focus();});
  window.addEventListener('popstate',()=>{const service=pageService(location.pathname,location.hash);if(service)select(service,false);else location.replace('/overview');});
  window.addEventListener('hashchange',()=>{const service=SERVICES.find(s=>s.hash===location.hash);if(service){history.replaceState(null,'',service.path+location.search);select(service,false);}});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});
  setInterval(()=>{if(!document.hidden)updateClock();},1000);
  select(active,false);setInterval(()=>{if(!document.hidden)refresh();},5000);
})();
