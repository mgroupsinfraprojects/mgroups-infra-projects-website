# Elite Folder Structure — v9.9.3

```text
gst_invoice_audit_desktop/
├── main.py                         # GUI entry point
├── START_GST_AUDIT_PRO.bat          # one-click Windows launcher for users
├── build_exe.bat                    # gated EXE build script
├── requirements.txt                 # runtime dependencies
├── pyproject.toml                   # package metadata and test config
├── config/
│   ├── app_identity.json            # editable software name + navigation labels
│   └── README.md                    # how to customize app identity
├── app/
│   ├── version.py                   # single source for app version
│   ├── core/                        # GST parsing, audit, security, export, DB logic
│   ├── ui/                          # PySide6 screens, widgets, theme, worker
│   ├── assets/                      # icons, previews, reference QSS skins
│   └── resources/                   # fallback style resources
├── scripts/
│   ├── dev.py                       # test/smoke/release-check commands
│   ├── verify_release.py            # clean package verifier
│   ├── preflight_windows.py         # Windows/runtime diagnostics
│   ├── smoke_test_processor.py      # processor smoke test
│   └── run_sample_dataset_checks.py # golden sample dataset checks
├── sample_data/                     # known input files with expected outcomes
├── tests/                           # unit, integration, contract, release tests
├── docs/                            # current docs and validation reports
├── quality/                         # architecture rules and test matrix
├── deployment/                      # release checklist/deployment notes
├── frontend/                        # import-safe readable facade to UI
├── backend/                         # import-safe readable facade to core
├── data_layer/                      # import-safe readable facade to persistence
└── security_layer/                  # import-safe readable facade to security
```

## Recommended rule

Keep customer-facing release packages clean. Do not include old scorecards, training mind maps, temporary screenshots, `.coverage`, `.pytest_cache`, `__pycache__`, or local build outputs.
