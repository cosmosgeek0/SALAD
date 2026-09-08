"""Offline checks: terminal-only entry and a secret-free helper argument list."""

from contextlib import nullcontext, redirect_stdout, redirect_stderr
import getpass
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import Mock, patch


SOURCE = Path(__file__).resolve().parents[1] / "scripts/save-provider-access.py"
spec = importlib.util.spec_from_file_location("provider_access", SOURCE)
access = importlib.util.module_from_spec(spec)
spec.loader.exec_module(access)


class ProviderAccessTest(unittest.TestCase):
    def call(self, answers, mode="1\n", args=None, result=None):
        terminal = Mock()
        terminal.readline.return_value = mode
        stdout, stderr = io.StringIO(), io.StringIO()
        result = result or subprocess.CompletedProcess([], 0, "", "")
        with patch.object(access, "open_terminal", return_value=nullcontext(terminal)), \
                patch.object(access.getpass, "getpass", side_effect=answers), \
                patch.object(access.getpass, "getuser", return_value="test-user"), \
                patch.object(access.subprocess, "run", return_value=result) as helper, \
                redirect_stdout(stdout), redirect_stderr(stderr):
            code = access.main(args or [])
        return code, helper, stdout.getvalue() + stderr.getvalue()

    def test_noninteractive_refused_before_helper_or_prompt(self):
        with patch.object(access.sys, "stdin", Mock(isatty=lambda: False)), \
                patch.object(access, "storage") as helper, \
                patch.object(access.getpass, "getpass") as prompt, \
                redirect_stderr(io.StringIO()):
            self.assertEqual(access.main([]), 1)
        helper.assert_not_called()
        prompt.assert_not_called()

    def test_no_controlling_terminal_refused(self):
        with patch.object(access.sys, "stdin", Mock(isatty=lambda: True)), \
                patch.object(access.sys, "stderr", Mock(isatty=lambda: True)), \
                patch("builtins.open", side_effect=OSError("unavailable")), \
                self.assertRaises(access.AccessError):
            with access.open_terminal():
                self.fail("opened a nonexistent terminal")

    def test_empty_secret_never_calls_helper(self):
        for answers in ([""], ["test@example.invalid", "   "]):
            code, helper, output = self.call(answers)
            self.assertEqual(code, 1)
            helper.assert_not_called()
            self.assertIn("Empty credentials", output)

    def test_hidden_input_warning_is_failure(self):
        def insecure(*args, **kwargs):
            import warnings
            warnings.warn("Password input may be echoed", getpass.GetPassWarning)
            return "must-not-save"
        code, helper, output = self.call(insecure)
        self.assertEqual(code, 1)
        helper.assert_not_called()
        self.assertNotIn("must-not-save", output)

    def test_email_password_only_in_helper_stdin(self):
        email, password = "unique@example.invalid", "  unique password!  "
        code, helper, output = self.call([email, password])
        self.assertEqual(code, 0)
        command = helper.call_args.args[0]
        sent = json.loads(helper.call_args.kwargs["input"])
        self.assertEqual(sent["mode"], "email_password")
        self.assertEqual(sent["email"], email)
        self.assertEqual(sent["password"], password)
        self.assertIn("saved_at", sent)
        self.assertNotIn("expires_at", sent)
        for secret in (email, password):
            self.assertNotIn(secret, " ".join(command))
            self.assertNotIn(secret, output)
        self.assertIn("repocket-provider-session", command)
        self.assertIn("test-user", command)
        self.assertTrue(helper.call_args.kwargs["capture_output"])

    def test_password_mode_skips_method_menu(self):
        code, helper, output = self.call(["owner@example.invalid", "private-password"],
                                         mode="invalid if read", args=["--mode", "email_password"])
        self.assertEqual(code, 0)
        sent = json.loads(helper.call_args.kwargs["input"])
        self.assertEqual(sent["mode"], "email_password")
        self.assertNotIn("private-password", output)
        self.assertNotIn("private-password", " ".join(helper.call_args.args[0]))

    def test_refresh_token_and_helper_errors_never_print_secrets(self):
        token = "unique-firebase-refresh-secret"
        result = subprocess.CompletedProcess([], 1, token, token)
        code, helper, output = self.call([token], mode="2\n", result=result)
        self.assertEqual(code, 1)
        sent = json.loads(helper.call_args.kwargs["input"])
        self.assertEqual(sent["mode"], "refresh_token")
        self.assertEqual(sent["refresh_token"], token)
        self.assertNotIn("password", sent)
        self.assertNotIn(token, " ".join(helper.call_args.args[0]))
        self.assertNotIn(token, output)

    def test_check_only_discloses_known_mode_and_presence(self):
        stored = {"mode": "email_password", "email": "private@example.invalid",
                  "password": "private-password", "refresh_token": ""}
        code, helper, output = self.call([], args=["--check"], result=
            subprocess.CompletedProcess([], 0, json.dumps(stored), ""))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output), {"mode": "email_password", "email_present": True,
            "password_present": True, "refresh_token_present": False})
        self.assertIn("--read", helper.call_args.args[0])
        self.assertIsNone(helper.call_args.kwargs["input"])
        self.assertEqual(helper.call_args.kwargs["stdin"], subprocess.DEVNULL)

    def test_unknown_mode_is_redacted_and_incomplete_is_failure(self):
        for stored in ({"mode": "secret-mistakenly-in-mode"},
                       {"mode": "email_password", "email": "present@example.invalid"}):
            code, _, output = self.call([], args=["--check"], result=
                subprocess.CompletedProcess([], 0, json.dumps(stored), ""))
            self.assertEqual(code, 1)
            self.assertNotIn("secret-mistakenly-in-mode", output)
            self.assertNotIn("present@example.invalid", output)


if __name__ == "__main__":
    unittest.main()
