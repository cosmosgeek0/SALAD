#!/usr/bin/env python3
"""Create Grass or install its native recovery using a privately transferred login."""
import argparse
import base64
import getpass
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import tarfile
import uuid

ROOT = Path(__file__).resolve().parent
ORG = os.environ.get('GRASS_ORGANIZATION', 'cosmosgeeketh')
PROJECT = os.environ.get('GRASS_PROJECT', 'default')
GROUP = os.environ.get('GRASS_GROUP', 'grass')
IMAGE = 'docker.io/mangup/grassminer@sha256:92b9f50fc784f69d3f8dd49f84e670d55e30dd5f6eb58b57e0381bb55b6b6302'
BASE = f'https://api.salad.com/api/public/organizations/{ORG}/projects/{PROJECT}/containers'
PORTAL = f'https://portal.salad.com/organizations/{ORG}/projects/{PROJECT}/containers/{GROUP}'


def api(key, suffix, method='GET', body=None):
    media = 'application/merge-patch+json' if method == 'PATCH' else 'application/json'
    config = 'header = ' + json.dumps('Salad-Api-Key: ' + key) + '\nheader = ' + json.dumps('Content-Type: ' + media) + '\n'
    if body is not None:
        config += 'data-binary = ' + json.dumps(json.dumps(body)) + '\n'
    result = subprocess.run(['curl', '-sS', '--max-time', '30', '--config', '-', '--request', method,
        '--write-out', '\n%{http_code}', BASE + suffix], input=config, text=True, capture_output=True, timeout=35)
    if result.returncode:
        raise RuntimeError('Salad transport request failed; inspect the group before repeating a write')
    raw, status = result.stdout.rsplit('\n', 1)
    return int(status), json.loads(raw) if raw.strip() else {}


def workload_command():
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w') as archive:
        for name in ('worker.pl', 'bootstrap.sh'):
            content = (ROOT / name).read_bytes()
            entry = tarfile.TarInfo(name)
            entry.size, entry.mode, entry.mtime = len(content), 0o755, 0
            archive.addfile(entry, io.BytesIO(content))
    encoded = base64.b64encode(gzip.compress(buffer.getvalue(), mtime=0)).decode()
    script = 'set -eu; mkdir -p /opt/grass; printf "%s" "$@" | base64 -d | tar -xz -C /opt/grass; cp /opt/grass/bootstrap.sh /etc/cont-init.d/50-grass.sh; exec /init'
    command = ['/bin/sh', '-c', script, 'grass', *[encoded[i:i+900] for i in range(0, len(encoded), 900)]]
    if len(command) > 100 or any(len(part) > 1000 for part in command):
        raise RuntimeError('Grass command exceeds the tested Salad command envelope')
    return command


def openssl(arguments, data=None, pass_fds=()):
    result = subprocess.run(['openssl', *arguments], input=data, capture_output=True, pass_fds=pass_fds, timeout=30)
    if result.returncode:
        raise RuntimeError('OpenSSL could not complete the private Grass login transfer')
    return result.stdout


