"""Deployment guard tests using an in-memory Salad API; no live requests."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
import io

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('deploy',ROOT/'earnfm.py')
cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        (ROOT/'.work').mkdir(exist_ok=True);self.temp=tempfile.TemporaryDirectory(dir=ROOT/'.work')
        cli.DATA=Path(self.temp.name);self.calls=[];cli.key=lambda *a:'fixture-client-key'
        self.group={'id':'existing','version':9,'create_time':'2026-09-06T20:33:33Z','replicas':10,'country_codes':['gb'],
            'current_state':{'status':'running'},'container':{'image':cli.CONFIG['image'],'command':['old'],
            'environment_variables':{'EARNFM_TOKEN':'fixture-client-key','EARNFM_COUNTRY':'GB','KEEP':'unchanged'}}}
        (cli.DATA/'target.json').write_text(json.dumps({'id':'existing','measurement_started_ms':12345}))
        (cli.DATA/'provider-baseline.json').write_text('{"balance":0.1}')
        def api(path,method='GET',body=None,missing=False):
            self.calls.append((path,method,body))
            if path=='/log-entries':return {'items':[]}
            if method=='PATCH':self.group.update(copy.deepcopy(body));self.group['version']+=1;return {}
            return copy.deepcopy(self.group)
        cli.api=api

    def tearDown(self):self.temp.cleanup()

    def test_update_preserves_country_identity_baseline_and_environment(self):
        with redirect_stdout(io.StringIO()):cli.deploy(True)
        self.assertEqual(self.group['country_codes'],['gb']);self.assertEqual(self.group['replicas'],10)
        self.assertEqual(self.group['container']['environment_variables']['EARNFM_COUNTRY'],'GB')
        self.assertEqual(self.group['container']['environment_variables']['KEEP'],'unchanged')
        self.assertEqual(cli.source_bytes(self.group['container']['command']),(ROOT/'container/start.sh').read_bytes())
        target=json.loads((cli.DATA/'target.json').read_text());self.assertEqual(target['measurement_started_ms'],12345)
        self.assertEqual(target['id'],'existing');self.assertEqual((cli.DATA/'provider-baseline.json').read_text(),'{"balance":0.1}')

    def test_mismatched_country_refuses_mutation(self):
        self.group['container']['environment_variables']['EARNFM_COUNTRY']='US'
        with self.assertRaisesRegex(RuntimeError,'Placement'):cli.deploy(True)
        self.assertFalse(any(method=='PATCH' for _,method,_ in self.calls))

    def test_existing_cloud_credential_survives_missing_local_entry(self):
        cli.key=lambda *a: (_ for _ in ()).throw(RuntimeError('Entry unavailable'))
        with redirect_stdout(io.StringIO()):cli.deploy(True)
        self.assertEqual(self.group['container']['environment_variables']['EARNFM_TOKEN'],'fixture-client-key')

    def test_orphan_baseline_refuses_mutation(self):
        (cli.DATA/'target.json').unlink()
        with self.assertRaisesRegex(RuntimeError,'survives'):cli.deploy(True)
        self.assertFalse(any(method=='PATCH' for _,method,_ in self.calls))

    def test_concurrent_version_change_refuses_mutation(self):
        original=cli.api;reads=0
        def api(path,method='GET',body=None,**kwargs):
            nonlocal reads
            if path==cli.GROUP and method=='GET':
                reads+=1
                if reads>1:self.group['version']+=1
            return original(path,method,body,**kwargs)
        cli.api=api
        with self.assertRaisesRegex(RuntimeError,'changed during'):cli.deploy(True)
        self.assertFalse(any(method=='PATCH' for _,method,_ in self.calls))


if __name__=='__main__':unittest.main()
