# Strict Score — v5 Verified Content Edition

## Package score

**88 / 100**

## Live score before environment setup

**80–83 / 100**

## Live score after PostgreSQL + Cloudinary + SMTP + real photos

**90–92 / 100**

## Improvements over v4

- Replaced placeholder contact details with registration-backed details.
- Added Udyam, GST, enterprise type, commencement date, registered address and major activity fields.
- Added business credentials section to Home and About pages.
- Added document-backed project/case-study seed entries from experience records and invoice/work order documentation.
- Removed vague generic claims and replaced with document-backed language.
- Added a Drive integration report explaining what is public-safe and what remains private.

## Remaining limits

- Experience certificates were visible by title but not text-extracted, so exact scope/value/duration was not invented.
- Project photos are still missing; construction websites need real photos to reach 90+ trust.
- Render production score still depends on DATABASE_URL, CLOUDINARY_URL and SMTP configuration.
- Public phone/email should be confirmed by the business owner before final sharing.
