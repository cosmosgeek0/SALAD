#!/usr/bin/env python3
"""Save an operator-supplied value to the configured credential helper."""
import argparse
import getpass
import sys
import warnings
from pathlib import Path
import subprocess
p=argparse.ArgumentParser(description=__doc__);p.add_argument('service');args=p.parse_args()
helper=Path(__file__).resolve().parents[1]/'.runtime/keychain-store'
if not sys.stdin.isatty() or not sys.stderr.isatty():
    raise SystemExit('Run in an interactive terminal; piped input is refused.')
with warnings.catch_warnings():
    warnings.simplefilter('error', getpass.GetPassWarning)
    try:
        secret=getpass.getpass('Value for '+args.service+' (hidden): ')
    except (getpass.GetPassWarning, EOFError, KeyboardInterrupt):
        raise SystemExit('Hidden input unavailable or cancelled; nothing saved.')
if not secret:raise SystemExit('Empty secret not saved')
subprocess.run([str(helper),'--service',args.service,'--account',getpass.getuser()],input=secret,text=True,check=True)
print('Saved '+args.service+'; value not printed.')
