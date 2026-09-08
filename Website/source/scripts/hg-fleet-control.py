#!/usr/bin/env python3
"""Operate a bounded ten-worker Honeygain control using existing registrations."""
import argparse
import fcntl
from datetime import datetime, timedelta, timezone
import getpass
import ipaddress
import json
import os
import re
import math
import sys
import time
from pathlib import Path
import subprocess
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path(os.environ.get('HG_FLEET_DIR', str(ROOT / '.runtime/hg-fleet')))
IMAGE = 'docker.io/honeygain/honeygain@sha256:5cd8c361517d0cbae4aa2c75e13239e45f9193ab8e205d57fa29f2e695ea3ec1'
ORGS = ('deathadder', 'cosmosgeeketh', 'hyperlane')
DEVICES = (
    'salad-us-1', 'worker-us-1',
    'salad-c4385ee4-0693-505d-8bd4-76f0e37054a9',
    'salad-5cd61ffc-5e1a-7f55-86a6-ebf67cf06478',
    'salad-b8ababd8-ac4b-d45c-b6a0-b499236dee05',
    'salad-45ef0f8f-0a89-6a5d-9f16-9b606250128e',
    'salad-eeec7129-d81e-d851-8a2e-2a94747b15d2',
    'salad-62d87783-409d-825e-9125-d5166b9038e0',
    'salad-d645de46-f7cc-1859-98a4-cfe7f88bc346',
    'salad-a1d8dea8-73bc-5356-8980-b652388c1659',
)
GROUPS = ('hg1',) + tuple('hg-solo-%02d' % n for n in range(2, 11))


def recovery_command():
    script = r'''set -u
child=""; state=starting; error=none; reason=""; deadline=120; next_sample=0
stop_client() { if [ -n "$child" ]; then kill "$child" 2>/dev/null || true; sleep 1; kill -KILL "$child" 2>/dev/null || true; wait "$child" 2>/dev/null || true; child=""; fi; }
trap 'stop_client; exit 0' TERM INT
start_client() {
  exec 3< <(exec /app/honeygain -tou-accept -email "$HONEYGAIN_EMAIL" -pass "$HONEYGAIN_PASSWORD" -device "$HONEYGAIN_DEVICE_NAME" 2>&1)
  child=$!
}
printf 'HG_SELF_START controller=imds time=%s\n' "$(date -u +%FT%TZ)"
start_client
while :; do
  if IFS= read -r -t 1 line <&3; then
    printf '%s\n' "$line"
    case "${line,,}" in
      *overused*) state=network_overused; error=network_overused; reason=network_overused; break ;;
      *unusable*) state=network_unusable; error=network_unusable; reason=network_unusable; break ;;
      *'connected and running'*) state=connected; error=none ;;
      *disconnected*) if [ "$state" != disconnected ]; then deadline=$((SECONDS+120)); fi; state=disconnected; error=disconnected ;;
      *'already active'*) state=waiting; error=device_already_active ;;
      *'error processing'*) state=authorization_error; error=authorization_error ;;
    esac
  elif ! kill -0 "$child" 2>/dev/null; then
    wait "$child"; code=$?; child=""
    printf 'HG_STOCK_EXIT status=%s time=%s\n' "$code" "$(date -u +%FT%TZ)"
    if [ "$error" = device_already_active ] && (( SECONDS < deadline )); then sleep 15; start_client; else reason=client_exited; break; fi
  fi
  if [ "$state" != connected ] && (( SECONDS >= deadline )); then reason=connection_timeout; break; fi
  if (( SECONDS >= next_sample )); then
    while read -r iface rx rp re rd rf rfr rc rm tx rest; do
      if [ "$iface" = 'eth0:' ]; then printf '{"kind":"hg_native_sample","time":"%s","version":"0.6.6","rx_total":%s,"tx_total":%s,"state":"%s","error":"%s"}\n' "$(date -u +%FT%TZ)" "$rx" "$tx" "$state" "$error"; fi
    done </proc/net/dev
    next_sample=$((SECONDS+10))
  fi
done
stop_client
printf 'HG_SELF_REALLOCATE reason=%s time=%s\n' "$reason" "$(date -u +%FT%TZ)"
for attempt in 1 2 3; do
  if timeout 10 /bin/bash -c '
    body="{\"reason\":\"Honeygain $1\"}"
    exec 4<>/dev/tcp/169.254.169.254/80 || exit 1
    printf "POST /v1/reallocate HTTP/1.1\r\nHost: 169.254.169.254\r\nMetadata: true\r\nContent-Type: application/json\r\nContent-Length: %s\r\nConnection: close\r\n\r\n%s" "${#body}" "$body" >&4
    IFS= read -r response <&4 || exit 1
    printf "HG_SELF_IMDS_RESPONSE %s\n" "$response"
    [[ "$response" =~ ^HTTP/1\.[01][[:space:]]+(200|204)[[:space:]] ]]
  ' hg-imds "$reason"; then
    printf 'HG_SELF_IMDS_ACCEPTED time=%s\n' "$(date -u +%FT%TZ)"
    exit 75
  fi
  printf 'HG_SELF_IMDS_FAILED attempt=%s time=%s\n' "$attempt" "$(date -u +%FT%TZ)"
  sleep 15
done
exit 75'''
    return ['/bin/bash', '-c', 'printf "%s\\n" "$@" > /tmp/hg-stock-run.sh; exec /bin/bash /tmp/hg-stock-run.sh', 'hg-stock', *script.splitlines()]


