"""Exercise the shell wrapper with fake SSH/sudo; never contact a host."""

import json
import os
from pathlib import Path
import pty
import shutil
import signal
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/connect-provider.sh"


class ConnectProviderTest(unittest.TestCase):
    def setUp(self):
        self.scratch = ROOT / ".work/secret-entry"
        self.scratch.mkdir(parents=True, exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=self.scratch)
        self.base = Path(self.directory.name) / "bundle with spaces"
        self.script = self.base / "repocket/scripts/connect-provider.sh"
        self.script.parent.mkdir(parents=True)
        shutil.copyfile(SOURCE, self.script)
        self.config = self.base / "Website/linux/ssh_config"
        self.config.parent.mkdir(parents=True)
        self.config.write_text("Host salad-mumbai\n")
        self.bin = Path(self.directory.name) / "fake-bin"
        self.bin.mkdir()
        self.calls = Path(self.directory.name) / "calls.jsonl"
        self.environment = {**os.environ, "PATH": str(self.bin) + os.pathsep + os.environ["PATH"],
                            "RP_TEST_CALLS": str(self.calls)}
        self.stub("ssh", """import json, os, sys
with open(os.environ['RP_TEST_CALLS'], 'a') as target:
    target.write(json.dumps(sys.argv[1:]) + '\\n')
""")

    def tearDown(self):
        self.directory.cleanup()
        try:
            self.scratch.rmdir()
        except OSError:
            pass

    def stub(self, name, source):
        script = self.bin / name
        script.write_text("#!/usr/bin/env python3\n" + source)
        script.chmod(0o700)

    def local(self, *, stdin_tty=True, stderr_tty=True):
        master, slave = pty.openpty()
        try:
            return subprocess.run(["/bin/bash", str(self.script)], cwd="/",
                stdin=slave if stdin_tty else subprocess.DEVNULL,
                stderr=slave if stderr_tty else subprocess.PIPE,
                stdout=subprocess.PIPE, env=self.environment, text=True, timeout=5)
        finally:
            os.close(slave)
            os.close(master)

    def remote_command(self):
        result = self.local()
        self.assertEqual(result.returncode, 0, result.stderr)
        command = json.loads(self.calls.read_text().splitlines()[0])
        self.calls.unlink()
        return command

    def run_remote(self, *, entry_code=0, stop_code=0, start_code=0, entry_signal=0):
        command = self.remote_command()
        self.stub("sudo", """import json, os, sys
args = sys.argv[1:]
with open(os.environ['RP_TEST_CALLS'], 'a') as target:
    target.write(json.dumps(args) + '\\n')
if args[:2] == ['-n', 'systemctl']:
    sys.exit(int(os.environ['RP_TEST_STOP' if args[2] == 'stop' else 'RP_TEST_START']))
if int(os.environ['RP_TEST_SIGNAL']):
    os.kill(os.getppid(), int(os.environ['RP_TEST_SIGNAL']))
sys.exit(int(os.environ['RP_TEST_ENTRY']))
""")
        result = subprocess.run(["/bin/sh", "-c", command[-1]],
            env={**self.environment, "RP_TEST_ENTRY": str(entry_code),
                 "RP_TEST_STOP": str(stop_code), "RP_TEST_START": str(start_code),
                 "RP_TEST_SIGNAL": str(int(entry_signal))},
            capture_output=True, text=True, timeout=5)
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        return result, calls

    def test_either_non_tty_stream_blocks_ssh(self):
        for stdin_tty, stderr_tty in ((False, True), (True, False), (False, False)):
            result = self.local(stdin_tty=stdin_tty, stderr_tty=stderr_tty)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(self.calls.exists())

    def test_paths_with_spaces_and_arbitrary_working_directory(self):
        command = self.remote_command()
        self.assertEqual(command[0], "-F")
        self.assertEqual(Path(command[1]).resolve(), self.config)
        self.assertEqual(command[2:4], ["-tt", "salad-mumbai"])
        self.assertEqual(len(command), 5)
        self.assertEqual(self.config.read_text(), "Host salad-mumbai\n")

    def test_missing_config_blocks_ssh(self):
        self.config.unlink()
        self.assertEqual(self.local().returncode, 2)
        self.assertFalse(self.calls.exists())

    def test_success_and_cancel_restart_only_provider(self):
        for code in (0, 1, 130):
            result, calls = self.run_remote(entry_code=code)
            self.assertEqual(result.returncode, code, result.stderr)
            self.assertEqual(calls, [
                ["-n", "systemctl", "stop", "salad-repocket-provider.service"],
                ["-n", "-u", "salad", "/usr/bin/python3", "-B",
                 "/opt/salad/scripts/save-provider-access.py", "--mode", "email_password"],
                ["-n", "systemctl", "start", "salad-repocket-provider.service"],
            ])
            self.calls.unlink()

    def test_failed_stop_attempts_restart_without_opening_entry(self):
        result, calls = self.run_remote(stop_code=130)
        self.assertEqual(result.returncode, 130)
        self.assertEqual([call[2] for call in calls], ["stop", "start"])

    def test_interruption_and_disconnect_signals_restart_provider(self):
        for signum in (signal.SIGINT, signal.SIGHUP, signal.SIGTERM):
            result, calls = self.run_remote(entry_signal=signum)
            self.assertEqual(result.returncode, 128 + signum, result.stderr)
            self.assertEqual(calls[-1],
                ["-n", "systemctl", "start", "salad-repocket-provider.service"])
            self.calls.unlink()

    def test_restart_failure_is_reported_and_nonzero(self):
        result, _ = self.run_remote(start_code=1)
        self.assertEqual(result.returncode, 1)
        self.assertIn("could not restart", result.stderr)


if __name__ == "__main__":
    unittest.main()
