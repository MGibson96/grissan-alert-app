import logging
import time

from src.audit_log import AuditLog
from src.config import load_settings
from src.email_dispatcher import EmailDispatcher
from src.inbox_watcher import InboxWatcher, get_body_text, get_message_id
from src.parser import ParseError, parse_oem_alert
from src.recipient_mapping import RecipientMapping
from src.sms_dispatcher import SmsDispatcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

MAX_SEND_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 5


def with_retry(fn, *, description: str):
    last_error: Exception | None = None
    for attempt in range(1, MAX_SEND_ATTEMPTS + 1):
        try:
            fn()
            return None
        except Exception as exc:  # noqa: BLE001 - genuinely want to catch/report any send failure
            last_error = exc
            logger.warning("%s failed (attempt %d/%d): %s", description, attempt, MAX_SEND_ATTEMPTS, exc)
            if attempt < MAX_SEND_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    return str(last_error)


def build_sms_message(alert) -> str:
    return (
        f"ALERT - high {alert.metric} vibration has been detected on "
        f"{alert.machine} at {alert.measuring_point}. Please check within 24 hours."
    )


def process_message(msg, deps) -> None:
    message_id = get_message_id(msg)
    if deps["audit"].already_processed(message_id):
        return

    deps["audit"].record_received(message_id, msg.get("From", ""), msg.get("Subject", ""))

    body = get_body_text(msg)
    subject = msg.get("Subject", "")
    try:
        alert = parse_oem_alert(subject, body)
    except ParseError as exc:
        logger.error("Failed to parse alert %s: %s", message_id, exc)
        deps["audit"].record_parsed(message_id, None, str(exc))
        notify_internal_failure(deps, message_id, msg, str(exc))
        return

    deps["audit"].record_parsed(message_id, alert.as_dict(), None)

    recipients = deps["recipients"].lookup(alert.site, alert.machine)
    if recipients is None:
        logger.error("No recipient mapping for site=%s machine=%s", alert.site, alert.machine)
        deps["audit"].record_match(message_id, None)
        notify_internal_failure(
            deps, message_id, msg, f"No recipient mapping for site={alert.site} machine={alert.machine}"
        )
        return

    deps["audit"].record_match(message_id, recipients.customer)

    fields = alert.as_dict()
    subject = f"[{deps['settings'].company_name}] {alert.metric} alert - {alert.site}"

    email_error = with_retry(
        lambda: deps["email"].send(recipients.emails, subject, fields),
        description=f"email send for {message_id}",
    )
    deps["audit"].record_email_result(message_id, email_error is None, email_error)

    sms_message = build_sms_message(alert)

    if not deps["settings"].enable_sms:
        print(f"\n[SMS preview - not sent, ENABLE_SMS=false]\nTo: {', '.join(recipients.phones)}\n{sms_message}\n")
        deps["audit"].record_sms_result(message_id, False, "skipped (ENABLE_SMS=false)")
        return

    sms_error = with_retry(
        lambda: deps["sms"].send(recipients.phones, sms_message),
        description=f"sms send for {message_id}",
    )
    deps["audit"].record_sms_result(message_id, sms_error is None, sms_error)


def notify_internal_failure(deps, message_id: str, msg, reason: str) -> None:
    settings = deps["settings"]
    try:
        deps["email"].send(
            [settings.internal_alert_email],
            f"[{settings.company_name}] Alert relay failure",
            {
                "site": "n/a",
                "machine": "n/a",
                "metric": f"PROCESSING FAILURE: {reason}",
                "reading_value": "n/a",
                "measuring_point": None,
                "vib_direction": None,
                "threshold_value": None,
                "comparison": None,
                "severity": "internal",
                "timestamp": None,
            },
        )
    except Exception:  # noqa: BLE001 - best-effort internal notification, don't crash the poll loop
        logger.exception("Failed to send internal failure notification for %s", message_id)


def build_dependencies():
    settings = load_settings()
    return {
        "settings": settings,
        "watcher": InboxWatcher(settings.gmail_address, settings.gmail_app_password, settings.oem_sender_filter),
        "audit": AuditLog(settings.audit_db_path),
        "recipients": RecipientMapping(settings.recipients_config_path),
        "email": EmailDispatcher(settings.smtp_address, settings.smtp_app_password, settings.company_name),
        "sms": SmsDispatcher(settings.aws_region, settings.company_name, settings.sns_sender_id),
    }


def poll_once(deps) -> None:
    messages = deps["watcher"].fetch_new_alert_emails()
    for msg in messages:
        try:
            process_message(msg, deps)
        except Exception:  # noqa: BLE001 - one bad message shouldn't kill the poll loop
            logger.exception("Unexpected error processing message %s", msg.get("Message-ID"))


def main() -> None:
    deps = build_dependencies()
    logger.info(
        "Watching %s for mail from %s every %ds",
        deps["settings"].gmail_address,
        deps["settings"].oem_sender_filter,
        deps["settings"].poll_interval_seconds,
    )
    while True:
        poll_once(deps)
        time.sleep(deps["settings"].poll_interval_seconds)


if __name__ == "__main__":
    main()
