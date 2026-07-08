# M-GROUPS Final Production Details Checklist

Do not send real passwords in chat. Set them privately in Render Environment or in your local `.env` file.

## 1. Admin account details

Required:

- `ADMIN_USERNAME`: recommended `admin` or `owner`
- `ADMIN_DEFAULT_PASSWORD`: temporary first-login password only
- `ADMIN_RECOVERY_EMAIL`: owner recovery email address

Password recommendation:

- Minimum 14 characters
- Use uppercase + lowercase + number + symbol
- Do not use name, phone number, company name, date of birth, `ChangeMe`, `Admin@123`, or Gmail password
- Example format only: `Mg@2026-SiteOwner-7xQ!` — make your own, do not copy this

After first login:

1. Open `/admin`.
2. Login with the temporary password.
3. Open Admin > Change Password.
4. Change to the real owner password.
5. Store it in a password manager or written private company record.

## 2. Recovery email

Recommended:

- Use a Gmail or business email owned by the company owner.
- Enable 2FA on that email.
- Do not use an employee-only email as the only recovery address.

Example variable:

```text
ADMIN_RECOVERY_EMAIL=mgroups.owner@example.com
```

## 3. Database storage

Required for final Render deployment:

```text
DATABASE_URL=postgresql://...
```

Use PostgreSQL. Do not depend on local SQLite for final hosting because data can be lost during redeploys.

## 4. Image/file storage

Required for final Render deployment:

```text
CLOUDINARY_URL=cloudinary://...
```

Use Cloudinary for logo, gallery, project images, and uploaded content. Do not depend on local uploads for final hosting.

## 5. Contact enquiry email and admin forgot-password email

Recommended:

```text
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-business-gmail@gmail.com
SMTP_PASSWORD=google-app-password
SMTP_FROM=your-business-gmail@gmail.com
SMTP_TO=main-business-email@example.com
SMTP_USE_TLS=1
```

Important: Gmail SMTP requires an App Password. Do not use the normal Gmail login password.

The admin forgot-password feature also uses the same SMTP settings. Without SMTP, the recovery page will exist but cannot send reset links.

## 6. Public company details needed from you

Provide/enter inside admin panel:

- Official company name
- Registered office address
- Public phone number / WhatsApp number
- Public email ID
- Google Maps embed link
- Google Business Profile link
- GST/Udyam visibility decision: public, hidden, or partial
- Real service list
- Real project names and locations
- Project photos you are allowed to publish
- Privacy Policy and Terms text if you want custom legal wording

## 7. Recommended role setup

Create separate accounts:

| Person | Role | Access |
|---|---|---|
| You / owner | owner | Full admin, users, backup, restore |
| Boss | owner or viewer | Owner only if they must manage users/settings |
| Manager | editor | Content/project/gallery updates |
| Staff | viewer | Read-only admin view |

Do not share one admin password across all people.

## 8. Backup rule

After final content setup:

1. Download Admin > Backup.
2. Store one copy in Google Drive.
3. Store one copy offline.
4. Repeat backup after major project/content updates.
