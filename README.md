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

Once those four are set, check it end-to-end (no AWS needed for this) with:

```bash
python -m scripts.check_inbox
```

Lists every matching email currently in the inbox and what the parser
extracts from each. Read-only — doesn't send anything or touch the audit
log, so it's safe to re-run anytime.

### AWS SNS (SMS)

1. Create an IAM user with a policy scoped to just `sns:Publish` (see
   below), and generate an access key for it.
2. Set `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_REGION` (or
   rely on the default credential chain — instance role, `~/.aws/credentials`,
   etc. — and leave the key vars blank).
3. Note: new AWS accounts start in the SNS SMS "sandbox" in most regions,
   which only allows sending to verified numbers. Verify your own number
   in the SNS console for testing; request production access before going
   live with real customer numbers.
4. Many destination countries (UK included) require a registered **Sender
   ID** before AWS will send anything there at all — including the
   sandbox verification text. If adding/verifying a number fails with
   "No origination entities available to send", go to **AWS End User
   Messaging SMS and voice → Sender IDs → Request sender ID**, pick the
   destination country, and submit a short use case (e.g. "transactional
   equipment alert notifications for existing customers"). Once approved,
   set `SNS_SENDER_ID` in `.env` to that ID.

Minimal IAM policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": ["sns:Publish"], "Resource": "*" }
  ]
}
```

Once `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/`AWS_REGION` are set in
`.env`, verify the setup in isolation (no Gmail config needed) with:

```bash
python -m scripts.verify_sns +15551234567
```

### Recipient mapping

Edit `config/recipients.yaml` — maps `site` (the "Site" field from the
Analytix alarm, e.g. `Grissan`) to a customer name, email contacts, and
E.164-format phone numbers. Optionally add per-machine contact overrides
under a site's `machines` key.

## Running

```bash
python -m src.main
```

Polls every `POLL_INTERVAL_SECONDS` (default 300s). Runs indefinitely —
`Ctrl+C` to stop; run it under `systemd`, `supervisord`, `pm2`, or
similar for production use on a VM or Pi.

Set `ENABLE_SMS=false` in `.env` to run the full pipeline (Gmail →
parse → recipient lookup → branded email) without AWS set up yet — SMS
is skipped and logged instead of attempted. Set it back to `true` (or
remove it — that's the default) once AWS SNS is ready.

## Tests

```bash
pytest tests/
```

## Parser status

`src/parser.py` is built against one real sample: an Analytix
condition-monitoring alarm email (vibration TWF acceleration, Critical
severity, site "Grissan"). That fixture lives at
`tests/fixtures/analytix_twf_acceleration.txt` and is covered by
`tests/test_parser.py`.

Fields extracted: `severity` (from the subject line), `site`, `machine`,
`measuring_point`, `vib_direction`, `metric` + `reading_value` (the
"`<metric> received:`" line — the metric name is dynamic per alarm type),
`threshold_value` + `comparison` (from "greater than"/"less than" in the
alarm description), `alarm_id` (UUID), and `timestamp`.

Only `severity`, `site`, `machine`, and the reading are required —
everything else is best-effort so a slightly different alarm layout
doesn't hard-fail the pipeline.

**Still open:** only one alarm type has been seen so far (vibration). If
Analytix sends other metric types (temperature, RPM, etc.), the
"Vib direction" field may not apply, and there could be other structural
differences. If you can forward a few more real alerts — different
severities, different metrics, ideally the raw source (Gmail: **⋮ → Show
original**, save as `.eml`) rather than just copied text, since exact
HTML/whitespace structure matters — drop them somewhere I can read them
and I'll tighten the patterns and add them as fixtures.

Note: don't commit raw sample emails to this repo if they contain real
customer/site data — `tests/fixtures/` is meant for sanitized or
already-non-sensitive samples only (the current fixture uses "Grissan",
which you've already used as the repo name, so it's treated as fine to
commit here).

## Not yet built (Phase 2 / open items from the plan)

- AWS SES inbound + Lambda migration (only worth it if polling volume/latency
  becomes a problem — start with Phase 1 IMAP polling as-is).
- Slack notification channel for internal failures (currently email-only).
