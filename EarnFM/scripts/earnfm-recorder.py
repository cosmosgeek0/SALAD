#!/usr/bin/env python3
"""Record EarnFM source intervals, provider observations and recovery outcomes."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
import fcntl
import getpass
import hashlib
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
DATA = Path.home()/'.hg1/earnfm'
OUTPUT = DATA/'view.json'
FIELDS = ('run', 'seq', 'instance', 'machine', 'start_ms', 'end_ms', 'rx', 'tx',
          'total_rx', 'total_tx', 'state', 'valid', 'final', 'ip', 'country')
STATES = ('starting', 'running', 'connecting', 'retrying', 'rate_limited', 'authorization_error', 'provider_rejected', 'connection_error',
          'observer_unknown', 'stopping', 'reallocating')
UUID = re.compile(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}')
SALAD_KEY = None


def millis(value):
    if not isinstance(value, str):
        raise ValueError('Invalid source timestamp')
    value = re.sub(r'\.(\d+)(?=[+-]\d\d:\d\d$)', lambda m: '.'+m[1][:6].ljust(6, '0'), value.replace('Z', '+00:00'))
    return int(datetime.fromisoformat(value).timestamp()*1000)


def iso(value):
    return datetime.fromtimestamp(value/1000, timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def secret(service):
    return subprocess.check_output([str(ROOT/'.runtime/keychain-store'), '--read', '--service', service,
                                    '--account', getpass.getuser()], text=True).strip()


def http(url, header, body=None):
    config = 'header = '+json.dumps(header)+'\nheader = "Content-Type: application/json"\n'
    if body is not None:
        config += 'data-binary = '+json.dumps(json.dumps(body))+'\n'
    response = subprocess.run(['curl', '-sS', '--max-time', '20', '--config', '-', '--write-out', '\n%{http_code}', url],
                              input=config, text=True, capture_output=True, timeout=25)
    raw, _, status = response.stdout.rpartition('\n')
    if response.returncode or status != '200':
        raise RuntimeError('Reading failed (HTTP '+status+')')
    return json.loads(raw)


def request(path, body=None):
    global SALAD_KEY
    if SALAD_KEY is None:
        SALAD_KEY = secret('salad-bandwidth-api')
    try:
        return http('https://api.salad.com/api/public/organizations/ssh3'+path, 'Salad-Api-Key: '+SALAD_KEY, body)
    except RuntimeError as exc:
        if 'HTTP 401' in str(exc) or 'HTTP 403' in str(exc):
            SALAD_KEY = None
        raise


def provider_reading(db):
    path = DATA/'provider.json'
    previous = json.loads(path.read_text()) if path.exists() else {}
    now = int(time.time()*1000)
    if now-previous.get('checked_ms', 0) < 60000:
        return previous
    result = dict(previous, checked_ms=now)
    try:
        session = json.loads(secret('earnfm-read-session'))
        if session['expires_at'] <= time.time():
            raise RuntimeError('EarnFM account login expired; network recording continues')
        responses = {}
        for name in ('view_balance', 'devices_online'):
            response = http('https://api.earn.fm/v2/harvester/'+name, 'X-API-Key: '+session['access_token'])
            if response.get('status') != 200 or not isinstance(response.get('data'), dict):
                raise RuntimeError('EarnFM returned an unsuccessful account response')
            responses[name] = response
        balance = responses['view_balance']['data']
        paid = Decimal(str(balance['bandwidthBalance']))+Decimal(str(balance['bandwidthDCBalance']))
        shared = Decimal(str(balance['totalBandwidthShared']))+Decimal(str(balance['totalDCBandwidthShared']))
        if not paid.is_finite() or not shared.is_finite() or paid < 0 or shared < 0:
            raise RuntimeError('Invalid provider amounts')
        observed = integer(responses['view_balance']['timestamp'])
        baseline_path = DATA/'provider-baseline.json'
        baseline = json.loads(baseline_path.read_text()) if baseline_path.exists() else {'time_ms': observed, 'balance': float(paid), 'gb': float(shared)}
        if not baseline_path.exists():
            baseline_path.write_text(json.dumps(baseline))
        devices = []
        for item in responses['devices_online']['data']['devices']:
            match = UUID.search(item.get('deviceName', ''))
            devices.append({'instance': match[0] if match else None, 'ip': str(ipaddress.ip_address(item['IP'])),
                            'hosting': item.get('isHosting')})
        result = {'checked_ms': now, 'observed_ms': observed, 'devices_observed_ms': integer(responses['devices_online']['timestamp']),
                  'received_ms': int(time.time()*1000), 'balance': float(paid), 'gb': float(shared),
                  'earned': float(paid-Decimal(str(baseline['balance']))),
                  'credited_mb': float((shared-Decimal(str(baseline['gb'])))*1000),
                  'baseline_ms': baseline['time_ms'], 'scope': 'EarnFM account gross balance change; not per-node profit',
                  'devices': devices, 'error': None}
        with db:
            db.execute('INSERT OR IGNORE INTO provider_history VALUES (?,?,?)', (observed, result['received_ms'], json.dumps(result)))
            remember_provider_devices(db, result)
    except Exception as exc:
        result['error'] = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
    temporary = path.with_suffix('.tmp'); temporary.write_text(json.dumps(result)); os.replace(temporary, path)
    return result


def remember_provider_devices(db, reading):
    observed = reading.get('devices_observed_ms', reading.get('observed_ms'))
    if observed is None:
        return
    for device in reading.get('devices', []):
        if device.get('instance') and device.get('ip'):
            db.execute('INSERT INTO provider_devices VALUES (?,?,?) ON CONFLICT(instance) DO UPDATE SET ip=excluded.ip,observed_ms=excluded.observed_ms WHERE excluded.observed_ms>provider_devices.observed_ms',
                       (device['instance'], device['ip'], observed))


def integer(value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value != int(value) or not minimum <= value < 2**53:
        raise ValueError('Invalid integer measurement')
    return int(value)


def parse_record(item, target, recorded_ms):
    if not isinstance(item, dict):
        raise ValueError('Invalid telemetry entry shape')
    row = item.get('json_log')
    if not isinstance(row, dict):
        try:
            row = json.loads(item.get('text_log', ''))
        except (ValueError, TypeError):
            return None
    if row.get('kind') not in ('earnfm_sample', 'earnfm_event'):
        return None
    labels = item.get('resource', {}).get('labels', {})
    if labels.get('container_group_id') and labels['container_group_id'] != target['id']:
        raise ValueError('Telemetry group ID does not match deployment')
    if labels.get('machine_id') != row.get('machine') or not UUID.fullmatch(row.get('machine', '')) or not UUID.fullmatch(row.get('instance', '')):
        raise ValueError('Invalid runtime identity')
    if not isinstance(row.get('run'), str) or not row['run'].startswith(row['instance']+'/') or len(row['run']) > 140:
        raise ValueError('Invalid run identity')
    source_ms = millis(item['time'])
    if source_ms < millis(target['created_at']):
        return None
    detail = {'log_time_ms': source_ms, 'received_ms': millis(item['receive_time']) if item.get('receive_time') else None,
              'recorded_ms': recorded_ms, 'revision': integer(row.get('revision', 1))}
    if row['kind'] == 'earnfm_event':
        event_ms = integer(row['time_ms'], 1)
        if event_ms > recorded_ms+10000:
            raise ValueError('Recovery event source timestamp is in the future')
        for name in ('action', 'reason'):
            if not re.fullmatch('[A-Za-z0-9_]{1,80}', row.get(name, '')):
                raise ValueError('Invalid recovery event')
        return {'event': dict(detail, run=row['run'], instance=row['instance'], machine=row['machine'],
                              time_ms=event_ms, event_seq=integer(row['event_seq']),
                              action=row['action'], reason=row['reason'], http_status=integer(row.get('http_status', 0)),
                              retry_at_ms=integer(row.get('retry_at_ms', 0)))}
    if detail['revision'] not in (1, 2):
        raise ValueError('Unknown EarnFM sample revision')
    result = {k: row.get(k, '') if k in ('ip', 'country') else row[k] for k in FIELDS}
    for name in ('seq', 'start_ms', 'end_ms', 'rx', 'tx', 'total_rx', 'total_tx', 'valid', 'final'):
        result[name] = integer(result[name])
    if not 0 < result['start_ms'] <= result['end_ms'] <= recorded_ms+10000 or result['valid'] not in (0, 1) or result['final'] not in (0, 1) or result['state'] not in STATES:
        raise ValueError('Invalid sample boundary/state')
    if result['ip']:
        result['ip'] = str(ipaddress.ip_address(result['ip']))
    if result['country'] and not re.fullmatch('[A-Z]{2}', result['country']):
        raise ValueError('Invalid country')
    if result['rx'] > result['total_rx'] or result['tx'] > result['total_tx']:
        raise ValueError('Interval exceeds cumulative counter')
    for name in ('control_sockets', 'client_generation', 'retry_at_ms', 'activity_observing', 'activity_window_ms', 'activity_min_bytes', 'activity_bytes', 'activity_elapsed_ms', 'activity_due_ms'):
        detail[name] = integer(row[name], -1 if name == 'control_sockets' else 0) if name in row else None
    detail['error'] = row.get('error') if re.fullmatch('[a-z_]{1,80}', str(row.get('error', ''))) else None
    result['_detail'] = detail
    return result


def cache_sample(db, row):
    if not row['valid'] or row['seq'] == 0:
        return
    start, end = row['start_ms'], row['end_ms']
    span = end-start
    buckets = range(start//60000*60000, ((end-1 if span else end)//60000+1)*60000, 60000)
    used_rx = used_tx = 0
    for bucket in buckets:
        overlap = min(end, bucket+60000)-max(start, bucket) if span else 0
        last = bucket+60000 >= end
        rx = row['rx']-used_rx if last else row['rx']*overlap//span
        tx = row['tx']-used_tx if last else row['tx']*overlap//span
        used_rx += rx; used_tx += tx
        estimated = int(not span or start//60000 != (end-1)//60000)
        db.execute('''INSERT INTO minute_cache VALUES (?,?,?,?,?,?,?,?,?,?,?)
          ON CONFLICT(time_ms,run,ip) DO UPDATE SET rx=rx+excluded.rx,tx=tx+excluded.tx,
          duration_ms=duration_ms+excluded.duration_ms,samples=samples+1,estimated=MAX(estimated,excluded.estimated)''',
                   (bucket, row['run'], row['instance'], row['machine'], row['ip'] or '', row['country'] or '', rx, tx, overlap, 1, estimated))


def database(path):
    db = sqlite3.connect(path, timeout=20); db.row_factory = sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
      CREATE TABLE IF NOT EXISTS samples (run TEXT,seq INTEGER,instance TEXT,machine TEXT,start_ms INTEGER,end_ms INTEGER,
        rx INTEGER,tx INTEGER,total_rx INTEGER,total_tx INTEGER,state TEXT,valid INTEGER,final INTEGER,ip TEXT,country TEXT,PRIMARY KEY(run,seq));
      CREATE INDEX IF NOT EXISTS samples_time ON samples(end_ms);
      CREATE INDEX IF NOT EXISTS samples_run_time ON samples(run,end_ms);
      CREATE TABLE IF NOT EXISTS runs (run TEXT PRIMARY KEY,seq INTEGER,instance TEXT,machine TEXT,start_ms INTEGER,end_ms INTEGER,
        rx INTEGER,tx INTEGER,total_rx INTEGER,total_tx INTEGER,state TEXT,valid INTEGER,final INTEGER,ip TEXT,country TEXT);
      CREATE TABLE IF NOT EXISTS cursors (machine TEXT PRIMARY KEY,time_ms INTEGER);
      CREATE TABLE IF NOT EXISTS collector (name TEXT PRIMARY KEY,value TEXT);
      CREATE TABLE IF NOT EXISTS sample_details (run TEXT,seq INTEGER,body TEXT,PRIMARY KEY(run,seq));
      CREATE TABLE IF NOT EXISTS provider_history (observed_ms INTEGER PRIMARY KEY,received_ms INTEGER,body TEXT);
      CREATE TABLE IF NOT EXISTS provider_devices (instance TEXT PRIMARY KEY,ip TEXT,observed_ms INTEGER);
      CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY,time_ms INTEGER,run TEXT,instance TEXT,machine TEXT,action TEXT,body TEXT);
      CREATE INDEX IF NOT EXISTS events_time ON events(time_ms);
      CREATE TABLE IF NOT EXISTS rejected_records (id TEXT PRIMARY KEY,log_time_ms INTEGER,recorded_ms INTEGER,reason TEXT,body TEXT);
      CREATE INDEX IF NOT EXISTS rejected_time ON rejected_records(log_time_ms);
      CREATE TABLE IF NOT EXISTS observer_status (machine TEXT PRIMARY KEY,time_ms INTEGER,body TEXT);
      CREATE TABLE IF NOT EXISTS observer_success (machine TEXT PRIMARY KEY,time_ms INTEGER);
      CREATE TABLE IF NOT EXISTS minute_cache (time_ms INTEGER,run TEXT,instance TEXT,machine TEXT,ip TEXT,country TEXT,
        rx INTEGER,tx INTEGER,duration_ms INTEGER,samples INTEGER,estimated INTEGER,PRIMARY KEY(time_ms,run,ip));
      CREATE INDEX IF NOT EXISTS minute_cache_run ON minute_cache(run);
    ''')
    for table in ('samples', 'runs'):
        names = {row[1] for row in db.execute('PRAGMA table_info('+table+')')}
        for name in ('ip', 'country'):
            if name not in names:
                db.execute('ALTER TABLE '+table+' ADD COLUMN '+name+' TEXT')
    if not db.execute("SELECT value FROM collector WHERE name='minute_cache_version'").fetchone():
        with db:
            for row in db.execute('SELECT * FROM samples WHERE seq>0 AND valid=1 ORDER BY end_ms'):
                cache_sample(db, row)
            db.execute("INSERT INTO collector VALUES ('minute_cache_version','1')")
    if not db.execute("SELECT value FROM collector WHERE name='observer_success_version'").fetchone():
        with db:
            db.execute('INSERT OR REPLACE INTO observer_success SELECT machine,MAX(end_ms) FROM samples WHERE valid=1 GROUP BY machine')
            db.execute("INSERT INTO collector VALUES ('observer_success_version','1')")
    if not db.execute("SELECT value FROM collector WHERE name='provider_devices_version'").fetchone():
        with db:
            for row in db.execute('SELECT body FROM provider_history ORDER BY observed_ms'):
                remember_provider_devices(db, json.loads(row[0]))
            db.execute("INSERT INTO collector VALUES ('provider_devices_version','1')")
    return db


def ingest(db, records, reject_conflict=None):
    added = 0
    with db:
        for row in records:
            if 'event' in row:
                event = row['event']; identity = event['run']+'/event/'+str(event['event_seq'])
                db.execute('INSERT OR IGNORE INTO events VALUES (?,?,?,?,?,?,?)', (identity, event['time_ms'], event['run'], event['instance'], event['machine'], event['action'], json.dumps(event)))
                if event['action'] == 'observer_error':
                    saved = db.execute('SELECT time_ms FROM observer_success WHERE machine=?', (event['machine'],)).fetchone()
                    success = saved[0] if saved else None
                    if success is None or success <= event['time_ms']:
                        db.execute('INSERT INTO observer_status VALUES (?,?,?) ON CONFLICT(machine) DO UPDATE SET time_ms=excluded.time_ms,body=excluded.body WHERE excluded.time_ms>observer_status.time_ms',
                                   (event['machine'], event['time_ms'], json.dumps(event)))
                continue
            values = tuple(row[k] for k in FIELDS)
            previous = db.execute('SELECT * FROM samples WHERE run=? AND seq=?', (row['run'], row['seq'])).fetchone()
            if previous and any((previous[k] or '') != (row[k] or '') for k in FIELDS):
                if reject_conflict is not None:
                    reject_conflict(row)
                    continue
                raise RuntimeError('Conflicting source sample for one run/sequence; original retained')
            new = db.execute('INSERT OR IGNORE INTO samples ('+','.join(FIELDS)+') VALUES ('+','.join('?' for _ in FIELDS)+')', values).rowcount
            db.execute('INSERT OR IGNORE INTO sample_details VALUES (?,?,?)', (row['run'], row['seq'], json.dumps(row['_detail'])))
            if new:
                cache_sample(db, row); added += 1
            if row['valid']:
                db.execute('INSERT INTO observer_success VALUES (?,?) ON CONFLICT(machine) DO UPDATE SET time_ms=MAX(observer_success.time_ms,excluded.time_ms)', (row['machine'], row['end_ms']))
                db.execute('DELETE FROM observer_status WHERE machine=? AND time_ms<?', (row['machine'], row['end_ms']))
            db.execute('INSERT INTO runs ('+','.join(FIELDS)+') VALUES ('+','.join('?' for _ in FIELDS)+') ON CONFLICT(run) DO UPDATE SET '+','.join(k+'=excluded.'+k for k in FIELDS if k != 'run')+' WHERE excluded.seq>runs.seq', values)
    return added


def collect(db, target, now):
    saved = db.execute("SELECT value FROM collector WHERE name='cursor'").fetchone()
    if saved:
        cursor = int(saved[0])
    else:
        old = db.execute('SELECT MIN(time_ms) FROM cursors').fetchone()[0]
        cursor = old if old is not None else max(target['measurement_started_ms'], now-300000)
    start = max(millis(target['created_at']), min(cursor, now)-120000)
    end = min(now, max(cursor, start)+300000)
    query = 'resource.type = "container" and resource.labels.project_name = "default" and resource.labels.container_group_name = "earnfm-us" and (json_log.kind = "earnfm_sample" or json_log.kind = "earnfm_event")'
    calls = 0
    def fetch(bounds):
        a, b = bounds
        rows = request('/log-entries', {'query': query, 'start_time': iso(a), 'end_time': iso(b), 'page_size': 100, 'sort_order': 'asc'}).get('items')
        if not isinstance(rows, list):
            raise RuntimeError('Invalid telemetry response')
        return rows
    pending = [(start, end)]; items = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        while pending:
            batch, pending = pending[:4], pending[4:]
            calls += len(batch)
            if calls > 128:
                raise RuntimeError('Telemetry page budget exceeded; cursor retained')
            for (a, b), rows in zip(batch, pool.map(fetch, batch)):
                if len(rows) < 100:
                    items.extend(rows)
                elif b-a <= 1:
                    raise RuntimeError('Too many telemetry records at one timestamp; cursor retained')
                else:
                    middle = (a+b)//2
                    pending.extend(((a,middle),(middle,b)))
    recorded = int(time.time()*1000)
    records = []; rejected = []
    for item in items:
        try:
            row = parse_record(item, target, recorded)
            if row is not None: records.append(row)
        except (ValueError, TypeError, KeyError, OverflowError, AttributeError) as exc:
            value = item.get('json_log', {}) if isinstance(item, dict) else {}
            source_time = item.get('time') if isinstance(item, dict) else None
            safe = {key: value[key] for key in (*FIELDS, 'kind', 'revision', 'event_seq', 'time_ms', 'action', 'reason') if key in value} if isinstance(value, dict) else {}
            body = json.dumps({'time': source_time, 'record': safe, 'entry_type': type(item).__name__}, sort_keys=True)
            try: source_ms = millis(source_time)
            except (ValueError, TypeError, KeyError, AttributeError): source_ms = None
            rejected.append((hashlib.sha256(body.encode()).hexdigest(), source_ms, recorded, str(exc)[:240], body))
    def reject_conflict(row):
        body = json.dumps({key: row[key] for key in FIELDS}, sort_keys=True)
        rejected.append((hashlib.sha256(body.encode()).hexdigest(), row['_detail']['log_time_ms'], recorded,
                         'Conflicting run/sequence; original sample retained', body))
    with db:
        count = ingest(db, records, reject_conflict)
        for value in rejected:
            db.execute('INSERT OR IGNORE INTO rejected_records VALUES (?,?,?,?,?)', value)
        db.execute("INSERT OR REPLACE INTO collector VALUES ('cursor',?)", (str(end),))
    return {'cursor_ms': end, 'calls': calls, 'inserted': count, 'rejected': len(rejected), 'caught_up': end >= now}


def record_inventory(db, inventory, observed):
    saved = db.execute("SELECT value FROM collector WHERE name='inventory'").fetchone()
    previous = {x['id']: x for x in json.loads(saved[0])} if saved else {}
    current = {x['id']: {'id': x['id'], 'machine_id': x['machine_id'], 'state': x['state'], 'update_time': x['update_time']} for x in inventory}
    with db:
        for identity in previous.keys() | current.keys():
            old, new = previous.get(identity), current.get(identity)
            if old == new:
                continue
            value = new or dict(old, state='removed')
            event = dict(value, time_ms=observed, source='Salad inventory observation')
            key = 'inventory/'+identity+'/'+value['state']+'/'+str(observed)
            db.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?)', (key, observed, '', identity, value['machine_id'], 'inventory_'+value['state'], json.dumps(event)))
        db.execute("INSERT OR REPLACE INTO collector VALUES ('inventory',?)", (json.dumps(list(current.values())),))


def snapshot(db, target, inventory, observed_ms, provider, error=None, collection=None):
    now = int(time.time()*1000)
    latest_rows = db.execute('SELECT r.*,d.body AS detail FROM runs r LEFT JOIN sample_details d ON d.run=r.run AND d.seq=r.seq').fetchall()
    latest = {}
    for row in latest_rows:
        if row['machine'] not in latest or row['end_ms'] > latest[row['machine']]['end_ms']:
            latest[row['machine']] = row
    online = {x['instance']: x for x in provider.get('devices', []) if x.get('instance')}
    observer_errors = {row['machine']:json.loads(row['body']) for row in db.execute('SELECT * FROM observer_status')}
    last_seen = {row['instance']:row for row in db.execute('SELECT * FROM provider_devices')}
    workers = []
    for node in inventory:
        row = latest.get(node['machine_id']); detail = json.loads(row['detail']) if row and row['detail'] else {}
        identity = row['instance'] if row else node['id']; peer = online.get(identity, {})
        previous_peer = last_seen.get(identity)
        public_ip = peer.get('ip') or (row['ip'] if row else None)
        issue = observer_errors.get(node['machine_id'])
        received = detail.get('received_ms')
        recorded = detail.get('recorded_ms')
        # Collector time is assigned only when this run/sequence is first ingested.
        # Salad's independent receipt clock can precede the source by minutes.
        receipt_fresh = isinstance(recorded, int) and 0 <= now-recorded < 90000
        fresh = bool(row and not issue and receipt_fresh and 0 <= now-row['end_ms'] < 90000 and not row['final'])
        provider_fresh = not provider.get('error') and 0 <= now-provider.get('devices_observed_ms', provider.get('observed_ms', 0)) < 180000
        totals = db.execute('SELECT SUM(rx+tx),SUM(duration_ms) FROM minute_cache WHERE run=?', (row['run'],)).fetchone() if row else (None, None)
        rate = db.execute('SELECT SUM((rx+tx)*1.0*(end_ms-MAX(start_ms,?))/(end_ms-start_ms)),SUM(end_ms-MAX(start_ms,?)) FROM samples WHERE run=? AND seq>0 AND valid=1 AND end_ms>start_ms AND end_ms>?', (row['end_ms']-60000,row['end_ms']-60000,row['run'],row['end_ms']-60000)).fetchone() if row else (None, None)
        state = row['state'] if row else 'awaiting_sample'
        if issue: state = 'observer_unknown'
        note = {'connecting':'No established control socket; replacement after 120 seconds', 'connection_error':'Native connection errors; recovery active',
                'authorization_error':'Account key rejected; waiting for the recorded retry. Check the EarnFM Docker credential.',
                'provider_rejected':'Provider rejected the handshake; waiting for the recorded retry. Check account restrictions.',
                'observer_unknown':'Control socket inspection unavailable', 'rate_limited':'Provider cooldown; retry at the recorded deadline',
                'reallocating':'Replacement requested; waiting for the current inventory', 'retrying':'Restarting after a low-activity window'}.get(state, '')
        if issue: note = issue['reason'].replace('_',' ')+': traffic observation unavailable since '+iso(issue['time_ms'])
        if row and not receipt_fresh: note += ('; ' if note else '')+'Recorder receipt is stale or unavailable; current native state and traffic are unverified'
        clock_note = ''
        if row and isinstance(received, int) and received < row['end_ms']-10000:
            clock_note = 'Salad receipt clock precedes source by '+str(round((row['end_ms']-received)/1000))+'s; freshness uses source and first recorder receipt'
        workers.append({'instance':node['id'],'runtime_instance':identity,'machine':node['machine_id'],'run':row['run'] if row else None,
            'salad_state':node['state'],'client_state':state,'provider_online':bool(fresh and node['state']=='running' and state=='running' and provider_fresh and identity in online),
            'ip':public_ip,'country':row['country'] if row and peer.get('ip') and peer['ip']==row['ip'] else None,'error':note,
            'last_provider_ip':previous_peer['ip'] if previous_peer else None,'last_provider_seen_ms':previous_peer['observed_ms'] if previous_peer else None,
            'sample_ms':row['end_ms'] if row else None,'received_ms':detail.get('received_ms'),'recorded_ms':detail.get('recorded_ms'),
            'freshness_basis':'source_and_first_recorder_receipt','telemetry_note':clock_note,
            'total_mb':totals[0]/1e6 if totals[0] is not None else None,'recorded_duration_ms':totals[1],
            'kb_per_second':rate[0]/rate[1] if fresh and rate[1] and node['state']=='running' else None,
            'final':bool(row['final']) if row else False,'health':detail,'observation_error':issue})
    points = {}; identities = {}; history_nodes = []
    start = max(target['measurement_started_ms']//60000*60000, now//60000*60000-1439*60000)
    for row in db.execute('SELECT * FROM minute_cache WHERE time_ms>=? ORDER BY time_ms', (start,)):
        point = points.setdefault(row['time_ms'], {'time_ms':row['time_ms'],'mb':0,'duration_ms':0,'contributions':[],'by_instance':{},'estimated':False})
        mb = (row['rx']+row['tx'])/1e6; point['mb'] += mb; point['duration_ms'] += row['duration_ms']; point['estimated'] |= bool(row['estimated'])
        identity = (row['run'], row['ip'], row['country'])
        if identity not in identities:
            identities[identity] = len(history_nodes)
            history_nodes.append({'instance':row['instance'],'machine':row['machine'],'run':row['run'],'ip':row['ip'] or None,'country':row['country'] or None})
        point['contributions'].append([identities[identity], mb, row['duration_ms']])
        # Keep the existing page usable while the shared frontend rolls forward independently.
        point['by_instance'][row['instance']] = point['by_instance'].get(row['instance'], 0)+mb
    for point in points.values(): point['partial'] = point['duration_ms'] < 60000*target['desired']
    total = db.execute('SELECT SUM(rx+tx) FROM minute_cache').fetchone()[0]
    recent = []
    for row in db.execute("SELECT body FROM events WHERE action IN ('reallocate_requested','reallocate_accepted','reallocate_failed','client_restart','cooldown_started') ORDER BY time_ms DESC LIMIT 12"):
        value = json.loads(row[0]); value['old_instance_present'] = any(n['id']==value['instance'] or n['machine_id']==value['machine'] for n in inventory); recent.append(value)
    history = db.execute('SELECT COUNT(*),MIN(observed_ms),MAX(observed_ms) FROM provider_history').fetchone()
    rejected = db.execute('SELECT COUNT(*),MAX(recorded_ms) FROM rejected_records').fetchone()
    return {'generated_ms':now,'inventory_ms':observed_ms,'error':error,'test_started_ms':target['measurement_started_ms'],'desired':target['desired'],
            'group':'ssh3/default/earnfm-us','workers':workers,'points':list(points.values()),'history_nodes':history_nodes,'total_mb':total/1e6 if total is not None else None,
            'counter_total_mb':sum(r['total_rx']+r['total_tx'] for r in latest_rows)/1e6,'sample_count':db.execute('SELECT COUNT(*) FROM samples').fetchone()[0],
            'database_bytes':sum(p.stat().st_size for p in (DATA/'traffic.sqlite3',DATA/'traffic.sqlite3-wal') if p.exists()),
            'provider':provider,'provider_history':{'observations':history[0],'first_ms':history[1],'last_ms':history[2]},'recent_recovery':recent,'collection':collection,
            'telemetry_rejections':{'count':rejected[0],'last_ms':rejected[1]},
            'basis':'Recorded eth0 RX + TX intervals, including relay crossings and overhead. Provider credits are separate account observations.'}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--once',action='store_true'); args=parser.parse_args()
    os.umask(0o077); DATA.mkdir(parents=True,exist_ok=True)
    lock=(DATA/'recorder.lock').open('a'); fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    db=database(DATA/'traffic.sqlite3'); inventory=[]; observed=None
    while True:
        began=time.monotonic(); target=json.loads((DATA/'target.json').read_text()); error=None; collection=None
        try:
            group=request('/projects/default/containers/earnfm-us')
            if group['id']!=target['id'] or group['container']['image']!=target['image']: raise RuntimeError('EarnFM deployment identity changed')
            bound=db.execute("SELECT value FROM collector WHERE name='group_id'").fetchone()
            if bound and bound[0]!=target['id']: raise RuntimeError('Ledger belongs to another deployment')
            with db: db.execute("INSERT OR IGNORE INTO collector VALUES ('group_id',?)",(target['id'],))
            inventory=request('/projects/default/containers/earnfm-us/instances')['instances']; observed=int(time.time()*1000)
            record_inventory(db,inventory,observed); collection=collect(db,target,observed)
        except Exception as exc: error=type(exc).__name__+': '+str(exc)
        output=snapshot(db,target,inventory,observed,provider_reading(db),error,collection)
        OUTPUT.parent.mkdir(parents=True,exist_ok=True); temporary=OUTPUT.with_suffix('.tmp'); temporary.write_text(json.dumps(output,separators=(',',':'))); os.replace(temporary,OUTPUT)
        if args.once:
            print(json.dumps({'workers':len(output['workers']),'samples':output['sample_count'],'total_mb':output['total_mb'],'error':error})); break
        time.sleep(max(1,(15 if error or collection and not collection['caught_up'] else 60)-(time.monotonic()-began)))
    db.close()


if __name__=='__main__': main()
