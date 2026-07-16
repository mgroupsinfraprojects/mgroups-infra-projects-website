# v11.8 Clean Important Review UI

This release reduces review noise and keeps only real important items in Fix Issues.

## Review threshold controls

Admin Settings → Audit Rules now controls:

- Critical invoice-value difference
- Advisory difference starting amount
- Ignore tiny difference below amount
- Critical GST component difference
- Duplicate review minimum value
- Critical percentage difference
- High-value supplier threshold

Identity problems remain reviewable regardless of amount:

- GSTIN error
- supplier missing
- invoice number missing
- date error
- meaningful duplicate supplier invoice

## Dashboard simplification

Dashboard now focuses on:

- Search
- Totals
- Charts
- Optional supplier drill-down

The full Fix Issues panel is not embedded in Dashboard. Users must open the Fix Issues page for corrections.

## Appearance safety

Custom theme now exposes only controlled accent colours. Background, card, and text colours are locked to professional palettes so users cannot create unreadable combinations.
