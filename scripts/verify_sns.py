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

    print(f"Sending test SMS to {phone_number} via SNS in {aws_region}...")
    dispatcher = SmsDispatcher(aws_region, company_name)
    try:
        dispatcher.send([phone_number], f"{settings.company_name} SNS setup test - if you got this, it works.")
    except Exception as exc:  # noqa: BLE001 - want to surface any error clearly to a human running this by hand
        print(f"FAILED: {exc}")
        if "not opted in" in str(exc).lower() or "unverified" in str(exc).lower():
            print(
                "\nThis looks like an SNS sandbox restriction - verify this phone number in "
                "the SNS console (Text messaging (SMS) -> Sandbox destination phone numbers), "
                "or request production access to send to any number."
            )
        sys.exit(1)

    print("Sent. Check the phone for the message.")


if __name__ == "__main__":
    main()
