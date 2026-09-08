import importlib.util
import json
import io
from urllib.error import HTTPError
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('provider', ROOT/'repocket-monitor/provider.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
REPORT = {'userId': 'report-user', 'bandwidth': {'own': {'bytes': 1048576, 'cents': '7.38'}}, 'centsCredited': 999999}


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.saved = {'mode': 'email_password', 'email': 'owner@example.test', 'password': 'SYNTHETIC_PASSWORD'}
        self.calls = []
        self.writes = []
        self.responses = []
        self.secret_patch = patch.object(p, 'secret', self.secret)
        self.request_patch = patch.object(p, 'request', self.request)
        self.expected_patch = patch.object(p, 'expected_email', lambda: 'owner@example.test')
        for item in (self.secret_patch, self.request_patch, self.expected_patch):item.start();self.addCleanup(item.stop)

    def secret(self, service=p.SERVICE, payload=None):
        if payload is None:return json.dumps(self.saved)
        self.saved=payload.copy();self.writes.append(payload.copy())

    def request(self, url, payload=None, headers=None, form=False):
        self.calls.append((url, payload, headers))
        if url == p.LOGIN:return {'idToken': 'ID_A', 'refreshToken': 'REFRESH_A', 'expiresIn': '3600'}
        if url == p.REFRESH:return {'id_token': 'ID_B', 'refresh_token': 'REFRESH_B', 'expires_in': '3600'}
        if url == p.LOOKUP:return {'users': [{'email': 'owner@example.test', 'localId': 'firebase-user'}]}
        if self.responses:
            result=self.responses.pop(0)
            if isinstance(result, Exception):raise result
            return result
        return REPORT

    def test_login_reuse_and_renewal(self):
        client=p.Client();self.assertEqual(client.fetch(),REPORT)
        self.assertNotIn('password',self.saved)
        self.assertEqual(self.saved['mode'],'refresh_token')
        client.fetch();self.assertEqual(sum(c[0]==p.LOGIN for c in self.calls),1)
        client.expires_ms=0;client.fetch()
        self.assertEqual(self.saved['refresh_token'],'REFRESH_B')
        self.assertEqual(self.calls[-1][2],{'auth-token':'ID_B','x-app-version':'web','device-os':'web'})

    def test_mismatched_account_never_attempts_password(self):
        self.saved['email']='wrong@example.test'
        with self.assertRaises(p.ProviderError):p.Client().fetch()
        self.assertEqual(self.calls,[]);self.assertEqual(self.writes,[])

    def test_renewed_account_must_match(self):
        self.saved={'mode':'refresh_token','refresh_token':'REFRESH_A','user_id':'another-user'}
        with self.assertRaises(p.ProviderError):p.Client().fetch()
        self.assertEqual(self.writes,[])
        self.assertFalse(any(c[0]==p.REPORT for c in self.calls))

    def test_one_auth_retry(self):
        self.responses=[p.ProviderError('rejected',401),p.ProviderError('rejected',403)]
        with self.assertRaises(p.ProviderError):p.Client().fetch()
        self.assertEqual(sum(c[0]==p.REPORT for c in self.calls),2)
        self.assertEqual(sum(c[0]==p.REFRESH for c in self.calls),1)

    def test_terminal_rejection_waits_for_changed_access(self):
        self.responses=[p.ProviderError('Account sign-in must be renewed',403,requires_login=True)]
        client=p.Client()
        for _ in range(3):
            with self.assertRaises(p.ProviderError):client.fetch()
        self.assertEqual(sum(c[0]==p.REPORT for c in self.calls),1)
        self.assertEqual(sum(c[0]==p.REFRESH for c in self.calls),0)
        self.saved['refresh_token']='NEW_USER_SUPPLIED_TOKEN'
        self.assertEqual(client.fetch(),REPORT)
        self.assertEqual(sum(c[0]==p.REFRESH for c in self.calls),1)

    def test_money_uses_bandwidth_cents_not_account_balance(self):
        result=p.reading(REPORT,'firebase-user',123)
        self.assertEqual(result['earned_text'],'$0.0738 · account total')
        self.assertEqual(result['traffic_text'],'1.00 MiB · account total')
        self.assertEqual(result['total_usd_cents'],'7.38')
        self.assertIsNone(result['provider_updated_ms'])
        self.assertNotIn('today_earned_text',result)

    def test_unknown_is_not_zero(self):
        for value in (None,True,'NaN','Infinity',-1):
            with self.subTest(value=value),self.assertRaises(p.ProviderError):p.number(value)
        self.assertEqual(p.number(0),0)
        with self.assertRaises(p.ProviderError):p.reading({'data':{'userId':'x'}},'u',123)

    def test_recorder_imports_verified_provider_fields(self):
        import sys
        sys.path.insert(0,str(ROOT))
        spec=importlib.util.spec_from_file_location('rp_observer_for_test',ROOT/'repocket-monitor/observe.py')
        observer=importlib.util.module_from_spec(spec);spec.loader.exec_module(observer)
        with tempfile.TemporaryDirectory(dir=ROOT) as directory,patch.object(p,'DATA',Path(directory)),patch.object(observer,'DATA',Path(directory)):
            p.save(Path(directory)/'provider.json',p.reading(REPORT,'firebase-user',1000))
            db=observer.database('fixture-group')
            result=observer.snapshot(db,{'id':'fixture-group','replicas':1},{'replicas':1},[],2000,{'inventory_ms':2000},{})
            self.assertEqual(result['provider']['earned_text'],'$0.0738 · account total')
            self.assertEqual(result['provider']['observed_ms'],1000)
            self.assertEqual(result['provider_record_count'],1)
            self.assertNotIn('auth_user_id',result['provider'])
            db.close()

    def test_unchanged_amount_retains_change_time(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory,patch.object(p,'DATA',Path(directory)):
            db=sqlite3.connect(':memory:');db.execute('CREATE TABLE readings(observed_ms INTEGER PRIMARY KEY,body TEXT)')
            p.record(db,p.reading(REPORT,'u',1000));p.record(db,p.reading(REPORT,'u',2000))
            output=json.loads((Path(directory)/'provider.json').read_text())
            self.assertEqual(output['observed_ms'],2000);self.assertEqual(output['last_changed_ms'],1000)
            self.assertEqual(db.execute('SELECT count(*) FROM readings').fetchone()[0],2)


class ReportTransportTests(unittest.TestCase):
    def test_live_report_shape_and_secret_free_transport(self):
        import subprocess
        with patch.object(p.subprocess,'run',return_value=subprocess.CompletedProcess([],0,json.dumps(REPORT)+'\n200','')) as call:
            value=p.request(p.REPORT,headers={'auth-token':'PRIVATE_TOKEN','x-app-version':'web','device-os':'web'})
        self.assertEqual(p.reading(value,'firebase-user',123)['total_usd_cents'],'7.38')
        self.assertNotIn('PRIVATE_TOKEN',' '.join(call.call_args.args[0]))
        self.assertIn('PRIVATE_TOKEN',call.call_args.kwargs['input'])
        self.assertNotIn('--location',call.call_args.args[0])
    def test_inactive_or_faked_report_is_rejected(self):
        for key in ('isFaked','isUserDeleted'):
            with self.assertRaises(p.ProviderError):p.reading({**REPORT,key:True},'u',123)


class SaladVerificationTests(unittest.TestCase):
    def test_salad_error_does_not_invalidate_repocket_access(self):
        import subprocess
        with patch.object(p,'secret',return_value='PRIVATE_SALAD_KEY'),patch.object(p.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'{"error":"banned"}\n403','')) as request:
            with self.assertRaises(p.ProviderError) as error:p.expected_email()
        self.assertFalse(error.exception.requires_login)
        self.assertNotIn('PRIVATE_SALAD_KEY',' '.join(request.call_args.args[0]))
        self.assertIn('PRIVATE_SALAD_KEY',request.call_args.kwargs['input'])


class HttpErrorTests(unittest.TestCase):
    def test_throttle_and_invalid_refresh_have_different_recovery(self):
        for code, terminal in [('TOO_MANY_ATTEMPTS_TRY_LATER',False),('INVALID_REFRESH_TOKEN',True),('USER_DISABLED',True)]:
            with self.subTest(code=code):
                error=HTTPError(p.REFRESH,400,'rejected',{},io.BytesIO(json.dumps({'error':{'message':code}}).encode()))
                class Opener:
                    def open(self,*args,**kwargs):raise error
                with patch.object(p,'build_opener',lambda *args:Opener()):
                    with self.assertRaises(p.ProviderError) as raised:p.request(p.REFRESH,{'refresh_token':'SYNTHETIC_SECRET'},form=True)
                self.assertEqual(raised.exception.requires_login,terminal)
                self.assertNotIn('SYNTHETIC_SECRET',str(raised.exception))


if __name__=='__main__':unittest.main()
