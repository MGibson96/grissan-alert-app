import re
from dataclasses import dataclass

# NOTE: These patterns are placeholders. The plan calls the OEM emails a
# fixed template with only variables changing, which makes this a simple
# regex job — but we don't have a real sample email yet to build the
# patterns against (see plan's open questions). Replace these with real
# patterns once a sample alert email is available, and add a fixture under
# tests/fixtures/ to lock the format in.
FIELD_PATTERNS = {
    "sensor_id": re.compile(r"Sensor(?:\s*ID)?\s*[:\-]\s*(\S+)", re.IGNORECASE),
    "site_id": re.compile(r"Site(?:\s*ID)?\s*[:\-]\s*(\S+)", re.IGNORECASE),
    "alert_type": re.compile(r"Alert\s*Type\s*[:\-]\s*(.+)", re.IGNORECASE),
    "severity": re.compile(r"Severity\s*[:\-]\s*(\S+)", re.IGNORECASE),
    "timestamp": re.compile(r"Time(?:stamp)?\s*[:\-]\s*(.+)", re.IGNORECASE),
    "reading_value": re.compile(r"Reading(?:\s*Value)?\s*[:\-]\s*(\S+)", re.IGNORECASE),
}

REQUIRED_FIELDS = ("sensor_id", "site_id", "alert_type", "severity")


class ParseError(Exception):
    pass


@dataclass
class ParsedAlert:
    sensor_id: str
    site_id: str
    alert_type: str
    severity: str
    timestamp: str | None
    reading_value: str | None
    raw_body: str

    def as_dict(self) -> dict:
        return {
            "sensor_id": self.sensor_id,
            "site_id": self.site_id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "timestamp": self.timestamp,
            "reading_value": self.reading_value,
        }


def parse_oem_alert(body: str) -> ParsedAlert:
    """Extracts structured fields from an OEM alert email body.

    Raises ParseError if any required field can't be found, so the caller
    can route the alert to the internal failure notification path instead
    of silently dropping it.
    """
    extracted: dict[str, str | None] = {}
    for field, pattern in FIELD_PATTERNS.items():
        match = pattern.search(body)
        extracted[field] = match.group(1).strip() if match else None

    missing = [f for f in REQUIRED_FIELDS if not extracted.get(f)]
    if missing:
        raise ParseError(f"Could not extract required field(s): {', '.join(missing)}")

    return ParsedAlert(
        sensor_id=extracted["sensor_id"],
        site_id=extracted["site_id"],
        alert_type=extracted["alert_type"],
        severity=extracted["severity"],
        timestamp=extracted.get("timestamp"),
        reading_value=extracted.get("reading_value"),
        raw_body=body,
    )
