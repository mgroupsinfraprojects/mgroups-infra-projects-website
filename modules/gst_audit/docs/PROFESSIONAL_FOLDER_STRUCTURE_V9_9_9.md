# v9.9.9 Professional Folder Structure

This release keeps the runtime code stable under `app/`, but adds clear readable layer folders so the project is easier to review section-wise.

## Top-level structure

```text
GST Audit Pro/
├─ START_GST_AUDIT_PRO.bat       # one file the user opens on Windows
├─ main.py                       # Python entry point
├─ app/                          # actual runtime application
│  ├─ core/                      # backend GST logic and export logic
│  ├─ ui/                        # PySide6 frontend screens/controllers/widgets
│  ├─ assets/                    # QSS/theme assets
│  └─ resources/                 # app resources
├─ frontend/                     # readable facade for UI layer
├─ backend/                      # readable facade for core audit layer
├─ dashboard/                    # readable facade for dashboard ownership
├─ theme/                        # readable facade for theme/display ownership
├─ workflow/                     # readable facade for review-policy ownership
├─ data_layer/                   # readable facade for persistence/database
├─ security_layer/               # readable facade for security helpers
├─ config/                       # admin defaults and app identity
├─ sample_data/                  # known-good test files
├─ scripts/                      # release checks, smoke tests, sample checks
├─ tests/                        # regression, release, and architecture tests
└─ docs/                         # guides, architecture, review checklists
```

## What each layer owns

| Folder | Owns | Must not do |
|---|---|---|
| `app/core/` | GST parsing, validation, duplicate logic, quality gate, export | Import PySide6 or UI widgets |
| `app/ui/` | Windows GUI, pages, widgets, user actions | Recalculate GST rules independently |
| `frontend/` | Human-readable map to UI objects | Replace runtime UI code |
| `backend/` | Human-readable map to backend/domain logic | Import UI code |
| `dashboard/` | Dashboard discovery/ownership facade | Own tax calculation |
| `theme/` | Theme/display discovery/ownership facade | Hide audit warnings |
| `workflow/` | Review policy discovery/ownership facade | Export or alter database directly |
| `data_layer/` | Database/persistence facade | Own GST business rules |
| `security_layer/` | Security helper facade | Replace OS/enterprise security policy |
| `scripts/` | Developer/release automation | Contain business logic |
| `tests/` | Verification and regression proof | Ship runtime data |

## Why this structure is professional

The application has one stable runtime root: `app/`. The extra folders are facades/documentation layers. This avoids breaking imports while still giving a clear project map for reviewers, developers, and admin users.
