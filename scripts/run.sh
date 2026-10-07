#!/bin/sh
# Serves the built visualizer (build/site/) on this computer only and opens it in your browser.
# Builds it first if there is no build yet; after a change, run scripts/build.sh and reload.
#
#   sh scripts/run.sh            # port 8000, or the next free one
#   PORT=9000 sh scripts/run.sh  # start looking at another port
#   NO_OPEN=1 sh scripts/run.sh  # don't open a browser
#
# Ctrl+C stops it. A port something else already uses is skipped, never shared.
set -e
cd "$(dirname "$0")/.."

if [ ! -f build/site/index.html ]; then
  echo "No build yet: building first."
  sh scripts/build.sh
fi

port=$(python3 - "${PORT:-8000}" <<'EOF'
import socket, sys
start = int(sys.argv[1])
for port in range(start, start + 50):
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", port))
        except OSError:
            continue
        print(port)
        break
else:
    sys.exit("no free port from %d to %d" % (start, start + 49))
EOF
)
url="http://127.0.0.1:$port/"
echo "Serving build/site at $url (Ctrl+C stops)"

if [ -z "$NO_OPEN" ]; then
  (sleep 1; open "$url" 2>/dev/null || xdg-open "$url" 2>/dev/null || true) &
fi
exec python3 -m http.server "$port" --bind 127.0.0.1 --directory build/site
