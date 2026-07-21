from dataclasses import dataclass

import yaml


@dataclass
class Recipients:
    customer: str
    emails: list[str]
    phones: list[str]


class RecipientMapping:
    def __init__(self, config_path: str):
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        self.sites: dict = data.get("sites") or {}
        self.sensors: dict = data.get("sensors") or {}

    def lookup(self, site_id: str | None, sensor_id: str | None) -> Recipients | None:
        entry = None
        if site_id and site_id in self.sites:
            entry = self.sites[site_id]
        elif sensor_id and sensor_id in self.sensors:
            entry = self.sensors[sensor_id]

        if entry is None:
            return None

        return Recipients(
            customer=entry.get("customer", "Unknown Customer"),
            emails=entry.get("emails") or [],
            phones=entry.get("phones") or [],
        )
