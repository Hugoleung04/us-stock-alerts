from __future__ import annotations

import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def serve(output_dir: str, host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    root = Path(output_dir).resolve()
    dash = root / "dashboard.html"
    if not dash.exists():
        raise FileNotFoundError(f"Missing {dash}. Run a scan first.")

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

        def log_message(self, fmt: str, *args) -> None:
            print("[dash] " + (fmt % args))

    httpd = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}/dashboard.html"
    print(f"Dashboard: {url}")
    print("Notify only. No orders. Ctrl+C to stop.")
    if open_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()
