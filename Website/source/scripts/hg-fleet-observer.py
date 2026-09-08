#!/usr/bin/env python3
"""Read Salad native lifecycle and network counters into a per-worker ledger."""
import argparse
import fcntl
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import re
from pathlib import Path
import time

spec = importlib.util.spec_from_file_location('hg_fleet_control', Path(__file__).with_name('hg-fleet-control.py'))
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


def milliseconds(value):
    value = value.replace('Z', '+00:00')
    value = re.sub(r'\.(\d+)(?=[+-])', lambda m: '.' + m.group(1)[:6].ljust(6, '0'), value)
    return int(datetime.fromisoformat(value).timestamp() * 1000)


def classify(text):
    low = text.lower()
    if 'hg_self_reallocate' in low or 'hg_self_imds_accepted' in low:
        return 'reallocating'
    if 'user_device_limit_exceeded' in low or 'device limit' in low:
        return 'device_limit'
    if 'already active' in low:
        return 'device_already_active'
    if 'overused' in low:
        return 'network_overused'
    if 'unusable' in low:
        return 'network_unusable'
    if 'connected and running' in low:
        return 'connected'
    if 'disconnected' in low:
        return 'disconnected'
    if 'authorisation successful' in low:
        return 'authenticated'
    if 'service is starting' in low:
        return 'starting'
    if 'error processing' in low:
        return 'authorization_error'
    if 'hg_stock_exit' in low:
        return 'exited'
    return None


def read_provider():
    path = control.RUNTIME / 'provider-latest.json'
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def observe_worker(fleet, index, group, device, provider):
    worker = {'worker': index, 'organization': 'deathadder', 'group': group, 'device': device,
              'machine': None, 'ip': None, 'state': 'unverified', 'client_status': 'unverified',
              'credits': None, 'credit_observed_ms': None, 'error': None}
    device_reading = next((x for x in provider.get('devices', []) if x.get('device') == device), {})
    worker.update(credits=device_reading.get('credits'), ip=device_reading.get('ip'),
                  credit_observed_ms=provider.get('observed_ms'),
                  provider_active=device_reading.get('provider_active'))
    try:
        path = '/projects/default/containers/' + group
        g = fleet.api('deathadder', path)
        if fleet.device(g) != device or g.get('replicas') != 1 or g['container']['image'] != control.IMAGE:
            raise RuntimeError('Configuration differs from the approved independent stock control')
        instances = fleet.api('deathadder', path + '/instances').get('instances', [])
        worker.update(state=g.get('current_state', {}).get('status'), image=g['container']['image'],
                      replica_count=len(instances), running_instances=sum(x.get('state') == 'running' for x in instances))
        if len(instances) > 1:
            raise RuntimeError('Multiple instances share one registration during rollout')
        if not instances:
            worker['client_status'] = 'not_started'
            return worker
        instance = instances[0]
        worker.update(instance=instance['id'], machine=instance.get('machine_id'),
                      instance_state=instance.get('state'), ready=instance.get('ready'))
        end = datetime.now(timezone.utc)
        native_recovery = any('HG_SELF_START' in part for part in g['container'].get('command', []))
        identity = 'machine_id' if native_recovery else 'instance_id'
        base = ('resource.type = "container" and resource.labels.project_name = "default" and '
                'resource.labels.container_group_name = "' + group + '" and '
                'resource.labels.' + identity + ' = "' + instance.get(identity, instance['id']) + '"')
        lifecycle_query = base + ' and (text_log contains "Honeygain" or text_log contains "Authorisation" or text_log contains "HG_STOCK" or text_log contains "HG_SELF" or text_log contains "device" or text_log contains "overused" or text_log contains "Error")'
        def logs(query, minutes, size):
            calls = 0
            def fetch_window(start, stop):
                nonlocal calls
                calls += 1
                if calls > 63:
                    raise RuntimeError('Salad log window exceeds bounded pagination budget')
                items = fleet.api('deathadder', '/log-entries', 'POST', {'query': query,
                    'start_time': start.isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
                    'end_time': stop.isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
                    'page_size': size, 'sort_order': 'asc'}).get('items', [])
                if len(items) < size:
                    return items
                # A full response can contain an older capped page, regardless of
                # requested sort order. Split time until every window is complete.
                if (stop-start) <= timedelta(milliseconds=1):
                    raise RuntimeError('Too many Salad logs share one timestamp')
                midpoint = start + (stop-start)/2
                return fetch_window(start, midpoint) + fetch_window(midpoint, stop)
            start = end-timedelta(minutes=minutes)
            if native_recovery and instance.get('update_time'):
                start = max(start, datetime.fromtimestamp(milliseconds(instance['update_time'])/1000, timezone.utc))
            items = fetch_window(start, end) if start < end else []
            unique = {json.dumps(item, sort_keys=True): item for item in items}
            return list(unique.values())
        events = logs(lifecycle_query, 3 if native_recovery else 120, 100)
        safe_events = []
        for entry in events:
            text = entry.get('text_log', '')
            status = classify(text)
            if status:
                safe_events.append({'time': entry.get('time'), 'status': status})
        safe_events.sort(key=lambda x: x['time'] or '', reverse=True)
        if safe_events:
            worker.update(client_status=safe_events[0]['status'], last_event_at=safe_events[0]['time'])
            if safe_events[0]['status'] in ('device_limit', 'device_already_active', 'network_overused', 'network_unusable', 'authorization_error'):
                worker['error'] = safe_events[0]['status']
        worker['lifecycle'] = safe_events[:20]
        samples = logs(base + ' and json_log.kind = "hg_native_sample"', 3, 30)
        readings = [{'time': x.get('time'), 'native_time': x.get('json_log', {}).get('time'),
                     **{k: x.get('json_log', {}).get(k) for k in ('rx_total', 'tx_total', 'state', 'error')}} for x in samples]
        readings.sort(key=lambda x: x['time'] or '')
        if readings:
            worker['sample'] = readings[-1]
            worker['sample_age_seconds'] = (int(time.time()*1000) - milliseconds(readings[-1]['time'])) / 1000
            if len(readings) >= 2:
                seconds = (milliseconds(readings[-1]['time']) - milliseconds(readings[0]['time'])) / 1000
                worker['network_window_seconds'] = seconds
                worker['rx_bytes_window'] = max(0, readings[-1]['rx_total'] - readings[0]['rx_total'])
                worker['tx_bytes_window'] = max(0, readings[-1]['tx_total'] - readings[0]['tx_total'])
        worker['connection_evidence_fresh'] = worker.get('sample_age_seconds', 9999) < 120 and instance.get('state') == 'running'
        if worker['client_status'] == 'connected' and not worker['connection_evidence_fresh']:
            worker['client_status'] = 'connected_last_observed_telemetry_stale'
        if readings and worker['connection_evidence_fresh'] and readings[-1].get('state') in ('connected', 'starting', 'waiting', 'disconnected', 'authorization_error'):
            if not safe_events or milliseconds(readings[-1]['time']) >= milliseconds(safe_events[0]['time']):
                worker['client_status'] = readings[-1]['state']
                worker['error'] = readings[-1].get('error') if readings[-1].get('error') not in (None, 'none') else None
        if not safe_events and worker['client_status'] == 'unverified':
            previous = control.RUNTIME / ('worker-%02d.json' % index)
            if previous.exists():
                old = json.loads(previous.read_text())
                previous_age = int(time.time()*1000) - milliseconds(old.get('checked_at', '1970-01-01T00:00:00Z'))
                if old.get('instance') == instance['id'] and worker.get('connection_evidence_fresh') and previous_age < 600000:
                    worker['client_status'] = old.get('client_status', 'unverified')
                    worker['last_event_at'] = old.get('last_event_at')
    except Exception as error:
        worker['error'] = type(error).__name__ + ': ' + str(error)
        if worker['client_status'] == 'connected':
            worker['client_status'] = 'connected_last_observed_telemetry_unverified'
    return worker


