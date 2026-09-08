#!/usr/bin/env python3
"""Collect Repocket's reported account bandwidth earnings, independently of traffic."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import fcntl
import getpass
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler

ROOT = Path(__file__).resolve().parents[1]
DATA = Path.home() / '.hg1/repocket'
SERVICE = 'repocket-provider-session'
# Public application identifier from Repocket's own web bundle, not an account key.
FIREBASE_KEY = 'AIzaSyBJf6hyw47O-5TrAwQszkwvDEh-Ri6q6SU'
LOGIN = 'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=' + FIREBASE_KEY
LOOKUP = 'https://identitytoolkit.googleapis.com/v1/accounts:lookup?key=' + FIREBASE_KEY
REFRESH = 'https://securetoken.googleapis.com/v1/token?key=' + FIREBASE_KEY
REPORT = 'https://api.repocket.com/api/reports/total'
SALAD_GROUP = 'https://api.salad.com/api/public/organizations/ssh2/projects/default/containers/rp-test-us'
INTERVAL = 60


class ProviderError(Exception):
    def __init__(self, message, status=None, retry_after=60, requires_login=False):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after
        self.requires_login = requires_login


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def request(url, payload=None, headers=None, form=False):
    if url not in (LOGIN, LOOKUP, REFRESH, REPORT):
        raise ProviderError('Request outside the configured provider scope')
    if url == REPORT:
        return report_request(headers or {})
    headers = {'Accept': 'application/json', **(headers or {})}
    body = None
    if payload is not None:
        headers['Content-Type'] = 'application/x-www-form-urlencoded' if form else 'application/json'
        body = (urlencode(payload) if form else json.dumps(payload)).encode()
    try:
        with build_opener(NoRedirect).open(Request(url, data=body, headers=headers), timeout=20) as response:
            raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ProviderError('Provider response exceeded the expected size')
            value = json.loads(raw, parse_float=Decimal)
            if not isinstance(value, dict):
                raise ProviderError('Unexpected provider response format')
            return value
    except HTTPError as error:
        try:
            retry = max(60, min(1800, int(error.headers.get('Retry-After', '60'))))
        except ValueError:
            retry = 60
        # Classify only known terminal markers; never relay response bodies.
        reason = error.read(65536).decode('utf-8', errors='replace').casefold()
        try:
            auth_code = json.loads(reason)['error']['message'].split(':', 1)[0].strip().upper()
        except (ValueError, KeyError, TypeError, AttributeError):
            auth_code = ''
        invalid_access = {'EMAIL_NOT_FOUND', 'INVALID_PASSWORD', 'USER_DISABLED', 'INVALID_LOGIN_CREDENTIALS',
                          'INVALID_REFRESH_TOKEN', 'TOKEN_EXPIRED', 'USER_NOT_FOUND', 'INVALID_ID_TOKEN',
                          'PROJECT_NUMBER_MISMATCH', 'OPERATION_NOT_ALLOWED', 'CREDENTIAL_TOO_OLD_LOGIN_AGAIN'}
        terminal = ('banned' in reason or 'session has been invalidated' in reason
                    or url in (LOGIN, LOOKUP, REFRESH) and auth_code in invalid_access)
        throttled = error.code == 429 or auth_code == 'TOO_MANY_ATTEMPTS_TRY_LATER'
        message = 'Account sign-in must be renewed' if terminal else 'Provider temporarily throttled requests' if throttled else 'Account access rejected' if error.code in (400, 401, 403) else 'Provider HTTP ' + str(error.code)
        raise ProviderError(message, error.code, retry, requires_login=terminal) from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise ProviderError('Provider request failed or returned invalid JSON') from None


def report_request(headers):
    config = 'header = "Accept: application/json"\n'
    for name in ('auth-token', 'x-app-version', 'device-os'):
        config += 'header = ' + json.dumps(name + ': ' + headers[name]) + '\n'
    try:
        result = subprocess.run(['curl', '-sS', '--max-time', '20', '--max-filesize', '2000000', '--config', '-',
                                 '--write-out', '\n%{http_code}', REPORT], input=config, text=True, capture_output=True, timeout=25)
        raw, status = result.stdout.rsplit('\n', 1)
        if result.returncode or len(raw.encode()) > 2000000:
            raise ProviderError('Repocket report request failed')
        if status != '200':
            terminal = status in ('401', '403') and any(marker in raw.casefold() for marker in ('banned', 'session has been invalidated'))
            raise ProviderError('Account sign-in must be renewed' if terminal else 'Repocket report HTTP ' + status,
                                int(status), requires_login=terminal)
        value = json.loads(raw, parse_float=Decimal)
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        raise ProviderError('Repocket report request failed or changed format') from None


def secret(service=SERVICE, payload=None):
    command = [str(ROOT / '.runtime/keychain-store'), '--service', service, '--account', getpass.getuser()]
    if payload is None:
        command.append('--read')
    try:
        result = subprocess.run(command, input=json.dumps(payload) if payload is not None else None,
                                capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise ProviderError('Repocket account access is missing or the credential store is unavailable')
        return result.stdout.strip() if payload is None else None
    except (OSError, subprocess.SubprocessError):
        raise ProviderError('Credential store is unavailable') from None


def expected_email():
    # Match the deployed Salad recorder's supported HTTP transport. Credentials
    # remain on stdin; a Salad error must never invalidate the RP account token.
    config = 'header = ' + json.dumps('Salad-Api-Key: ' + secret('salad-bandwidth-api')) + '\nheader = "Content-Type: application/json"\n'
    try:
        result = subprocess.run(['curl', '-sS', '--max-time', '20', '--config', '-', '--write-out', '\n%{http_code}', SALAD_GROUP],
                                input=config, text=True, capture_output=True, timeout=25)
        raw, status = result.stdout.rsplit('\n', 1)
        if result.returncode or status != '200':
            raise ProviderError('Salad account verification is unavailable')
        group = json.loads(raw)
    except (OSError, ValueError, subprocess.SubprocessError):
        raise ProviderError('Salad account verification is unavailable') from None
    deployment = json.loads((DATA / 'deployment.json').read_text())
    if group.get('id') != deployment['id']:
        raise ProviderError('Repocket group identity changed; account verification stopped')
    email = group.get('container', {}).get('environment_variables', {}).get('RP_EMAIL')
    if not isinstance(email, str) or not email.strip():
        raise ProviderError('The deployed RP account email is unavailable')
    return email.strip().casefold()


def text_field(value, field):
    item = value.get(field)
    if not isinstance(item, str) or not item:
        raise ProviderError('Incomplete provider authentication response')
    return item


class Client:
    def __init__(self):
        self.token = None
        self.expires_ms = 0
        self.uid = None
        self.access_digest = None
        self.verified_email = None
        self.stored_digest = None
        self.blocked_digest = None
        self.blocked_error = None

    def authenticate(self, access):
        mode = access.get('mode')
        expected = expected_email()
        if mode == 'email_password':
            email = text_field(access, 'email').strip().casefold()
            if email != expected:
                raise ProviderError('The supplied account does not match the deployed RP account')
            response = request(LOGIN, {'email': access['email'], 'password': text_field(access, 'password'), 'returnSecureToken': True})
            token = text_field(response, 'idToken')
            refresh = text_field(response, 'refreshToken')
            lifetime = response.get('expiresIn')
        elif mode == 'refresh_token':
            response = request(REFRESH, {'grant_type': 'refresh_token', 'refresh_token': text_field(access, 'refresh_token')}, form=True)
            token = text_field(response, 'id_token')
            refresh = text_field(response, 'refresh_token')
            lifetime = response.get('expires_in')
        else:
            raise ProviderError('Unsupported RP access method; run private account setup')
        account = request(LOOKUP, {'idToken': token}).get('users')
        if not isinstance(account, list) or len(account) != 1 or not isinstance(account[0], dict):
            raise ProviderError('Provider account identity could not be verified')
        user = account[0]
        email = text_field(user, 'email').strip().casefold()
        uid = text_field(user, 'localId')
        if email != expected or access.get('user_id') not in (None, uid):
            raise ProviderError('Provider login does not match the configured RP account')
        try:
            seconds = int(lifetime)
            if not 60 <= seconds <= 86400:
                raise ValueError()
        except (TypeError, ValueError):
            raise ProviderError('Provider token expiry is missing or invalid') from None
        saved = {'mode': 'refresh_token', 'refresh_token': refresh, 'user_id': uid,
                 'email': email, 'saved_at': datetime.now(timezone.utc).isoformat()}
        # After a verified login keep renewable access; remove the supplied password.
        secret(payload=saved)
        self.access_digest = hashlib.sha256(json.dumps(saved, sort_keys=True).encode()).hexdigest()
        self.stored_digest = self.access_digest
        self.token, self.uid, self.verified_email = token, uid, email
        self.expires_ms = int(time.time() * 1000) + seconds * 1000

    def fetch(self):
        try:
            access = json.loads(secret())
            if not isinstance(access, dict):
                raise ValueError()
        except (ValueError, TypeError):
            raise ProviderError('Stored RP access has an invalid format') from None
        digest = hashlib.sha256(json.dumps(access, sort_keys=True).encode()).hexdigest()
        if digest == self.blocked_digest:
            raise self.blocked_error
        self.stored_digest = digest
        try:
            return self.fetch_authenticated(access, digest)
        except ProviderError as error:
            if error.requires_login:
                self.blocked_digest, self.blocked_error = self.stored_digest, error
            raise

    def fetch_authenticated(self, access, digest):
        if digest != self.access_digest or int(time.time() * 1000) >= self.expires_ms - 60000:
            self.authenticate(access)
        for attempt in range(2):
            try:
                return request(REPORT, headers={'auth-token': self.token, 'x-app-version': 'web', 'device-os': 'web'})
            except ProviderError as error:
                if error.requires_login or error.status not in (401, 403) or attempt:
                    raise
                # One renewal/retry; never loop a rejected account indefinitely.
                self.authenticate(json.loads(secret()))


def number(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ProviderError('Provider bandwidth amount is missing or invalid')
    try:
        result = Decimal(str(value))
        if not result.is_finite() or result < 0:
            raise InvalidOperation()
        return result
    except InvalidOperation:
        raise ProviderError('Provider bandwidth amount is missing or invalid') from None


def provider_time(value):
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError()
        return int(parsed.timestamp() * 1000)
    except (ValueError, AttributeError, OverflowError):
        raise ProviderError('Provider report timestamp is invalid') from None


def reading(response, uid, now):
    try:
        # The live HTTP response is the report itself; axios's .data unwraps
        # the transport response, not another JSON envelope.
        data = response
        account = text_field(data, 'userId')
        if data.get('isFaked') is True or data.get('isUserDeleted') is True:
            raise ProviderError('Provider report is not a valid active-account reading')
        own = data['bandwidth']['own']
        total_bytes, cents = number(own['bytes']), number(own['cents'])
        if total_bytes != total_bytes.to_integral_value():
            raise ProviderError('Provider byte counter was not an integer')
    except (KeyError, TypeError, AttributeError):
        raise ProviderError('Provider earnings response is missing required fields') from None
    usd = cents / 100
    updated_ms = provider_time(data.get('updatedAt'))
    pending = own.get('pending') or {}
    return {'observed_ms': now, 'source': 'Repocket API /reports/total; account lifetime own-bandwidth only',
            'traffic_text': format((total_bytes / 1048576).quantize(Decimal('.01'), rounding=ROUND_HALF_UP), ',f') + ' MiB · account total',
            'earned_text': '$' + format(usd.quantize(Decimal('.0001'), rounding=ROUND_HALF_UP), ',f') + ' · account total',
            'total_bytes': str(total_bytes), 'total_usd_cents': str(cents), 'auth_user_id': uid,
            'report_user_id': account, 'scope': 'account lifetime own-bandwidth', 'provider_updated_ms': updated_ms,
            'provider_period_start_ms': provider_time(data.get('periodStart')),
            'pending_bytes': str(number(pending['bytes'])) if 'bytes' in pending else None,
            'pending_usd_cents': str(number(pending['cents'])) if 'cents' in pending else None,
            'account_earned_usd_cents': str(number(data['centsEarned'])) if data.get('centsEarned') is not None else None,
            'account_credited_usd_cents': str(number(data['centsCredited'])) if data.get('centsCredited') is not None else None,
            'account_withdrawn_usd_cents': str(number(data['centsWithdrawn'])) if data.get('centsWithdrawn') is not None else None,
            'poll_interval_seconds': INTERVAL}


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, separators=(',', ':'), allow_nan=False))
    os.replace(temporary, path)


def record(db, value):
    previous = db.execute('SELECT body FROM readings ORDER BY observed_ms DESC LIMIT 1').fetchone()
    previous = json.loads(previous[0]) if previous else None
    same = previous and all(previous.get(k) == value[k] for k in ('auth_user_id', 'report_user_id', 'total_bytes', 'total_usd_cents'))
    value['last_changed_ms'] = previous['last_changed_ms'] if same else value['observed_ms']
    with db:
        db.execute('INSERT INTO readings VALUES(?,?)', (value['observed_ms'], json.dumps(value, separators=(',', ':'))))
    save(DATA / 'provider.json', value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    DATA.mkdir(parents=True, exist_ok=True)
    lock = (DATA / 'provider.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    db = sqlite3.connect(DATA / 'provider.sqlite3')
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS readings(observed_ms INTEGER PRIMARY KEY,body TEXT NOT NULL)')
    db.commit()
    client = Client()
    failures = 0
    while True:
        started = time.monotonic()
        delay = INTERVAL
        try:
            response = client.fetch()
            value = reading(response, client.uid, int(time.time() * 1000))
            record(db, value)
            failures = 0
            status = {'checked_ms': value['observed_ms'], 'observed_ms': value['observed_ms'], 'state': 'ok', 'poll_interval_seconds': INTERVAL,
                      'provider_updated_ms': value['provider_updated_ms'], 'posting_interval': 'not published; observation time is not provider settlement time'}
        except Exception as error:
            failures += 1
            delay = min(900, INTERVAL * 2 ** min(failures - 1, 4))
            if isinstance(error, ProviderError):
                delay = max(delay, error.retry_after)
            status = {'checked_ms': int(time.time() * 1000), 'state': 'error', 'error': str(error) if isinstance(error, ProviderError) else type(error).__name__,
                      'consecutive_failures': failures, 'next_check_seconds': delay,
                      'requires_login': isinstance(error, ProviderError) and error.requires_login}
        save(DATA / 'provider-status.json', status)
        print(json.dumps(status), flush=True)
        if args.once:
            return 1 if failures else 0
        time.sleep(max(1, delay - (time.monotonic() - started)))


if __name__ == '__main__':
    raise SystemExit(main())
