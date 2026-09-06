"""Serve dist with Cloudflare Pages' extensionless HTML paths for local review."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit, unquote
import argparse

ROOT = Path(__file__).resolve().parents[1] / "dist"

class Preview(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def translate_path(self, path):
        resolved = Path(super().translate_path(path))
        if not resolved.exists() and not Path(unquote(urlsplit(path).path)).suffix:
            html = resolved.with_suffix('.html')
            if html.is_file():
                return str(html)
        return str(resolved)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8873)
    args = parser.parse_args()
    print(f"Preview: http://127.0.0.1:{args.port}", flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Preview).serve_forever()
