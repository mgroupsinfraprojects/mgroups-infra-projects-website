from __future__ import annotations

import argparse

from web_portal.server import run


def main() -> int:
    parser = argparse.ArgumentParser(description="Run GST Audit Pro in browser/web mode.")
    parser.add_argument("--host", default="127.0.0.1", help="Host/interface to bind. Use 0.0.0.0 for LAN/server use.")
    parser.add_argument("--port", default=8088, type=int, help="Port number.")
    args = parser.parse_args()
    run(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
