from __future__ import annotations

import sys
import time
import webbrowser


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8088"
    delay = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
    time.sleep(max(0.0, delay))
    webbrowser.open(url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