def login_seed(group):
    saved = group['container']['environment_variables'].get('GRASS_STATE_B64')
    if saved:
        value = json.loads(base64.b64decode(saved, validate=True))
        if not isinstance(value, dict) or not value.get('accessToken'):
            raise RuntimeError('The saved Grass login seed is invalid')
        return saved
    if group['replicas'] != 1:
        raise RuntimeError('Capture the first Grass login with one instance before adding replicas')
    private_key = openssl(['genrsa', '3072'])
    certificate = openssl(['req', '-new', '-x509', '-key', '/dev/stdin', '-subj', '/CN=Grass session transfer', '-days', '1'], private_key)
    nonce = uuid.uuid4().hex
    certificate_path = '/tmp/grass-transfer-' + nonce + '.crt'
    encrypted_path = '/opt/noVNC/grass-transfer-' + nonce + '.bin'
    command = "umask 077; printf '%s' " + shlex.quote(base64.b64encode(certificate).decode()) + ' | base64 -d > ' + shlex.quote(certificate_path)
    command += ' && openssl cms -encrypt -binary -aes-256-cbc -outform DER -in /config/xdg/data/io.getgrass.desktop/store.json -out ' + shlex.quote(encrypted_path) + ' ' + shlex.quote(certificate_path)
    command += ' && chmod 644 ' + shlex.quote(encrypted_path) + ' && rm -f ' + shlex.quote(certificate_path)
    command += ' && (nohup sh -c ' + shlex.quote('sleep 300; rm -f "$1"') + ' grass-transfer ' + shlex.quote(encrypted_path) + ' </dev/null >/dev/null 2>&1 &)'
    print('Open the running Grass instance in Salad, choose Terminal, and paste this SINGLE LINE.', flush=True)
    print('It exports an encrypted login backup; its private decryption key stays in this process.', flush=True)
    print(command, flush=True)
    input('Press Return here after the command finishes in Salad: ')
    url = 'https://' + group['networking']['dns'] + '/grass-transfer-' + nonce + '.bin'
    download = subprocess.run(['curl', '-fsS', '--max-time', '20', '--max-filesize', '100000', url], capture_output=True, timeout=25)
    if download.returncode:
        raise RuntimeError('The encrypted Grass login backup could not be downloaded; repeat the transfer')
    encrypted = download.stdout
    key_read, key_write = os.pipe()
    cert_read, cert_write = os.pipe()
    try:
        os.write(key_write, private_key)
        os.close(key_write)
        os.write(cert_write, certificate)
        os.close(cert_write)
        raw = openssl(['cms', '-decrypt', '-binary', '-inform', 'DER', '-inkey', f'/dev/fd/{key_read}',
            '-recip', f'/dev/fd/{cert_read}'], encrypted, (key_read, cert_read))
    finally:
        os.close(key_read)
        os.close(cert_read)
    value = json.loads(raw)
    if not isinstance(value, dict) or not value.get('accessToken') or not value.get('refreshToken'):
        raise RuntimeError('The transferred Grass login does not contain an authenticated session')
    for name in list(value):
        if name.startswith('wynd:device_') or name in ('wynd:browser_id', 'wynd:status'):
            del value[name]
    return base64.b64encode(json.dumps(value, separators=(',', ':')).encode()).decode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('create', 'repair', 'status'), nargs='?', default='create')
    args = parser.parse_args()
    key = os.environ.get('SALAD_API_KEY') or getpass.getpass('Salad API key: ').strip()
    if not key:
        raise SystemExit('No API key entered')
    status, group = api(key, '/' + GROUP)
    if status == 404 and args.action == 'create':
        password = getpass.getpass('New desktop-access password: ')
        if len(password) != 8 or not password.isascii() or not password.isalnum():
            raise SystemExit('Use exactly eight English letters or digits; no group was created')
        created, _ = api(key, '', 'POST', {'name': GROUP, 'display_name': 'Grass', 'replicas': 1,
            'autostart_policy': True, 'restart_policy': 'always', 'country_codes': ['us'],
            'container': {'image': IMAGE, 'priority': 'batch', 'resources': {'cpu': 1, 'memory': 1024},
                'environment_variables': {'SECURE_CONNECTION': '0', 'WEB_AUTHENTICATION': '0', 'VNC_PASSWORD': password}},
            'networking': {'auth': False, 'protocol': 'http', 'port': 5800, 'load_balancer': 'least_number_of_connections'}})
        status, group = api(key, '/' + GROUP)
        if status != 200:
            raise RuntimeError(f'Create returned HTTP {created}; readback HTTP {status}. Inspect {PORTAL}')
    if status != 200:
        raise RuntimeError('Salad group read returned HTTP ' + str(status))
    if group['container']['image'] != IMAGE:
        raise RuntimeError('The group image differs from this verified Grass setup')
    if args.action == 'repair':
        command = workload_command()
        environment = dict(group['container']['environment_variables'])
        environment['GRASS_STATE_B64'] = login_seed(group)
        if group['container'].get('command') != command or environment != group['container']['environment_variables']:
            changed, _ = api(key, '/' + GROUP, 'PATCH', {'container': {'command': command, 'environment_variables': environment}})
            if changed != 200:
                raise RuntimeError('Grass recovery update returned HTTP ' + str(changed) + '; inspect before retrying')
            status, group = api(key, '/' + GROUP)
            if status != 200 or group['container'].get('command') != command:
                raise RuntimeError('Grass recovery configuration was not confirmed by readback')
        print('Native recovery configuration confirmed. Verify a new worker_started record and live provider acceptance.')
        print('Command SHA256:', hashlib.sha256(json.dumps(command, separators=(',', ':')).encode()).hexdigest())
    print('Group:', group['id'])
    print('Version:', group['version'])
    print('State:', group['current_state']['status'])
    print('Portal:', PORTAL)
    print('Desktop:', 'https://' + group['networking']['dns'])
    print('Login seed configured:', bool(group['container']['environment_variables'].get('GRASS_STATE_B64')))


if __name__ == '__main__':
    main()
