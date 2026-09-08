#!/usr/bin/env python3
"""Bind fresh local ledgers to existing Salad groups; do not deploy containers."""
import argparse
from datetime import datetime, timezone
import getpass
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('rebuild_cloud',ROOT/'scripts/rebuild-cloud.py')
cloud=importlib.util.module_from_spec(spec);spec.loader.exec_module(cloud)
targets={'ps':('hyperlane','ps-test-us'),'pr':('ssh1','pr'),'rp':('ssh2','rp-test-us'),'rfm':('ssh3','earnfm-us'),'tm':('ssh4','tm-test-us')}
p=argparse.ArgumentParser(description=__doc__);p.add_argument('services',nargs='+',choices=targets);args=p.parse_args()
key=subprocess.check_output([str(ROOT/'.runtime/keychain-store'),'--read','--service','salad-bandwidth-api','--account',getpass.getuser()],text=True).strip()
os.umask(0o077);data=Path.home()/'.hg1'
for name in args.services:
 org,group=targets[name];g=cloud.api(key,org,'/projects/default/containers/'+group)
 now=int(time.time()*1000);started=datetime.fromtimestamp(now/1000,timezone.utc).isoformat()
 common=dict(organization=org,project='default',group=group,image=g['container']['image'])
 if name=='ps':
  path=data/'packetstream/observer-target.json';value=dict(mode='native-census',group_id=g['id'],**common)
 elif name=='pr':
  path=data/'proxyrack/deployment.json';value=dict(name=group,replicas=g['replicas'],group_id=g['id'],created_at=started,namespace=g['container']['environment_variables']['PR_NAMESPACE'],**common)
 elif name=='rp':
  path=data/'repocket/deployment.json';value=dict(id=g['id'],replicas=g['replicas'],version=g['version'],created_at=started,start_requested_at=started,**common)
 elif name=='rfm':
  path=data/'earnfm/target.json';value=dict(id=g['id'],desired=g['replicas'],version=g['version'],created_at=started,measurement_started_ms=now,**common)
 else:
  path=data/'traffmonetizer/deployment.json'
  if path.exists():raise SystemExit('Existing metadata preserved: '+str(path))
  sys.path.insert(0,str(ROOT/'traffmonetizer'))
  from observer import provider_reading
  baseline=provider_reading(dict(started_at=started,provider_baseline_usd=0,provider_baseline_bytes=0,provider_baseline_earned_usd=0))
  value=dict(group_id=g['id'],desired_replicas=g['replicas'],started_at=started,measurement_started_ms=now,
      provider_baseline_usd=baseline['balance_usd'],provider_baseline_bytes=baseline['credited_bytes'],
      provider_baseline_earned_usd=baseline['credited_usd'],**common)
 if path.exists():raise SystemExit('Existing metadata preserved: '+str(path))
 cloud.write(path,value);print(name+' bound to '+g['id']+'; new measurement baseline, not restored history.')
