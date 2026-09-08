#!/usr/bin/env python3
"""Record Grass native health, recovery, traffic and provider observations."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import getpass
import time
import uuid

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('GRASS_DATA_DIR', str(Path.home() / '.hg1/grass')))
ORG = os.environ.get('GRASS_ORGANIZATION', 'cosmosgeeketh')
PROJECT = os.environ.get('GRASS_PROJECT', 'default')
GROUP = os.environ.get('GRASS_GROUP', 'grass')
PATH = '/projects/' + PROJECT + '/containers/' + GROUP
FRESH_MS = 90_000
PROVIDER_FRESH_MS = 180_000
LABELS = {'connected': 'Connected', 'starting': 'Starting', 'offline': 'Disconnected',
    'client_missing': 'Client not running', 'client_stalled': 'Client stalled',
    'network_rejected': 'Network quality rejected', 'login_required': 'Sign-in required',
    'unknown': 'Grass status unavailable', 'stopping': 'Stopping'}


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, separators=(',', ':'), allow_nan=False))
    os.replace(temporary, path)


def api(key, path, body=None):
    config = 'header = ' + json.dumps('Salad-Api-Key: ' + key) + '\nheader = "Content-Type: application/json"\n'
    if body is not None:
        config += 'data-binary = ' + json.dumps(json.dumps(body)) + '\n'
    response = subprocess.run(['curl', '-sS', '--max-time', '20', '--config', '-',
        '--write-out', '\n%{http_code}', 'https://api.salad.com/api/public/organizations/' + ORG + path],
        input=config, text=True, capture_output=True, timeout=25)
    if response.returncode:
        raise RuntimeError('Salad transport request failed')
    raw, status = response.stdout.rsplit('\n', 1)
    if status != '200':
        raise RuntimeError('Salad read returned HTTP ' + status)
    return json.loads(raw)


def integer(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value != int(value) or not 0 <= value < 2**53:
        raise ValueError('Invalid ' + name)
    return int(value)


def parse_record(entry, received_ms):
    text = entry.get('text_log', '')
    if not text.startswith(('GRASS_SAMPLE_V1 ', 'GRASS_SAMPLE_V2 ', 'GRASS_EVENT_V2 ')):
        return None
    row = json.loads(text.split(' ', 1)[1])
    revision, kind = row.get('revision'), row.get('kind')
    if revision not in (1, 2) or kind not in ('grass_sample', 'grass_event'):
        return None
    for name in ('instance', 'machine'):
        if str(uuid.UUID(row[name])) != row[name]:
            raise ValueError('Invalid native identity')
    if not isinstance(row.get('run'), str) or not row['run'].startswith(row['instance'] + ':' + row['machine'] + ':'):
        raise ValueError('Invalid native run')
    row['source_ms'] = integer(row['source_ms'], 'source time')
    if row['source_ms'] > received_ms + 10_000:
        raise ValueError('Future native source time')
    if revision == 2 and str(uuid.UUID(row['group_id'])) != row['group_id']:
        raise ValueError('Invalid native group')
    if kind == 'grass_sample':
        for name in ('rx', 'tx', 'monotonic_ms'):
            row[name] = integer(row[name], name)
        if row.get('ip') is not None:
            row['ip'] = str(ipaddress.ip_address(row['ip']))
        if row.get('country') is not None and not re.fullmatch('[A-Z]{2}', row['country']):
            raise ValueError('Invalid native country')
        if revision == 2:
            row['seq'] = integer(row['seq'], 'sequence')
            health = row['health']
            if health.get('state') not in LABELS:
                raise ValueError('Invalid native health state')
            integer(health['observed_ms'], 'health time')
            if health.get('account_id') is not None and not isinstance(health['account_id'], str):
                raise ValueError('Invalid provider account identity')
            if health.get('pid') is not None:
                integer(health['pid'], 'client process')
            if health['state'] == 'connected' and (not health.get('pid') or not health.get('device_id') or not row.get('ip')):
                raise ValueError('Connected status lacks native identity')
            if type(row.get('final')) is not bool:
                raise ValueError('Invalid final-sample flag')
            provider = row.get('provider') or {}
            if provider.get('observed_ms') is not None:
                integer(provider['observed_ms'], 'provider time')
                for name in ('network_points', 'total_points'):
                    value = provider[name]
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                        raise ValueError('Invalid provider points')
    elif not isinstance(row.get('event'), str):
        raise ValueError('Invalid native event')
    row['recorded_ms'] = received_ms
    return row


def collect(key, start, end):
    iso = lambda ms: datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    calls = 0

    def fetch(begin, stop):
        nonlocal calls
        calls += 1
        if calls > 64:
            raise RuntimeError('Grass log window exceeded its pagination budget; cursor retained')
        result = api(key, '/log-entries', {'query': 'resource.type = "container" and resource.labels.project_name = "' + PROJECT + '" and resource.labels.container_group_name = "' + GROUP + '" and (text_log startswith "GRASS_SAMPLE_V" or text_log startswith "GRASS_EVENT_V2 ")',
            'start_time': iso(begin), 'end_time': iso(stop), 'page_size': 100, 'sort_order': 'asc'})
        rows = result.get('items')
        if not isinstance(rows, list):
            raise RuntimeError('Grass log response has no record list')
        if len(rows) < 100:
            return rows
        middle = (begin + stop) // 2
        if middle <= begin:
            raise RuntimeError('Grass log timestamp contains an incomplete capped page; cursor retained')
        return fetch(begin, middle) + fetch(middle, stop)

    records = []
    for entry in fetch(start, end):
        try:
            row = parse_record(entry, int(time.time() * 1000))
        except (ValueError, KeyError, TypeError, AttributeError):
            raise RuntimeError('A Grass native record is malformed; cursor retained') from None
        if row is not None:
            records.append(row)
    return records


def update_interval(db, run, source_ms):
    current = db.execute('SELECT body FROM samples WHERE run=? AND source_ms=?', (run, source_ms)).fetchone()
    previous = db.execute('SELECT body FROM samples WHERE run=? AND source_ms<? ORDER BY source_ms DESC LIMIT 1', (run, source_ms)).fetchone()
    if current is None or previous is None:
        return
    current, previous = json.loads(current[0]), json.loads(previous[0])
    elapsed = current['source_ms'] - previous['source_ms']
    monotonic = current['monotonic_ms'] - previous['monotonic_ms']
    rx, tx = current['rx'] - previous['rx'], current['tx'] - previous['tx']
    reason = None
    if elapsed <= 0 or monotonic <= 0 or abs(elapsed - monotonic) > 5000:
        reason = 'clock boundary'
    elif rx < 0 or tx < 0:
        reason = 'counter reset'
    elif not current.get('ip') or not previous.get('ip') or current['ip'] != previous['ip']:
        reason = 'IP boundary'
    elif db.execute('SELECT 1 FROM conflicts WHERE run=? AND source_ms IN (?,?) LIMIT 1', (run, source_ms, previous['source_ms'])).fetchone():
        reason = 'conflicting native sample'
    valid = reason is None
    old = db.execute('SELECT rx+tx,duration_ms,valid FROM intervals WHERE run=? AND source_ms=?', (run, source_ms)).fetchone()
    old_bytes, old_duration, old_count = (old[0], old[1], 1) if old and old[2] else (0, 0, 0)
    new_bytes, new_duration, new_count = (rx + tx, elapsed, 1) if valid else (0, 0, 0)
    db.execute('INSERT OR REPLACE INTO intervals VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (run, source_ms, current['instance'], current['machine'], current.get('group_id'), current.get('ip'), current.get('country'),
         previous['source_ms'], rx, tx, elapsed, int(valid), reason))
    db.execute('INSERT INTO totals VALUES(?,?,?,?,?,?) ON CONFLICT(run) DO UPDATE SET bytes=bytes+excluded.bytes, duration_ms=duration_ms+excluded.duration_ms, intervals=intervals+excluded.intervals, started_ms=min(started_ms,excluded.started_ms)',
        (run, current['instance'], new_bytes-old_bytes, new_duration-old_duration, new_count-old_count, previous['source_ms']))


def open_database(path):
    db = sqlite3.connect(path)
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
        CREATE TABLE IF NOT EXISTS samples(run TEXT,source_ms INTEGER,body TEXT,PRIMARY KEY(run,source_ms));
        CREATE TABLE IF NOT EXISTS state(name TEXT PRIMARY KEY,value INTEGER);
        CREATE INDEX IF NOT EXISTS sample_instance_time ON samples(json_extract(body,'$.instance'),source_ms);
        CREATE INDEX IF NOT EXISTS sample_source_time ON samples(source_ms);
        CREATE TABLE IF NOT EXISTS conflicts(run TEXT,source_ms INTEGER,body TEXT,PRIMARY KEY(run,source_ms,body));
        CREATE TABLE IF NOT EXISTS intervals(run TEXT,source_ms INTEGER,instance TEXT,machine TEXT,group_id TEXT,ip TEXT,country TEXT,start_ms INTEGER,rx INTEGER,tx INTEGER,duration_ms INTEGER,valid INTEGER,reason TEXT,PRIMARY KEY(run,source_ms));
        CREATE INDEX IF NOT EXISTS interval_time ON intervals(source_ms);
        CREATE TABLE IF NOT EXISTS totals(run TEXT PRIMARY KEY,instance TEXT,bytes INTEGER,duration_ms INTEGER,intervals INTEGER,started_ms INTEGER);
        CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,source_ms INTEGER,instance TEXT,machine TEXT,event TEXT,action TEXT,body TEXT);
        CREATE INDEX IF NOT EXISTS event_time ON events(source_ms);
        CREATE INDEX IF NOT EXISTS event_kind_time ON events(event,action,source_ms);
        CREATE INDEX IF NOT EXISTS event_instance_time ON events(instance,machine,event,source_ms);
        CREATE TABLE IF NOT EXISTS provider(scope TEXT,observed_ms INTEGER,body TEXT,PRIMARY KEY(scope,observed_ms));
        CREATE INDEX IF NOT EXISTS provider_time ON provider(observed_ms);
    ''')
    if not db.execute("SELECT 1 FROM state WHERE name='derived_v2'").fetchone():
        with db:
            for run, source_ms in db.execute('SELECT run,source_ms FROM samples ORDER BY run,source_ms'):
                update_interval(db, run, source_ms)
            db.execute("INSERT INTO state VALUES('derived_v2',1)")
    return db


def ingest(db, records, group_id):
    inserted = 0
    with db:
        for row in sorted(records, key=lambda r: (r['source_ms'], r['run'])):
            if row.get('revision') == 2 and row.get('group_id') != group_id:
                continue
            if row['kind'] == 'grass_event':
                native = {k: v for k, v in row.items() if k != 'recorded_ms'}
                event_id = hashlib.sha256(json.dumps(native, sort_keys=True).encode()).hexdigest()
                db.execute('INSERT OR IGNORE INTO events VALUES(?,?,?,?,?,?,?)', (event_id, row['source_ms'], row['instance'], row['machine'], row['event'], row.get('action'), json.dumps(row)))
                continue
            old = db.execute('SELECT body FROM samples WHERE run=? AND source_ms=?', (row['run'], row['source_ms'])).fetchone()
            if old:
                original = json.loads(old[0])
                clean = lambda value: {k: v for k, v in value.items() if k != 'recorded_ms'}
                if clean(original) == clean(row):
                    continue
                db.execute('INSERT OR IGNORE INTO conflicts VALUES(?,?,?)', (row['run'], row['source_ms'], json.dumps(row)))
            else:
                db.execute('INSERT INTO samples VALUES(?,?,?)', (row['run'], row['source_ms'], json.dumps(row)))
                inserted += 1
            update_interval(db, row['run'], row['source_ms'])
            next_row = db.execute('SELECT source_ms FROM samples WHERE run=? AND source_ms>? ORDER BY source_ms LIMIT 1', (row['run'], row['source_ms'])).fetchone()
            if next_row:
                update_interval(db, row['run'], next_row[0])
            provider = row.get('provider') or {}
            if provider.get('observed_ms') and not provider.get('error') and not db.execute('SELECT 1 FROM conflicts WHERE run=? AND source_ms=?', (row['run'], row['source_ms'])).fetchone():
                scope = '|'.join(str(provider.get(k, '')) for k in ('account_id', 'stage', 'start_date', 'end_date'))
                reading = dict(provider, sample_run=row['run'], sample_ms=row['source_ms'])
                db.execute('INSERT OR IGNORE INTO provider VALUES(?,?,?)', (scope, provider['observed_ms'], json.dumps(reading)))
    return inserted


def view(db, inventory, inventory_ms, desired, error=None, history_note=None, now=None):
    now = int(time.time() * 1000) if now is None else now
    totals = {row[0]: row[1:] for row in db.execute('SELECT instance,SUM(bytes),SUM(duration_ms),SUM(intervals),MIN(started_ms) FROM totals GROUP BY instance')}
    minutes = {}
    cutoff = (now // 60000 - 1439) * 60000
    for run, source_ms, instance, machine, group, ip, country, start, rx, tx, duration, valid, reason in db.execute('SELECT * FROM intervals WHERE source_ms>=? AND valid=1 AND duration_ms<=90000 ORDER BY source_ms', (cutoff,)):
        amount = (rx + tx) / 1e6
        bucket = max(start // 60000 * 60000, cutoff)
        while bucket < source_ms:
            overlap = max(0, min(source_ms, bucket+60000) - max(start, bucket))
            if overlap:
                minute = minutes.setdefault(bucket, {'minute_ms': bucket, 'mb': 0.0, 'estimated': False, 'coverage': {}, 'nodes': {}})
                part = amount * overlap / duration
                node = minute['nodes'].setdefault((instance, ip), {'instance': instance, 'ip': ip, 'country': country, 'mb': 0.0})
                node['mb'] += part
                minute['mb'] += part
                minute['coverage'][instance] = minute['coverage'].get(instance, 0) + overlap
                minute['estimated'] |= start != bucket or source_ms != bucket+60000
            bucket += 60000
    workers, native = [], []
    for instance in inventory:
        ident = instance['id']
        record = db.execute("SELECT body FROM samples WHERE json_extract(body,'$.instance')=? AND json_extract(body,'$.machine')=? ORDER BY source_ms DESC LIMIT 1", (ident, instance['machine_id'])).fetchone()
        sample = json.loads(record[0]) if record else None
        fresh = sample is not None and 0 <= now-sample['source_ms'] <= FRESH_MS
        health = (sample or {}).get('health') or {}
        current_health = fresh and 0 <= now-health.get('observed_ms', 0) <= FRESH_MS
        conflict = sample and db.execute('SELECT 1 FROM conflicts WHERE run=? AND source_ms=? LIMIT 1', (sample['run'], sample['source_ms'])).fetchone()
        state, problem, working, note = 'Awaiting native sample', 'No fresh measurement from this instance', None, None
        recovery = (sample or {}).get('recovery') or {}
        if current_health and not conflict:
            state = LABELS[health['state']]
            problem = health.get('error')
            working = None if health['state'] == 'unknown' else health['state'] == 'connected' and not problem
            if health.get('quality') is not None:
                note = f"Provider network quality: {health['quality']:g}%"
            if problem and health.get('next_check_ms', 0) > now:
                note = f"Next status attempt in {(health['next_check_ms']-now)/1000:.0f}s"
            if recovery.get('phase') == 'restarting':
                state, working = 'Restarting Grass', False
            elif recovery.get('phase') == 'reallocating':
                state, working = 'Reallocating', False
            if recovery.get('requested_ms'):
                when = datetime.fromtimestamp(recovery['requested_ms']/1000, timezone.utc).isoformat(timespec='seconds')
                result = recovery.get('phase', recovery.get('last_action', 'requested'))
                detail = f"Recovery {result}: {recovery.get('last_reason', 'unknown')}; requested at {when}"
                note = '; '.join(x for x in (note, detail, recovery.get('error')) if x)
            if not (sample or {}).get('replacement_ready'):
                note = '; '.join(x for x in (note, 'Machine replacement awaits the initial login backup') if x)
        elif fresh and sample.get('revision') == 1:
            state, problem = 'Legacy sampler; health unavailable', 'This instance still has the old sampler, without live provider checks'
        elif conflict:
            state, problem = 'Conflicting native data', 'Conflicting records share the same run and source timestamp'
        elif fresh:
            state, problem = 'Grass status delayed', health.get('error') or 'The native health observation is stale'
        boot = db.execute("SELECT body FROM events WHERE instance=? AND machine=? AND event='bootstrap_failed' AND source_ms>? ORDER BY source_ms DESC LIMIT 1", (ident, instance['machine_id'], max(now-FRESH_MS, sample['source_ms'] if sample else 0))).fetchone() if not fresh else None
        if boot:
            boot = json.loads(boot[0])
            state, problem = 'Setup failed', f"Grass startup failed at {boot.get('reason')}; exit {boot.get('exit_code')}"
        interval = db.execute('SELECT rx+tx,duration_ms,valid,reason FROM intervals WHERE run=? AND source_ms=?', (sample['run'], sample['source_ms'])).fetchone() if sample else None
        total = totals.get(ident)
        valid_total = total is not None and total[2] > 0
        rate = interval[0] * 60000 / interval[1] / 1e6 if interval and interval[2] and 0 < interval[1] <= 90000 and fresh else None
        if interval and not interval[2]:
            note = '; '.join(x for x in (note, 'Traffic interval excluded: ' + interval[3]) if x)
        if sample and sample.get('final'):
            state, working, rate = 'Stopping', False, None
        if instance['state'] != 'running':
            working, rate = False, None
        if error or not inventory_ms or now-inventory_ms > FRESH_MS:
            working, rate = None, None
        workers.append({'id': ident, 'ip': sample.get('ip') if sample else None, 'country': sample.get('country') if sample else None,
            'client_status': state, 'salad_state': instance['state'], 'working': working, 'mb_per_minute': rate,
            'total_mb': total[0]/1e6 if valid_total else None, 'recorded_duration_ms': total[1] if valid_total else None,
            'recorded_ms': sample.get('recorded_ms') if sample else None, 'sample_ms': sample['source_ms'] if sample else None,
            'error': problem, 'note': note})
        if sample:
            native.append(sample)
    history = []
    for minute in sorted(minutes.values(), key=lambda row: row['minute_ms']):
        coverage = minute.pop('coverage')
        minute['nodes'] = sorted(minute['nodes'].values(), key=lambda node: -node['mb'])
        minute['count'] = len(coverage)
        minute['partial'] = len(coverage) < desired or any(value < 60000 for value in coverage.values())
        history.append(minute)
    good_provider = "NOT EXISTS (SELECT 1 FROM conflicts WHERE run=json_extract(provider.body,'$.sample_run') AND source_ms=json_extract(provider.body,'$.sample_ms'))"
    reading = db.execute('SELECT scope,body FROM provider WHERE '+good_provider+' ORDER BY observed_ms DESC LIMIT 1').fetchone()
    credited, provider_note = None, 'Provider points have not been recorded yet.'
    provider_errors = [x.get('provider', {}).get('error') for x in native if x.get('provider')]
    if reading:
        scope, provider = reading[0], json.loads(reading[1])
        accounts = {x.get('health', {}).get('account_id') for x in native if x.get('health', {}).get('account_id')}
        if not accounts or accounts == {provider.get('account_id')}:
            age = now-provider['observed_ms']
            stale = not 0 <= age <= PROVIDER_FRESH_MS or any(provider_errors)
            credited = f"{provider['network_points']} Network Points" + (' (stale)' if stale else '')
            when = datetime.fromtimestamp(provider['observed_ms']/1000, timezone.utc).isoformat(timespec='seconds')
            first = json.loads(db.execute('SELECT body FROM provider WHERE scope=? AND '+good_provider+' ORDER BY observed_ms LIMIT 1', (scope,)).fetchone()[0])
            delta = provider['network_points']-first['network_points']
            provider_note = (f"Provider account-wide finalized {provider.get('epoch', 'epoch')} values: {provider['network_points']} Network Points; "
                f"{provider['total_points']} total points including other rewards. Observed {when}; provider record updated {provider.get('modified_at', 'unknown')}. "
                f"Network Points change since this scope's first observation: {delta:+g}. Cash earnings are not reported.")
    if any(provider_errors):
        provider_note += ' ' + next(value for value in provider_errors if value)
    if desired == 1:
        for sample, worker in zip(native, [w for w in workers if w['sample_ms'] is not None]):
            if worker['working'] is not True:
                continue
            for event_id, raw in db.execute("SELECT id,body FROM events WHERE event='accepted' AND action='reallocate' ORDER BY source_ms DESC LIMIT 20").fetchall():
                event = json.loads(raw)
                first_seen = db.execute("SELECT MIN(source_ms) FROM samples WHERE json_extract(body,'$.instance')=?", (sample['instance'],)).fetchone()[0]
                if event.get('group_id') == sample.get('group_id') and event['machine'] != sample['machine'] and first_seen > event['source_ms']:
                    confirmation = dict(kind='grass_event', revision=2, event='replacement_connected', action='reallocate',
                        source_ms=sample['source_ms'], recorded_ms=now, group_id=sample.get('group_id'), instance=sample['instance'],
                        machine=sample['machine'], previous_instance=event['instance'], previous_machine=event['machine'],
                        request_id=event_id, reason=event.get('reason'), requested_ms=event.get('request_ms'), ip=sample.get('ip'))
                    with db:
                        db.execute('INSERT OR IGNORE INTO events VALUES(?,?,?,?,?,?,?)', (event_id+':connected', sample['source_ms'], sample['instance'], sample['machine'], 'replacement_connected', 'reallocate', json.dumps(confirmation)))
                    break
    last_recovery = db.execute("SELECT body FROM events WHERE action IN ('restart_app','reallocate','replacement_requires_seed') ORDER BY source_ms DESC, CASE event WHEN 'replacement_connected' THEN 6 WHEN 'recovered' THEN 5 WHEN 'failed' THEN 4 WHEN 'unconfirmed' THEN 4 WHEN 'replacement_unavailable' THEN 4 WHEN 'accepted' THEN 3 WHEN 'response' THEN 2 ELSE 1 END DESC LIMIT 1").fetchone()
    recovery_note = ''
    if last_recovery:
        event = json.loads(last_recovery[0])
        when = datetime.fromtimestamp(event['source_ms']/1000, timezone.utc).isoformat(timespec='seconds')
        recovery_note = (f" Latest recorded recovery: {event['action'].replace('_', ' ')} — {event['event'].replace('_', ' ')}"
            + (f" ({event['reason'].replace('_', ' ')})" if event.get('reason') else '')
            + f" at {when}; instance {event['instance']}, machine {event['machine']}.")
        if event['event'] == 'accepted' and event['action'] == 'reallocate':
            recovery_note += ' Waiting for a provider-confirmed replacement.'
    starts = [row[0] for row in db.execute('SELECT MIN(source_ms) FROM samples') if row[0] is not None]
    known = sum(row[2] for row in totals.values())
    inventory_fresh = inventory_ms is not None and 0 <= now-inventory_ms <= FRESH_MS and not error
    unknown = any(w['working'] is None for w in workers if w['salad_state'] == 'running')
    return {'generated_ms': now, 'inventory_ms': inventory_ms, 'desired': desired,
        'running': sum(x['state'] == 'running' for x in inventory) if inventory_fresh else None,
        'working': sum(w['working'] is True for w in workers) if inventory_fresh and not unknown else None,
        'started_ms': min(starts) if starts else None, 'total_mb': sum(row[0] for row in totals.values())/1e6 if known else None,
        'credited_text': credited, 'earned_text': None, 'error': error, 'workers': workers, 'minutes': history,
        'credit_note': ('Raw container receive + send traffic includes monitoring, setup and viewer traffic; it is not sold bandwidth. '
            'Minute allocation is estimated when intervals cross boundaries. Long gaps contribute measured endpoint totals without invented minute bars. '
            + provider_note + recovery_note + (' History recovery: ' + history_note if history_note else ''))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    DATA.mkdir(parents=True, exist_ok=True)
    lock = (DATA/'recorder.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    key = os.environ.get('SALAD_API_KEY')
    if not key:
        helper = Path(os.environ.get('SALAD_KEYCHAIN_HELPER', str(ROOT.parent/'.runtime/keychain-store')))
        if not helper.is_file():
            helper = Path.home()/'Library/Application Support/Salad Bandwidth Dashboard/.runtime/keychain-store'
        key = subprocess.check_output([str(helper), '--read', '--service', 'salad-bandwidth-api', '--account', getpass.getuser()], text=True).strip()
    db = open_database(DATA/'traffic.sqlite3')
    saved = db.execute("SELECT value FROM state WHERE name='cursor'").fetchone()
    cursor = saved[0] if saved else int(time.time()*1000)-600000
    inventory, inventory_ms, desired = [], None, 1
    while True:
        began, error, history_note = time.monotonic(), None, None
        try:
            group = api(key, PATH)
            desired = group['replicas']
            inventory = api(key, PATH+'/instances').get('instances', [])
            inventory_ms = int(time.time()*1000)
            records = collect(key, max(0, inventory_ms-120000), inventory_ms)
            ingest(db, records, group['id'])
            if cursor < inventory_ms-120000:
                history_note = 'Earlier native records are still being recovered; missing bars are not zero.'
                save(DATA/'view.json', view(db, inventory, inventory_ms, desired, history_note=history_note))
                end = min(cursor+600000, inventory_ms)
                try:
                    ingest(db, collect(key, max(0, cursor-120000), end), group['id'])
                    cursor = end
                except Exception as failure:
                    history_note = str(failure) if isinstance(failure, RuntimeError) else type(failure).__name__
            else:
                cursor = inventory_ms
            with db:
                db.execute("INSERT OR REPLACE INTO state VALUES('cursor',?)", (cursor,))
        except Exception as failure:
            error = str(failure) if isinstance(failure, RuntimeError) else type(failure).__name__
        output = view(db, inventory, inventory_ms, desired, error, history_note)
        save(DATA/'view.json', output)
        print(json.dumps({'at': output['generated_ms'], 'running': output['running'], 'working': output['working'],
            'total_mb': output['total_mb'], 'minutes': len(output['minutes']), 'error': error, 'history': history_note}), flush=True)
        if args.once:
            break
        time.sleep(max(1, 15-(time.monotonic()-began)))
    db.close()


if __name__ == '__main__':
    main()
