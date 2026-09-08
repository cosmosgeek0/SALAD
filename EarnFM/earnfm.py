#!/usr/bin/env python3
"""EarnFM recovery commands. No live actions happen on import."""
import argparse
import base64
from datetime import datetime, timezone
import getpass
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import plistlib
import re
import shutil
import socket
import subprocess
import sys
import time
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DATA = Path.home() / '.hg1/earnfm'
CONFIG = json.loads((ROOT / 'config.json').read_text())
BASE = 'https://api.salad.com/api/public/organizations/' + CONFIG['organization']
GROUP = '/projects/' + CONFIG['project'] + '/containers/' + CONFIG['name']
HELPER = Path(os.environ.get('EARNFM_KEY_HELPER', str(ROOT / '.runtime/keychain-store')))
SERVICES = {'salad': 'salad-bandwidth-api', 'client': 'earnfm-api-key', 'reader': 'earnfm-read-session'}


def key(service):
    p = subprocess.run([str(HELPER), '--read', '--service', service, '--account', getpass.getuser()],
                       capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError('Keychain entry unavailable: ' + service + '; run the keys command in Terminal')
    return p.stdout.strip()


def call(url, header, method='GET', body=None, missing=False):
    lines = ['header = ' + json.dumps(header)]
    if body is not None:
        kind = 'application/merge-patch+json' if method == 'PATCH' else 'application/json'
        lines += ['header = ' + json.dumps('Content-Type: ' + kind), 'data-binary = ' + json.dumps(json.dumps(body))]
    p = subprocess.run(['curl', '-sS', '--max-time', '30', '--config', '-', '-X', method,
                        '--write-out', '\n%{http_code}', url], input='\n'.join(lines)+'\n',
                       text=True, capture_output=True, timeout=35)
    raw, _, code = p.stdout.rpartition('\n')
    if missing and code == '404':
        return None
    if p.returncode or not code.isdigit() or not 200 <= int(code) < 300:
        raise RuntimeError(method + ' failed: HTTP ' + code + '; no automatic mutation retry was made')
    return json.loads(raw) if raw.strip() else {}


def api(path, method='GET', body=None, missing=False):
    return call(BASE + path, 'Salad-Api-Key: ' + key(SERVICES['salad']), method, body, missing)


def ms(value):
    value = re.sub(r'\.(\d+)(?=[+-]\d\d:\d\d$)', lambda m: '.'+m[1][:6].ljust(6, '0'), value.replace('Z', '+00:00'))
    return int(datetime.fromisoformat(value).timestamp()*1000)


def iso(value):
    return datetime.fromtimestamp(value/1000, timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def source_bytes(command):
    if command[:2] != ['/bin/sh', '-c']:
        raise RuntimeError('Existing group has an unrecognized command; inspect it before updating')
    if 'base64 -d' in command[2]:
        return base64.b64decode(''.join(command[4:]), validate=True)
    if 'printf "%s\\n" "$@"' in command[2]:
        return ('\n'.join(command[4:])+'\n').encode()
    raise RuntimeError('Existing command encoding is unknown; no update performed')


def command():
    payload = base64.b64encode((ROOT/'container/start.sh').read_bytes()).decode()
    args = ['/bin/sh', '-c', 'umask 077; printf "%s" "$@" | base64 -d > /tmp/earnfm-start.sh; exec /bin/sh /tmp/earnfm-start.sh', 'policy-start']
    args += [payload[i:i+900] for i in range(0, len(payload), 900)]
    if len(args) > 100 or max(map(len, args)) > 1000:
        raise RuntimeError('Command exceeds Salad argument limits')
    return args


def log_rows(start, end, query):
    rows = api('/log-entries', 'POST', {'query': query, 'start_time': iso(start), 'end_time': iso(end),
                                      'page_size': 100, 'sort_order': 'asc'}).get('items', [])
    if len(rows) < 100:
        return rows
    if end-start < 1000:
        raise RuntimeError('Log page still full at one second; result would be incomplete')
    middle = (start+end)//2
    return log_rows(start, middle, query) + log_rows(middle, end, query)


def cooldowns(group):
    holds = dict(CONFIG.get('recorded_cooldowns', {}))
    if group:
        env = group['container'].get('environment_variables', {})
        for item in env.get('EARNFM_COOLDOWNS', '').split():
            if item == 'none':
                continue
            machine, until = item.rsplit(':', 1)
            holds[machine] = max(holds.get(machine, 0), int(until))
        now = int(time.time()*1000)
        query = 'resource.type = "container" and resource.labels.container_group_name = '+json.dumps(CONFIG['name'])+' and (text_log contains "EF_BACKOFF" or (json_log.kind = "earnfm_event" and json_log.action = "cooldown_started"))'
        for row in log_rows(now-129600000, now, query):
            event = row.get('json_log')
            if not isinstance(event, dict): event = {}
            if event.get('kind') == 'earnfm_event' and event.get('action') == 'cooldown_started':
                machine = event.get('machine', '')
                until = event.get('retry_at_ms', 0)
                if re.fullmatch('[0-9a-f-]{36}', machine) and isinstance(until, (int, float)):
                    holds[machine] = max(holds.get(machine, 0), math.ceil(until/1000))
            match = re.search(r'machine=([0-9a-f-]{36}) seconds=(\d+)', row.get('text_log', ''))
            if match:
                until = math.ceil(ms(row['time'])/1000)+int(match[2])
                holds[match[1]] = max(holds.get(match[1], 0), until)
    return {k: v for k, v in holds.items() if v > time.time()}


def prepare():
    for binary in ('curl', 'swiftc'):
        if not shutil.which(binary):
            raise RuntimeError(binary+' is missing; install Apple Command Line Tools first')
    manifest = json.loads((ROOT/'manifest.json').read_text())
    for name, digest in manifest.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest:
            raise RuntimeError('Source checksum mismatch: '+name)
    HELPER.parent.mkdir(exist_ok=True)
    if not HELPER.exists():
        subprocess.run(['swiftc', str(ROOT/'scripts/keychain-store.swift'), '-o', str(HELPER)], check=True)
        HELPER.chmod(0o700)
    DATA.mkdir(parents=True, exist_ok=True)
    print('Source checksums verified; Keychain helper ready. No cloud change made.')


def save_keys(which, replace):
    if not sys.stdin.isatty():
        raise RuntimeError('Run keys interactively in Terminal so secret entry is hidden')
    for name in (list(SERVICES) if which == 'all' else [which]):
        service = SERVICES[name]
        try:
            current = key(service)
            usable = name != 'reader' or json.loads(current)['expires_at'] > time.time()
            if usable and not replace:
                print(service+': existing entry retained')
                continue
        except (RuntimeError, ValueError, KeyError):
            pass
        prompt = {'salad': 'Salad API key: ', 'client': 'EarnFM Docker EARNFM_TOKEN: ',
                  'reader': 'EarnFM account X-API-Key access JWT (not the Docker key): '}[name]
        value = getpass.getpass(prompt).strip()
        if not value:
            raise RuntimeError('Empty credential; nothing saved')
        if name == 'reader':
            middle = value.split('.')[1]
            expiry = json.loads(base64.urlsafe_b64decode(middle+'='*((-len(middle))%4)))['exp']
            if expiry <= time.time():
                raise RuntimeError('Access JWT expired; sign in to EarnFM again')
            for endpoint in ('view_balance', 'devices_online'):
                result = call('https://api.earn.fm/v2/harvester/'+endpoint, 'X-API-Key: '+value)
                if result.get('status') != 200 or 'data' not in result:
                    raise RuntimeError('EarnFM account session verification failed')
            value = json.dumps({'access_token': value, 'expires_at': expiry})
        subprocess.run([str(HELPER), '--service', service, '--account', getpass.getuser()],
                       input=value, text=True, check=True, stdout=subprocess.DEVNULL)
        print(service+': saved securely')


def deploy(update):
    DATA.mkdir(parents=True, exist_ok=True)
    existing = api(GROUP, missing=True)
    desired = command()
    local = json.loads((DATA/'target.json').read_text()) if (DATA/'target.json').exists() else None
    old_state = ('traffic.sqlite3', 'traffic.sqlite3-wal', 'traffic.sqlite3-shm', 'provider-baseline.json', 'provider.json')
    if not local and any((DATA/name).exists() for name in old_state):
        raise RuntimeError('Ledger/provider state survives without target.json. Restore its matching target or archive the stopped recorder state as described in docs/RECOVERY.md before deploying.')
    if local and (not existing or local['id'] != existing['id']):
        raise RuntimeError('Saved target belongs to another/deleted group. Follow the old-data archive step in docs/RECOVERY.md first.')
    try:
        client_token = key(SERVICES['client'])
    except RuntimeError:
        client_token = existing['container'].get('environment_variables', {}).get('EARNFM_TOKEN') if existing else None
        if not client_token:
            raise RuntimeError('No EarnFM Docker credential is available locally or in the existing deployment')
    same = bool(existing) and not update
    if same:
        try:
            same = source_bytes(existing['container']['command']) == (ROOT/'container/start.sh').read_bytes()
        except RuntimeError:
            same = False
    if existing:
        same = same and existing['container']['image'] == CONFIG['image'] and existing['replicas'] == 10
        same = same and existing['container']['resources']['cpu'] == 1
        same = same and existing['container']['resources']['memory'] == 1024 and not existing['container']['resources'].get('gpu_classes')
        same = same and existing['restart_policy'] == 'always' and existing.get('priority') == 'batch'
        same = same and bool(client_token) and existing['container'].get('environment_variables', {}).get('EARNFM_TOKEN') == client_token
        env = existing['container'].get('environment_variables', {})
        same = same and env.get('EARNFM_ACTIVITY_SECONDS', '900') == str(CONFIG.get('activity_seconds', 900)) and env.get('EARNFM_MIN_BYTES', '262144') == str(CONFIG.get('activity_min_bytes', 262144))
        same = same and existing['display_name'] == 'EF' and existing['autostart_policy'] is False
        same = same and existing['container']['image_caching'] is True and existing['container']['resources'].get('shm_size') == 64
        if not same and not update:
            raise RuntimeError('Existing group differs. Inspect it; --update explicitly replaces its configuration and restarts replicas.')
    holds = cooldowns(existing)
    changed = not same or update
    if changed:
        env = dict(existing['container'].get('environment_variables', {})) if existing else {}
        env.update(EARNFM_ACTIVITY_SECONDS=str(CONFIG.get('activity_seconds', 900)), EARNFM_MIN_BYTES=str(CONFIG.get('activity_min_bytes', 262144)))
        env.update(EARNFM_TOKEN=client_token, EARNFM_COOLDOWNS=' '.join(k+':'+str(v) for k, v in sorted(holds.items())) or 'none')
        container = {'image': CONFIG['image'], 'command': desired, 'resources': {'cpu': 1, 'memory': 1024, 'shm_size': 64, 'gpu_classes': []},
                     'priority': 'batch', 'image_caching': True, 'environment_variables': env}
        countries = existing['country_codes'] if existing else CONFIG.get('country_codes', ['us'])
        if len(countries) != 1 or env.get('EARNFM_COUNTRY', 'US').lower() != countries[0]:
            raise RuntimeError('Placement and EARNFM_COUNTRY must name the same single country; preserve the active country trial before updating.')
        body = {'container': container, 'replicas': 10, 'display_name': 'EF', 'country_codes': countries,
                'restart_policy': 'always', 'autostart_policy': False}
        if existing:
            latest = api(GROUP)
            if latest['id'] != existing['id'] or latest['version'] != existing['version']:
                raise RuntimeError('Cloud configuration changed during preparation; inspect the active owner before retrying.')
            api(GROUP, 'PATCH', body)
        else:
            body['name'] = CONFIG['name']
            api('/projects/'+CONFIG['project']+'/containers', 'POST', body)
    deadline = time.monotonic()+30
    while True:
        actual = api(GROUP)
        if source_bytes(actual['container']['command']) == (ROOT/'container/start.sh').read_bytes():
            break
        if not changed or time.monotonic() >= deadline:
            raise RuntimeError('Cloud command verification failed; inspect before any further mutation')
        time.sleep(2)
    resources = actual['container']['resources']
    if (actual['container']['image'] != CONFIG['image'] or actual['replicas'] != 10 or
            resources['cpu'] != 1 or resources['memory'] != 1024 or resources.get('shm_size') != 64 or
            resources.get('gpu_classes') or actual['container'].get('environment_variables', {}).get('EARNFM_TOKEN') != client_token):
        raise RuntimeError('Cloud image/resource/replica/credential verification failed; do not call start')
    now = int(time.time()*1000)
    target = dict(local or {}, id=actual['id'], organization=CONFIG['organization'], project=CONFIG['project'],
                  group=CONFIG['name'], desired=10, image=CONFIG['image'], display_name='EF', phase='measuring',
                  created_at=actual['create_time'], version=actual['version'], cooldowns=holds,
                  country_codes=actual['country_codes'],
                  agent_sha256=hashlib.sha256((ROOT/'container/start.sh').read_bytes()).hexdigest())
    target.setdefault('measurement_started_ms', now)
    temporary = DATA/'target.tmp'; temporary.write_text(json.dumps(target, indent=2)); os.replace(temporary, DATA/'target.json')
    print(json.dumps({'id': actual['id'], 'version': actual['version'], 'replicas': actual['replicas'],
                      'cloud_changed': changed, 'state': actual['current_state']['status']}))


def inspect():
    group = api(GROUP, missing=True)
    if group is None:
        print('EF group does not exist; deploy can create it.')
        return
    print(json.dumps({k: group[k] for k in ('id', 'name', 'display_name', 'version', 'replicas', 'country_codes', 'current_state')}, indent=2))
    print('Cloud script SHA256:', hashlib.sha256(source_bytes(group['container']['command'])).hexdigest())
    nodes = api(GROUP+'/instances').get('instances', [])
    print(json.dumps([{k: n[k] for k in ('id', 'machine_id', 'state', 'version')} for n in nodes], indent=2))
    path = DATA/'view.json'
    if path.exists():
        value = json.loads(path.read_text())
        print(json.dumps({'snapshot_age_s': round(time.time()-value['generated_ms']/1000), 'error': value['error'],
                          'provider': {k: v for k, v in value.get('provider', {}).items() if k != 'devices'},
                          'workers': value['workers']}, indent=2))


class Page(BaseHTTPRequestHandler):
    def do_GET(self):
        name = {'/': 'earnfm.html', '/ef': 'earnfm.html', '/earnfm': 'earnfm.html', '/earnfm.html': 'earnfm.html',
                '/styles.css': 'styles.css', '/ef.json': 'earnfm.json', '/earnfm.json': 'earnfm.json',
                '/api/earnfm': 'earnfm.json'}.get(urlparse(self.path).path)
        if not name:
            self.send_error(404)
            return
        path = DATA/'view.json' if name == 'earnfm.json' else ROOT/'dashboard/static'/name
        if not path.exists():
            self.send_error(503, 'Recorder has not published yet; run observe or inspect recorder.err.log')
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', {'html': 'text/html; charset=utf-8', 'css': 'text/css', 'json': 'application/json'}[name.rsplit('.', 1)[1]])
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


def install(shared):
    labels = ['com.cosmosgeek.earnfm-recorder'] + ([] if shared else ['com.cosmosgeek.earnfm-dashboard'])
    directory = Path.home()/'Library/LaunchAgents'
    directory.mkdir(parents=True, exist_ok=True)
    for label in labels:
        if (directory/(label+'.plist')).exists():
            raise RuntimeError(label+' already exists. Inspect the existing service; do not install a second recorder.')
    if not shared:
        with socket.socket() as check:
            check.bind(('127.0.0.1', 8787))
    DATA.mkdir(parents=True, exist_ok=True)
    for label in labels:
        recorder = label.endswith('recorder')
        arguments = [sys.executable, '-B', str(ROOT/'scripts/earnfm-recorder.py')] if recorder else [sys.executable, '-B', str(ROOT/'earnfm.py'), 'serve']
        log = 'recorder' if recorder else 'standalone-dashboard'
        value = {'Label': label, 'ProgramArguments': arguments, 'WorkingDirectory': str(ROOT), 'RunAtLoad': True,
                 'KeepAlive': True, 'ThrottleInterval': 10, 'StandardOutPath': str(DATA/(log+'.out.log')),
                 'StandardErrorPath': str(DATA/(log+'.err.log'))}
        path = directory/(label+'.plist')
        with path.open('wb') as file:
            plistlib.dump(value, file)
        subprocess.run(['launchctl', 'bootstrap', 'gui/'+str(os.getuid()), str(path)], check=True)
    print('Installed:', ', '.join(labels))


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('prepare')
    keys = sub.add_parser('keys'); keys.add_argument('--service', choices=['all']+list(SERVICES), default='all'); keys.add_argument('--replace', action='store_true')
    sub.add_parser('plan')
    deploy_parser = sub.add_parser('deploy'); deploy_parser.add_argument('--update', action='store_true')
    for name in ('inspect', 'start', 'stop', 'observe'):
        sub.add_parser(name)
    server = sub.add_parser('serve'); server.add_argument('--port', type=int, default=8787)
    service = sub.add_parser('install'); service.add_argument('--shared-dashboard', action='store_true')
    logs = sub.add_parser('logs'); logs.add_argument('--minutes', type=int, default=15); logs.add_argument('--machine')
    args = parser.parse_args()
    if args.action == 'prepare': prepare()
    elif args.action == 'keys': save_keys(args.service, args.replace)
    elif args.action == 'plan': print(json.dumps({'organization': CONFIG['organization'], 'project': CONFIG['project'], 'name': CONFIG['name'], 'replicas': 10, 'image': CONFIG['image'], 'cpu': 1, 'memory_mib': 1024, 'countries': ['us'], 'command_args': len(command()), 'script_sha256': hashlib.sha256((ROOT/'container/start.sh').read_bytes()).hexdigest()}, indent=2))
    elif args.action == 'deploy': deploy(args.update)
    elif args.action == 'inspect': inspect()
    elif args.action in ('start', 'stop'):
        if args.action == 'start' and not (DATA/'target.json').exists():
            raise RuntimeError('Run deploy first to verify/adopt the group and create target.json')
        api(GROUP+'/'+args.action, 'POST'); print('Salad accepted '+args.action+'; inspect to verify completion.')
    elif args.action == 'observe': subprocess.run([sys.executable, '-B', str(ROOT/'scripts/earnfm-recorder.py'), '--once'], check=True)
    elif args.action == 'serve': ThreadingHTTPServer(('127.0.0.1', args.port), Page).serve_forever()
    elif args.action == 'install': install(args.shared_dashboard)
    elif args.action == 'logs':
        if not 1 <= args.minutes <= 1440: raise RuntimeError('Use a window from 1 to 1440 minutes')
        query = 'resource.type = "container" and resource.labels.container_group_name = '+json.dumps(CONFIG['name'])+' and (text_log contains "EF_" or json_log.kind = "earnfm_event")'
        if args.machine:
            if not re.fullmatch('[0-9a-f-]{36}', args.machine): raise RuntimeError('Use the full machine UUID')
            query += ' and resource.labels.machine_id = '+json.dumps(args.machine)
        now = int(time.time()*1000)
        for row in log_rows(now-args.minutes*60000, now, query):
            event = row.get('json_log')
            if not isinstance(event, dict): event = {}
            if event.get('kind') == 'earnfm_event':
                print(row['time'], json.dumps({k:event.get(k) for k in ('action','reason','instance','machine','time_ms','retry_at_ms','http_status')}))
                continue
            text = re.sub(r'(?i)(apikey=)[^&\s]+', r'\1[redacted]', row.get('text_log', ''))
            print(row['time'], text)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, IndexError, KeyError, OSError, subprocess.SubprocessError) as exc:
        print('Recovery stopped: '+str(exc), file=sys.stderr)
        sys.exit(1)
