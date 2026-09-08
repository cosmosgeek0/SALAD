#!/usr/bin/env python3
"""Record independent Salad tests; provider credits never derive from network bytes."""
import argparse
from datetime import datetime, timezone
import fcntl
import getpass
import json
import math
import os
import re
from pathlib import Path
import shutil
import signal
import sqlite3
import subprocess
import threading
import time
import urllib.request

from dashboard.salad_api import SaladLogClient, _parse_iso

DATA = Path(os.environ.get('FLEET_TEST_DIR', str(Path.home() / '.hg1/fleet-tests')))
HG_DATA = Path(os.environ.get('HG_FLEET_DIR', str(Path.home() / '.hg1/hg-fleet')))
PS_DATA = Path.home() / '.hg1/packetstream'
COST_TARGETS = {'hg': ('deathadder', ('hg1',) + tuple('hg-solo-%02d' % n for n in range(2, 11))),
                'ps': ('hyperlane', ('ps-test-us',)), 'proxyrack': ('ssh1', ('pr',)),
                'rp': ('ssh2', ('rp-test-us',)), 'earnfm': ('ssh3', ('earnfm-us',)),
                'tm': ('ssh4', ('tm-test-us',)), 'pawns': ('cosmosgeeketh', ('pawns',)),
                'earnapp': ('cosmosgeeketh', ('earnapp-live',)), 'grass': ('cosmosgeeketh', ('grass',))}


def cost_state(db, service, group, instance, machine, version, at, kind, seen_ms):
    old = db.execute('SELECT body FROM runs WHERE group_id=? AND instance=?', (group['id'], instance)).fetchone()
    node = json.loads(old[0]) if old else {'service': service, 'group_id': group['id'], 'group': group['name'],
        'instance': instance, 'machine': machine, 'version': version, 'start_ms': None, 'end_ms': None,
        'last_running_ms': None, 'absent_ms': None, 'resources': group['resources'],
        'resource_observed_ms': group['observed_ms'], 'resource_assumed': str(version) != str(group['version'])}
    recorded_ms = int(time.time() * 1000)
    if node['machine'] != machine:
        node['error'] = 'Conflicting Salad machine identity'
    if node['resource_assumed'] and str(version) == str(group['version']):
        node.update(resources=group['resources'], version=version, resource_assumed=False, resource_observed_ms=group['observed_ms'])
    if 'states' not in node:
        node['legacy'] = {k: node.get(k) for k in ('start_ms', 'end_ms', 'last_running_ms', 'end_reason', 'start_recorded_ms', 'end_recorded_ms')}
        node['states'] = []
        if node['start_ms'] is not None:
            node['states'].append({'at_ms': node['start_ms'], 'kind': 'running', 'seen_ms': node['start_ms'],
                                   'recorded_ms': node.get('start_recorded_ms')})
        if node['end_ms'] is not None:
            node['states'].append({'at_ms': node['end_ms'], 'kind': node.get('end_reason') or 'not running',
                                   'seen_ms': node['end_ms'], 'recorded_ms': node.get('end_recorded_ms')})
        if node.get('last_running_ms') is not None:
            node['states'].append({'at_ms': node['last_running_ms'], 'kind': 'running',
                                   'seen_ms': node['last_running_ms'], 'recorded_ms': None})
    state = next((r for r in node['states'] if r['at_ms'] == at and r['kind'] == kind), None)
    if state is None:
        node['states'].append({'at_ms': at, 'kind': kind, 'seen_ms': seen_ms, 'recorded_ms': recorded_ms})
    else:
        state['seen_ms'] = max(state['seen_ms'], seen_ms)
    node['states'].sort(key=lambda r: (r['at_ms'], r['kind'] == 'running', r['kind']))
    periods, period = [], None
    for state in node['states']:
        if state['kind'] == 'running':
            if period is None:
                period = {'start_ms': state['at_ms'], 'end_ms': None, 'last_running_ms': state['seen_ms']}
                periods.append(period)
            else:
                period['last_running_ms'] = max(period['last_running_ms'], state['seen_ms'])
        elif period is not None:
            period.update(end_ms=state['at_ms'], end_reason=state['kind'])
            period = None
        elif not periods and state['kind'] not in ('Instance Allocated', 'Instance Downloading', 'Instance Starting'):
            periods.append({'start_ms': None, 'end_ms': state['at_ms'], 'last_running_ms': None, 'end_reason': state['kind']})
    node['periods'] = periods
    node['start_ms'] = periods[0]['start_ms'] if periods else None
    node['end_ms'] = periods[-1]['end_ms'] if periods else None
    node['last_running_ms'] = max((p['last_running_ms'] for p in periods if p['last_running_ms'] is not None), default=None)
    if kind == 'running' and node.get('absent_ms') is not None and seen_ms > node['absent_ms']:
        node['absent_ms'] = None
    db.execute('INSERT OR REPLACE INTO runs VALUES(?,?,?,?,?,?)',
               (service, group['id'], instance, node['start_ms'], node['end_ms'], json.dumps(node, separators=(',', ':'))))


