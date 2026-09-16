# askher

## Email notifications

Every time someone responds, an email is sent to `NOTIFY_EMAIL` via
[Resend](https://resend.com)'s HTTPS API (used instead of SMTP because
Render blocks outbound SMTP ports on standard plans).

1. Sign up free at https://resend.com and grab an API key from the
   dashboard (starts with `re_`).
2. Set these environment variables on your host:

```
RESEND_API_KEY=re_yourapikeyhere
NOTIFY_EMAIL=abhiabhi4a@gmail.com   # optional, this is already the default
```

`RESEND_FROM` defaults to `onboarding@resend.dev`, which works out of the
box with no domain setup — fine for personal notification use. If you
verify your own domain in Resend later, you can set `RESEND_FROM` to an
address on that domain instead.

If `RESEND_API_KEY` isn't set, the app still saves responses normally —
it just skips sending the email and logs a note instead.

