import pytest

from src.parser import ParseError, parse_oem_alert

# Placeholder body matching the placeholder regexes in src/parser.py.
# Replace with a real sample once we have one from the OEM.
SAMPLE_BODY = """
Sensor ID: SN-4821
Site ID: SITE-001
Alert Type: High Vibration
Severity: Critical
Timestamp: 2026-07-21T08:15:00Z
Reading Value: 12.4mm/s
"""


def test_parses_all_fields():
    alert = parse_oem_alert(SAMPLE_BODY)
    assert alert.sensor_id == "SN-4821"
    assert alert.site_id == "SITE-001"
    assert alert.alert_type == "High Vibration"
    assert alert.severity == "Critical"
    assert alert.reading_value == "12.4mm/s"


def test_raises_on_missing_required_field():
    body = "Sensor ID: SN-4821\nSite ID: SITE-001\n"
    with pytest.raises(ParseError):
        parse_oem_alert(body)
