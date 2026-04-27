from __future__ import annotations

from dataclasses import dataclass


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
