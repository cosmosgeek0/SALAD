#!/usr/bin/env python3
"""Initialize a fresh shared ledger without resetting any existing experiment."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
os.umask(0o077)
data=Path.home()/'.hg1';root=data/'fleet-tests';root.mkdir(parents=True,exist_ok=True)
current=root/'current.json'
if current.exists():raise SystemExit('Existing experiment preserved. Do not reset it to repair a display.')
provider=data/'hg-fleet/provider-latest.json'
hg=json.loads(provider.read_text()) if provider.exists() else {}
now=int(time.time()*1000);started=datetime.fromtimestamp(now/1000,timezone.utc).isoformat();ident=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
record=dict(id=ident,started_at=started,started_ms=now,status='measuring',phase='bandwidth-test',
    ps=dict(organization='hyperlane',project='default',group='ps-test-us',desired=10,baseline_provider_bytes=None),
    hg=dict(organization='deathadder',desired=10,version='0.6.6',baseline_provider_gathering_credits=hg.get('gathering_credits'),
        baseline_provider_observed_ms=hg.get('observed_ms'),baseline_started_ms=hg.get('observed_ms')),interventions=[])
current.write_text(json.dumps(record,indent=2)+'\n')
(root/'network-state.json').write_text(json.dumps(dict(experiment_id=ident,rx=0,tx=0,last={})))
print('Started new recording metadata '+ident+'; historical values were not invented.')