def now():
    return datetime.now(timezone.utc).isoformat()


class Fleet:
    def __init__(self):
        RUNTIME.mkdir(mode=0o700, parents=True, exist_ok=True)
        helper = os.environ.get('HG_KEYCHAIN_HELPER', str(ROOT / '.runtime/keychain-store'))
        self.key = subprocess.check_output([helper, '--read',
            '--service', 'salad-bandwidth-api', '--account', getpass.getuser()], text=True).strip()

    def api(self, org, path='', method='GET', body=None):
        url = 'https://api.salad.com/api/public/organizations/' + org + path
        media = 'application/merge-patch+json' if method == 'PATCH' else 'application/json'
        config = 'header = ' + json.dumps('Salad-Api-Key: ' + self.key) + '\n'
        config += 'header = ' + json.dumps('Content-Type: ' + media) + '\n'
        if body is not None:
            config += 'data-binary = ' + json.dumps(json.dumps(body)) + '\n'
        response = subprocess.run(['curl', '--silent', '--show-error', '--max-time', '35',
            '--config', '-', '--request', method, '--write-out', '\n%{http_code}', url],
            input=config, capture_output=True, text=True, timeout=40)
        if response.returncode:
            raise RuntimeError('Salad transport request failed')
        raw, code = response.stdout.rsplit('\n', 1)
        if not 200 <= int(code) < 300:
            raise RuntimeError('%s %s%s returned HTTP %s' % (method, org, path, code))
        return json.loads(raw) if raw.strip() else {}

    def groups(self, org):
        return self.api(org, '/projects/default/containers').get('items', [])

    @staticmethod
    def device(g):
        c = g.get('container', {})
        device = c.get('environment_variables', {}).get('HONEYGAIN_DEVICE_NAME')
        if device:
            return device
        command = c.get('command') or []
        if '-device' in command and command.index('-device') + 1 < len(command):
            return command[command.index('-device') + 1]
        matches = re.findall(r'-device[ =]+[\"\x27]?([A-Za-z0-9-]+)', ' '.join(command))
        if len(matches) == 1:
            return matches[0]
        return None

    @staticmethod
    def safe(g):
        return {'group': g['name'], 'id': g['id'], 'replicas': g.get('replicas'),
                'image': g.get('container', {}).get('image'), 'device': Fleet.device(g),
                'state': g.get('current_state', {}), 'version': g.get('version')}

    def inventory(self):
        result = []
        for org in ORGS:
            try:
                for g in self.groups(org):
                    result.append({'organization': org, **self.safe(g)})
            except RuntimeError as e:
                result.append({'organization': org, 'error': str(e)})
        return result

    @staticmethod
    def write(name, record):
        path = RUNTIME / name
        temp = path.with_suffix(path.suffix + '.%s.tmp' % os.getpid())
        temp.write_text(json.dumps(record, indent=2) + '\n')
        temp.chmod(0o640 if name in ('provider-api-traffic-latest.json', 'provider-feed-status.json') else 0o600)
        temp.replace(path)

    def stop_redundant(self):
        result = []
        for org in ORGS:
            for g in self.groups(org):
                if not self.device(g):
                    continue
                if org == 'deathadder' and g['name'] in GROUPS:
                    continue
                if g.get('current_state', {}).get('status') != 'stopped':
                    self.api(org, '/projects/default/containers/' + g['name'] + '/stop', 'POST')
                    result.append({'organization': org, 'group': g['name'], 'device': self.device(g),
                                   'stop_requested_at': now()})
        self.write('redundant-stops.json', result)
        return result

    def deploy(self):
        # Read every org first; never add workers while another HG group is active.
        for org in ORGS:
            for g in self.groups(org):
                if not self.device(g):
                    continue
                intended = org == 'deathadder' and g['name'] in GROUPS
                if not intended:
                    instances = self.api(org, '/projects/default/containers/' + g['name'] + '/instances')
                    if instances.get('instances'):
                        raise RuntimeError('Redundant HG instances must finish stopping: ' + org + '/' + g['name'])
        original = self.api('deathadder', '/projects/default/containers/hg1')
        if original['container']['image'] != IMAGE or self.device(original) != DEVICES[0] or original['replicas'] != 1:
            raise RuntimeError('Existing solo control changed; inspect before deployment')
        env = original['container']['environment_variables']
        current = {g['name']: g for g in self.groups('deathadder')}
        assert len(DEVICES) == len(set(DEVICES)) == len(GROUPS) == 10
        receipt = []
        for index, (group, device) in enumerate(zip(GROUPS, DEVICES), 1):
            if group in current:
                g = current[group]
                if self.device(g) != device or g['container']['image'] != IMAGE or g['replicas'] != 1:
                    raise RuntimeError('Existing group does not match approved control: ' + group)
            else:
                payload = {'name': group, 'display_name': 'HG Solo %02d' % index, 'replicas': 1,
                    'autostart_policy': True, 'restart_policy': 'always', 'country_codes': ['us'],
                    'container': {'image': IMAGE, 'resources': {'cpu': 1, 'memory': 1024},
                        'priority': 'low', 'command': original['container']['command'],
                        'environment_variables': {'HONEYGAIN_EMAIL': env['HONEYGAIN_EMAIL'],
                            'HONEYGAIN_PASSWORD': env['HONEYGAIN_PASSWORD'], 'HONEYGAIN_DEVICE_NAME': device}}}
                g = self.api('deathadder', '/projects/default/containers', 'POST', payload)
            receipt.append({'worker': index, 'organization': 'deathadder', **self.safe(g), 'checked_at': now()})
            self.write('deployment.json', receipt)
            print(json.dumps({'worker': index, 'group': group, 'device': device,
                              'state': g.get('current_state', {}).get('status')}), flush=True)
        return receipt

    def start_ready(self):
        result = []
        for group in GROUPS:
            g = self.api('deathadder', '/projects/default/containers/' + group)
            if g.get('current_state', {}).get('status') == 'stopped':
                try:
                    self.api('deathadder', '/projects/default/containers/' + group + '/start', 'POST')
                    result.append({'group': group, 'start_requested_at': now()})
                except RuntimeError as e:
                    result.append({'group': group, 'error': str(e)})
        return result

    def enable_recovery(self, groups=GROUPS):
        command = recovery_command()
        result = []
        for group in groups:
            if group not in GROUPS:
                raise ValueError('Unknown Honeygain group')
            path = '/projects/default/containers/' + group
            current = self.api('deathadder', path)
            if current['container']['image'] != IMAGE or current['replicas'] != 1 or self.device(current) != DEVICES[GROUPS.index(group)]:
                raise RuntimeError('Honeygain registration or deployment changed: ' + group)
            if current['container']['command'] != command:
                current = self.api('deathadder', path, 'PATCH', {'container': {'command': command}})
            result.append({'group': group, 'version': current.get('version'), 'recovery': 'IMDS inside container'})
        return result


