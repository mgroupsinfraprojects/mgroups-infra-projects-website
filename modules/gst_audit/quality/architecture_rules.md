# Architecture Rules

1. `app/core` must not import `app/ui`.
2. `app/core` must not import PySide6.
3. UI may depend on core, but core must remain headless.
4. Exporter may format audit results; it must not own independent audit rules.
5. New folders must include README documentation.
6. Release ZIPs must not contain cache, coverage, or local runtime artifacts.
