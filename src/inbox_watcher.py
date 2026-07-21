import email
import html as html_module
import imaplib
import logging
import re
from email.message import Message

logger = logging.getLogger(__name__)

IMAP_HOST = "imap.gmail.com"


class InboxWatcher:
    """Polls a Gmail inbox over IMAP for new mail from a specific sender.

    Auth is a Gmail app password (requires 2-Step Verification enabled on
    the Google account) rather than OAuth, per the plan's IMAP approach.
    """

    def __init__(self, gmail_address: str, gmail_app_password: str, sender_filter: str):
        self.gmail_address = gmail_address
        self.gmail_app_password = gmail_app_password
        self.sender_filter = sender_filter

    def _connect(self) -> imaplib.IMAP4_SSL:
        conn = imaplib.IMAP4_SSL(IMAP_HOST)
        conn.login(self.gmail_address, self.gmail_app_password)
        conn.select("INBOX")
        return conn

    def fetch_new_alert_emails(self) -> list[Message]:
        """Returns all messages from the OEM sender, newest last.

        Dedup against already-processed messages is the caller's job (via
        the audit log's Message-ID check) — this just returns everything
        matching the sender filter currently in the inbox.
        """
        messages: list[Message] = []
        conn = self._connect()
        try:
            status, data = conn.search(None, "FROM", f'"{self.sender_filter}"')
            if status != "OK":
                logger.warning("IMAP search failed: %s", status)
                return messages

            message_nums = data[0].split()
            for num in message_nums:
                status, msg_data = conn.fetch(num, "(RFC822)")
                if status != "OK" or not msg_data or not msg_data[0]:
                    logger.warning("IMAP fetch failed for message %s", num)
                    continue
                raw_bytes = msg_data[0][1]
                messages.append(email.message_from_bytes(raw_bytes))
        finally:
            try:
                conn.close()
            except imaplib.IMAP4.error:
                pass
            conn.logout()

        return messages


def get_message_id(msg: Message) -> str:
    message_id = msg.get("Message-ID")
    if message_id:
        return message_id.strip()
    # Fallback for OEM senders that omit Message-ID: hash sender+subject+date.
    fallback = f"{msg.get('From')}|{msg.get('Subject')}|{msg.get('Date')}"
    return f"generated:{hash(fallback)}"


def _html_to_text(raw_html: str) -> str:
    """Rough HTML -> text conversion, good enough for label/value regex parsing.

    Inserts newlines at block-element boundaries (the OEM alert emails are
    tables of label/value rows) rather than doing a full DOM parse, since
    we're only after visible text, not structure.
    """
    text = re.sub(r"(?is)<(br|/tr|/p|/div|/li)\s*/?>", "\n", raw_html)
    text = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", "", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_module.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]*", "\n", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def get_body_text(msg: Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition") or "")
            if content_type == "text/plain" and "attachment" not in disposition:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition") or "")
            if content_type == "text/html" and "attachment" not in disposition:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return _html_to_text(payload.decode(charset, errors="replace"))
        return ""

    payload = msg.get_payload(decode=True)
    if payload is None:
        return str(msg.get_payload())
    charset = msg.get_content_charset() or "utf-8"
    text = payload.decode(charset, errors="replace")
    if msg.get_content_type() == "text/html":
        text = _html_to_text(text)
    return text
