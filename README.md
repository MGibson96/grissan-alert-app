# Grissan Alert App

Intercepts OEM sensor alert emails, rebrands them as Ailsa-branded customer
communications, and relays an SMS alert to designated contacts. See
`docs/oemalertrelayplan.md`-equivalent context: this implements Phase 1
(IMAP polling) of the plan.

## Pipeline

1. `src/inbox_watcher.py` polls a Gmail inbox over IMAP for mail from the
   OEM's alert sender address.
2. `src/parser.py` extracts structured fields (sensor/site ID, alert type,
   severity, timestamp, reading value) from the email body.
3. `src/recipient_mapping.py` looks up the customer/contacts for the
   sensor or site the alert came from (`config/recipients.yaml`).
4. `src/email_dispatcher.py` sends an Ailsa-branded HTML email to the
   customer's contacts.
5. `src/sms_dispatcher.py` sends an SMS via AWS SNS to the customer's
   phone numbers.
6. `src/audit_log.py` records every alert (received, parsed, matched,
   delivery status per channel) in a local SQLite database.

If parsing fails or an alert can't be matched to a known site, an internal
notification email is sent to `INTERNAL_ALERT_EMAIL` instead of silently
dropping the alert.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:

### Gmail (IMAP + SMTP)

1. Enable 2-Step Verification on the Gmail account that will receive OEM
   alerts.
2. Create an [app password](https://myaccount.google.com/apppasswords) —
   this is `GMAIL_APP_PASSWORD` (also reused for `SMTP_APP_PASSWORD` by
   default, since the plan sends the rebranded email from the same
   account).
3. Set `GMAIL_ADDRESS` to that inbox.
4. Set `OEM_SENDER_FILTER` to the OEM's alert sender address.

### AWS SNS (SMS)

1. Create an IAM user/role with `sns:Publish` permission.
2. Set `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_REGION` (or
   rely on the default credential chain — instance role, `~/.aws/credentials`,
   etc. — and leave the key vars blank).
3. Note: new AWS accounts start in the SNS SMS "sandbox" in most regions,
   which only allows sending to verified numbers. Request production
   access in the SNS console before going live with real customer numbers.

### Recipient mapping

Edit `config/recipients.yaml` — maps `site_id` (or `sensor_id`) to a
customer name, email contacts, and E.164-format phone numbers.

## Running

```bash
python -m src.main
```

Polls every `POLL_INTERVAL_SECONDS` (default 300s). Runs indefinitely;
run it under `systemd`, `supervisord`, `pm2`, or similar for production
use on a VM or Pi.

## Tests

```bash
pytest tests/
```

## Known gap: the parser needs a real sample email

`src/parser.py` currently extracts fields with placeholder regex patterns
(`Sensor ID: ...`, `Site ID: ...`, etc.) that are **not** based on an
actual OEM alert email — we don't have one yet. Before this goes live:

1. Get a real sample OEM alert email (forward one into the monitored
   inbox, or paste the raw source).
2. Update `FIELD_PATTERNS` in `src/parser.py` to match its actual
   structure (plain text vs. HTML table, exact field labels, etc.).
3. Add the real sample as a fixture in `tests/` and update
   `test_parser.py` to parse it directly.

## Not yet built (Phase 2 / open items from the plan)

- AWS SES inbound + Lambda migration (only worth it if polling volume/latency
  becomes a problem — start with Phase 1 IMAP polling as-is).
- Slack notification channel for internal failures (currently email-only).
