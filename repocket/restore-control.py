"""Recreate or attach to the documented RP Salad group; no secrets saved locally."""
import argparse
import base64
from datetime import datetime, timezone
import getpass
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
DATA = Path.home() / '.hg1/repocket'
ORG, PROJECT, GROUP = 'ssh2', 'default', 'rp-test-us'
IMAGE = 'docker.io/repocket/repocket@sha256:5888d756de7e0e74b95b5eb08bb93f4240a0ce840c910a7e528d1143ad0c502b'
SOURCE_SHA = '937d35e7c59fdd9c2afac80ffb3f45fbf2fbc8f06e21d43c3f66fe6a03a7ae8b'
BASE = f'https://api.salad.com/api/public/organizations/{ORG}/projects/{PROJECT}/containers'
KEY = None


def now():
    return datetime.now(timezone.utc).isoformat()


def worker():
    source = (ROOT / 'repocket-monitor/start.js').read_bytes()
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA:
        raise RuntimeError('Worker differs from this recovery edition; inspect before deploying')
    encoded = base64.b64encode(source).decode('ascii')
    command = ['/bin/sh', '-c', 'umask 077; printf "%s" "$@" | base64 -d > /tmp/repocket-start.js; exec /usr/local/bin/node /tmp/repocket-start.js', 'policy-start']
    command += [encoded[i:i + 900] for i in range(0, len(encoded), 900)]
    assert len(command) <= 100 and all(len(part) <= 1000 for part in command)
    return command


def payload(email, rp_key):
    return {'name': GROUP, 'display_name': 'RP', 'replicas': 10,
            'autostart_policy': False, 'restart_policy': 'always', 'country_codes': ['us'],
            'container': {'image': IMAGE, 'command': worker(), 'priority': 'batch',
                          'resources': {'cpu': 1, 'memory': 1024, 'gpu_classes': [], 'shm_size': 64},
                          'environment_variables': {'RP_EMAIL': email, 'RP_API_KEY': rp_key}}}


def api(method, suffix='', body=None):
    global KEY
    if KEY is None:
        helper = ROOT / '.runtime/keychain-store'
        if sys.platform == 'darwin' and helper.exists():
            result = subprocess.run([str(helper), '--read', '--service', 'salad-bandwidth-api',
                                     '--account', getpass.getuser()], capture_output=True, text=True)
            KEY = result.stdout.strip() if result.returncode == 0 else None
        if not KEY:
            KEY = getpass.getpass('Salad API key (hidden): ').strip()
        if not KEY:
            raise RuntimeError('Salad API key is required')
    config = 'header = ' + json.dumps('Salad-Api-Key: ' + KEY) + '\nheader = "Content-Type: application/json"\n'
    if body is not None:
        config += 'data-binary = ' + json.dumps(json.dumps(body)) + '\n'
    try:
        result = subprocess.run(['curl', '-sS', '--max-time', '30', '--config', '-',
                                 '--request', method, '--write-out', '\n%{http_code}', BASE + suffix],
                                input=config, text=True, capture_output=True, timeout=35)
    except subprocess.TimeoutExpired:
        raise RuntimeError('Salad request timed out; inspect before retrying a mutation') from None
    if result.returncode or '\n' not in result.stdout:
        raise RuntimeError('Salad transport failed; inspect before retrying a mutation')
    content, status = result.stdout.rsplit('\n', 1)
    # Do not print response bodies: a provider could echo credentials/configuration.
    status = int(status)
    return status, json.loads(content) if 200 <= status < 300 and content.strip() else {}


def get_group():
    status, group = api('GET', '/' + GROUP)
    if status != 200:
        raise RuntimeError('Group read returned HTTP ' + str(status))
    return group


