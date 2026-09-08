#!/usr/bin/env python3
"""Save RP provider access through the installed private credential helper."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import getpass
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import warnings


ROOT = Path(__file__).resolve().parents[1]
SERVICE = "repocket-provider-session"
MODES = ("email_password", "refresh_token")


class AccessError(Exception):
    """An error whose message is safe to display."""


@contextmanager
def open_terminal():
    # getpass can otherwise fall back to echoed stdin. Never permit that path.
    if not sys.stdin.isatty() or not sys.stderr.isatty():
        raise AccessError("Run this command in an interactive terminal; piped input is refused.")
    try:
        # BufferedRandom (ordinary r+) requires a seekable stream; a terminal is
        # not seekable. Wrap an unbuffered bidirectional device instead.
        terminal = io.TextIOWrapper(open("/dev/tty", "r+b", buffering=0),
                                   encoding="utf-8", write_through=True)
    except OSError:
        raise AccessError("A controlling terminal is required.") from None
    with terminal:
        if not os.isatty(terminal.fileno()):
            raise AccessError("A controlling terminal is required.")
        yield terminal


def present(value):
    return isinstance(value, str) and bool(value.strip())


def hidden(prompt, terminal):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            value = getpass.getpass(prompt, stream=terminal)
    except (getpass.GetPassWarning, EOFError, OSError):
        raise AccessError("Hidden terminal input is unavailable; nothing was saved.") from None
    if not present(value):
        raise AccessError("Empty credentials are refused; nothing was saved.")
    return value


def read_access(terminal, mode=None):
    if mode is None:
        terminal.write("Access method: 1 = email/password, 2 = Firebase refresh token\nChoose 1 or 2: ")
        terminal.flush()
        choice = terminal.readline().strip()
    else:
        choice = "1" if mode == "email_password" else "2"
    if choice == "1":
        payload = {
            "mode": "email_password",
            "email": hidden("Repocket email (hidden): ", terminal).strip(),
            "password": hidden("Repocket password (hidden): ", terminal),
        }
    elif choice == "2":
        payload = {
            "mode": "refresh_token",
            "refresh_token": hidden("Firebase refresh token (hidden): ", terminal).strip(),
        }
    else:
        raise AccessError("Choose 1 or 2; nothing was saved.")
    payload["saved_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return payload


def storage(*, payload=None):
    command = [str(ROOT / ".runtime/keychain-store"), "--service", SERVICE,
               "--account", getpass.getuser()]
    if payload is None:
        command.append("--read")
    try:
        result = subprocess.run(
            command,
            input=None if payload is None else json.dumps(payload, separators=(",", ":")),
            stdin=subprocess.DEVNULL if payload is None else None,
            text=True, capture_output=True, timeout=30, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        raise AccessError("Credential helper did not complete; saved state is unverified.") from None
    if result.returncode:
        # Helper errors can contain request bodies. Do not relay either stream.
        raise AccessError("Credential helper failed; saved state is unverified.")
    if payload is not None:
        return None
    try:
        value = json.loads(result.stdout)
    except (ValueError, TypeError):
        raise AccessError("Stored access is not a valid credential record.") from None
    if not isinstance(value, dict):
        raise AccessError("Stored access is not a valid credential record.")
    return value


def check_access():
    payload = storage()
    mode = payload.get("mode")
    summary = {
        "mode": mode if mode in MODES else "unsupported",
        "email_present": present(payload.get("email")),
        "password_present": present(payload.get("password")),
        "refresh_token_present": present(payload.get("refresh_token")),
    }
    print(json.dumps(summary, separators=(",", ":")))
    if mode == "email_password":
        return 0 if summary["email_present"] and summary["password_present"] else 1
    return 0 if mode == "refresh_token" and summary["refresh_token_present"] else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=MODES,
                        help="select the known sign-in method without another menu")
    parser.add_argument("--check", action="store_true",
                        help="show only the stored mode and field presence; no provider login is attempted")
    args = parser.parse_args(argv)
    try:
        with open_terminal() as terminal:
            if args.check:
                return check_access()
            storage(payload=read_access(terminal, args.mode))
        print("Repocket access saved through the private credential helper. Provider login is not yet verified.")
        return 0
    except (KeyboardInterrupt, EOFError):
        print("Cancelled; saved state is unverified.", file=sys.stderr)
        return 1
    except AccessError as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
