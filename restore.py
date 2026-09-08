#!/usr/bin/env python3
"""Restore a verified source bundle into a fresh runtime directory."""
import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('packages', nargs='+', choices=('Honeygain', 'PacketStream', 'Website'))
parser.add_argument('--to', type=Path, default=Path.home() / 'Library/Application Support/Salad Bandwidth Dashboard')
args = parser.parse_args()
target_root = args.to.expanduser().resolve()
files = {}
for package in args.packages:
    source = ROOT / package / 'source'
    entries = (source / 'SHA256SUMS').read_text().splitlines()
    if not entries:
        raise SystemExit('Empty source manifest: ' + package)
    for entry in entries:
        digest, name = entry.split('  ', 1)
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise SystemExit('Unsafe source path: ' + name)
        raw = (source / relative).read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise SystemExit('Damaged source file: ' + package + '/' + name)
        if name in files and files[name] != raw:
            raise SystemExit('Conflicting shared source: ' + name)
        target = target_root / relative
        parent = target.parent
        while parent != target_root.parent:
            if parent.is_symlink() or parent.exists() and not parent.is_dir():
                raise SystemExit('Existing non-directory or symlink parent preserved: ' + str(parent))
            parent = parent.parent
        if target.is_symlink() or target.exists() and target.read_bytes() != raw:
            raise SystemExit('Existing different file or symlink preserved: ' + str(target))
        files[name] = raw
for name, raw in files.items():
    target = target_root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
print('Restored', len(files), 'verified source files to', target_root)