def check_group(group):
    c = group.get('container', {})
    resources = c.get('resources', {})
    if not (group.get('name') == GROUP and group.get('display_name') == 'RP'
            and c.get('image') == IMAGE and c.get('command') == worker()
            and resources.get('cpu') == 1 and resources.get('memory') == 1024
            and resources.get('shm_size') == 64 and resources.get('gpu_classes') == []
            and group.get('autostart_policy') is False
            and set(c.get('environment_variables', {})) == {'RP_EMAIL', 'RP_API_KEY'}
            and all(c['environment_variables'].values())
            and group.get('replicas') == 10 and group.get('country_codes') == ['us']
            and group.get('restart_policy') == 'always'
            and (group.get('priority') or c.get('priority')) == 'batch'):
        raise RuntimeError('Existing group differs from this recovery edition; it was not modified')


def save(group, capture_from=None):
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = DATA / 'deployment.json'
    old = json.loads(path.read_text()) if path.exists() else {}
    if old and old.get('id') != group['id']:
        raise RuntimeError('Local RP data belongs to another group; move that directory to a backup first')
    record = {**old, 'organization': ORG, 'project': PROJECT, 'group': GROUP, 'id': group['id'],
              'replicas': 10, 'image': IMAGE, 'version': group['version'], 'source_revision': 11,
              'source_sha256': SOURCE_SHA, 'created_at': group.get('create_time', now()),
              'start_requested_at': capture_from or old.get('start_requested_at') or now(),
              'budget_usd': 5}
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(record, indent=2) + '\n')
    temporary.chmod(0o600)
    temporary.replace(path)


def summary(group):
    return {'id': group['id'], 'name': group['display_name'], 'version': group['version'],
            'replicas': group['replicas'], 'state': group.get('current_state', {}),
            'worker_sha256': SOURCE_SHA}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'inspect', 'create', 'attach', 'start', 'stop'])
    args = parser.parse_args()
    if args.action == 'plan':
        print(json.dumps(payload('ENTER_YOUR_RP_EMAIL', 'ENTER_YOUR_RP_DOCKER_KEY'), indent=2))
        return
    if args.action == 'create':
        if (DATA / 'deployment.json').exists():
            raise RuntimeError('Local deployment state already exists: use inspect/attach; do not create a duplicate')
        status, _ = api('GET', '/' + GROUP)
        if status != 404:
            raise RuntimeError('Create requires confirmed HTTP 404; read returned HTTP ' + str(status) + '. Use inspect/attach for an existing group')
        email = input('Repocket account email: ').strip()
        rp_key = getpass.getpass('Repocket Docker API key (hidden): ').strip()
        if not email or not rp_key:
            raise RuntimeError('Both Repocket values are required')
        status, group = api('POST', '', payload(email, rp_key))
        if status not in (200, 201, 202) or 'id' not in group:
            raise RuntimeError('Create returned HTTP ' + str(status) + '; inspect before retrying')
        save(group)
        print(json.dumps(summary(group), indent=2))
        print('Created. Run start explicitly when ready to consume prepaid credit.')
        return
    group = get_group()
    if args.action == 'inspect':
        check_group(group)
        print(json.dumps(summary(group), indent=2))
        return
    check_group(group)
    if args.action == 'attach':
        save(group)
        print('Attached local recorder state to ' + group['id'] + '; existing capture cursor/history preserved if present')
        return
    state_file = DATA / 'deployment.json'
    if not state_file.exists() or json.loads(state_file.read_text()).get('id') != group['id']:
        raise RuntimeError('Run attach before controlling this group')
    current = group.get('current_state', {}).get('status')
    if args.action == 'start' and current == 'running':
        print('Already running; no start request sent')
        return
    if args.action == 'stop' and current == 'stopped':
        print('Already stopped; no stop request sent')
        return
    status, _ = api('POST', '/' + GROUP + '/' + args.action)
    if status not in (200, 202, 204):
        raise RuntimeError(args.action + ' returned HTTP ' + str(status) + '; inspect current state')
    print(args.action + ' request accepted; run inspect to check completion')


if __name__ == '__main__':
    try:
        main()
    except RuntimeError as error:
        raise SystemExit(str(error))
