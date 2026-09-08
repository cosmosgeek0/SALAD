#!/usr/bin/env python3
"""Save numbers the operator has just read on the signed-in Repocket dashboard."""
import argparse
import json
import os
from pathlib import Path
import re
import time
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--traffic',help='Exact displayed provider-day traffic including unit')
p.add_argument('--earned',help='Exact displayed provider-day earned amount including currency')
args=p.parse_args();os.umask(0o077)
traffic=args.traffic or input('Provider-day traffic exactly as displayed, with unit: ').strip()
earned=args.earned or input('Provider-day earnings exactly as displayed, with currency: ').strip()
if not all(re.search(r'\d',x) for x in (traffic,earned)):raise SystemExit('Read the real numeric values first; placeholders were not saved.')
root=Path.home()/'.hg1/repocket';root.mkdir(parents=True,exist_ok=True)
value=dict(observed_ms=int(time.time()*1000),today_traffic_text=traffic,today_earned_text=earned,source='Fresh operator reading of the Repocket provider-day account dashboard')
temporary=root/'provider.tmp';temporary.write_text(json.dumps(value));temporary.replace(root/'provider.json')
print('Saved actual provider reading; it will become stale normally until refreshed.')
