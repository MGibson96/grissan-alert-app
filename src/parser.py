import re
from dataclasses import dataclass

# Built against a real Analytix (condition-monitoring) alarm email — see
# tests/fixtures/analytix_twf_acceleration.txt. Structure observed:
#
#   Subject: Critical - TWF acceleration peak (high res) alarm triggered!
#   ...
#   Alarms
#   Critical
#   Vertical TWF acceleration peak (high res) greater than 655.42mg
#   ID: 19ea67ea-a70f-4b66-92de-4808fe25cd00
#   Mon Jul 13 2026 06:03:32 GMT+0100
#   Alarm Information
#   Site:	Grissan
#   Machine:	Screw Conveyor C9
#   Measuring point:	Conveyor Shaft
#   Vib direction:	Vertical
#   TWF acceleration peak (high res) received:	1839.92mg
#
# Only one sample so far, and only one alarm/metric type (vibration TWF
# acceleration). Fields expected to vary across metric types: the
# "<metric> received:" label, the "greater than"/"less than" comparison,
# and possibly whether "Vib direction" is present at all for non-vibration
# metrics. Revisit these patterns once more samples (different severities,
# metrics, and non-vibration alarms) are available.

ALARM_ID_PATTERN = re.compile(
    r"ID:\s*([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
)
TIMESTAMP_PATTERN = re.compile(
    r"((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+\w+\s+\d{1,2}\s+\d{4}\s+\d{2}:\d{2}:\d{2}\s+GMT[+-]\d{4})"
)
SUBJECT_SEVERITY_PATTERN = re.compile(r"^\s*(\w+)\s*-\s*")
SITE_PATTERN = re.compile(r"^Site:\s*(.+)$", re.MULTILINE)
MACHINE_PATTERN = re.compile(r"^Machine:\s*(.+)$", re.MULTILINE)
MEASURING_POINT_PATTERN = re.compile(r"^Measuring point:\s*(.+)$", re.MULTILINE)
VIB_DIRECTION_PATTERN = re.compile(r"^Vib direction:\s*(.+)$", re.MULTILINE)
READING_PATTERN = re.compile(r"^(.+?)\s+received:\s*(.+)$", re.MULTILINE)
THRESHOLD_PATTERN = re.compile(r"(greater than|less than|exceeds|below)\s+(\S+)", re.IGNORECASE)


class ParseError(Exception):
    pass


@dataclass
class ParsedAlert:
    severity: str
    site: str
    machine: str
    metric: str
    reading_value: str
    measuring_point: str | None
    vib_direction: str | None
    threshold_value: str | None
    comparison: str | None
    alarm_id: str | None
    timestamp: str | None
    raw_body: str

    def as_dict(self) -> dict:
        return {
            "severity": self.severity,
            "site": self.site,
            "machine": self.machine,
            "metric": self.metric,
            "reading_value": self.reading_value,
            "measuring_point": self.measuring_point,
            "vib_direction": self.vib_direction,
            "threshold_value": self.threshold_value,
            "comparison": self.comparison,
            "alarm_id": self.alarm_id,
            "timestamp": self.timestamp,
        }


def parse_oem_alert(subject: str, body: str) -> ParsedAlert:
    """Extracts structured fields from an Analytix alarm email.

    Raises ParseError if any required field can't be found, so the caller
    can route the alert to the internal failure notification path instead
    of silently dropping it.
    """
    severity_match = SUBJECT_SEVERITY_PATTERN.match(subject or "")
    site_match = SITE_PATTERN.search(body)
    machine_match = MACHINE_PATTERN.search(body)
    reading_match = READING_PATTERN.search(body)

    missing = []
    if not severity_match:
        missing.append("severity")
    if not site_match:
        missing.append("site")
    if not machine_match:
        missing.append("machine")
    if not reading_match:
        missing.append("reading")
    if missing:
        raise ParseError(f"Could not extract required field(s): {', '.join(missing)}")

    measuring_point_match = MEASURING_POINT_PATTERN.search(body)
    vib_direction_match = VIB_DIRECTION_PATTERN.search(body)
    alarm_id_match = ALARM_ID_PATTERN.search(body)
    timestamp_match = TIMESTAMP_PATTERN.search(body)
    threshold_match = THRESHOLD_PATTERN.search(body)

    return ParsedAlert(
        severity=severity_match.group(1).strip(),
        site=site_match.group(1).strip(),
        machine=machine_match.group(1).strip(),
        metric=reading_match.group(1).strip(),
        reading_value=reading_match.group(2).strip(),
        measuring_point=measuring_point_match.group(1).strip() if measuring_point_match else None,
        vib_direction=vib_direction_match.group(1).strip() if vib_direction_match else None,
        threshold_value=threshold_match.group(2).strip() if threshold_match else None,
        comparison=threshold_match.group(1).strip().lower() if threshold_match else None,
        alarm_id=alarm_id_match.group(1) if alarm_id_match else None,
        timestamp=timestamp_match.group(1) if timestamp_match else None,
        raw_body=body,
    )