def record_costs(stop, once=False):
    path = DATA.parent / 'costs.sqlite3'
    with sqlite3.connect(path) as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript('''CREATE TABLE IF NOT EXISTS targets(service TEXT,name TEXT,body TEXT,error TEXT,PRIMARY KEY(service,name));
            CREATE TABLE IF NOT EXISTS runs(service TEXT,group_id TEXT,instance TEXT,start_ms INTEGER,end_ms INTEGER,body TEXT,PRIMARY KEY(group_id,instance));
            CREATE INDEX IF NOT EXISTS cost_service_time ON runs(service,start_ms,end_ms);
            CREATE TABLE IF NOT EXISTS cursors(organization TEXT PRIMARY KEY,time_ms INTEGER,error TEXT);''')
        columns = {row[1] for row in db.execute('PRAGMA table_info(cursors)')}
        for name in ('periods_start_ms', 'periods_ms'):
            if name not in columns:
                db.execute('ALTER TABLE cursors ADD COLUMN ' + name + ' INTEGER')
        with db:
            for service, (_, names) in COST_TARGETS.items():
                for name in names:
                    db.execute('INSERT OR IGNORE INTO targets VALUES(?,?,NULL,?)', (service, name, 'Waiting for cost inventory'))
        while not stop.is_set():
            groups = {}
            try:
                helper = Path(__file__).resolve().parent / '.runtime/keychain-store'
                key = subprocess.check_output([str(helper), '--read', '--service', 'salad-bandwidth-api',
                                               '--account', getpass.getuser()], text=True, stderr=subprocess.PIPE).strip()
            except (OSError, subprocess.SubprocessError):
                with db:
                    for service, (_, names) in COST_TARGETS.items():
                        for name in names:
                            db.execute('INSERT INTO targets VALUES(?,?,NULL,?) ON CONFLICT(service,name) DO UPDATE SET error=excluded.error',
                                       (service, name, 'Cost recorder cannot read configured Salad access'))
                if once:
                    return
                stop.wait(60)
                continue
            for service, (organization, names) in COST_TARGETS.items():
                for name in names:
                    if stop.is_set():
                        return
                    base = 'https://api.salad.com/api/public/organizations/' + organization + '/projects/default/containers/' + name
                    try:
                        with urllib.request.urlopen(urllib.request.Request(base, headers={'Salad-Api-Key': key, 'User-Agent': 'salad-bandwidth-dashboard/1'}), timeout=20) as response:
                            source = json.load(response)
                        with urllib.request.urlopen(urllib.request.Request(base + '/instances', headers={'Salad-Api-Key': key, 'User-Agent': 'salad-bandwidth-dashboard/1'}), timeout=20) as response:
                            instances = json.load(response)['instances']
                        observed = int(time.time() * 1000)
                        group = {'id': source['id'], 'name': name, 'organization': organization,
                                 'created_ms': int(_parse_iso(source['create_time']).timestamp() * 1000),
                                 'version': source['version'], 'resources': source['container']['resources'],
                                 'observed_ms': observed, 'instances': [
                                     {k: n.get(k) for k in ('id', 'machine_id', 'version', 'state', 'update_time')} for n in instances]}
                        members = {n['id'] for n in instances}
                        with db:
                            for node in instances:
                                at = int(_parse_iso(node['update_time']).timestamp() * 1000)
                                if node['state'] == 'running':
                                    cost_state(db, service, group, node['id'], node['machine_id'], node['version'], at, 'running', observed)
                                else:
                                    old = db.execute('SELECT body FROM runs WHERE group_id=? AND instance=?', (group['id'], node['id'])).fetchone()
                                    saved = json.loads(old[0]) if old else {}
                                    if any(p.get('start_ms') is not None and at >= p['start_ms'] for p in saved.get('periods', [saved])):
                                        cost_state(db, service, group, node['id'], node['machine_id'], node['version'], at, node['state'], observed)
                            for instance, body in db.execute('SELECT instance,body FROM runs WHERE group_id=? AND end_ms IS NULL', (group['id'],)).fetchall():
                                saved = json.loads(body)
                                if instance not in members and saved.get('absent_ms') is None:
                                    saved['absent_ms'] = observed
                                    db.execute('UPDATE runs SET body=? WHERE group_id=? AND instance=?', (json.dumps(saved), group['id'], instance))
                            db.execute('INSERT OR REPLACE INTO targets VALUES(?,?,?,NULL)', (service, name, json.dumps(group)))
                        groups.setdefault(organization, {})[name] = service, group
                    except Exception as error:
                        message = 'Cost inventory read failed: ' + type(error).__name__ + (' HTTP ' + str(error.code) if hasattr(error, 'code') else '')
                        with db:
                            db.execute('INSERT INTO targets VALUES(?,?,NULL,?) ON CONFLICT(service,name) DO UPDATE SET error=excluded.error', (service, name, message))
            for organization, targets in groups.items():
                try:
                    now = int(time.time() * 1000)
                    first = max(min(g['created_ms'] for _, g in targets.values()), now - 7 * 86400000)
                    saved = db.execute('SELECT periods_ms,periods_start_ms FROM cursors WHERE organization=?', (organization,)).fetchone()
                    cursor = max(first, saved[0] if saved and saved[0] is not None else first)
                    coverage_start = saved[1] if saved and saved[0] is not None and saved[0] >= first and saved[1] is not None else first
                    query = 'resource.type = "instance_controller" and resource.labels.project_name = "default" and ('
                    query += ' or '.join('resource.labels.container_group_name = ' + json.dumps(name) for name in targets)
                    query += ') and (json_log.message = "Instance Running" or json_log.message startswith "Instance Reallocated" or json_log.message startswith "Instance Interrupted" or json_log.message startswith "Instance Exited" or json_log.message = "Instance Stopped" or json_log.message = "Instance Starting" or json_log.message = "Instance Downloading" or json_log.message = "Instance Allocated")'
                    client = SaladLogClient(organization, 'default', '', lambda: key, timeout=20, log_query=query)
                    until = min(now, cursor + 2 * 3600000)
                    windows = [(max(first, cursor - 180000), until)]
                    if until < now - 180000:
                        windows.append((max(first, now - 180000), now))
                    for begin, end in windows:
                        records = client.fetch(stamp(begin), stamp(end))
                        with db:
                            for record in records:
                                labels = record['resource']['labels']
                                target = targets.get(labels.get('container_group_name'))
                                if target is None:
                                    continue
                                service, group = target
                                at = int(_parse_iso(record['time']).timestamp() * 1000)
                                if at < group['created_ms']:
                                    continue
                                message = record['json_log']['message']
                                # Historical events confirm only their event time, not the later receipt time.
                                cost_state(db, service, group, labels['instance_id'], labels['machine_id'],
                                           labels.get('container_group_version'), at,
                                           'running' if message == 'Instance Running' else message, at)
                            if end == until and len(targets) == sum(len(names) for org, names in COST_TARGETS.values() if org == organization):
                                db.execute('''INSERT INTO cursors(organization,time_ms,error,periods_start_ms,periods_ms) VALUES(?,?,NULL,?,?)
                                    ON CONFLICT(organization) DO UPDATE SET time_ms=MAX(cursors.time_ms,excluded.time_ms),
                                    error=NULL,periods_start_ms=excluded.periods_start_ms,periods_ms=excluded.periods_ms''',
                                    (organization, until, coverage_start, until))
                except Exception as error:
                    with db:
                        db.execute('INSERT INTO cursors(organization,time_ms,error) VALUES(?,0,?) ON CONFLICT(organization) DO UPDATE SET error=excluded.error',
                                   (organization, 'Cost history read failed: ' + type(error).__name__))
            if once:
                return
            stop.wait(60)


