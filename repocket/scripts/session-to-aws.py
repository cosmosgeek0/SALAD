#!/usr/bin/env python3
"""One-use local forms for transferring already-authorized provider sessions.

The only output is a private loopback form URL. Credentials remain in memory and
travel to the existing host's credential helper over SSH stdin.
"""

from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
import hmac
import html
import json
import math
from pathlib import Path
import re
import secrets
import shlex
import signal
import subprocess
import sys
import time
from types import MappingProxyType
from urllib.parse import parse_qsl


ROOT = Path(__file__).resolve().parents[1]
SSH_CONFIG = ROOT.parent / "Website/linux/ssh_config"
MAX_BODY = 64 * 1024
LIFETIME = 600
PROVIDERS = MappingProxyType({
    "rp": ("Repocket", "repocket-provider-session", "salad-repocket-provider.service"),
    "ps": ("PacketStream", "packetstream-provider-session", "salad-packetstream-provider.service"),
})


class InvalidAccess(ValueError):
    """Always raised with a fixed, secret-free message."""


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidAccess("Duplicate fields are refused.")
        result[key] = value
    return result


def validate_access(provider, raw, now=None):
    if provider not in PROVIDERS or not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_BODY:
        raise InvalidAccess("Invalid provider access.")
    try:
        value = json.loads(raw, object_pairs_hook=unique_object)
    except (ValueError, TypeError, RecursionError):
        raise InvalidAccess("Invalid provider access.") from None
    if not isinstance(value, dict):
        raise InvalidAccess("Invalid provider access.")
    expected = {"mode", "refresh_token"} if provider == "rp" else {"mode", "auth_cookie", "expires_at"}
    if set(value) != expected:
        raise InvalidAccess("Invalid provider access fields.")
    field = "refresh_token" if provider == "rp" else "auth_cookie"
    mode = "refresh_token" if provider == "rp" else "browser_cookie"
    secret = value.get(field)
    if value.get("mode") != mode or not isinstance(secret, str) or not secret or not re.fullmatch(r"[\x21-\x7e]+", secret):
        raise InvalidAccess("Invalid provider access.")
    if provider == "ps":
        if any(char in secret for char in ';,"\\'):
            raise InvalidAccess("Invalid provider cookie.")
        expires = value["expires_at"]
        if isinstance(expires, bool) or not isinstance(expires, (float, int)) or expires <= (time.time() if now is None else now) or expires > 253402300799 or not math.isfinite(expires):
            raise InvalidAccess("An unexpired provider session is required.")
    value["saved_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return value


def remote_command(provider):
    # The route selects from two constants; no request field becomes a command.
    _, service, unit = PROVIDERS[provider]
    script = f'''import json, signal, subprocess, sys
signal.signal(signal.SIGHUP, signal.SIG_IGN)
payload = sys.stdin.read({MAX_BODY + 1})
if not payload or len(payload.encode("utf-8")) > {MAX_BODY}:
    raise SystemExit(2)
unit = {unit!r}
result = 1
stop_attempted = False
try:
    stop_attempted = True
    stop = subprocess.run(["/usr/bin/sudo", "-n", "/usr/bin/systemctl", "stop", unit], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    if stop.returncode == 0:
        saved = subprocess.run(["/usr/bin/sudo", "-n", "-u", "salad", "/opt/salad/.runtime/keychain-store", "--service", {service!r}, "--account", "salad"], input=payload, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=45)
        result = 0 if saved.returncode == 0 else 1
except BaseException:
    result = 1
finally:
    if stop_attempted:
        try:
            started = subprocess.run(["/usr/bin/sudo", "-n", "/usr/bin/systemctl", "start", unit], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
            if started.returncode:
                result = 1
        except BaseException:
            result = 1
raise SystemExit(result)
'''
    return ["ssh", "-F", str(SSH_CONFIG), "-o", "BatchMode=yes", "-T", "salad-mumbai",
            "/usr/bin/python3 -c " + shlex.quote(script)]


def save_access(provider, value):
    try:
        # Both streams are discarded: a helper/library error could echo a body.
        result = subprocess.run(remote_command(provider), input=json.dumps(value, separators=(",", ":"), allow_nan=False),
                                text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=130)
        return result.returncode == 0
    except (OSError, ValueError, subprocess.SubprocessError):
        return False


class Bridge(HTTPServer):
    allow_reuse_address = False

    def __init__(self, saver=save_access):
        self.capability = secrets.token_urlsafe(32)
        self.nonces = {provider: secrets.token_urlsafe(32) for provider in PROVIDERS}
        self.saved = set()
        self.expires = time.monotonic() + LIFETIME
        self.saver = saver
        self.stopping = False
        super().__init__(("127.0.0.1", 0), Handler)
        self.timeout = 0.5
        self.authority = "127.0.0.1:" + str(self.server_port)
        self.origin = "http://" + self.authority
        self.base_path = "/" + self.capability

    def get_request(self):
        request, address = super().get_request()
        request.settimeout(5)
        return request, address

    def handle_error(self, request, client_address):
        # HTTPServer's default traceback could expose request state.
        pass


class Handler(BaseHTTPRequestHandler):
    server_version = "SessionBridge"
    sys_version = ""

    def log_message(self, *args):
        pass

    def send_error(self, code, message=None, explain=None):
        self.respond(code, "Request refused.")

    def respond(self, code, body):
        encoded = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'none'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        self.wfile.write(encoded)

    def permitted(self, post=False):
        if self.server.stopping or time.monotonic() >= self.server.expires:
            self.respond(410, "This temporary connection form has expired.")
            return False
        host = self.headers.get_all("Host", [])
        origins = self.headers.get_all("Origin", [])
        if host != [self.server.authority] or len(origins) > 1 or (origins and origins != [self.server.origin]) or (post and origins != [self.server.origin]):
            self.respond(403, "Request refused.")
            return False
        sites = self.headers.get_all("Sec-Fetch-Site", [])
        # Opening a link from the browser extension is a cross-site GET. Only
        # the nonce-protected same-origin POST can store a session.
        if len(sites) > 1 or (post and sites and sites[0] not in ("same-origin", "none")):
            self.respond(403, "Request refused.")
            return False
        return True

    def provider(self):
        for provider in PROVIDERS:
            if self.path == self.server.base_path + "/" + provider:
                return provider
        return None

    def do_GET(self):
        if not self.permitted():
            return
        if self.path == self.server.base_path:
            links = "".join('<p><a href="' + self.server.base_path + '/' + key + '">' + item[0] + "</a></p>" for key, item in PROVIDERS.items())
            self.respond(200, "<!doctype html><title>Connect provider earnings</title><h1>Connect provider earnings</h1>" + links)
            return
        provider = self.provider()
        if provider is None:
            self.respond(404, "Request refused.")
            return
        if provider in self.server.saved:
            self.respond(409, "Access has already been saved for this provider.")
            return
        name = PROVIDERS[provider][0]
        self.respond(200, '<!doctype html><title>Connect ' + name + '</title><h1>Connect ' + name + '</h1>'
                     '<p>This temporary form saves the authorized session to the existing private AWS credential store.</p>'
                     '<form method="post" action="' + self.server.base_path + '/' + provider + '" autocomplete="off">'
                     '<input type="hidden" name="csrf" value="' + html.escape(self.server.nonces[provider], quote=True) + '">'
                     '<label>Authorized session <input type="password" name="access" autocomplete="off" required></label>'
                     '<button type="submit">Save</button></form>')

    def do_POST(self):
        if not self.permitted(post=True):
            return
        provider = self.provider()
        if provider is None:
            self.respond(404, "Request refused.")
            return
        if provider in self.server.saved:
            self.respond(409, "Access has already been saved for this provider.")
            return
        lengths = self.headers.get_all("Content-Length", [])
        types = self.headers.get_all("Content-Type", [])
        if self.headers.get_all("Transfer-Encoding") or len(lengths) != 1 or not re.fullmatch(r"[0-9]+", lengths[0]) or len(lengths[0]) > 8:
            self.respond(400, "Request refused.")
            return
        length = int(lengths[0])
        if not 0 < length <= MAX_BODY:
            self.respond(413, "Request too large or empty.")
            return
        if len(types) != 1 or not re.fullmatch(r"application/x-www-form-urlencoded(?:;\s*charset=UTF-8)?", types[0], re.I):
            self.respond(415, "Request refused.")
            return
        try:
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise InvalidAccess("Incomplete request.")
            decoded = raw.decode("utf-8", errors="strict")
            if re.search(r"%(?![0-9a-fA-F]{2})", decoded):
                raise InvalidAccess("Invalid form encoding.")
            fields = unique_object(parse_qsl(decoded, keep_blank_values=True, strict_parsing=True, encoding="utf-8", errors="strict", max_num_fields=3))
            if set(fields) != {"csrf", "access"} or not hmac.compare_digest(fields["csrf"], self.server.nonces[provider]):
                raise InvalidAccess("Invalid form.")
            value = validate_access(provider, fields["access"])
        except (ValueError, UnicodeError, OSError, TypeError, RecursionError):
            self.respond(400, "Request refused; access was not saved.")
            return
        if self.server.stopping or time.monotonic() >= self.server.expires:
            self.respond(410, "This temporary connection form has expired.")
            return
        # Consume the nonce even on a transport failure; reload to retry.
        self.server.nonces[provider] = secrets.token_urlsafe(32)
        if not self.server.saver(provider, value):
            self.respond(502, "Save or collector restart could not be verified. Reload this form to retry.")
            return
        self.server.saved.add(provider)
        self.respond(200, "<!doctype html><title>Access saved</title><h1>Access saved</h1><p>The collector was restarted. A fresh provider reading still needs verification.</p>")


def main():
    if not SSH_CONFIG.is_file():
        print("The sibling Website SSH configuration is required.", file=sys.stderr)
        return 1
    with Bridge() as server:
        def stop(signum, frame):
            server.stopping = True
        for signum in (signal.SIGINT, signal.SIGTERM):
            signal.signal(signum, stop)
        print(server.origin + server.base_path, flush=True)
        while not server.stopping and time.monotonic() < server.expires and len(server.saved) < len(PROVIDERS):
            server.handle_request()
        return 0 if len(server.saved) == len(PROVIDERS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
