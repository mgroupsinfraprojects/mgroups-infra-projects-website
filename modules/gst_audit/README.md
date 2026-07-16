# GST Invoice Audit — v11.13.0
APP_VERSION: 11.13.0

This package supports both desktop mode and local browser mode.

## Main change in v11.13.0

Web mode no longer has its own login screen. Use your main portal/login outside this module.

Web mode now uses a stricter invoice-row policy:

- Company / supplier name required
- GSTIN required
- Invoice number required
- Invoice value required
- Header rows, GSTR section rows, ITC summary rows, zero-value support rows, and incomplete identity rows are excluded from web dashboard and review actions

## Run desktop

```bat
START_GST_AUDIT_PRO.bat
```

## Run web

```bat
RUN_WEB_GST_AUDIT.bat
```

Open:

```text
http://127.0.0.1:8088
```

No username/password is required in this module. Add your own portal authentication before exposing it online.

## Web pages included

- Upload Excel / CSV
- Dashboard totals
- Month-wise totals
- File-wise totals
- Review only real invoice issues
- Supplier summary
- Click supplier to see invoice details
- Approved invoice data preview
- Excel export
- Audit log CSV

## Build Windows EXE

```bat
build_exe.bat
```

Expected output:

```text
dist\GSTInvoiceAudit\GSTInvoiceAudit.exe
```

## Notes

This is an audit/reconciliation assistant for Excel/CSV GST invoice data. It is not GST filing software and does not perform live GSTN/e-invoice/e-way bill submission.
