# Admin Password Recovery Setup

V13 adds an admin forgot-password flow.

## Login credentials

There is no shipped public password.

For Render, set:

```text
ADMIN_USERNAME=admin
ADMIN_DEFAULT_PASSWORD=your-private-temporary-password
ADMIN_RECOVERY_EMAIL=owner-recovery-email@example.com
```

For local testing, if `ADMIN_DEFAULT_PASSWORD` is missing, the app creates:

```text
instance/admin_bootstrap_password.txt
```

Open that local file once, login, then change the password inside Admin > Change Password.

## Forgot password flow

The login page now has:

```text
Forgot password?
```

The admin must enter:

```text
Username
Registered recovery email
```

If the details match and SMTP is configured, the app emails a reset link. The link expires after `ADMIN_RESET_TOKEN_MINUTES` minutes. Default: 30.

## SMTP required

Password recovery emails require SMTP variables:

```text
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-business-gmail@gmail.com
SMTP_PASSWORD=your-google-app-password
SMTP_FROM=your-business-gmail@gmail.com
SMTP_TO=your-business-email@gmail.com
SMTP_USE_TLS=1
```

For Gmail, use a Google App Password, not the normal Gmail password.

## Security notes

- Do not commit `.env` to GitHub.
- Do not share the owner password.
- Use one admin account per person.
- Keep `ADMIN_RECOVERY_EMAIL` controlled by the owner.
