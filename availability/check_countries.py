"""Read Salad's official CPU availability estimator once per country; never deploy."""
import argparse
import concurrent.futures
from datetime import datetime, timezone
import getpass
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.error
import urllib.request

# All 249 options read from the Salad Portal country selector on 2026-09-07.
COUNTRIES = '''af al dz as ad ao ai aq ag ar am aw au at az bs bh bd bb by be bz bj bm bt bo bq ba bw bv br io bn bg bf bi cv kh cm ca ky cf td cl cn cx cc co km cd cg ck cr hr cu cw cy cz ci dk dj dm do ec eg sv gq er ee sz et fk fo fj fi fr gf pf tf ga gm ge de gh gi gr gl gd gp gu gt gg gn gw gy ht hm va hn hk hu is in id ir iq ie im il it jm jp je jo kz ke ki kp kr kw kg la lv lb ls lr ly li lt lu mo mg mw my mv ml mt mh mq mr mu yt mx fm md mc mn me ms ma mz mm na nr np nl nc nz ni ne ng nu nf mp no om pk pw ps pa pg py pe ph pn pl pt pr qa mk ro ru rw re bl sh kn lc mf pm vc ws sm st sa sn rs sc sl sg sx sk si sb so za gs ss es lk sd sr sj se ch sy tw tj tz th tl tg tk to tt tn tr tm tc tv ug ua ae gb um us uy uz vu ve vn vg vi wf eh ye zm zw ax'''.split()
DOC = 'https://docs.salad.com/reference/saladcloud-api/organizations/get-cpu-availability'
GUIDE = 'https://docs.salad.com/container-engine/explanation/infrastructure-platform/availability'


