#!/usr/bin/env python3
"""Record PacketStream's account balance and dated rolling traffic report."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
import fcntl
import getpass
import hashlib
from html.parser import HTMLParser
from http.cookies import SimpleCookie, CookieError
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

ROOT = Path(__file__).resolve().parents[1]
DATA = Path.home() / '.hg1/packetstream'
SERVICE = 'packetstream-provider-session'
REPORT = 'https://app.packetstream.io/dashboard'
EXPECTED_REFERRAL = '8ExP'
INTERVAL = 60
SCOPE = 'account balance and provider rolling14day traffic'


class ProviderError(Exception):
    def __init__(self, message, *, retry_after=60, requires_login=False):
        super().__init__(message)
        self.retry_after = retry_after
        self.requires_login = requires_login


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def retry_delay(value):
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        try:
            seconds = int(parsedate_to_datetime(value).timestamp() - time.time())
        except (TypeError, ValueError, OverflowError):
            seconds = INTERVAL
    return max(INTERVAL, min(1800, seconds))


def request(cookie):
    # The sole request is a read of the observed dashboard URL. Redirects are
    # rejected, so the cookie cannot follow a redirect to another destination.
    headers = {'Accept': 'text/html', 'Cookie': 'auth=' + cookie,
               'User-Agent': 'Salad PacketStream provider recorder', 'Cache-Control': 'no-cache'}
    try:
        with build_opener(NoRedirect).open(Request(REPORT, headers=headers), timeout=20) as response:
            if response.geturl() != REPORT:
                raise ProviderError('Provider redirected account access', requires_login=True)
            raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ProviderError('Provider report exceeded the expected size')
            return raw.decode('utf-8'), response.headers.get_all('Set-Cookie', [])
    except HTTPError as error:
        if error.code in (301, 302, 303, 307, 308, 401, 403):
            raise ProviderError('PacketStream sign-in must be renewed', requires_login=True) from None
        if error.code == 429:
            raise ProviderError('Provider temporarily throttled requests',
                                retry_after=retry_delay(error.headers.get('Retry-After'))) from None
        raise ProviderError('Provider HTTP ' + str(error.code)) from None
    except (URLError, TimeoutError, OSError, UnicodeError):
        raise ProviderError('Provider request failed') from None


def secret(payload=None):
    command = [str(ROOT / '.runtime/keychain-store'), '--service', SERVICE, '--account', getpass.getuser()]
    if payload is None:
        command.append('--read')
    try:
        result = subprocess.run(command, input=json.dumps(payload) if payload is not None else None,
                                capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise ProviderError('PacketStream access is missing or the credential store is unavailable')
        return result.stdout.strip() if payload is None else None
    except (OSError, subprocess.SubprocessError):
        raise ProviderError('Credential store is unavailable') from None


class ReportHTML(HTMLParser):
    """Read only the observed balance card, referral guard, and report script."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.referrals, self.cards, self.scripts = [], [], []
        self.card_depth = 0
        self.card_text = []
        self.in_script = False
        self.script_text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'input' and attrs.get('id') == 'referral-link':
            self.referrals.append(attrs.get('value', ''))
        if tag == 'div':
            if self.card_depth:
                self.card_depth += 1
            elif 'metric-card-balance' in attrs.get('class', '').split():
                self.card_depth, self.card_text = 1, []
        if tag == 'script' and not attrs.get('src'):
            self.in_script, self.script_text = True, []

    def handle_endtag(self, tag):
        if tag == 'div' and self.card_depth:
            self.card_depth -= 1
            if not self.card_depth:
                self.cards.append(' '.join(self.card_text))
        if tag == 'script' and self.in_script:
            self.scripts.append(''.join(self.script_text))
            self.in_script = False

    def handle_data(self, data):
        if self.in_script:
            self.script_text.append(data)
        elif self.card_depth and data.strip():
            self.card_text.append(data.strip())


