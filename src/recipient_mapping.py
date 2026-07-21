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

    def lookup(self, site: str | None, machine: str | None) -> Recipients | None:
        if not site or site not in self.sites:
            return None
        entry = self.sites[site]

        machines = entry.get("machines") or {}
        machine_override = machines.get(machine) if machine else None

        return Recipients(
            customer=entry.get("customer", "Unknown Customer"),
            emails=(machine_override or {}).get("emails") or entry.get("emails") or [],
            phones=(machine_override or {}).get("phones") or entry.get("phones") or [],
        )
