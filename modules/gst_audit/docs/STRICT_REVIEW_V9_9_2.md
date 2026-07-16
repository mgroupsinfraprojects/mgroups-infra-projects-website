# Strict Review — GST Invoice Audit Desktop v9.9.3

## Final source-level score

**93 / 100**

Grade: **Elite source package candidate, not fully enterprise-certified yet.**

This score is based on direct source inspection, release verification, regression tests, smoke processing, sample datasets, settings improvements, packaging discipline, and remaining deployment limits.

## Verification evidence

| Check | Result |
|---|---:|
| `python scripts/dev.py release-check` | Passed |
| `python -m pytest --no-cov` | 159 passed, 2 skipped |
| `python -m pytest -q` | 89% `app.core` coverage |
| Processor smoke test | Passed |
| Sample datasets: balanced Excel | Fully verified |
| Sample datasets: review/duplicate Excel | Balanced, review required |
| Sample datasets: CSV import | Fully verified |
| Multi-file batch sample | Balanced, review required |

The two skipped tests are PySide6 GUI tests. They require a Windows/PySide6 runtime and are not a source-code failure.

## Category score

| Area | Score | Strict comment |
|---|---:|---|
| GST audit correctness | 92 | Strong duplicate control, Decimal money handling, reconciliation, GSTIN/HSN support, review flags. Still heuristic-heavy for messy real books. |
| Core test strength | 89 | Improved from 87 to 89 with security/performance/branding/logging tests. Needs more analytics/audit-engine branch coverage to exceed 92. |
| Settings/configuration | 90 | Improved materially. Software name, window title, sidebar labels, theme, density, window size, and GSTIN rule lists are now configurable. |
| UI workflow | 90 | Sidebar workflow, review queue, dashboard, reconciliation, export preview are strong. Full Windows GUI testing still needed. |
| Release discipline | 95 | `release-check` now passes cleanly and includes sample dataset checks. Build gate now calls full release gate. |
| Folder structure clarity | 93 | Runtime, scripts, docs, tests, config, deployment, and quality folders are clearer. Historical noise was removed. |
| Documentation | 90 | Current docs updated. Still needs a polished client-facing user manual with screenshots after Windows GUI validation. |
| Enterprise readiness | 82 | Source has security primitives, but signed installer, RBAC integration, DB-at-rest policy, backups, and auto-update are not complete. |

## What was improved in v9.9.3

1. Added `config/app_identity.json` for changing product name and navigation labels without editing Python.
2. Added `app.core.branding` with sanitization and safe fallbacks.
3. Upgraded Settings into a control center:
   - software short name,
   - window title,
   - sidebar title/subtitle,
   - sidebar navigation labels,
   - theme,
   - custom colors,
   - density,
   - startup size,
   - ignored GSTINs,
   - self GSTINs.
4. Updated `main.py` and `MainWindow` to use dynamic branding.
5. Improved build discipline: `build_exe.bat` now runs full `scripts/dev.py release-check` before building.
6. Replaced placeholder QSS files with meaningful reference skins.
7. Removed obsolete historical scorecards/training notes from the clean release package.
8. Added regression tests for branding/settings/security/performance/logging/money formatting.
9. Updated test results and release documentation.

## Remaining blockers before 98+

| Blocker | Why it matters |
|---|---|
| Windows GUI/EXE test not run here | Container lacks PySide6/Windows runtime; final app polish must be verified on target OS. |
| Unsigned installer/EXE | Client machines will show unknown-publisher trust warnings. |
| No real user/RBAC workflow in UI | Security helpers exist, but user management is not productized. |
| No database-at-rest deployment policy | Security primitives exist, but enterprise storage policy is not finalized. |
| Large UI files remain | `guided_filter.py` and `theme_manager.py` are functional but still large; future split would improve maintainability. |

## Verdict

v9.9.3 is now a strong elite-level **source package**. It is suitable for internal/power-user testing. It should not be called unbeatable enterprise software until Windows EXE validation, installer signing, and deployment security are completed.
