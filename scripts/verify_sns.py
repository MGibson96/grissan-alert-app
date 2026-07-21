"""Standalone check that AWS SNS credentials/permissions are working.

Usage:
    python -m scripts.verify_sns +15551234567

Sends one test SMS to the given E.164 number using the AWS credentials
and region from .env. Run this before wiring up the full pipeline, since
it isolates AWS SNS setup from Gmail/parsing/recipient-mapping issues.
"""

import os
import sys

from dotenv import load_dotenv

from src.sms_dispatcher import SmsDispatcher

load_dotenv()


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.verify_sns +15551234567")
        sys.exit(1)

    phone_number = sys.argv[1]
    aws_region = os.environ.get("AWS_REGION", "us-east-1")
    company_name = os.environ.get("COMPANY_NAME", "Ailsa")
    sender_id = os.environ.get("SNS_SENDER_ID") or None

    print(f"Sending test SMS to {phone_number} via SNS in {aws_region}" + (f" (Sender ID: {sender_id})" if sender_id else "") + "...")
    dispatcher = SmsDispatcher(aws_region, company_name, sender_id)
    try:
        dispatcher.send([phone_number], f"{company_name} SNS setup test - if you got this, it works.")
    except Exception as exc:  # noqa: BLE001 - want to surface any error clearly to a human running this by hand
        error_text = str(exc).lower()
        print(f"FAILED: {exc}")
        if "not opted in" in error_text or "unverified" in error_text:
            print(
                "\nThis looks like an SNS sandbox restriction - verify this phone number in "
                "the SNS console (Text messaging (SMS) -> Sandbox destination phone numbers), "
                "or request production access to send to any number."
            )
        elif "no origination" in error_text:
            print(
                "\nAWS has no approved way to send SMS to this country yet. Request a Sender ID "
                "for the destination country in the AWS End User Messaging SMS and voice console "
                "(Sender IDs -> Request sender ID), then set SNS_SENDER_ID in .env once approved."
            )
        sys.exit(1)

    print("Sent. Check the phone for the message.")


if __name__ == "__main__":
    main()