def reading(html, now):
    doc = ReportHTML()
    try:
        doc.feed(html)
    except Exception:
        raise ProviderError('Provider dashboard format changed') from None
    if len(doc.referrals) != 1:
        raise ProviderError('PacketStream account markup is unavailable or changed')
    try:
        referral = urlsplit(doc.referrals[0])
        correct = (referral.scheme == 'https' and referral.netloc == 'packetstream.io'
                   and parse_qs(referral.query).get('psr') == [EXPECTED_REFERRAL])
    except ValueError:
        correct = False
    if not correct:
        raise ProviderError('PacketStream account does not match the configured account', requires_login=True)
    if len(doc.cards) != 1 or 'Balance' not in doc.cards[0] or 'Available Funds' not in doc.cards[0]:
        raise ProviderError('Provider account balance is missing')
    amounts = re.findall(r'\$\s*((?:\d{1,3}(?:,\d{3})+|\d+)\.\d{2})(?![\d.])', doc.cards[0])
    if len(amounts) != 1:
        raise ProviderError('Provider account balance format changed')
    try:
        balance = Decimal(amounts[0].replace(',', ''))
        if not balance.is_finite() or balance < 0 or balance > Decimal('1000000000'):
            raise InvalidOperation()
    except InvalidOperation:
        raise ProviderError('Provider account balance is invalid') from None
    scripts = [s for s in doc.scripts if 'window.reportData' in s]
    if len(scripts) != 1:
        raise ProviderError('Provider traffic report is missing')
    matches = re.findall(r'\bconst\s+rd\s*=\s*("(?:\\.|[^"\\])*")\s*;', scripts[0])
    if len(matches) != 1:
        raise ProviderError('Provider traffic report format changed')
    try:
        report = json.loads(json.loads(matches[0]))
        rows = report['exitnode']
        if not isinstance(rows, list) or len(rows) > 10000:
            raise ValueError()
        days = {}
        for row in rows:
            stamp = row['timestamp']
            if not isinstance(stamp, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T00:00:00Z', stamp):
                raise ValueError()
            parsed = datetime.strptime(stamp, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
            if parsed.timestamp() * 1000 > now + 86400000:
                raise ValueError()
            up, down = row['bandwidth']['up'], row['bandwidth']['down']
            if any(type(v) is not int or not 0 <= v <= 10**18 for v in (up, down)):
                raise ValueError()
            day = days.setdefault(stamp[:10], {'date': stamp[:10], 'up': 0, 'down': 0})
            day['up'] += up
            day['down'] += down
        buckets = [days[k] for k in sorted(days)]
        total = sum(d['up'] + d['down'] for d in buckets)
        if total > 10**18:
            raise ValueError()
    except (ValueError, TypeError, KeyError, OverflowError):
        raise ProviderError('Provider dated traffic records are invalid') from None
    return {'observed_ms': now, 'checked_ms': now, 'balance_usd': float(balance),
            'balance_text': '$' + format(balance, '.2f'), 'rolling_bytes': total, 'days': buckets,
            'scope': SCOPE, 'source': 'Authenticated PacketStream /dashboard',
            'provider_updated_ms': None, 'poll_interval_seconds': INTERVAL,
            'error': None, 'requires_login': False}


def access_value(raw):
    try:
        access = json.loads(raw)
        cookie, expiry = access['auth_cookie'], access['expires_at']
        if (access.get('mode') != 'browser_cookie' or not isinstance(cookie, str)
                or not re.fullmatch(r'[\x21-\x7e]+', cookie) or any(c in cookie for c in ';,"\\')
                or isinstance(expiry, bool) or not isinstance(expiry, (float, int)) or not math.isfinite(expiry)):
            raise ValueError()
        return access
    except (ValueError, TypeError, KeyError):
        raise ProviderError('Stored PacketStream access has an invalid format', requires_login=True) from None


def renewed_access(access, headers, now):
    updated = dict(access)
    for header in headers:
        parsed = SimpleCookie()
        try:
            parsed.load(header)
        except CookieError:
            raise ProviderError('Provider session renewal format changed') from None
        if 'auth' not in parsed:
            continue
        item = parsed['auth']
        if item['domain'].lstrip('.') not in ('', 'packetstream.io', 'app.packetstream.io'):
            raise ProviderError('Provider session renewal scope changed')
        if item['path'] and not '/dashboard'.startswith(item['path']):
            raise ProviderError('Provider session renewal scope changed')
        expiry = access['expires_at']
        try:
            if item['max-age']:
                expiry = now + int(item['max-age'])
            elif item['expires']:
                expiry = parsedate_to_datetime(item['expires']).timestamp()
        except (ValueError, TypeError, OverflowError):
            raise ProviderError('Provider session expiry format changed') from None
        updated.update(auth_cookie=item.value, expires_at=expiry)
        if not item.value or expiry <= now:
            raise ProviderError('PacketStream sign-in must be renewed', requires_login=True)
        access_value(json.dumps(updated))
    return updated


def database(path):
    db = sqlite3.connect(path)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS readings(observed_ms INTEGER PRIMARY KEY,body TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS checks(checked_ms INTEGER PRIMARY KEY,state TEXT NOT NULL,error TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS blocked_access(digest TEXT PRIMARY KEY,error TEXT NOT NULL)')
    db.commit()
    return db


class Client:
    def __init__(self, db):
        self.db = db

    def fetch(self):
        raw = secret()
        digest = hashlib.sha256(raw.encode()).hexdigest()
        blocked = self.db.execute('SELECT error FROM blocked_access WHERE digest=?', (digest,)).fetchone()
        if blocked:
            raise ProviderError(blocked[0], requires_login=True)
        try:
            access = access_value(raw)
            now = time.time()
            if access['expires_at'] <= now:
                raise ProviderError('PacketStream sign-in has expired', requires_login=True)
            html, headers = request(access['auth_cookie'])
            updated = renewed_access(access, headers, time.time())
            if updated != access:
                secret(payload=updated)
                digest = hashlib.sha256(json.dumps(updated).encode()).hexdigest()
            return reading(html, int(time.time() * 1000))
        except ProviderError as error:
            if error.requires_login:
                with self.db:
                    self.db.execute('INSERT OR REPLACE INTO blocked_access VALUES(?,?)', (digest, str(error)))
            raise


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, separators=(',', ':'), allow_nan=False))
    os.replace(temporary, path)


def collect(client, db, data):
    now = int(time.time() * 1000)
    try:
        value = client.fetch()
        previous = db.execute('SELECT body FROM readings ORDER BY observed_ms DESC LIMIT 1').fetchone()
        previous = json.loads(previous[0]) if previous else None
        same = previous and all(previous.get(k) == value[k] for k in ('balance_usd', 'days'))
        value['last_changed_ms'] = previous['last_changed_ms'] if same else value['observed_ms']
        with db:
            db.execute('INSERT OR REPLACE INTO readings VALUES(?,?)', (value['observed_ms'], json.dumps(value)))
            db.execute('INSERT OR REPLACE INTO checks VALUES(?,?,NULL)', (now, 'ok'))
        save(data / 'provider.json', value)
        return {'checked_ms': now, 'observed_ms': value['observed_ms'], 'state': 'ok',
                'requires_login': False, 'poll_interval_seconds': INTERVAL}, INTERVAL
    except Exception as error:
        message = str(error) if isinstance(error, ProviderError) else 'Provider collector failed'
        login = isinstance(error, ProviderError) and error.requires_login
        previous = db.execute('SELECT body FROM readings ORDER BY observed_ms DESC LIMIT 1').fetchone()
        value = json.loads(previous[0]) if previous else {'observed_ms': None, 'balance_usd': None,
                'rolling_bytes': None, 'days': [], 'scope': SCOPE, 'provider_updated_ms': None}
        value.update(checked_ms=now, error=message, requires_login=login)
        with db:
            db.execute('INSERT OR REPLACE INTO checks VALUES(?,?,?)', (now, 'error', message))
        save(data / 'provider.json', value)
        return {'checked_ms': now, 'observed_ms': value['observed_ms'], 'state': 'error',
                'error': message, 'requires_login': login}, error.retry_after if isinstance(error, ProviderError) else INTERVAL


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    DATA.mkdir(parents=True, exist_ok=True)
    lock = (DATA / 'provider.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    db = database(DATA / 'provider.sqlite3')
    client = Client(db)
    failures = 0
    while True:
        started = time.monotonic()
        status, requested_delay = collect(client, db, DATA)
        failures = failures + 1 if status['state'] == 'error' else 0
        # Blocked sessions only re-read private access; no further provider request
        # is made until its stored value changes, even across service restarts.
        delay = INTERVAL if status['requires_login'] else max(requested_delay, min(900, INTERVAL * 2 ** min(max(0, failures - 1), 4)))
        status.update(consecutive_failures=failures, next_check_seconds=delay)
        save(DATA / 'provider-status.json', status)
        print(json.dumps(status), flush=True)
        if args.once:
            return int(bool(failures))
        time.sleep(max(1, delay - (time.monotonic() - started)))


if __name__ == '__main__':
    raise SystemExit(main())
