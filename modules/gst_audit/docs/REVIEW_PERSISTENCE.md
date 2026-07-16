# Review Decision Persistence

Manual accept/reject decisions are saved into SQLite.

Database file:

```text
data/gst_invoice_audit.sqlite3
```

Tables used:

```text
datasets
invoice_rows
review_decisions
```

When a row is accepted or rejected:

```text
invoice_rows.review_decision is updated
invoice_rows.include_in_totals is updated
invoice_rows.review_required is set to false
review_decisions receives a history record
```

Dashboard totals are recalculated after every manual decision.

Use **Load Last Saved Dataset** to verify that decisions remain after the app closes.
