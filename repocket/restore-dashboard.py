"""Serve the preserved dashboard's RP routes without starting other provider pollers."""
import argparse
from http.server import ThreadingHTTPServer
from pathlib import Path
from dashboard.server import make_handler
from dashboard.store import Store

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--port', type=int, default=8787)
args = parser.parse_args()
root = Path(__file__).resolve().parent
store = Store(Path.home() / '.hg1/repocket/recovery-dashboard.sqlite3')
handler = make_handler(store, lambda: {'poll_state': 'disabled'}, root / 'dashboard/static')
server = ThreadingHTTPServer(('127.0.0.1', args.port), handler)
print(f'RP monitor: http://127.0.0.1:{args.port}/#rp', flush=True)
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    server.server_close()
    store.close()
