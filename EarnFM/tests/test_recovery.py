from pathlib import Path
import concurrent.futures,subprocess,time,json,sys
root=Path(__file__).resolve().parent.parent;work=root/'.work/container-tests';work.mkdir(parents=True,exist_ok=True)
for program in ('test-server','test-client'):
 subprocess.run(['docker','run','--rm','--network','none','-v',str(root/'tests/fixtures')+':/src:ro','-v',str(root/'.work')+':/out','-w','/src','-e','GOOS=linux','-e','GOARCH=amd64','-e','CGO_ENABLED=0','golang:1.24-bookworm','go','build','-o','/out/'+program,program+'.go'],check=True)
source=(root/'container/start.sh').read_text();image='earnfm/earnfm-client@sha256:99a9feaa3dfab9e858012994fa1f922523f41b098e6b1cd9c9e9fca9286c3843';identity='11111111-1111-1111-1111-111111111111'
def check(case):
 d=work/case;d.mkdir(exist_ok=True);(d/'bin').mkdir(exist_ok=True)
 for name in ('actions','starts','output'):
  (d/name).unlink(missing_ok=True)
 # Only time and the interface fixture boundary differ; /proc socket ownership is real.
 s=source.replace('monotonic() { read -r ef_up ef_rest < /proc/uptime; printf \'%s\\n\' "${ef_up%%.*}"; }','monotonic() { n=$(date +%s); printf \'%s\\n\' "$((100000+(n-EF_TEST_EPOCH)*20))"; }').replace('/sys/class/net/eth0/','/sys/class/net/lo/').replace('/app/main','/fixture/client.sh')
 (d/'start.sh').write_text(s)
 if case=='missing_counter': (d/'start.sh').write_text(s.replace('/sys/class/net/lo/','/sys/class/net/missing-test-interface/'))
 if case=='auth_buffer': (d/'start.sh').write_text(s.replace('ef_until=$1;','ef_until=$(( $(date +%s)+1 ));').replace('sleep 10 & wait $!','sleep 1 & wait $!'))
 (d/'bin/wget').write_text('''#!/bin/sh
case "$*" in
 *ipinfo.io*) c=US; case "$EF_CASE" in foreign|uk) c=GB ;; esac; printf '{"ip":"192.0.2.1","country":"%s"}\\n' "$c" ;;
 *api.db-ip.com*) c=US; case "$EF_CASE" in foreign|uk) c=GB ;; esac; printf '{"countryCode":"%s"}\\n' "$c" ;;
 *169.254.169.254*) echo requested >> /fixture/actions; if [ "$EF_CASE" = imds_failure ]; then echo 'HTTP/1.1 503 Service Unavailable' >&2; exit 1; fi; echo 'HTTP/1.1 204 No Content' >&2 ;;
 *) exit 1 ;;
esac
''')
 (d/'client.sh').write_text('''#!/bin/sh
echo start >> /fixture/starts
case "$EF_CASE" in
 rate) echo "WebSocket dial to socket-prod.earn.fm failed: HTTP 429"; sleep 3600 ;;
 auth) echo 'WebSocket handshake rejected by socket-prod.earn.fm: HTTP 401 — not retrying other IPs'; exit 1 ;;
 auth_buffer) if [ "$(wc -l < /fixture/starts)" -eq 1 ]; then
   echo 'WebSocket handshake rejected by primary: HTTP 401 — not retrying other IPs'
   echo 'WebSocket handshake rejected by secondary: HTTP 401 — not retrying other IPs'; exit 1
  fi
  [ -p /fixture/input ] || mkfifo /fixture/input; exec 8<>/fixture/input; exec nc 127.0.0.1 8443 <&8 ;;
 forbidden) echo 'WebSocket handshake rejected by socket-prod.earn.fm: HTTP 403 — not retrying other IPs'; exit 1 ;;
 ip_change) echo 'IP change detected with different location'; sleep 3600 ;;
 flap|startup_burst) exec /checktools/test-client ;;
 exit|imds_failure) echo "exit token=$EARNFM_TOKEN"; exit 7 ;;
 error) while :; do echo 'WebSocket DNS lookup failed for socket-prod.earn.fm: timeout'; sleep 1; done ;;
 connected|activity|uk|missing_counter) [ -p /fixture/input ] || mkfifo /fixture/input; exec 8<>/fixture/input; exec nc 127.0.0.1 8443 <&8 ;;
 *) sleep 3600 ;;
esac
''')
 for p in [d/'bin/wget',d/'client.sh']:p.chmod(0o755)
 name='earnfm-check-'+case
 before=''
 if case in ('connected','activity','uk','missing_counter','flap','auth_buffer','startup_burst'):
  before='/checktools/test-server > /dev/null 2>&1 & '
 args=['docker','run','--rm','--name',name,'--platform','linux/amd64','--network','none','-v',str(d)+':/fixture','-v',str(root/'.work')+':/checktools:ro','-e','PATH=/fixture/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','-e','EARNFM_TOKEN=fixture-secret','-e','EF_CASE='+case,'-e','EF_TEST_EPOCH='+str(int(time.time())),'-e','SALAD_INSTANCE_ID='+identity,'-e','SALAD_MACHINE_ID='+identity,'-e','EARNFM_ACTIVITY_SECONDS='+('60'if case in ('activity','missing_counter','startup_burst')else'900')]
 if case=='hold':args+=['-e','EARNFM_COOLDOWNS='+identity+':'+str(int(time.time())+86400)]
 if case=='uk':args+=['-e','EARNFM_COUNTRY=GB']
 args+=['--entrypoint','/bin/sh',image,'-c',before+'exec /bin/sh /fixture/start.sh']
 p=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 stops=('connected','rate','hold','uk','auth','forbidden','ip_change','missing_counter','flap','auth_buffer','activity','startup_burst')
 if case in stops:
  time.sleep(18 if case in ('activity','startup_burst') else 9 if case=='flap' else 5);subprocess.run(['docker','kill','--signal','TERM',name],capture_output=True)
 try:out=p.communicate(timeout=35)[0]
 except subprocess.TimeoutExpired:
  subprocess.run(['docker','kill',name],capture_output=True);out=p.communicate()[0];(d/'output').write_text(out);raise
 (d/'output').write_text(out);records=[json.loads(line)for line in out.splitlines()if line.startswith('{')];events=[r for r in records if r['kind']=='earnfm_event'];samples=[r for r in records if r['kind']=='earnfm_sample'];assert 'fixture-secret'not in out
 expected=0 if case in stops else 75;assert p.returncode==expected,(case,p.returncode,out[-3000:]);assert case=='missing_counter' or any(r['final']==1 for r in samples),(case,'missing final')
 actions=[e['action']for e in events]
 if case in ('rate','hold','ip_change'):assert 'reallocate_requested'not in actions and any(s['state']=='rate_limited'for s in samples)
 if case in ('auth','forbidden'):assert 'reallocate_requested' not in actions and any(s['state']==('authorization_error' if case=='auth' else 'provider_rejected') for s in samples)
 if case in ('connected','uk','flap'):assert any(s['control_sockets']>0 and s['state']=='running'for s in samples),(case,out);assert 'reallocate_requested'not in actions
 if case=='missing_counter':assert 'observer_error' in actions and 'reallocate_requested'not in actions
 if case=='auth_buffer':assert actions.count('cooldown_started')==1 and actions.count('client_started')==2 and any(s['state']=='running'for s in samples),(case,out)
 if case=='silent':assert any(e['reason']=='control_offline'and e['action']=='reallocate_requested'for e in events)
 if case=='error':assert any(e['reason']=='connection_failure'and e['action']=='reallocate_requested'for e in events)
 if case in ('activity','startup_burst'):
  assert actions.count('client_started')==1 and 'client_restart' not in actions and 'reallocate_requested' not in actions,(case,out)
  assert any(s['state']=='running' and s['activity_min_bytes']==0 for s in samples),(case,out)
 if case=='startup_burst':assert max(s['total_rx']+s['total_tx'] for s in samples)>4000000
 if case=='foreign':assert not(d/'starts').exists() and any(e['reason']=='foreign_egress'for e in events)
 if case=='imds_failure':assert actions.count('reallocate_failed')==3
 return {'case':case,'exit':p.returncode,'samples':len(samples),'events':actions,'passed':True}
cases=['connected','silent','error','rate','hold','activity','foreign','exit','imds_failure','auth','forbidden','ip_change','uk','missing_counter','flap','auth_buffer','startup_burst'];results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=3)as pool:
 for result in pool.map(check,sys.argv[1:] or cases):results.append(result);print(json.dumps(result),flush=True)
(root/'.work/container-tests.json').write_text(json.dumps(results,indent=2))