def utc():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--organization', default='hyperlane')
    parser.add_argument('--cpu', type=int, default=1)
    parser.add_argument('--memory', type=int, default=1024, help='Memory in MB')
    parser.add_argument('--storage', type=int, help='Optional storage requirement in bytes')
    parser.add_argument('--countries', nargs='+', default=COUNTRIES)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--output', type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,61}[a-z0-9]', args.organization):
        parser.error('Invalid organization name')
    codes = list(dict.fromkeys(c.lower() for c in args.countries))
    if any(c not in COUNTRIES for c in codes) or args.cpu < 1 or args.memory < 1 or not 1 <= args.workers <= 8:
        parser.error('Use valid country codes, positive resources, and 1–8 workers')
    if args.storage is not None and args.storage < 0:
        parser.error('Storage cannot be negative')
    key = os.environ.get('SALAD_API_KEY')
    if not key:
        helper = Path.home() / 'Library/Application Support/Salad Bandwidth Dashboard/.runtime/keychain-store'
        if not helper.is_file():
            parser.error('Supply SALAD_API_KEY or use the existing authorized Mac credential helper')
        result = subprocess.run([str(helper), '--read', '--service', 'salad-bandwidth-api',
                                 '--account', getpass.getuser()], text=True, capture_output=True, timeout=20)
        if result.returncode or not result.stdout.strip():
            parser.error('The credential helper could not read the existing API key')
        key = result.stdout.strip()
    endpoint = 'https://api.salad.com/api/public/organizations/' + args.organization + '/availability/sce-cpu-availability'
    base = {'cpu': args.cpu, 'memory': args.memory}
    if args.storage is not None:
        base['storage_amount'] = args.storage

    def fetch(code):
        payload = dict(base, country_codes=[] if code == 'all' else [code])
        for attempt in range(3):
            started = time.monotonic()
            request = urllib.request.Request(endpoint, data=json.dumps(payload).encode(), method='POST',
                headers={'Salad-Api-Key': key, 'Content-Type': 'application/json',
                         'User-Agent': 'salad-bandwidth-dashboard/1'})
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    data = json.load(response)
                if any(type(data.get(k)) is not int or data[k] < 0 for k in ('available_cpu_batch', 'on_call_cpu')):
                    raise ValueError('Unexpected availability response')
                return {'country_code': code, 'observed_at_utc': utc(), **data,
                        'request_seconds': round(time.monotonic() - started, 3), 'error': None}
            except urllib.error.HTTPError as error:
                status = error.code
                if status not in (429, 500, 502, 503, 504) or attempt == 2:
                    return {'country_code': code, 'observed_at_utc': utc(),
                            'available_cpu_batch': None, 'on_call_cpu': None, 'error': 'HTTP ' + str(status)}
                retry = error.headers.get('Retry-After', '')
                time.sleep(min(60, max(2 ** (attempt + 1), int(retry) if retry.isdigit() else 0)))
            except (OSError, ValueError) as error:
                if attempt == 2:
                    return {'country_code': code, 'observed_at_utc': utc(),
                            'available_cpu_batch': None, 'on_call_cpu': None, 'error': type(error).__name__}
                time.sleep(2 ** (attempt + 1))

    started = utc()
    before = fetch('all')
    rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        tasks = {pool.submit(fetch, code): code for code in codes}
        for task in concurrent.futures.as_completed(tasks):
            rows.append(task.result())
            if len(rows) % 50 == 0:
                print(f'Checked {len(rows)}/{len(codes)} countries', flush=True)
    after = fetch('all')
    # Names use Node's standard ICU country names; numeric codes/results remain usable without Node.
    names = {}
    try:
        result = subprocess.run(['node', '-e', "const c=JSON.parse(require('fs').readFileSync(0,'utf8'));const n=new Intl.DisplayNames(['en'],{type:'region'});process.stdout.write(JSON.stringify(Object.fromEntries(c.map(x=>[x,n.of(x.toUpperCase())]))));"],
                                input=json.dumps(codes), text=True, capture_output=True, timeout=10)
        if result.returncode == 0:
            names = json.loads(result.stdout)
    except (OSError, ValueError):
        pass
    for row in rows:
        row['country'] = names.get(row['country_code'], row['country_code'].upper())
    rows.sort(key=lambda row: (row['available_cpu_batch'] is None, -(row['available_cpu_batch'] or 0), row['country']))
    report = {'started_at_utc': started, 'finished_at_utc': utc(), 'organization': args.organization,
              'resource_filters': base, 'priority': 'Lowest (CPU-only)', 'source_api': endpoint,
              'documentation': DOC, 'interpretation_guide': GUIDE, 'global_before': before,
              'global_after': after, 'countries_checked': len(rows), 'results': rows,
              'notes': ['Countries are queried separately, not as a simultaneous inventory snapshot.',
                        'Counts are estimates for the specified resources, not guaranteed allocations or unique public IPs.',
                        'on_call_cpu is preserved as a raw API field; public documentation does not define its unit or allocation timing.',
                        'Failed requests remain null with an error; they are never recorded as zero.']}
    args.output.mkdir(parents=True, exist_ok=True)
    stem = 'countries-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    json_path = args.output / (stem + '.json')
    json_path.write_text(json.dumps(report, indent=2) + '\n')
    lines = ['# Salad country availability', '', f'UTC window: {started} → {report["finished_at_utc"]}',
             f'Resources: {args.cpu} vCPU, {args.memory} MB RAM, no GPU; Lowest priority.',
             f'Storage filter: {args.storage if args.storage is not None else "not specified"}.', '',
             f'All-country estimate: {before.get("available_cpu_batch")} before; {after.get("available_cpu_batch")} after.',
             '', f'[Official API]({DOC}) · [Interpretation]({GUIDE})', '',
             'The on_call_cpu column is a raw API value with unspecified public semantics; do not add it to immediate capacity.', '',
             '| Country | Code | Immediate estimate | on_call_cpu (raw) | Observed UTC | Error |',
             '|---|---|---:|---:|---|---|']
    for row in rows:
        lines.append('| ' + ' | '.join(str(row.get(k)) if row.get(k) is not None else '—'
            for k in ('country', 'country_code', 'available_cpu_batch', 'on_call_cpu', 'observed_at_utc', 'error')) + ' |')
    md_path = args.output / (stem + '.md')
    md_path.write_text('\n'.join(lines) + '\n')
    print(json.dumps({'report': str(md_path.resolve()), 'json': str(json_path.resolve()),
                      'started_at_utc': started, 'finished_at_utc': report['finished_at_utc'],
                      'global_before': before, 'global_after': after, 'countries_checked': len(rows),
                      'countries_nonzero': sum((r['available_cpu_batch'] or 0) > 0 for r in rows),
                      'errors': [r for r in rows if r['error']], 'top_30': rows[:30]}, indent=2))


if __name__ == '__main__':
    main()
