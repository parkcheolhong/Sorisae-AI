from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class ProbeEvent:
    ts: datetime
    event: str
    raw_event: str
    fields: dict[str, Any] = field(default_factory=dict)

