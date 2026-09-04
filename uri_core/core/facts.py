from dataclasses import dataclass
from datetime import date
from typing import Optional


FACT_STATUSES = {
    "CONFIRMED",
    "VERIFIED",
    "PROVISIONAL",
    "HISTORICAL",
    "SUPERSEDED",
    "EXPIRED",
}

@dataclass
class Fact:
    """
    Represents one piece of information known to URI.

    Facts carry a status so historical information
    is not accidentally treated as current.
    """

    name: str
    value: str

    status: str = "PROVISIONAL"

    source: Optional[str] = None
    source_date: Optional[str] = None

    retrieved_date: str = (
        date.today().isoformat()
    )

    confirmed_by: Optional[str] = None

    notes: Optional[str] = None

    def is_current(self) -> bool:
        return self.status == "CONFIRMED"

    def is_historical(self) -> bool:
        return self.status == "HISTORICAL"

    def validate_status(self):
        if self.status not in FACT_STATUSES:
            raise ValueError(
                f"Invalid fact status: {self.status}"
            )