"""Exercise the real worker loop with controlled client replies, clock and IMDS."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest


def exercise(case):
    path = Path(__file__).resolve().parents[1] / 'source/traffmonetizer/worker.py'
    spec = importlib.util.spec_from_file_location('tm_fixture', path)
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    clock = SimpleNamespace(now=0, starts=0, kills=0, records=[], requests=[])
    worker.TOKEN = 'fixture'
    worker.time = SimpleNamespace(monotonic=lambda: clock.now, time=lambda: 1000000 + clock.now,
                                  sleep=lambda _: None)
    worker.counters = lambda: (0, 0)
    worker.signal = SimpleNamespace(SIGTERM=15, SIGINT=2, signal=lambda *_: None)
    worker.emit = lambda kind, **fields: clock.records.append(json.loads(json.dumps({'kind': kind, **fields})))

    class Client:
        def __init__(self, *_, **__):
            clock.starts += 1
            self.code = None
            self.stdout = SimpleNamespace(fileno=lambda: 1)
            self.stdin = SimpleNamespace(write=lambda _: None, flush=lambda: None)
        def poll(self):
            return 7 if case == 'exit' and clock.now >= 30 else self.code
        def terminate(self):
            clock.kills += 1
            self.code = 0
        kill = terminate
        def wait(self, **_):
            return self.code

    class Selector:
        def register(self, *_): pass
        def unregister(self, *_): pass
        def select(self, **_):
            clock.now += 10
            if clock.now >= 2400:
                worker.stopping = True
                return []
            if case == 'silent' and clock.now >= 30:
                return []
            return [(SimpleNamespace(fd=1, fileobj=None), 1)]

    def reply(*_):
        connected = 'false' if case == 'disconnected' and clock.now >= 30 else 'true'
        payload = 250000 if case == 'late_payload' and clock.now >= 1800 else 0
        return (f'Connected: {connected}; Accepting: {connected}\n'
                f'Inbound: {payload}; Outgoing: 0; Requests: {int(payload > 0)}\n').encode()

    class Response:
        status = 204
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def read(self, *_): return b'192.0.2.1'

    def open_url(request, **_):
        if not isinstance(request, str):
            clock.requests.append(request)
        return Response()

    worker.subprocess = SimpleNamespace(Popen=Client, PIPE=-1, STDOUT=-2,
                                       TimeoutExpired=TimeoutError)
    worker.selectors = SimpleNamespace(DefaultSelector=Selector, EVENT_READ=1)
    worker.os = SimpleNamespace(set_blocking=lambda *_: None, read=reply)
    worker.urllib = SimpleNamespace(request=SimpleNamespace(
        Request=worker.urllib.request.Request, urlopen=open_url))
    code = 0
    try:
        worker.main()
    except SystemExit as error:
        code = error.code
    return clock, code


class WorkerTests(unittest.TestCase):
    def test_healthy_idle_and_late_work_keep_same_client(self):
        for case in ('idle', 'late_payload'):
            with self.subTest(case=case):
                clock, code = exercise(case)
                self.assertEqual(code, 0)
                self.assertEqual(clock.starts, 1)
                self.assertEqual(clock.kills, 1)  # Operator stop only, after 40 simulated minutes.
                self.assertEqual(clock.requests, [])
                batches = [r for r in clock.records if r['kind'] == 'batch']
                self.assertTrue(batches)
                self.assertTrue(all(r['policy']['reallocate_on_idle'] is False for r in batches))
                self.assertTrue(any(s[4] == 0 and s[5] == 0 and s[8] == 'connected'
                                    for r in batches for s in r['samples']))
                if case == 'late_payload':
                    self.assertTrue(any(r['native_inbound'] == '250000' for r in batches))

    def test_actual_failures_still_request_replacement(self):
        for case, reason in [('silent', 'stopped replying'), ('disconnected', 'unavailable'),
                             ('exit', 'client exited')]:
            with self.subTest(case=case):
                clock, code = exercise(case)
                self.assertEqual(code, 75)
                self.assertEqual(len(clock.requests), 1)
                self.assertTrue(any(r['kind'] == 'reallocate' and reason in r['reason']
                                    for r in clock.records))


if __name__ == '__main__':
    unittest.main()
