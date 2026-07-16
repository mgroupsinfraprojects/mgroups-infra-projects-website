# GST Audit Pro v11.2 Scoreable + Editable Interface Patch

## Purpose

This patch makes the interface easier to score, explain, and edit during review.

## Added

1. **Audit Readiness Score**
   - Visible on Start, Dashboard, Review, and Export pages.
   - Shows `score / 100`, grade, and the next action.
   - Score is based on row coverage, amount match, critical rows, advisory rows, trace rows, and final-export readiness.

2. **Review Table Risk Score**
   - Added a visible `Risk` column after `Flag`.
   - Higher score means fix the row earlier.
   - Critical identity/GST/amount rows and large differences receive higher risk.

3. **Editable Row Dialog**
   - Added `Edit Selected Row` on the Review page.
   - User can edit supplier, GSTIN, invoice number, date, taxable value, GST fields, invoice value, expected value, mismatch reason, and severity.
   - A reason/note is mandatory before saving.
   - The app recalculates difference and audit summary after edit.
   - The edited row is persisted into the current dataset when a dataset is loaded.

4. **Scorecard Panels**
   - Added scorecard panels to Start, Dashboard, Review, and Export.
   - Each panel tells the user what to do next instead of only showing technical counts.

## Strict limitation

This is still a source/ZIP desktop release, not a signed Windows installer. It improves interface usability but does not add live GSTN/e-invoice/e-way bill production integrations.
