# Windows GUI Test Checklist

Run this checklist after `START_GST_AUDIT_PRO.bat` and again after `build_exe.bat`.

## 1. Startup
- App opens in its own window.
- No browser opens.
- No terminal error is shown.
- Status bar shows the SQLite database path.

## 2. Theme and display
- Settings tab opens.
- Professional Light, Professional Dark, Professional Blue, and Audit High Contrast apply correctly.
- Font size changes table text and page labels.
- Compact, Comfortable, and Large density changes table row height.
- Window size and fullscreen options work.

## 3. Upload and processing
- Select all GST Excel files.
- Process completes without crash.
- Dataset is saved to `data/gst_invoice_audit.sqlite3`.
- Dashboard shows raw rows, classified rows, approved rows, review rows, skipped rows, GST mismatches, and final status.

## 4. Audit rows
- Search by supplier name works.
- Search by GSTIN works.
- Search by invoice number works.
- Review Rows filter shows only pending review rows.
- View Raw / Detected / Final shows original row snapshot and detected values.

## 5. Manual review persistence
- Select a review row.
- Click Accept Selected and enter a note.
- Confirm dashboard total changes.
- Close the app.
- Reopen the app.
- Click Load Last Saved Dataset.
- Confirm the review decision and note are still present.

## 6. Supplier/GSTIN drill-down
- Search one supplier.
- Search one GSTIN.
- Confirm invoice count and totals match approved rows.

## 7. Reconciliation
- Raw Row Coverage must show MATCHED.
- Amount Cross-Check must show MATCHED.
- Final status may show BALANCED_BUT_REVIEW_REQUIRED if unresolved rows exist.

## 8. Export
- Export verified Excel.
- Open the exported workbook.
- Confirm sheets exist: Audit Summary, Approved Rows, Review Required, Skipped Rows, GST Mismatches, Supplier Summary, Source Reconciliation, Month Reconciliation.

## 9. EXE build test
- Run `build_exe.bat`.
- Confirm `dist/GSTInvoiceAudit/GSTInvoiceAudit.exe` exists.
- Double-click EXE.
- Repeat steps 1–8.
