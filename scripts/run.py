"""Serves the built visualizer (build/site/) on this computer only and opens it in your browser.
Builds it first if there is no build yet; after a change, run scripts/build.py and reload.

    python3 scripts/run.py               # port 8000, or the next free one
    python3 scripts/run.py --port 9000   # start looking at another port
    python3 scripts/run.py --no-open     # don't open a browser

Ctrl+C stops it. A port something else already uses is skipped, never shared.
"""
import argparse
import functools
import http.server
import os
import socket
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "build" / "site"


def free_port(start: int) -> int:
    """The first port from start on that nothing on this computer listens to."""
    for port in range(start, start + 50):
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise SystemExit("no free port from %d to %d" % (start, start + 49))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8000, help="the first port to try (default 8000)")
    parser.add_argument("--no-open", action="store_true", help="don't open a browser")
    args = parser.parse_args()

    if not (SITE / "index.html").exists():
        print("No build yet: building first.")
        sys.path.insert(0, str(ROOT / "scripts"))
        import build
        build.main()

    port = free_port(args.port)
    url = "http://127.0.0.1:%d/" % port
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    print("Serving build/site at %s (Ctrl+C stops)" % url, flush=True)
    if not args.no_open:
        threading.Timer(0.5, webbrowser.open, args=[url]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    os.chdir(ROOT)
    main()
