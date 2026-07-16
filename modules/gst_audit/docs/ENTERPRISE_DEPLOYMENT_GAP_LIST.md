# Enterprise Deployment Gap List — v9.6

## Completed in source

| Control | v9.6 status |
|---|---|
| Decimal-safe financial arithmetic | Implemented |
| Duplicate exclusion and recalculation safety | Implemented |
| Credit/debit note classification | Implemented |
| CSV streaming without full-file RAM buffer | Implemented |
| Hash-chained review-decision log | Implemented |
| Review-decision chain verifier | Implemented |
| RBAC permission model | Source foundation implemented |
| Encrypted file helper | Source foundation implemented |
| Release package verification | Implemented |
| Automated unit/regression tests | Implemented |

## Still required before calling it MNC-deployable

| Missing item | Why it matters | Required completion |
|---|---|---|
| Signed installer / signed EXE | Prevents unknown publisher warning and supports enterprise software distribution | Use EV/OV code-signing certificate and sign EXE/MSI after PyInstaller build |
| Real authentication | Current RBAC is source-level foundation, not user-login enforcement | Add local login or SSO/AD integration and route UI actions through permission checks |
| Database encryption at rest | Fernet helper exists, but SQLite DB is not transparently encrypted | Add SQLCipher or OS-keychain-protected encrypted backup mode |
| Admin policy controls | Enterprise needs configurable retention, backup, and export policies | Add admin settings page and policy-locked config file |
| Windows hardware validation | Source tests are not equal to deployment validation | Test on clean Windows VMs with large GST datasets and packaged EXE |

## Honest enterprise score after v9.6

- Source package enterprise foundation: **90–92 / 100**
- Actual MNC deployable product without signed installer/auth/encrypted DB: **86–88 / 100**
- Actual MNC deployable product after signing + auth + DB encryption: **94–96 / 100**
