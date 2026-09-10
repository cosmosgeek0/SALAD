import tempfile
import unittest
from pathlib import Path
from dashboard.server import make_handler, history_snapshot


class ServiceRetirement(unittest.TestCase):
    def test_removed_documents_and_feed_return_not_found(self):
        with tempfile.TemporaryDirectory() as directory:
            handler = make_handler(None, lambda: {}, Path(directory), trusted_uid=100)
            for path in ('/earnapp', '/earnapp.html', '/api/earnapp'):
                request = object.__new__(handler)
                request.path = path
                request.headers = {}
                seen = []
                request.send_json = lambda status, body: seen.append(status)
                request.do_GET()
                self.assertEqual(seen, [404], path)

    def test_retired_history_is_not_reopened(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'Unknown history service'):
                history_snapshot(Path(directory), {'service': ['earnapp']}, None, {}, None)

    def test_navigation_has_no_retired_service(self):
        source = (Path(__file__).resolve().parents[1] / 'static/fleet-test.js').read_text()
        self.assertNotIn("id:'earnapp'", source)
        self.assertIn("id:'grass'", source)


if __name__ == '__main__':
    unittest.main()
