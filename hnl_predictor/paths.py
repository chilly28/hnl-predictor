"""File locations. Everything is relative to the repository root."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Paths:
    root: Path

    @classmethod
    def default(cls) -> "Paths":
        return cls(Path(__file__).resolve().parent.parent)

    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def raw(self) -> Path:
        return self.data / "raw"

    @property
    def openfootball(self) -> Path:
        return self.raw / "openfootball"

    @property
    def matches(self) -> Path:
        return self.data / "matches.csv"

    @property
    def teams_yaml(self) -> Path:
        return self.data / "teams.yaml"

    @property
    def teams_seen(self) -> Path:
        return self.data / "teams_seen.json"

    @property
    def soft_factors(self) -> Path:
        return self.data / "soft_factors.yaml"

    @property
    def soft_factors_auto(self) -> Path:
        return self.data / "soft_factors_auto"

    @property
    def forecast_archive(self) -> Path:
        return self.data / "forecast_archive.json"

    @property
    def quality(self) -> Path:
        """Data-quality report from the Wikipedia cross-check."""
        return self.data / "quality.json"

    @property
    def issue_template(self) -> Path:
        return self.root / ".github" / "ISSUE_TEMPLATE" / "soft_factor.yml"

    @property
    def state(self) -> Path:
        return self.data / "state.json"

    @property
    def site(self) -> Path:
        return self.root / "site"

    @property
    def output(self) -> Path:
        """JSON outputs consumed by the website (and future apps)."""
        return self.site / "data"
