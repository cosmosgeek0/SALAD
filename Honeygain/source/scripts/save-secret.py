#!/usr/bin/env python3
"""Save an operator-supplied value to the existing macOS Keychain helper."""
import argparse
import getpass
from pathlib import Path
import subprocess
p=argparse.ArgumentParser(description=__doc__);p.add_argument('service');args=p.parse_args()
helper=Path(__file__).resolve().parents[1]/'.runtime/keychain-store'
secret=getpass.getpass('Value for '+args.service+' (hidden): ')
if not secret:raise SystemExit('Empty secret not saved')
subprocess.run([str(helper),'--service',args.service,'--account',getpass.getuser()],input=secret,text=True,check=True)
print('Saved '+args.service+'; value not printed.')
