# Render Environment Setup

Add these environment variables in Render > Your Service > Environment.

## Required for production

```text
SECRET_KEY=generate-a-long-random-secret
COOKIE_SECURE=1
DATABASE_URL=your-render-postgresql-or-external-postgres-url
CLOUDINARY_URL=your-cloudinary-url
```

## Required for first admin + password recovery

```text
ADMIN_USERNAME=admin
ADMIN_DEFAULT_PASSWORD=your-private-temporary-password
ADMIN_RECOVERY_EMAIL=owner-recovery-email@example.com
ADMIN_RESET_TOKEN_MINUTES=30
```

## Required for enquiry email notification and forgot-password email

```text
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-google-app-password
SMTP_FROM=your-email@gmail.com
SMTP_TO=your-business-email@gmail.com
SMTP_USE_TLS=1
```

## Recommended Render settings

```text
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app
```

## After deployment

1. Open `/healthz` and confirm database is OK.
2. Open `/admin` and login.
3. Change admin password.
4. Add real company content.
5. Add real project photos.
6. Add Google Map embed and Google Business Profile link.
7. Submit a test enquiry and check email notification.
8. Open `/admin/forgot-password` and verify password reset email sends correctly.
8. Download a backup from admin.
