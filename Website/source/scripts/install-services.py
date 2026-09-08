#!/usr/bin/env python3
"""Install only explicitly named local observers; never alter Salad workloads."""
import argparse
import os
from pathlib import Path
import plistlib
import subprocess
root=Path(__file__).resolve().parents[1];data=Path.home()/'.hg1';agents=Path.home()/'Library/LaunchAgents'
jobs={
 'dashboard':('com.cosmosgeek.salad-bandwidth-dashboard',['-m','dashboard.server','--port','8787','--data-dir',str(data),'--no-poll'],'dashboard'),
 'hg-provider':('com.cosmosgeek.salad-hg-provider-observer',[str(root/'scripts/hg-provider-observer.py'),'--interval','60'],'hg-fleet/provider-observer'),
 'hg-fleet':('com.cosmosgeek.salad-hg-fleet-observer',[str(root/'scripts/hg-fleet-observer.py'),'--interval','60'],'hg-fleet/observer'),
 'fleet':('com.cosmosgeek.salad-fleet-test-recorder',[str(root/'fleet-test-recorder.py'),'run'],'fleet-tests/recorder'),
 'ps':('com.cosmosgeek.ps1-recorder',['-B',str(root/'ps1-native-recorder.py')],'packetstream/native-recorder'),
 'pr':('com.cosmosgeek.proxyrack-recorder',['-B',str(root/'proxyrack.py'),'observe'],'proxyrack/observer'),
 'rp':('com.cosmosgeek.repocket-recorder',['-B',str(root/'repocket-monitor/observe.py')],'repocket/observer'),
 'rfm':('com.cosmosgeek.earnfm-recorder',['-B',str(root/'scripts/earnfm-recorder.py')],'earnfm/recorder'),
 'tm':('com.cosmosgeek.tm-observer',['-B',str(root/'traffmonetizer/observer.py')],'traffmonetizer/observer'),
 'pawns':('com.cosmosgeek.pawns-observer',['-B',str(root/'pawns/observe.py')],'pawns/observer'),
 'earnapp':('com.cosmosgeek.earnapp-recorder',['-B',str(root/'scripts/earnapp-recorder.py')],'earnapp/recorder'),
 'grass':('com.cosmosgeek.grass-recorder',['-B',str(root/'scripts/grass-recorder.py')],'grass/recorder')}
p=argparse.ArgumentParser(description=__doc__);p.add_argument('services',nargs='+',choices=jobs);p.add_argument('--write-only',action='store_true');args=p.parse_args()
env=dict(PYTHONPATH=str(root),PYTHONDONTWRITEBYTECODE='1',HG_FLEET_DIR=str(data/'hg-fleet'),HG_KEYCHAIN_HELPER=str(root/'.runtime/keychain-store'),PS_ORGANIZATION='hyperlane',PS_PROJECT='default',PS_GROUP='ps-test-us',EARNAPP_DATA_DIR=str(data/'earnapp'))
os.umask(0o077);agents.mkdir(parents=True,exist_ok=True)
for name in args.services:
 label,arguments,logs=jobs[name]
 for value in arguments:
  if value.endswith('.py') and not Path(value).exists():raise SystemExit('Missing embedded source: '+value)
 (data/logs).parent.mkdir(parents=True,exist_ok=True)
 document=dict(Label=label,ProgramArguments=['/usr/bin/python3',*arguments],WorkingDirectory=str(root),EnvironmentVariables=env,
     KeepAlive=True,RunAtLoad=True,ThrottleInterval=15,StandardOutPath=str(data/(logs+'.out.log')),StandardErrorPath=str(data/(logs+'.err.log')))
 path=agents/(label+'.plist');path.write_bytes(plistlib.dumps(document));path.chmod(0o600)
 if not args.write_only:
  domain='gui/'+str(os.getuid())
  subprocess.run(['launchctl','bootout',domain+'/'+label],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  subprocess.run(['launchctl','bootstrap',domain,str(path)],check=True)
 print(('Wrote ' if args.write_only else 'Started ')+label)
