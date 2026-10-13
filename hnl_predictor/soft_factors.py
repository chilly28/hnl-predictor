"""Soft factors: a transparent, capped adjustment layer on top of the statistics.

Statistics miss things like a coach being sacked, a key striker injured, or
fans boycotting matches. Each soft factor shifts one team's strength by a
number of *Elo points* for a period of time. The shift is capped per factor
type and in total, so a single note can never dominate the model.

Manual factors live in ``data/soft_factors.yaml``. Automatic providers (for
example a future news-sentiment signal) write JSON files with the same fields
to ``data/soft_factors_auto/*.json``; they are merged here and shown on the
site with ``origin: auto`` and their confidence, which scales the adjustment.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable, Protocol

import yaml

log = logging.getLogger(__name__)

# Maximum absolute adjustment (Elo points) per single factor of each type.
TYPE_CAPS = {
    "coach_change": 40,
    "tactical": 25,
    "injury": 50,
    "suspension": 40,
    "media": 15,
    "unrest": 40,
    "fatigue": 25,
    "other": 25,
}
TOTAL_CAP = 80          # maximum combined adjustment per team and match
DEFAULT_DURATION = 14   # days a factor stays active when no "until" is given


@dataclass
class SoftFactor:
    team: str
    date: str
    type: str
    note: str
    adjustment: float
    until: str = ""
    source: str = ""
    origin: str = "manual"
    confidence: float = 1.0
    match: str = ""          # optional: restrict to one opponent id

    @property
    def start(self) -> date:
        return date.fromisoformat(self.date)

    @property
    def end(self) -> date:
        if self.until:
            return date.fromisoformat(self.until)
        return self.start + timedelta(days=DEFAULT_DURATION)

    @property
    def capped(self) -> float:
        cap = TYPE_CAPS.get(self.type, TYPE_CAPS["other"])
        value = max(-cap, min(cap, float(self.adjustment)))
        return value * max(0.0, min(1.0, self.confidence))

    def applies(self, team: str, day: date, opponent: str | None = None) -> bool:
        if team != self.team:
            return False
        if self.match and opponent and self.match != opponent:
            return False
        return self.start <= day <= self.end


class SignalProvider(Protocol):
    """Interface for future automatic signal sources (news, social media...)."""

    name: str

    def signals(self, as_of: date) -> Iterable[SoftFactor]: ...


def _coerce(entry: dict, origin: str, resolve) -> SoftFactor | None:
    try:
        team = resolve(str(entry["team"])) if resolve else str(entry["team"])
        typ = str(entry.get("type", "other"))
        if typ not in TYPE_CAPS:
            log.warning("soft factor: unknown type %r, treated as 'other'", typ)
            typ = "other"
        return SoftFactor(
            team=team,
            date=str(entry["date"]),
            type=typ,
            note=str(entry.get("note", "")),
            adjustment=float(entry.get("adjustment", 0)),
            until=str(entry.get("until", "") or ""),
            source=str(entry.get("source", "") or ""),
            origin=str(entry.get("origin", origin)),
            confidence=float(entry.get("confidence", 1.0)),
            match=resolve(str(entry["match"])) if entry.get("match") and resolve else str(entry.get("match", "") or ""),
        )
    except (KeyError, ValueError, TypeError) as exc:
        log.warning("soft factor skipped (%s): %r", exc, entry)
        return None


def load_soft_factors(yaml_path: str | Path, auto_dir: str | Path | None = None, resolve=None) -> list[SoftFactor]:
    out: list[SoftFactor] = []
    yaml_path = Path(yaml_path)
    if yaml_path.exists():
        raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        entries = raw.get("factors", []) if isinstance(raw, dict) else raw
        for e in entries or []:
            f = _coerce(e, "manual", resolve)
            if f:
                out.append(f)
    if auto_dir and Path(auto_dir).exists():
        for p in sorted(Path(auto_dir).glob("*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except ValueError:
                log.warning("soft factors: invalid JSON in %s", p)
                continue
            for e in data if isinstance(data, list) else data.get("factors", []):
                f = _coerce(e, "auto", resolve)
                if f:
                    out.append(f)
    return out


def active_factors(factors: list[SoftFactor], team: str, day: date, opponent: str | None = None) -> list[SoftFactor]:
    return [f for f in factors if f.applies(team, day, opponent)]


def total_adjustment(factors: list[SoftFactor]) -> float:
    total = sum(f.capped for f in factors)
    return max(-TOTAL_CAP, min(TOTAL_CAP, total))


def factor_to_dict(f: SoftFactor) -> dict:
    d = asdict(f)
    d["applied"] = round(f.capped, 1)
    return d
