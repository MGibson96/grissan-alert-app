import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class Settings:
    gmail_address: str
    gmail_app_password: str
    smtp_address: str
    smtp_app_password: str
    oem_sender_filter: str
    poll_interval_seconds: int
    company_name: str
    internal_alert_email: str
    aws_region: str
    sns_sender_id: str | None
    enable_sms: bool
    audit_db_path: str
    recipients_config_path: str


def load_settings() -> Settings:
    return Settings(
        gmail_address=_require("GMAIL_ADDRESS"),
        gmail_app_password=_require("GMAIL_APP_PASSWORD"),
        smtp_address=os.environ.get("SMTP_ADDRESS") or _require("GMAIL_ADDRESS"),
        smtp_app_password=os.environ.get("SMTP_APP_PASSWORD") or _require("GMAIL_APP_PASSWORD"),
        oem_sender_filter=_require("OEM_SENDER_FILTER"),
        poll_interval_seconds=int(os.environ.get("POLL_INTERVAL_SECONDS", "300")),
        company_name=os.environ.get("COMPANY_NAME", "Ailsa"),
        internal_alert_email=_require("INTERNAL_ALERT_EMAIL"),
        aws_region=os.environ.get("AWS_REGION", "us-east-1"),
        sns_sender_id=os.environ.get("SNS_SENDER_ID") or None,
        enable_sms=os.environ.get("ENABLE_SMS", "true").strip().lower() not in ("false", "0", "no"),
        audit_db_path=os.environ.get("AUDIT_DB_PATH", "./data/audit.db"),
        recipients_config_path=os.environ.get("RECIPIENTS_CONFIG_PATH", "./config/recipients.yaml"),
    )
