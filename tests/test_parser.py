from pathlib import Path

import pytest

from src.parser import ParseError, parse_oem_alert

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> tuple[str, str]:
    raw = (FIXTURES_DIR / name).read_text()
    subject_line, _, rest = raw.partition("\n")
    subject = subject_line.removeprefix("Subject:").strip()
    body = rest.lstrip("\n")
    return subject, body


def test_parses_real_analytix_alert():
    subject, body = load_fixture("analytix_twf_acceleration.txt")
    alert = parse_oem_alert(subject, body)

    assert alert.severity == "Critical"
    assert alert.site == "Grissan"
    assert alert.machine == "Screw Conveyor C9"
    assert alert.measuring_point == "Conveyor Shaft"
    assert alert.vib_direction == "Vertical"
    assert alert.metric == "TWF acceleration peak (high res)"
    assert alert.reading_value == "1839.92mg"
    assert alert.threshold_value == "655.42mg"
    assert alert.comparison == "greater than"
    assert alert.alarm_id == "19ea67ea-a70f-4b66-92de-4808fe25cd00"
    assert alert.timestamp == "Mon Jul 13 2026 06:03:32 GMT+0100"


def test_raises_on_missing_required_field():
    subject = "Critical - something happened"
    body = "Site:\tGrissan\n"
    with pytest.raises(ParseError):
        parse_oem_alert(subject, body)


def test_raises_when_severity_missing_from_subject():
    subject = "TWF acceleration peak (high res) alarm triggered!"
    body = "Site:\tGrissan\nMachine:\tScrew Conveyor C9\nX received:\t1mg\n"
    with pytest.raises(ParseError):
        parse_oem_alert(subject, body)
