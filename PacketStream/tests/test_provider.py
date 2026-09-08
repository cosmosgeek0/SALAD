import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

MODULE = Path(__file__).resolve().parents[1] / 'source/packetstream-monitor/provider.py'
spec = importlib.util.spec_from_file_location('ps_provider', MODULE)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
NOW = 1788804000000


def html(rows=None, balance='1.18', referral='8ExP'):
    if rows is None:
        rows = [{'bandwidth': {'up': 120, 'down': 340}, 'cid': 17, 'timestamp': '2026-09-07T00:00:00Z'}]
    encoded = json.dumps(json.dumps({'customer': [], 'exitnode': rows}))
    return ('<input id="referral-link" value="https://packetstream.io/?psr=' + referral + '">'
            '<div class="card metric-card metric-card-balance"><h2 class="metric-title">Balance</h2>'
            '<p class="card-subtitle mb-4 text-muted">Available Funds</p>'
            '<h2 class="default-font fw-600">$' + balance + '</h2></div>'
            '<script>const rd = ' + encoded + '; window.reportData = JSON.parse(rd);</script>')


def access(cookie='example-private-cookie', expiry=2000000000):
    return {'mode': 'browser_cookie', 'auth_cookie': cookie, 'expires_at': expiry}


class ParserTests(unittest.TestCase):
    def test_observed_contract(self):
        result = p.reading(html(), NOW)
        self.assertEqual(result['balance_usd'], 1.18)
        self.assertEqual(result['rolling_bytes'], 460)
        self.assertEqual(result['days'], [{'date': '2026-09-07', 'up': 120, 'down': 340}])
        self.assertIsNone(result['provider_updated_ms'])
        self.assertNotIn('cid', json.dumps(result))

    def test_zero_is_valid(self):
        self.assertEqual(p.reading(html([], '0.00'), NOW)['rolling_bytes'], 0)
        self.assertEqual(p.reading(html([], '0.00'), NOW)['balance_usd'], 0)

    def test_missing_fields_are_unknown_not_zero(self):
        for value in (html().replace('metric-card-balance', 'other-card'),
                      html().replace('window.reportData', 'window.otherData'),
                      html().replace('Available Funds', 'Other value')):
            with self.subTest(value=value):
                with self.assertRaises(p.ProviderError):
                    p.reading(value, NOW)

    def test_wrong_account_requires_login(self):
        for value in (html(referral='different'), html().replace('packetstream.io/?', 'packetstream.io.evil/?')):
            with self.assertRaises(p.ProviderError) as error:
                p.reading(value, NOW)
            self.assertTrue(error.exception.requires_login)

    def test_format_and_numbers_fail_closed(self):
        for rows in (None, {}, [{'bandwidth': {'up': True, 'down': 0}, 'timestamp': '2026-09-07T00:00:00Z'}],
                     [{'bandwidth': {'up': -1, 'down': 0}, 'timestamp': '2026-09-07T00:00:00Z'}],
                     [{'bandwidth': {'up': 1.5, 'down': 0}, 'timestamp': '2026-09-07T00:00:00Z'}],
                     [{'bandwidth': {'up': 1, 'down': 0}, 'timestamp': '2026-09-07T12:00:00Z'}]):
            value = html(rows) if rows is not None else html().replace('const rd = ', 'const changed = ')
            with self.subTest(rows=rows), self.assertRaises(p.ProviderError):
                p.reading(value, NOW)

    def test_dated_records_survive_rolling_expiry_without_earnings_delta(self):
        rows = [{'bandwidth': {'up': 2, 'down': 3}, 'timestamp': '2026-09-06T00:00:00Z'},
                {'bandwidth': {'up': 100, 'down': 200}, 'timestamp': '2026-09-07T00:00:00Z'}]
        first = p.reading(html(rows), NOW)
        second = p.reading(html(rows[1:], '0.18'), NOW + 60000)
        self.assertEqual(len(first['days']), 2)
        self.assertEqual(second['rolling_bytes'], 300)
        self.assertEqual(second['balance_usd'], .18)
        self.assertFalse(any('earning' in key or 'delta' in key for key in second))

    def test_same_date_rows_are_aggregated(self):
        rows = [{'bandwidth': {'up': 2, 'down': 3}, 'timestamp': '2026-09-07T00:00:00Z'},
                {'bandwidth': {'up': 100, 'down': 200}, 'timestamp': '2026-09-07T00:00:00Z'}]
        self.assertEqual(p.reading(html(rows), NOW)['days'], [{'date': '2026-09-07', 'up': 102, 'down': 203}])


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.db = p.database(':memory:')
        self.client = p.Client(self.db)

    def tearDown(self):
        self.db.close()

    def test_expired_session_never_requests(self):
        with patch.object(p, 'secret', return_value=json.dumps(access(expiry=1))), patch.object(p, 'request') as req:
            for client in (self.client, p.Client(self.db)):
                with self.assertRaises(p.ProviderError):
                    client.fetch()
            req.assert_not_called()

    def test_rejected_session_stays_blocked_across_restart_until_changed(self):
        stored = json.dumps(access())
        with patch.object(p, 'secret', side_effect=lambda **kwargs: stored), patch.object(p, 'request', side_effect=p.ProviderError('Sign-in rejected', requires_login=True)) as req:
            for client in (self.client, p.Client(self.db)):
                with self.assertRaises(p.ProviderError):
                    client.fetch()
            self.assertEqual(req.call_count, 1)
            stored = json.dumps(access('new-private-cookie'))
            with self.assertRaises(p.ProviderError):
                self.client.fetch()
            self.assertEqual(req.call_count, 2)

    def test_valid_session_and_renewal(self):
        with patch.object(p, 'secret', return_value=json.dumps(access())) as keychain, patch.object(p, 'request', return_value=(html(), ['auth=renewed-private-cookie; Path=/; Max-Age=3600; Secure; HttpOnly'])):
            value = self.client.fetch()
            self.assertEqual(value['rolling_bytes'], 460)
            saved = keychain.call_args.kwargs['payload']
            self.assertEqual(saved['auth_cookie'], 'renewed-private-cookie')
            self.assertNotIn('private-cookie', json.dumps(value))

    def test_renewal_survives_temporarily_missing_report(self):
        with patch.object(p,'secret',return_value=json.dumps(access())) as keychain, patch.object(p,'request',return_value=('<html>Temporarily unavailable</html>',['auth=renewed-private-cookie; Path=/; Max-Age=3600'])):
            with self.assertRaises(p.ProviderError) as result:p.Client(self.db).fetch()
            self.assertFalse(result.exception.requires_login)
            self.assertEqual(keychain.call_args.kwargs['payload']['auth_cookie'],'renewed-private-cookie')
            self.assertEqual(self.db.execute('SELECT count(*) FROM blocked_access').fetchone()[0],0)

    def test_bad_cookie_cannot_inject_headers(self):
        for cookie in ('x\r\nother: bad', 'x; second=other', '', '"quoted"'):
            with self.assertRaises(p.ProviderError):
                p.access_value(json.dumps(access(cookie)))

    def test_renewal_rejects_wrong_scope_or_expiry(self):
        for header in ('auth=x; Domain=evil.example', 'auth=x; Max-Age=0', 'auth=; Expires=Thu, 01 Jan 1970 00:00:00 GMT'):
            with self.assertRaises(p.ProviderError):
                p.renewed_access(access(), [header], NOW / 1000)


