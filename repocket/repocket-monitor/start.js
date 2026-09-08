if (process.env.RP_DIAGNOSTICS === '1') {
  const net=require('net'), base='/app/node_modules/@geonode/repocket-peer-client/dist/src/';
  const stats={client_started_ms:Date.now(),attempts:0,connected:0,responses:0,failed:0,failed_without_response:0,closed_without_response:0,closed_failed_without_response:0,rx_bytes:0,tx_bytes:0,http:0,socks:0,errors:{},connect_forwarding:'transparent',errors_by_target:{},dns_fallback:{attempted:0,recovered:0,failed:0},control:{state:'starting',time_ms:0,changed_ms:Date.now()}};
  const active=new Set(), seen=new WeakSet();let context='';
  function sample(item){const rx=item.socket.bytesRead||0,tx=item.socket.bytesWritten||0;stats.rx_bytes+=Math.max(0,rx-item.rx);stats.tx_bytes+=Math.max(0,tx-item.tx);item.rx=rx;item.tx=tx;if(rx>0&&!item.responded){item.responded=true;stats.responses++;}}
  function failure(item,error){sample(item);if(!item.failed){item.failed=true;stats.failed++;if(!item.responded)stats.failed_without_response++;}const code=['ECONNRESET','ETIMEDOUT','ECONNREFUSED','EHOSTUNREACH','EPIPE','ENOTFOUND','EAI_AGAIN','ECONNABORTED','ENETUNREACH','EADDRNOTAVAIL','EMFILE','ENFILE'].includes(error?.code)?error.code:'OTHER';stats.errors[code]=(stats.errors[code]||0)+1;
    const family=net.isIP(error?.address||'');const group=code+'/'+item.kind+'/'+item.hostType+'/'+(family?'ipv'+family:'unresolved');stats.errors_by_target[group]=(stats.errors_by_target[group]||0)+1;
  }
  function finish(item){if(item.finished)return;item.finished=true;sample(item);if(!item.responded){stats.closed_without_response++;if(item.failed)stats.closed_failed_without_response++;}active.delete(item);}
  function track(socket,host){if(seen.has(socket))return;seen.add(socket);const ip=net.isIP(host||'');const item={socket,host,kind:context,hostType:ip?'ipv'+ip:typeof host!=='string'||/[\s/:\[\]]/.test(host)?'malformed':'domain',rx:0,tx:0,responded:false,failed:false};active.add(item);stats.attempts++;stats[context]++;
    socket.once('connect',()=>stats.connected++);socket.on('error',error=>failure(item,error));socket.on('timeout',()=>failure(item,{code:'ETIMEDOUT'}));
    socket.once('close',()=>finish(item));return item;}
  const dns=require('dns'),lookup=dns.lookup;
  dns.lookup=function(host,options,callback){
    if(!context||typeof callback!=='function'||options?.family===6||typeof host!=='string'||net.isIP(host)||/[\s/:\[\]]/.test(host))return lookup.apply(this,arguments);
    return lookup.call(this,host,options,(error,address,family)=>{if(error?.code!=='ENOTFOUND')return callback(error,address,family);stats.dns_fallback.attempted++;
      dns.resolve4(host,(failure,addresses)=>{if(!failure&&addresses?.length){stats.dns_fallback.recovered++;return options?.all?callback(null,addresses.map(address=>({address,family:4}))):callback(null,addresses[0],4);}stats.dns_fallback.failed++;callback(error,address,family);});});
  };
  const originalConnect=net.Socket.prototype.connect;
  net.Socket.prototype.connect=function(...args){const option=Array.isArray(args[0])?args[0][0]:args[0],host=option&&typeof option==='object'?option.host:args[1];const item=context?track(this,host):null;try{return originalConnect.apply(this,args);}catch(error){if(item){failure(item,error);finish(item);}throw error;}};
  for(const [file,name,method,kind] of [['P2P/target.socket.js','TargetSocket','connect','http'],['P2P/socks5/socks5.socket.js','Socket5Handler','createConnection','socks']]){
    const prototype=require(base+file)[name].prototype, original=prototype[method];prototype[method]=function(...args){const previous=context;context=kind;try{return original.apply(this,args);}finally{context=previous;}};
  }
  Object.defineProperty(require(base+'P2P/target.socket.js').TargetSocket.prototype,'shouldUseBufferProcessor',{configurable:true,get(){return this.useBufferProcessor&&this.isSMTP;}});
  const main=require(base+'P2P/main.socket.js').MainSocket.prototype,events=require(base+'services/P2P.service.js').PeerSocketEvents,read=main._handleRead;
  let activeMain=null;const connectMain=main.connect;main.connect=function(...args){activeMain=this;stats.control={state:'starting',time_ms:0,changed_ms:Date.now()};return connectMain.apply(this,args);};
  function control(owner,state,active=false){if(owner!==activeMain)return;if(stats.control.state!==state){stats.control.state=state;stats.control.changed_ms=Date.now();}if(active)stats.control.time_ms=Date.now();}
  main._handleRead=async function(data){const text=Buffer.from(data).toString();const result=await read.call(this,data);if(text===events.AuthenticationFailed)control(this,'rejected');else if(text===events.ConnectionCompleted&&this.onConnectionEstablishedEventFired)control(this,'connected',true);else if(stats.control.state==='connected')control(this,'connected',true);return result;};
  for(const method of ['onError','onClose']){const original=main[method];main[method]=function(...args){control(this,'disconnected');return original.apply(this,args);};}
  function publish(){for(const item of active)sample(item);if(process.connected&&process.send)process.send({type:'rp_diagnostics',...stats,active:active.size,time_ms:Date.now()},()=>{});}
  publish();setInterval(publish,15000).unref();process.once('beforeExit',publish);
} else {
const fs = require('fs');
const http = require('http');
const https = require('https');
const {spawn} = require('child_process');
const started = Date.now();
const identity = {service:'repocket',format:2,revision:12,group_id:process.env.SALAD_CONTAINER_GROUP_ID||'',machine:process.env.SALAD_MACHINE_ID || 'local',instance:process.env.SALAD_INSTANCE_ID || 'local',run:`${process.env.SALAD_INSTANCE_ID || 'local'}:${started}`,started_ms:started};
let sequence=0,diagnostics=null,deviceId='',lastPing=0;const logCounts={};
// Keep the legacy numeric floor field for readers, with zero meaning no traffic requirement.
const observation={window_ms:600000,min_target_bytes:0,traffic_reallocation:false,relay_idle_reallocation:false};
let history=[],lastDiagnosticAt=started,policy={...observation,state:'observing',observed_ms:0};
let child, phase='starting', reason='', ip='', failedSince=started, stopping=false, fatal=false;
const counters = () => ({rx:Number(fs.readFileSync('/sys/class/net/eth0/statistics/rx_bytes','utf8')),tx:Number(fs.readFileSync('/sys/class/net/eth0/statistics/tx_bytes','utf8'))});
const emit = (value,callback) => process.stdout.write('RP_MON '+JSON.stringify({...identity,seq:sequence++,...value})+'\n',callback);
const baseline=counters();let previous={...baseline,time_ms:started};
function tick() { const time_ms=Date.now(); emit({kind:'tick',time_ms,...counters(),phase,reason,ip,diagnostics,device_id:deviceId,last_ping_ms:lastPing,log_counts:logCounts,policy}); }
function minute(final=false) {
  const next={...counters(),time_ms:Date.now()}, elapsed_ms=next.time_ms-previous.time_ms;
  const valid=elapsed_ms>0&&next.rx>=previous.rx&&next.tx>=previous.tx;
  emit({kind:'minute',time_ms:next.time_ms,start_ms:previous.time_ms,end_ms:next.time_ms,rx_bytes:valid?next.rx-previous.rx:null,tx_bytes:valid?next.tx-previous.tx:null,total_rx:next.rx-baseline.rx,total_tx:next.tx-baseline.tx,elapsed_ms,valid,counter_error:valid?'':'Counter reset or nonpositive interval',partial:final||elapsed_ms<59000||elapsed_ms>61000,final,phase,reason,ip,diagnostics,device_id:deviceId,log_counts:logCounts,policy});
  previous=next;
}
function observeTraffic() {
  const d=diagnostics,now=d.time_ms;if(history.length&&history[0].client!==d.client_started_ms)history=[];
  const errors={...d.errors,...Object.fromEntries(Object.entries(logCounts).map(([name,n])=>['log '+name,n]))};
  const next={at:now,client:d.client_started_ms,bytes:d.rx_bytes+d.tx_bytes,replies:d.responses,failures:d.closed_failed_without_response,errors};
  history.push(next);while(history.length>1&&history[1].at<=now-observation.window_ms)history.shift();
  const first=history[0],elapsed=now-first.at,bytes=next.bytes-first.bytes,replies=next.replies-first.replies,failures=next.failures-first.failures,outcomes=replies+failures;
  const recentErrors=Object.fromEntries(Object.entries(errors).map(([name,n])=>[name,n-(first.errors[name]||0)]).filter(([,n])=>n>0));
  policy={...observation,state:elapsed<observation.window_ms?'observing':'keeping',checked_ms:now,observed_ms:elapsed,target_bytes:bytes,replies,failures,outcomes,errors:recentErrors};
}
function reallocate(why) {
  if(stopping)return;stopping=true;phase='reallocating';reason=why;policy={...policy,state:'reallocating',reason:why};minute(true);tick();
  if(child)child.kill('SIGTERM');
  const request_id=identity.run+':'+Date.now(),body=JSON.stringify({reason:'Repocket: '+why});
  function attempt(number){
    emit({kind:'recovery',time_ms:Date.now(),request_id,action:'requested',attempt:number,reason:why,ip});
    let finished=false;
    function done(status){if(finished)return;finished=true;const accepted=status===200||status===204;
      emit({kind:'recovery',time_ms:Date.now(),request_id,action:accepted?'accepted':'failed',attempt:number,reason:why,http_status:status,ip},()=>{if(accepted||number>=3)process.exit(75);else setTimeout(()=>attempt(number+1),number*2000);});
    }
    const request=http.request({host:'169.254.169.254',path:'/v1/reallocate',method:'POST',headers:{Metadata:'true','Content-Type':'application/json','Content-Length':Buffer.byteLength(body)},timeout:10000},response=>{response.resume();done(response.statusCode);});
    request.on('timeout',()=>{request.destroy();done(null);});request.on('error',()=>done(null));request.end(body);
  }
  attempt(1);setTimeout(()=>process.exit(75),40000);
}
function acceptLine(line, exited=false) {
  if(stopping||fatal)return;
  if(/^docker-[0-9a-f]{16}$/.test(line.trim()))deviceId=line.trim();
  if(!exited&&line.includes('MainSocket -> PING'))lastPing=Date.now();
  for(const label of ['onError: error when connecting to socket-server','MainSocket -> error','Peer monitor error','_markPeerAsAlive -> Error happened','Failed to get settings','Failed to create connection','Buffer size exceeds maximum allowed size','Record length exceeds maximum allowed size','Connection retries exceeded','Socket timeout','proxy timeout','ENOTFOUND','EAI_AGAIN','Unsupported SOCKS version','Unsupported method','not support'])if(line.includes(label))logCounts[label]=(logCounts[label]||0)+1;
  if(/invalid.?api.?key|invalid.?credential|login failed|auth\/user-not-found|auth\/wrong-password/i.test(line)||(phase==='starting'&&/unauthori[sz]ed/i.test(line))){fatal=true;phase='authorization_error';reason='Repocket rejected the credentials';if(child)child.kill('SIGTERM');return;}
  if(exited)return;
  if(/\bpeer connected\b/i.test(line)){phase='connected';reason='';failedSince=0;}
  else if(/peer disconnected|peer resetting|peer_server_error|refresh_token_required/i.test(line)){
    phase='reconnecting';reason=(line.match(/peer disconnected|peer resetting|peer_server_error|refresh_token_required/i)||['Peer connection error'])[0];if(!failedSince)failedSince=Date.now();
  }
  else if(phase!=='connected'&&/ECONN|ETIMEDOUT|ENOTFOUND/i.test(line))reason=(line.match(/ECONN\w+|ETIMEDOUT|ENOTFOUND/i)||['Connection error'])[0];
}
function launch() {
  if(stopping||fatal)return;
  phase='starting';reason='';failedSince=Date.now();diagnostics=null;deviceId='';lastPing=0;history=[];lastDiagnosticAt=Date.now();policy={...observation,state:'observing',observed_ms:0};
  let exited=false;const worker=spawn(process.execPath,['--require',__filename,'/app/dist/index.js'],{cwd:'/app',env:{...process.env,RP_DIAGNOSTICS:'1'},stdio:['ignore','pipe','pipe','ipc']});child=worker;
  worker.on('message',message=>{if(worker===child&&!exited&&!stopping&&!fatal&&message?.type==='rp_diagnostics'&&Number.isFinite(message.closed_failed_without_response)&&Date.now()-message.time_ms<45000){diagnostics=message;lastDiagnosticAt=Date.now();if(['starting','disconnected','rejected'].includes(message.control?.state)){if(phase!=='starting'||message.control.state!=='starting')phase='reconnecting';reason='Repocket relay '+message.control.state;if(!failedSince)failedSince=message.control.changed_ms||Date.now();}else if(message.control?.state==='connected'){phase='connected';reason='';failedSince=0;}observeTraffic();}});
  for(const stream of [worker.stdout,worker.stderr]) {let buffer='';stream.on('data',data=>{if(worker!==child)return;buffer+=data.toString();let at;while((at=buffer.indexOf('\n'))>=0){acceptLine(buffer.slice(0,at),exited);buffer=buffer.slice(at+1);}if(buffer.length>16384)buffer='';});}
  worker.on('error',()=>{if(worker===child&&!stopping&&!fatal)reallocate('Repocket process could not start');});
  worker.on('exit',()=>{exited=true;if(worker===child&&!stopping&&!fatal){phase='disconnected';reason='Repocket process exited';}});
  worker.on('close',()=>{if(worker!==child)return;child=null;if(!stopping&&!fatal)reallocate('Repocket process exited');});
}
function publicIP() {
  const req=https.get('https://api.ipify.org',{timeout:8000},response=>{let body='';response.on('data',data=>{if(body.length<64)body+=data;});response.on('end',()=>{if(/^\d{1,3}(\.\d{1,3}){3}$/.test(body.trim()))ip=body.trim();});});
  req.on('timeout',()=>req.destroy());req.on('error',()=>{});
}
function stop() {if(stopping)return;stopping=true;phase='stopped';minute(true);tick();if(child)child.kill('SIGTERM');setTimeout(()=>process.exit(0),1000);}
process.on('SIGTERM',stop);process.on('SIGINT',stop);
emit({kind:'start',time_ms:started,...counters(),phase,ip});launch();publicIP();
setInterval(()=>{if(!stopping)tick();},15000);
setInterval(()=>{if(!stopping&&!ip)publicIP();},30000);
function nextMinute(){setTimeout(()=>{if(!stopping){minute();nextMinute();}},60000-Date.now()%60000);}
nextMinute();
setInterval(()=>{
  if(stopping||fatal)return;
  if(phase==='connected'&&Date.now()-lastDiagnosticAt>=60000){reallocate('Repocket client diagnostics stopped for 60 seconds');return;}
  // A connected relay can be quiet while demand is low; activity age is telemetry only.
  if(failedSince&&Date.now()-failedSince>=60000)reallocate('Repocket control connection unavailable for 60 seconds');
},5000);

}