def record_provider(record):
    """Persist an actual fresh visible-UI reading; never read authentication state."""
    observed_ms = record.get('observed_ms')
    if not isinstance(observed_ms, int) or not -60000 <= int(time.time()*1000) - observed_ms <= 300000:
        raise ValueError('Provider reading needs its actual observation time within five minutes')
    source = record.get('source', 'Fresh Honeygain dashboard visible UI')
    if source not in ('Fresh Honeygain dashboard visible UI', 'Honeygain official dashboard API'):
        raise ValueError('Unrecognized provider reading source')
    def amount(value):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError('Credits must be finite nonnegative provider observations')
        return value
    devices = record.get('devices', [])
    if len(devices) != 10 or {x.get('device') for x in devices} != set(DEVICES):
        raise ValueError('Reading must contain exactly the ten existing fleet registrations once each')
    clean_devices = []
    for device in DEVICES:
        item = next(x for x in devices if x['device'] == device)
        if not isinstance(item.get('provider_active'), bool):
            raise ValueError('Provider active status must be observed, not inferred from historical device count')
        ip = item.get('ip')
        if ip:
            parsed = ipaddress.ip_address(ip)
            ip = str(parsed.ipv4_mapped or parsed) if isinstance(parsed, ipaddress.IPv6Address) else str(parsed)
        clean_devices.append({'device': device, 'credits': amount(item.get('credits')),
                              'provider_active': item['provider_active'], 'ip': ip})
    clean = {'checked_at': now(), 'observed_ms': observed_ms,
             'gathering_credits': amount(record.get('gathering_credits')),
             'account_balance_credits': amount(record.get('account_balance_credits')),
             'source': source, 'devices': clean_devices}
    if record.get('gathering_traffic_bytes') is not None:
        clean.update(gathering_traffic_bytes=amount(record['gathering_traffic_bytes']), report_dates=record['report_dates'])
    RUNTIME.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (RUNTIME / 'provider-writer.lock').open('a') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        latest = RUNTIME / 'provider-latest.json'
        if latest.exists() and json.loads(latest.read_text()).get('observed_ms', 0) >= observed_ms:
            raise ValueError('Reading does not advance the actual provider observation timestamp')
        Fleet.write('provider-latest.json', clean)
        with (RUNTIME / 'provider-readings.jsonl').open('a') as output:
            output.write(json.dumps(clean) + '\n')
    return {'observed_ms': observed_ms, 'gathering_credits': clean['gathering_credits'],
            'device_count': len(clean_devices), 'provider_active': sum(x['provider_active'] for x in clean_devices)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['inventory', 'stop-redundant', 'deploy', 'start-ready', 'record-provider', 'enable-recovery'])
    args = p.parse_args()
    if args.action == 'record-provider':
        print(json.dumps(record_provider(json.load(sys.stdin))))
        return
    fleet = Fleet()
    action = getattr(fleet, args.action.replace('-', '_'))
    result = action()
    if args.action != 'deploy':
        print(json.dumps(result, indent=2))
    fleet.write(args.action + '-latest.json', {'checked_at': now(), 'result': result})


if __name__ == '__main__':
    main()