class TransportTests(unittest.TestCase):
    def test_throttle_uses_bounded_retry_without_body(self):
        error = HTTPError(p.REPORT, 429, 'unused', {'Retry-After': '180'}, io.BytesIO(b'secret response'))
        with patch.object(p, 'build_opener') as opener:
            opener.return_value.open.side_effect = error
            with self.assertRaises(p.ProviderError) as result:
                p.request('private-cookie')
        self.assertEqual(result.exception.retry_after, 180)
        self.assertNotIn('secret', str(result.exception))
        self.assertFalse(result.exception.requires_login)

    def test_redirect_or_rejection_requires_login(self):
        for status in (302, 401, 403):
            with patch.object(p, 'build_opener') as opener:
                opener.return_value.open.side_effect = HTTPError(p.REPORT, status, '', {'Location': 'https://unrelated.example'}, None)
                with self.assertRaises(p.ProviderError) as result:
                    p.request('private-cookie')
                self.assertTrue(result.exception.requires_login)
        self.assertIsNone(p.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://unrelated.example'))

    def test_transport_errors_are_sanitized(self):
        with patch.object(p, 'build_opener') as opener:
            opener.return_value.open.side_effect = URLError('private-cookie')
            with self.assertRaises(p.ProviderError) as result:
                p.request('private-cookie')
            self.assertNotIn('private-cookie', str(result.exception))


class JournalTests(unittest.TestCase):
    def test_failed_check_preserves_snapshot_and_history(self):
        root = Path(__file__).resolve().parents[1] / '.work'
        root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            data = Path(directory)
            db = p.database(data / 'provider.sqlite3')
            client = unittest.mock.Mock()
            client.fetch.return_value = p.reading(html(), NOW)
            status, _ = p.collect(client, db, data)
            self.assertEqual(status['state'], 'ok')
            client.fetch.side_effect = RuntimeError('credential-must-never-appear')
            status, _ = p.collect(client, db, data)
            value = json.loads((data / 'provider.json').read_text())
            self.assertEqual(value['observed_ms'], NOW)
            self.assertEqual(value['balance_usd'], 1.18)
            self.assertEqual(value['rolling_bytes'], 460)
            self.assertEqual(db.execute('SELECT count(*) FROM readings').fetchone()[0], 1)
            self.assertEqual(status['state'], 'error')
            self.assertNotIn('credential-must-never-appear', json.dumps(status))
            self.assertNotIn('credential-must-never-appear', json.dumps(value))
            db.close()

    def test_first_failure_is_unknown_not_zero(self):
        root = Path(__file__).resolve().parents[1] / '.work'
        root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            data = Path(directory)
            db = p.database(data / 'provider.sqlite3')
            client = unittest.mock.Mock()
            client.fetch.side_effect = p.ProviderError('Access missing')
            p.collect(client, db, data)
            value = json.loads((data / 'provider.json').read_text())
            self.assertIsNone(value['observed_ms'])
            self.assertIsNone(value['balance_usd'])
            self.assertIsNone(value['rolling_bytes'])
            db.close()


if __name__ == '__main__':
    unittest.main()