def observe(fleet):
    provider = read_provider()
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(observe_worker, fleet, index, group, device, provider)
                   for index, (group, device) in enumerate(zip(control.GROUPS, control.DEVICES), 1)]
        workers = [x.result() for x in futures]
    stamp = control.now()
    record = {'checked_at': stamp, 'time_ms': int(time.time()*1000), 'desired': 10,
              'running': sum(x.get('running_instances', 0) for x in workers),
              'connected': sum(x['client_status'] == 'connected' for x in workers),
              'provider_gathering_credits': provider.get('gathering_credits'),
              'provider_observed_ms': provider.get('observed_ms'), 'workers': workers,
              'connection_definition': 'Current native connected lifecycle without later exit/disconnect, live Salad instance and telemetry sample under 120s old. Provider credits remain separate.',
              'network_definition': 'Container interface bytes include protocol overhead and are not provider billed traffic.'}
    for worker in workers:
        worker['checked_at'] = stamp
        fleet.write('worker-%02d.json' % worker['worker'], worker)
    fleet.write('status.json', record)
    with (control.RUNTIME / 'observations.jsonl').open('a') as output:
        output.write(json.dumps(record) + '\n')
    print(json.dumps({k: record[k] for k in ('checked_at', 'desired', 'running', 'connected')}), flush=True)
    print(json.dumps([{'group': x['group'], 'state': x['state'], 'client_status': x['client_status'], 'error': x['error']} for x in workers]), flush=True)
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--once', action='store_true')
    p.add_argument('--interval', type=int, default=60)
    args = p.parse_args()
    fleet = control.Fleet()
    lock = (control.RUNTIME / 'observer.lock').open('a')
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('A Honeygain fleet observer is already running')
    while True:
        observe(fleet)
        if args.once:
            return
        time.sleep(max(30, args.interval))


if __name__ == '__main__':
    main()
