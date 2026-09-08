"""No-network-cloud tests for the short-lived local session transport."""

import http.client
import importlib.util
import json
from pathlib import Path
import re
import shlex
import signal
import subprocess
import threading
import time
import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlencode


SOURCE = Path(__file__).resolve().parents[1] / "scripts/session-to-aws.py"
SPEC = importlib.util.spec_from_file_location("session_bridge", SOURCE)
bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge)
RP = {"mode": "refresh_token", "refresh_token": "unique-private-refresh-token"}
PS = {"mode": "browser_cookie", "auth_cookie": "unique-private-auth-cookie", "expires_at": 4102444800}


class BridgeHTTPTest(unittest.TestCase):
    def setUp(self):
        self.saver = Mock(return_value=True)
        self.server = bridge.Bridge(saver=self.saver)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, method="GET", suffix="", body=None, headers=None, path=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        connection.request(method, self.server.base_path + suffix if path is None else path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read().decode()
        connection.close()
        return result

    def post(self, provider="rp", value=None, extra=None, headers=None, path=None, fields=None):
        form = fields if fields is not None else [("csrf", self.server.nonces[provider]), ("access", json.dumps(value or (RP if provider == "rp" else PS)))]
        if extra:
            form += extra
        request_headers = {"Origin": self.server.origin, "Content-Type": "application/x-www-form-urlencoded"}
        request_headers.update(headers or {})
        return self.request("POST", "/" + provider, urlencode(form), request_headers, path=path)

    def test_loopback_and_random_capability(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        self.assertGreaterEqual(len(self.server.capability), 43)
        self.assertNotEqual(self.server.capability, self.server.nonces["rp"])
        self.assertNotEqual(self.server.nonces["rp"], self.server.nonces["ps"])

    def test_private_index_and_separate_password_forms(self):
        self.assertEqual(self.request()[0], 200)
        for provider in ("rp", "ps"):
            status, headers, body = self.request(suffix="/" + provider)
            self.assertEqual(status, 200)
            self.assertIn('type="password" name="access"', body)
            self.assertIn('type="hidden" name="csrf"', body)
            self.assertIn("no-store", headers["Cache-Control"])
            self.assertEqual(headers["Referrer-Policy"], "same-origin")
            self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
            self.assertNotIn("<script", body)
            self.assertNotIn("https://", body)

    def test_wrong_capability_path_query_and_method(self):
        for path in ("/", "/wrong/rp", self.server.base_path + "/hg", self.server.base_path + "/rp?x=1", self.server.base_path + "/rp/"):
            self.assertEqual(self.request(path=path)[0], 404)
            self.assertEqual(self.post(path=path)[0], 404)
        for method in ("PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"):
            self.assertEqual(self.request(method, "/rp")[0], 501)
        self.saver.assert_not_called()

    def test_exact_host_origin_and_fetch_site(self):
        for headers in ({"Host": "localhost:" + str(self.server.server_port)},
                        {"Host": "attacker.invalid"},
                        {"Origin": "https://attacker.invalid"},
                        {"Origin": "null"}, {"Origin": ""},
                        {"Sec-Fetch-Site": "cross-site"}):
            self.assertEqual(self.post(headers=headers)[0], 403)
        self.assertEqual(self.request(suffix="/rp", headers={"Origin": "https://attacker.invalid"})[0], 403)
        self.assertEqual(self.request("POST", "/rp", "x=1", {"Content-Type": "application/x-www-form-urlencoded"})[0], 403)
        self.saver.assert_not_called()

    def test_external_navigation_can_open_but_not_submit(self):
        self.assertEqual(self.request(suffix='/ps',headers={'Sec-Fetch-Site':'cross-site'})[0],200)
        self.assertEqual(self.post('ps',headers={'Sec-Fetch-Site':'cross-site'})[0],403)
        self.saver.assert_not_called()

    def test_duplicate_host_and_origin_headers(self):
        for duplicate in ("Host", "Origin"):
            connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
            connection.putrequest("POST", self.server.base_path + "/rp", skip_host=True)
            connection.putheader("Host", self.server.authority)
            connection.putheader("Origin", self.server.origin)
            connection.putheader(duplicate, self.server.authority if duplicate == "Host" else self.server.origin)
            connection.putheader("Content-Length", "0")
            connection.endheaders()
            response = connection.getresponse()
            self.assertEqual(response.status, 403)
            response.read()
            connection.close()
        self.saver.assert_not_called()

    def test_csrf_duplicate_form_fields_and_extra_fields(self):
        tests = [[("csrf", "wrong"), ("access", json.dumps(RP))],
                 [("csrf", self.server.nonces["ps"]), ("access", json.dumps(RP))],
                 [("csrf", self.server.nonces["rp"]), ("access", json.dumps(RP)), ("access", json.dumps(RP))],
                 [("csrf", self.server.nonces["rp"]), ("access", json.dumps(RP)), ("service", "arbitrary")]]
        for form in tests:
            self.assertEqual(self.post(fields=form)[0], 400)
        self.saver.assert_not_called()

    def test_only_correct_provider_payload_is_saved(self):
        self.assertEqual(self.post("rp", PS)[0], 400)
        self.assertEqual(self.post("ps", RP)[0], 400)
        self.assertEqual(self.post("rp")[0], 200)
        self.assertEqual(self.post("ps")[0], 200)
        self.assertEqual(self.server.saved, {"rp", "ps"})
        self.assertEqual(self.saver.call_count, 2)
        self.assertEqual(self.saver.call_args_list[0].args[0], "rp")
        self.assertEqual(self.saver.call_args_list[0].args[1]["refresh_token"], RP["refresh_token"])
        self.assertEqual(self.saver.call_args_list[1].args[1]["auth_cookie"], PS["auth_cookie"])

    def test_duplicate_save_refused_and_no_credential_echo(self):
        status, _, body = self.post()
        self.assertEqual(status, 200)
        self.assertNotIn(RP["refresh_token"], body)
        self.assertEqual(self.post()[0], 409)
        self.assertEqual(self.request(suffix="/rp")[0], 409)
        self.saver.assert_called_once()

    def test_transport_failure_consumes_nonce_then_reload_permits_retry(self):
        self.saver.return_value = False
        nonce = self.server.nonces["rp"]
        self.assertEqual(self.post()[0], 502)
        self.assertNotIn("rp", self.server.saved)
        self.assertNotEqual(nonce, self.server.nonces["rp"])
        self.saver.return_value = True
        self.assertEqual(self.post(fields=[("csrf", nonce), ("access", json.dumps(RP))])[0], 400)
        self.assertEqual(self.request(suffix="/rp")[0], 200)
        self.assertEqual(self.post()[0], 200)

    def test_expiry_and_stop_refuse_save(self):
        self.server.expires = time.monotonic() - 1
        self.assertEqual(self.request()[0], 410)
        self.assertEqual(self.post()[0], 410)
        self.server.expires = time.monotonic() + 60
        self.server.stopping = True
        self.assertEqual(self.post()[0], 410)
        self.saver.assert_not_called()

    def test_size_encoding_and_content_type(self):
        self.assertEqual(self.post(value={"mode": "refresh_token", "refresh_token": "a" * bridge.MAX_BODY})[0], 413)
        self.assertEqual(self.post(headers={"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.post(headers={"Transfer-Encoding": "chunked"})[0], 400)
        for bad in (b"x=%ZZ", b"x=\xff", b"x=%FF"):
            self.assertEqual(self.request("POST", "/rp", bad, {"Origin": self.server.origin, "Content-Type": "application/x-www-form-urlencoded"})[0], 400)
        self.saver.assert_not_called()


class ValidationAndTransportTest(unittest.TestCase):
    def test_cookie_grammar_matches_provider_reader(self):
        for cookie in ('x; injected=1','"quoted"','comma,value','back\\slash'):
            with self.subTest(cookie=cookie), self.assertRaises(bridge.InvalidAccess):
                bridge.validate_access('ps',json.dumps({**PS,'auth_cookie':cookie}))

    def test_validation_rejects_bad_json_fields_expiry_and_controls(self):
        for provider, value in (("rp", "[]"), ("rp", "null"), ("rp", '{"mode":"refresh_token","mode":"refresh_token","refresh_token":"secret"}'),
                                ("rp", json.dumps({**RP, "extra": "no"})),
                                ("rp", json.dumps({**RP, "refresh_token": "\nsecret"})),
                                ("rp", json.dumps({**RP, "refresh_token": ""})),
                                ("ps", json.dumps({**PS, "expires_at": 1})),
                                ("ps", json.dumps({**PS, "expires_at": True})),
                                ("ps", json.dumps({**PS, "expires_at": float("inf")})),
                                ("ps", json.dumps({**PS, "expires_at": 10 ** 400})),
                                ("ps", json.dumps({**PS, "expires_at": -(10 ** 400)})),
                                ("ps", json.dumps({**PS, "auth_cookie": "secret\r\nheader"}))):
            with self.assertRaises(bridge.InvalidAccess):
                bridge.validate_access(provider, value)
        with self.assertRaises(bridge.InvalidAccess):
            bridge.validate_access("arbitrary", json.dumps(RP))

    def test_secret_only_in_ssh_stdin(self):
        for provider, value in (("rp", RP), ("ps", PS)):
            with patch.object(bridge.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
                self.assertTrue(bridge.save_access(provider, value))
            command = run.call_args.args[0]
            for secret in (RP["refresh_token"], PS["auth_cookie"]):
                self.assertNotIn(secret, " ".join(command))
            self.assertEqual(json.loads(run.call_args.kwargs["input"]), value)
            self.assertEqual(run.call_args.kwargs["stdout"], subprocess.DEVNULL)
            self.assertEqual(run.call_args.kwargs["stderr"], subprocess.DEVNULL)
            self.assertIn(str(bridge.SSH_CONFIG), command)
            self.assertIn("salad-mumbai", command)
            self.assertTrue(command[-1].startswith("/usr/bin/python3 -c "))
            self.assertNotIn("sudo -n /usr/bin/python3 -c", command[-1])
            self.assertIn(bridge.PROVIDERS[provider][1], command[-1])
            self.assertIn(bridge.PROVIDERS[provider][2], command[-1])

    def test_transport_failure_is_boolean_and_redacted(self):
        with patch.object(bridge.subprocess, "run", side_effect=subprocess.TimeoutExpired("hidden", 130, output=RP["refresh_token"])):
            self.assertFalse(bridge.save_access("rp", RP))
        with patch.object(bridge.subprocess, "run", return_value=subprocess.CompletedProcess([], 1)):
            self.assertFalse(bridge.save_access("rp", RP))

    def test_remote_restart_in_finally_on_save_failure_and_stop_timeout(self):
        import io
        for fail_at in ("save", "stop", "none"):
            results = ([subprocess.CompletedProcess([], 0), subprocess.CompletedProcess([], 1), subprocess.CompletedProcess([], 0)] if fail_at == "save" else
                       [subprocess.TimeoutExpired("stop", 30), subprocess.CompletedProcess([], 0)] if fail_at == "stop" else
                       [subprocess.CompletedProcess([], 0)] * 3)
            command = shlex.split(bridge.remote_command("rp")[-1])
            script = command[-1]
            with patch.object(bridge.subprocess, "run", side_effect=results) as run, \
                    patch("sys.stdin", io.StringIO(json.dumps(RP))), patch("signal.signal"), self.assertRaises(SystemExit) as exited:
                exec(compile(script, "<fixed-remote-command>", "exec"), {})
            self.assertEqual(exited.exception.code, 0 if fail_at == "none" else 1)
            self.assertEqual(run.call_args.args[0], ["/usr/bin/sudo", "-n", "/usr/bin/systemctl", "start", "salad-repocket-provider.service"])
            if fail_at != "stop":
                saved = run.call_args_list[1]
                self.assertEqual(json.loads(saved.kwargs["input"]), RP)
                self.assertNotIn(RP["refresh_token"], " ".join(saved.args[0]))

    def test_cli_prints_only_local_url_and_closes_on_termination(self):
        import sys
        from urllib.parse import urlsplit
        process = subprocess.Popen([sys.executable, "-B", str(SOURCE)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            url = process.stdout.readline().strip()
            parsed = urlsplit(url)
            self.assertEqual(parsed.scheme, "http")
            self.assertEqual(parsed.hostname, "127.0.0.1")
            self.assertRegex(parsed.path, r"^/[A-Za-z0-9_-]{43}$")
            connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=2)
            connection.request("GET", parsed.path)
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            response.read()
            connection.close()
            process.send_signal(signal.SIGTERM)
            stdout, stderr = process.communicate(timeout=3)
            self.assertEqual(process.returncode, 1)
            self.assertEqual(stdout, "")
            self.assertEqual(stderr, "")
            with self.assertRaises(OSError):
                http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=1).connect()
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=3)


if __name__ == "__main__":
    unittest.main()
