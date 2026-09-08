#!/usr/bin/env python3
"""Record Honeygain provider credits through its official dashboard API."""
import argparse
from decimal import Decimal
import fcntl
import importlib.util
import json
from pathlib import Path
import subprocess
import time

spec = importlib.util.spec_from_file_location('hg_fleet_control', Path(__file__).with_name('hg-fleet-control.py'))
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


class HoneygainProvider:
    def __init__(self):
        fleet = control.Fleet()
        source = fleet.api('deathadder', '/projects/default/containers/hg1')['container']['environment_variables']
        self.credentials = {'email': source['HONEYGAIN_EMAIL'], 'password': source['HONEYGAIN_PASSWORD']}
        self.token = None

    def request(self, path, method='GET', payload=None, authenticate=True):
        if path not in ('/api/v1/users/tokens', '/api/v2/devices', '/api/v1/earnings/stats', '/api/v1/users/balances'):
            raise RuntimeError('Unrecognized Honeygain endpoint')
        config = 'header = ' + json.dumps('Content-Type: application/json') + '\n'
        config += 'header = ' + json.dumps('Accept: application/json') + '\n'
        if authenticate:
            if not self.token:
                self.login()
            config += 'header = ' + json.dumps('Authorization: Bearer ' + self.token) + '\n'
        if payload is not None:
            config += 'data-binary = ' + json.dumps(json.dumps(payload)) + '\n'
        result = subprocess.run(['curl', '--silent', '--show-error', '--max-time', '20', '--config', '-',
            '--request', method, '--write-out', '\n%{http_code}', 'https://dashboard.honeygain.com' + path],
            input=config, capture_output=True, text=True, timeout=25)
        if result.returncode:
            raise RuntimeError('Honeygain request transport failed')
        raw, status = result.stdout.rsplit('\n', 1)
        if int(status) == 401 and authenticate:
            self.token = None
        if not 200 <= int(status) < 300:
            raise RuntimeError('Honeygain ' + path + ' returned HTTP ' + status)
        return json.loads(raw)

    def login(self):
        data = self.request('/api/v1/users/tokens', 'POST', self.credentials, authenticate=False)
        token = data.get('data', {}).get('access_token')
        if not isinstance(token, str) or not token:
            raise RuntimeError('Honeygain login returned no usable session')
        self.token = token

    def fetch(self):
        return (self.request('/api/v2/devices'), self.request('/api/v1/earnings/stats'),
                self.request('/api/v1/users/balances'))


def build_reading(devices, stats, balances, observed_ms):
    rows = devices['data']
    by_name = {row.get('model'): row for row in rows if row.get('model') in control.DEVICES}
    if len(by_name) != 10 or sum(row.get('model') in control.DEVICES for row in rows) != 10:
        raise RuntimeError('Provider did not return exactly the ten registered fleet devices')
    gathering = sum((Decimal(str(day['gathering']['credits'])) for day in stats.values()), Decimal(0))
    return {'observed_ms': observed_ms, 'gathering_credits': float(gathering),
            'gathering_traffic_bytes': sum(day['gathering']['traffic'] for day in stats.values()),
            'report_dates': sorted(stats),
            'account_balance_credits': balances['data']['payout']['credits'],
            'source': 'Honeygain official dashboard API',
            'devices': [{'device': name, 'credits': by_name[name]['stats']['total_credits'],
                         'ip': by_name[name].get('ip'), 'provider_active': by_name[name]['status'] == 'active'}
                        for name in control.DEVICES]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inspect-schema', action='store_true')
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--interval', type=int, default=60)
    args = parser.parse_args()
    if args.inspect_schema:
        devices, stats, balances = HoneygainProvider().fetch()
        rows = devices.get('data', [])
        day = stats[sorted(stats)[-1]]
        print(json.dumps({'device_count': len(rows), 'device_title': rows[0].get('title') if rows else None,
            'device_identity_fields': [{k: row.get(k) for k in ('manufacturer', 'model', 'title')} for row in rows],
            'device_status': rows[0].get('status') if rows else None,
            'device_stats': rows[0].get('stats') if rows else None,
            'day_stats': day, 'balances': balances.get('data')}, indent=2))
        return
    control.RUNTIME.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock = (control.RUNTIME / 'provider-observer.lock').open('a')
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('A Honeygain provider observer is already running')
    provider = None
    failures = 0
    while True:
        started = time.monotonic()
        try:
            if provider is None:
                provider = HoneygainProvider()
            devices, stats, balances = provider.fetch()
            observed_ms = int(time.time()*1000)
            result = control.record_provider(build_reading(devices, stats, balances, observed_ms))
            # Retain only the provider's traffic/credit measurements, never auth responses.
            control.Fleet.write('provider-api-traffic-latest.json', {
                'observed_ms': observed_ms, 'source': 'Honeygain official dashboard API',
                'account_balance_credits': balances['data']['payout']['credits'],
                'account_balance_observed_ms': observed_ms,
                'days': {date: {'gathering_credits': day['gathering']['credits'],
                                'gathering_traffic_bytes': day['gathering']['traffic']}
                         for date, day in stats.items()},
                'devices': [{'device': row['model'], 'total_traffic_bytes': row['stats']['total_traffic'],
                             'total_credits': row['stats']['total_credits']}
                            for row in devices['data'] if row.get('model') in control.DEVICES]})
            control.Fleet.write('provider-feed-status.json', {'checked_at': control.now(),
                'observed_ms': observed_ms, 'state': 'ok', 'interval_seconds': max(60, args.interval),
                'authentication_storage': 'process memory only'})
            print(json.dumps(result), flush=True)
            failures = 0
        except Exception as error:
            failures += 1
            message = str(error) if isinstance(error, RuntimeError) else type(error).__name__
            control.Fleet.write('provider-feed-status.json', {'checked_at': control.now(),
                'state': 'error', 'error': message, 'consecutive_failures': failures})
            print(json.dumps({'state': 'error', 'error': message}), flush=True)
            if args.once:
                raise SystemExit(1)
        if args.once:
            return
        interval = min(1800, max(60, args.interval) * (2 ** min(failures, 5)))
        time.sleep(max(1, interval - (time.monotonic()-started)))


if __name__ == '__main__':
    main()
