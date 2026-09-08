"""Provider figures must survive dashboard normalization with their actual scope."""
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'Website/source'))
spec=importlib.util.spec_from_file_location('earnfm_dashboard',os.environ.get('EARNFM_SERVER_SOURCE',str(ROOT.parent/'Website/source/dashboard/server.py')))
server=importlib.util.module_from_spec(spec);spec.loader.exec_module(server)


class DashboardTests(unittest.TestCase):
    def test_balance_changes_include_decreases_without_inventing_gross_earnings(self):
        (ROOT/'.work').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'.work') as directory:
            root=Path(directory);(root/'earnfm').mkdir()
            readings=[{'observed_ms':1000,'gb':1,'balance':.10,'baseline_ms':1},
                      {'observed_ms':2000,'gb':1.1,'balance':.11,'baseline_ms':1},
                      {'observed_ms':3000,'gb':1.2,'balance':.06,'baseline_ms':1}]
            with sqlite3.connect(root/'earnfm/traffic.sqlite3') as db:
                db.execute('CREATE TABLE provider_history (observed_ms INTEGER,body TEXT)')
                db.executemany('INSERT INTO provider_history VALUES (?,?)',[(r['observed_ms'],json.dumps(r))for r in readings])
            result=server.provider_changes('earnfm',root,{})
            self.assertEqual([r['credited_mb']for r in result],[100,100])
            self.assertEqual([r['balance_change_usd']for r in result],[.01,-.05])
            self.assertTrue(all(r['earned_usd']is None for r in result))
            view={'provider':dict(readings[-1],earned=-.04,credited_mb=200,error=None)}
            metrics=server.provider_metrics('earnfm',view,root,lambda p:{},3000)
            self.assertEqual(metrics['balance_usd'],.06)
            self.assertEqual(metrics['balance_change_usd'],-.04)
            self.assertIsNone(metrics['earned_usd'])


if __name__=='__main__':unittest.main()
