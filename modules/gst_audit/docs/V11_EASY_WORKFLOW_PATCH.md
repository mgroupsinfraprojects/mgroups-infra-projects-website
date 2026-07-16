# GST Audit Pro v11 Easy Workflow Patch

This patch focuses on reducing the number of decisions a normal user must make after processing files.

## User workflow

1. Start Audit — choose Excel/CSV files and run the audit.
2. Audit Summary — read the decision card: Fix Critical Issues or Export.
3. Fix Issues — handle only Critical Review rows first.
4. Suppliers / GSTIN — inspect supplier-level invoice detail only when needed.
5. Reconciliation — verify row and amount proof.
6. Export — create a Draft Report anytime; create Final Report only when Critical Review = 0.

## Interface changes

- Start page text is now a checklist rather than a technical explanation.
- Review page wording is changed from a generic queue to a fix-first workflow.
- Supplier page explains exactly what to click and what the lower table means.
- Export page has separate Draft and Final report actions.
- Final Report button is disabled until Critical Review = 0.
- Supplier detail selection works for review-only suppliers, not only included-total suppliers.
- Final export guard blocks accidental clean reports while critical review rows remain open.

## Release validation

- Python compile: passed.
- Full pytest suite: 199 passed.
- Core coverage: 89%.
- Real uploaded 11-file smoke check: 4,031 rows processed; 3,874 approved; 78 review rows; status BALANCED_BUT_REVIEW_REQUIRED.

## Known remaining limitations

- This is still a ZIP/source launcher release, not a signed Windows installer.
- GSTN/e-invoice/e-way bill modules are guarded/scaffolded, not live production integrations.
- SQLite resource warnings remain in the test environment; they did not fail tests but should be cleaned before commercial release.
