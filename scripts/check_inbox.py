"""Read-only check of the monitored Gmail inbox — no sending, no audit log writes.

Usage:
    python -m scripts.check_inbox

Connects via IMAP, lists every message currently in the inbox from
OEM_SENDER_FILTER, and shows what the parser extracts from each (or why
it failed to parse). Safe to run repeatedly while setting things up —
it doesn't mark mail as read, send anything, or touch the audit log.
"""

import os
import sys

from dotenv import load_dotenv

from src.inbox_watcher import InboxWatcher, get_body_text, get_message_id
from src.parser import ParseError, parse_oem_alert

load_dotenv()

REQUIRED_VARS = ("GMAIL_ADDRESS", "GMAIL_APP_PASSWORD", "OEM_SENDER_FILTER")


def main() -> None:
    missing = [name for name in REQUIRED_VARS if not os.environ.get(name)]
    if missing:
        print(f"Missing required .env value(s): {', '.join(missing)}")
        sys.exit(1)

    gmail_address = os.environ["GMAIL_ADDRESS"]
    gmail_app_password = os.environ["GMAIL_APP_PASSWORD"]
    oem_sender_filter = os.environ["OEM_SENDER_FILTER"]

    print(f"Connecting to {gmail_address}, searching for mail from {oem_sender_filter}...")
    watcher = InboxWatcher(gmail_address, gmail_app_password, oem_sender_filter)

    try:
        messages = watcher.fetch_new_alert_emails()
    except Exception as exc:  # noqa: BLE001 - want to surface any error clearly to a human running this by hand
        print(f"FAILED to connect/search: {exc}")
        if "invalid credentials" in str(exc).lower() or "authenticationfailed" in str(exc).lower():
            print(
                "\nThis looks like a login failure - double check GMAIL_ADDRESS/GMAIL_APP_PASSWORD, "
                "and that 2-Step Verification + an app password are set up on that Gmail account."
            )
        sys.exit(1)

    if not messages:
        print(f"No messages found from {oem_sender_filter}. Nothing to show yet.")
        return

    print(f"Found {len(messages)} message(s):\n")

    for i, msg in enumerate(messages, start=1):
        subject = msg.get("Subject", "")
        print(f"--- [{i}/{len(messages)}] {subject}")
        print(f"    From: {msg.get('From', '')}")
        print(f"    Date: {msg.get('Date', '')}")
        print(f"    Message-ID: {get_message_id(msg)}")

        body = get_body_text(msg)
        try:
            alert = parse_oem_alert(subject, body)
        except ParseError as exc:
            print(f"    PARSE FAILED: {exc}")
            continue

        print("    Parsed OK:")
        for key, value in alert.as_dict().items():
            print(f"      {key}: {value}")
        print()


if __name__ == "__main__":
    main()