def stamp(ms=None):
    return datetime.fromtimestamp((ms or time.time()*1000)/1000, timezone.utc).isoformat()


def read(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default if default is not None else {}


def atomic(path, value):
    temp = Path(str(path) + '.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.replace(path)


def last_provider():
    try:
        rows = (PS_DATA / 'provider-observations.jsonl').read_text().splitlines()
    except OSError:
        return None
    for line in reversed(rows):
        try:
            r = json.loads(line)
            if not isinstance(r.get('provider_bytes'), int):
                continue
            dt = datetime.fromisoformat((r.get('observed_at') or r['recorded_at']).replace('Z', '+00:00'))
            return {'bytes': r['provider_bytes'], 'time_ms': int(dt.timestamp()*1000)}
        except (KeyError, ValueError, TypeError):
            continue
    return None


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=6) as response:
            return json.load(response)
    except Exception:
        return {}


def moved(n):
    if isinstance(n.get('rx_moved_bytes'), int) and isinstance(n.get('tx_moved_bytes'), int):
        return n['rx_moved_bytes'], n['tx_moved_bytes']
    # No conversion from a rounded MB display: wait for the repaired collector.
    return None


def exact_counter(value):
    # Salad serializes structured log numbers as doubles, including integer counters.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value) if math.isfinite(value) and 0 <= value <= 2**53 and int(value) == value else None


def accumulate(network, nodes):
    """Sum observed per-run increments, never add a replacement's lifetime baseline."""
    resets = []
    for n in nodes:
        counters = moved(n)
        if counters is None:
            continue
        key = n['run']
        old = network['last'].get(key)
        if old is not None:
            if counters[0] >= old[0] and counters[1] >= old[1]:
                network['rx'] += counters[0]-old[0]
                network['tx'] += counters[1]-old[1]
            else:
                resets.append(key)
        network['last'][key] = list(counters)
    return resets


def inventory_changes(state, result):
    events=[]
    previous=state.get('inventory')
    current={}
    for service in ['ps','hg']:
        for worker in result[service]['workers']:
            identity=worker.get('group') if service=='hg' else worker.get('machine')
            if not identity:continue
            key=service+'/'+identity
            current[key]={k:worker.get(k) for k in ['machine','ip','client_status']}
            old=previous.get(key) if previous is not None else None
            if old:
                for field in ['machine','ip','client_status']:
                    if old.get(field) is not None and current[key].get(field) is not None and old[field]!=current[key][field]:
                        events.append({'time_ms':result['time_ms'],'service':service,'worker':identity,
                                       'action':field+'_changed','previous':old[field],'value':current[key][field]})
            elif previous is not None:
                events.append({'time_ms':result['time_ms'],'service':service,'worker':identity,'action':'worker_appeared'})
    if previous is not None:
        for key in previous.keys()-current.keys():
            service,identity=key.split('/',1)
            events.append({'time_ms':result['time_ms'],'service':service,'worker':identity,'action':'worker_not_observed'})
    state['inventory']=current
    return events


def observation(current, network):
    raw = get('http://127.0.0.1:8789/api/ps1/status')
    view = get('http://127.0.0.1:8787/api/ps1/view')
    now = int(time.time()*1000)
    target=current.get('ps',{})
    target_path='/'.join([target.get('organization','hyperlane'),target.get('project','default'),target.get('group','ps1')])
    census=read(PS_DATA/'native-census.json')
    plain=False
    try:
        census_ms=int(datetime.fromisoformat((census.get('last_success_at') or census.get('checked_at','')).replace('Z','+00:00')).timestamp()*1000)
        plain=census.get('group')==target_path and 0<=now-census_ms<180000
    except (ValueError,TypeError):
        census_ms=0
    if plain:
        entries=[]
        for row in census.get('nodes',[]):
            client=row.get('client_status') or {}
            net=row.get('network') or {}
            try:status_age=now-int(datetime.fromisoformat(client.get('source_time','').replace('Z','+00:00')).timestamp()*1000)
            except (ValueError,TypeError):status_age=None
            entry={'machine':row['machine'],'run':row['machine']+'/'+row['instance_id']+'/'+str(net.get('observer','status')),
                'deployment_current':True,'salad_state':row.get('salad_state'),'client_status':client,
                'client_status_age_ms':status_age,'ip':row.get('ip'),'sample_source':'native_status_only'}
            if net.get('available') and isinstance(net.get('observed_rx_bytes'),int) and isinstance(net.get('observed_tx_bytes'),int):
                entry.update(rx_moved_bytes=net['observed_rx_bytes'],tx_moved_bytes=net['observed_tx_bytes'],
                    sample_age_ms=now-net['received_ms'],source_sample_age_ms=now-net['time_ms'],
                    sample_source='native_minutes',source_granularity_seconds=60,
                    last_interval_seconds=net.get('last_interval_seconds'))
            entries.append(entry)
        raw={'nodes':entries,'accepted_nodes':sum((r.get('client_status')or{}).get('state')=='running' and
                r.get('client_status_age_ms') is not None and -15000<=r['client_status_age_ms']<=600000 for r in entries),
             'connected_machines':[],'deployment_membership_age_ms':now-census_ms}
        view['running_nodes']=sum(r.get('salad_state')=='running' for r in entries)
    membership = {n['machine']: n for n in view.get('nodes', []) if n.get('current')}
    if any('deployment_current' in n for n in raw.get('nodes', [])):
        nodes = [n for n in raw['nodes'] if n.get('deployment_current')]
    else:
        nodes = [n for n in raw.get('nodes', []) if n.get('current') and n.get('machine') in membership]
    workers = []
    for n in nodes:
        client = n.get('client_status') or {}
        if not isinstance(client, dict):
            client = {'state': str(client)}
        counters = moved(n)
        workers.append({'machine': n['machine'], 'run': n['run'], 'ip': n.get('ip'),
                        'state': n.get('salad_state') or membership.get(n['machine'], {}).get('state'),
                        'client_status': client.get('state', 'unknown'),
                        'client_status_age_ms': n.get('client_status_age_ms'),
                        'error': client.get('message') if client.get('state') == 'error' else None,
                        'network_bytes': sum(counters) if counters else None,
                        'received_age_ms': n.get('sample_age_ms'),
                        'source_age_ms': n.get('source_sample_age_ms'),
                        'sample_source':n.get('sample_source'),
                        'source_granularity_seconds':n.get('source_granularity_seconds'),
                        'last_interval_seconds':n.get('last_interval_seconds')})
    resets = accumulate(network, nodes)
    provider = last_provider()
    fresh = [n for n in workers if isinstance(n.get('received_age_ms'), (int,float)) and
             0 <= n['received_age_ms'] <= (150000 if n.get('sample_source')=='native_minutes' else 45000 if n.get('sample_source')=='sysfs_via_salad_logs_1s' else
                                         25000 if n.get('sample_source')=='salad_logs_10s' else 15000)]
    membership_age = raw.get('deployment_membership_age_ms', view.get('membership_age_ms'))
    complete = len(fresh) == 10 and len(workers) == 10 and all(n['network_bytes'] is not None for n in workers)
    complete = complete and membership_age is not None and membership_age < 45000 and not resets
    complete = complete and all(isinstance(n['source_age_ms'],(int,float)) and -15000<=n['source_age_ms']<=60000 for n in workers)
    hg = read(HG_DATA / 'status.json')
    hg_workers = []
    hg_samples = []
    for w in hg.get('workers', []):
        safe = {k:w.get(k) for k in ['group','device','machine','ip','state','client_status','credits','credit_observed_ms','error']}
        sample=w.get('sample') or {}
        safe['run']=w.get('instance')
        sample_time=re.sub(r'\.(\d+)(?=[+-])', lambda m: '.'+m.group(1)[:6].ljust(6,'0'), sample.get('time','').replace('Z','+00:00'))
        safe['sample_ms']=int(datetime.fromisoformat(sample_time).timestamp()*1000) if sample_time else None
        rx,tx=exact_counter(sample.get('rx_total')),exact_counter(sample.get('tx_total'))
        safe['network_bytes']=rx+tx if isinstance(rx,int) and isinstance(tx,int) else None
        safe['received_age_ms']=hg['time_ms']-safe['sample_ms'] if safe['sample_ms'] is not None else None
        hg_workers.append(safe)
        if safe['network_bytes'] is not None and w.get('instance'):
            hg_samples.append({'run':w['group']+'/'+w['instance'],'rx_moved_bytes':rx,'tx_moved_bytes':tx})
    hg_network=network.setdefault('hg',{'rx':0,'tx':0,'last':{}})
    hg_resets=accumulate(hg_network,hg_samples)
    hg_complete=len(hg_workers)==10 and len(hg_samples)==10 and not hg_resets
    hg_complete=hg_complete and all(isinstance(w['received_age_ms'],(int,float)) and 0<=w['received_age_ms']<=120000 for w in hg_workers)
    hg_complete=hg_complete and isinstance(hg.get('time_ms'),(int,float)) and now-hg['time_ms']<120000
    result = {'recorded_at': stamp(now), 'time_ms': now, 'experiment_id': current['id'], 'phase': current.get('phase'),
              'ps': {'running': view.get('running_nodes'), 'reporting': len(fresh),
                     'desired': 10, 'accepted': raw.get('accepted_nodes'),
                     'monitor_connections': len(raw.get('connected_machines', [])),
                     'provider_bytes': provider['bytes'] if provider else None,
                     'provider_observed_ms': provider['time_ms'] if provider else None,
                     'network_rx_bytes': network['rx'] if network['last'] else None,
                     'network_tx_bytes': network['tx'] if network['last'] else None,
                     'network_total_bytes': network['rx']+network['tx'] if network['last'] else None, 'network_complete': bool(complete),
                     'network_observed_ms': census_ms if plain and network['last'] else now if raw and not plain else None, 'counter_resets': resets,
                     'status_observed_ms':census_ms if plain else now if raw else None,
                     'group_started_at':census.get('group_state',{}).get('start_time') if plain else None,
                     'workers': workers},
              'hg': {'running': hg.get('running'), 'connected': hg.get('connected'), 'desired': 10,
                     'provider_gathering_credits': hg.get('provider_gathering_credits'),
                     'provider_observed_ms': hg.get('provider_observed_ms'),
                     'status_observed_ms': hg.get('time_ms'),
                     'network_rx_bytes':hg_network['rx'],'network_tx_bytes':hg_network['tx'],
                     'network_total_bytes':hg_network['rx']+hg_network['tx'],
                     'network_complete':bool(hg_complete),'network_observed_ms':hg.get('time_ms'),
                     'workers': hg_workers}}
    result['events']=inventory_changes(network,result)
    return result


def start_new(phase):
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    old = read(DATA/'current.json')
    now = int(time.time()*1000)
    ident = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    archive = DATA/'archives'/(old.get('id') or 'pre-fleet-'+ident)
    archive.mkdir(parents=True, exist_ok=True, mode=0o700)
    if old:
        for filename in ['current.json','observations.jsonl','network-state.json','latest.json','events.jsonl']:
            source=DATA/filename
            if source.exists():
                shutil.copy2(source, archive/filename)
    else:
        # Preserve the exact earlier credited ledger. Existing raw network log remains append-only.
        if (PS_DATA/'provider-observations.jsonl').exists():
            shutil.copy2(PS_DATA/'provider-observations.jsonl', archive/'provider-observations.jsonl')
        atomic(archive/'legacy-sources.json', {'archived_at':stamp(now), 'network_log':str(PS_DATA/'network/samples.jsonl'),
               'network_size_bytes':(PS_DATA/'network/samples.jsonl').stat().st_size if (PS_DATA/'network/samples.jsonl').exists() else None})
    provider = last_provider()
    hg_provider = read(HG_DATA/'provider-latest.json')
    value = {'id':ident, 'started_at':stamp(now), 'started_ms':now, 'status':'preparing' if phase=='repair' else 'measuring',
             'phase':phase, 'ps':{'organization':'hyperlane','group':'ps1','desired':10,
               'baseline_provider_bytes':provider['bytes'] if provider else None,
               'baseline_provider_observed_ms':provider['time_ms'] if provider else None,
               'estimated_fleet_cost_usd_per_hour':0.05,'cost_basis':'Previously quoted estimate; invoice unverified'},
             'hg':{'organization':'deathadder','desired':10,'version':'0.6.6',
                   'baseline_provider_gathering_credits':hg_provider.get('gathering_credits'),
                   'baseline_provider_observed_ms':hg_provider.get('observed_ms'),
                   'baseline_started_ms':hg_provider.get('observed_ms'),
                   'phase':phase},
             'interventions':[], 'archive_path':str(archive),
             'measurement_note':'Network totals are observed per-run increments. Provider totals are account-level. Missing samples are not zero traffic.'}
    (DATA/'observations.jsonl').write_text('')
    (DATA/'events.jsonl').write_text('')
    atomic(DATA/'network-state.json', {'experiment_id':ident,'rx':0,'tx':0,'last':{}})
    atomic(DATA/'current.json', value)
    return value


def run(once=False):
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock=(DATA/'recorder.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
    stopping = False
    cost_stop = threading.Event()
    def stop(_sig,_frame):
        nonlocal stopping
        stopping=True
        cost_stop.set()
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    if not once:
        threading.Thread(target=record_costs, args=(cost_stop,), daemon=True).start()
    while not stopping:
        current=read(DATA/'current.json')
        if not current:
            raise RuntimeError('Start a test before starting recorder')
        network=read(DATA/'network-state.json')
        if network.get('experiment_id')!=current['id']:
            network={'experiment_id':current['id'],'rx':0,'tx':0,'last':{}}
        record=observation(current,network)
        atomic(DATA/'network-state.json',network)
        with (DATA/'observations.jsonl').open('a') as out:
            out.write(json.dumps(record,separators=(',',':'))+'\n');out.flush()
        if record.get('events'):
            with (DATA/'events.jsonl').open('a') as out:
                for event in record['events']:out.write(json.dumps(event)+'\n')
        atomic(DATA/'latest.json',record)
        if once:
            record_costs(cost_stop, once=True)
            print(json.dumps({'at':record['recorded_at'],'ps_running':record['ps']['running'],'ps_reporting':record['ps']['reporting'],
                              'hg_running':record['hg']['running'],'hg_connected':record['hg']['connected']}));return
        for _ in range(10):
            if stopping:break
            time.sleep(1)


def main():
    os.umask(0o077)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['start-new','run','once','mark'])
    parser.add_argument('--phase',default='repair')
    parser.add_argument('--reason',default='')
    args=parser.parse_args()
    if args.action=='start-new':
        # Prevent archive/reset racing an active writer. Stop the launchd job first.
        DATA.mkdir(parents=True,exist_ok=True,mode=0o700)
        lock=(DATA/'recorder.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        print(json.dumps(start_new(args.phase),indent=2))
    elif args.action=='mark':
        current=read(DATA/'current.json');current['phase']=args.phase
        current['interventions'].append({'time_ms':int(time.time()*1000),'reason':args.reason,'phase':args.phase,
                                         'service':'fleet','action':args.phase})
        atomic(DATA/'current.json',current)
    else:run(args.action=='once')


if __name__=='__main__':
    main()
