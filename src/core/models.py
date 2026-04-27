from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _int_or_default(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True, slots=True)
class ProtonSummary:
    tier: str
    confidence: str | None
    total: int


@dataclass(frozen=True, slots=True)
class GameSummary:
    app_id: int
    name: str
    tier: str
    price: str
    is_free: bool
    has_windows: bool
    has_mac: bool
    has_linux: bool
    metascore: str
    proton_confidence: str
    proton_reports: int

    def to_settings_dict(self) -> dict[str, Any]:
        return {
            "app_id": self.app_id,
            "name": self.name,
            "tier": self.tier,
            "price": self.price,
            "is_free": self.is_free,
            "has_windows": self.has_windows,
            "has_mac": self.has_mac,
            "has_linux": self.has_linux,
            "metascore": self.metascore,
            "proton_confidence": self.proton_confidence,
            "proton_reports": self.proton_reports,
        }

    @classmethod
    def from_settings_dict(cls, data: dict[str, Any]) -> "GameSummary":
        return cls(
            app_id=_int_or_default(data.get("app_id")),
            name=str(data.get("name") or ""),
            tier=str(data.get("tier") or "Unknown"),
            price=str(data.get("price") or "N/A"),
            is_free=bool(data.get("is_free")),
            has_windows=bool(data.get("has_windows")),
            has_mac=bool(data.get("has_mac")),
            has_linux=bool(data.get("has_linux")),
            metascore=str(data.get("metascore") or ""),
            proton_confidence=str(data.get("proton_confidence") or ""),
            proton_reports=_int_or_default(data.get("proton_reports")),
        )
