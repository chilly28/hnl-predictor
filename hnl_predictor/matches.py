"""Match record, CSV storage and merging of data from several sources."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import asdict, dataclass, field, fields
from datetime import date
from pathlib import Path
from typing import Iterable

# Competition codes used throughout the package.
HNL = "HNL"
UEL = "UEL"      # UEFA Europa League (incl. qualifying)
UECL = "UECL"    # UEFA Conference League (incl. qualifying)
UCL = "UCL"      # UEFA Champions League (incl. qualifying)
EUROPEAN = {UEL, UECL, UCL}

STATUS_FINISHED = "FT"
STATUS_SCHEDULED = "NS"
STATUS_POSTPONED = "PST"

# Lower number wins when two sources disagree about the same match.
SOURCE_PRIORITY = {"manual": 0, "api-football": 1, "thesportsdb": 2, "openfootball": 3, "clubelo": 4, "sample": 9}


@dataclass
class Match:
    competition: str
    season: str            # e.g. "2025-26"
    date: str              # ISO date (local match date)
    home: str              # canonical team id
    away: str
    home_goals: int | None = None   # goals after 90 minutes (+ stoppage time)
    away_goals: int | None = None
    status: str = STATUS_SCHEDULED
    round: str = ""
    time: str = ""         # local kick-off "HH:MM" if known
    stage: str = ""        # e.g. "qualifying", "league phase"
    neutral: bool = False
    source: str = ""
    id: str = field(default="")

    def __post_init__(self) -> None:
        if not self.id:
            self.id = match_id(self.competition, self.date, self.home, self.away)

    @property
    def finished(self) -> bool:
        return self.status == STATUS_FINISHED and self.home_goals is not None and self.away_goals is not None

    @property
    def day(self) -> date:
        return date.fromisoformat(self.date)

    def result(self) -> str | None:
        """'H', 'D' or 'A' for a finished match."""
        if not self.finished:
            return None
        if self.home_goals > self.away_goals:
            return "H"
        if self.home_goals < self.away_goals:
            return "A"
        return "D"


def match_id(competition: str, day: str, home: str, away: str) -> str:
    raw = f"{competition}|{day}|{home}|{away}"
    return hashlib.sha1(raw.encode()).hexdigest()[:10]


CSV_FIELDS = [f.name for f in fields(Match)]


def read_matches(path: str | Path) -> list[Match]:
    path = Path(path)
    if not path.exists():
        return []
    out = []
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            out.append(
                Match(
                    competition=row["competition"],
                    season=row["season"],
                    date=row["date"],
                    home=row["home"],
                    away=row["away"],
                    home_goals=int(row["home_goals"]) if row["home_goals"] != "" else None,
                    away_goals=int(row["away_goals"]) if row["away_goals"] != "" else None,
                    status=row["status"],
                    round=row.get("round", ""),
                    time=row.get("time", ""),
                    stage=row.get("stage", ""),
                    neutral=row.get("neutral", "") in ("1", "True", "true"),
                    source=row.get("source", ""),
                    id=row.get("id", ""),
                )
            )
    return out


def write_matches(path: str | Path, matches: Iterable[Match]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(matches, key=lambda m: (m.date, m.time, m.competition, m.home))
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS, lineterminator="\n")
        w.writeheader()
        for m in rows:
            d = asdict(m)
            d["neutral"] = "1" if m.neutral else ""
            d["home_goals"] = "" if m.home_goals is None else m.home_goals
            d["away_goals"] = "" if m.away_goals is None else m.away_goals
            w.writerow(d)


def _pair_key(m: Match) -> tuple:
    return (m.competition, m.home, m.away)


def merge_matches(*groups: Iterable[Match], date_tolerance_days: int = 4) -> list[Match]:
    """Merge match lists from several sources.

    The same fixture can appear with slightly different dates (postponements,
    time zones), so fixtures with the same competition/home/away within
    ``date_tolerance_days`` are treated as one match. A finished result beats a
    scheduled one; otherwise the higher-priority source wins.
    """
    by_pair: dict[tuple, list[Match]] = {}
    for group in groups:
        for m in group:
            bucket = by_pair.setdefault(_pair_key(m), [])
            for i, existing in enumerate(bucket):
                if abs((existing.day - m.day).days) <= date_tolerance_days:
                    bucket[i] = _better(existing, m)
                    break
            else:
                bucket.append(m)
    return drop_mirrored([m for bucket in by_pair.values() for m in bucket])


def drop_mirrored(matches: list[Match]) -> list[Match]:
    """Remove source errors where one match appears twice with home/away swapped on the same day.

    Each club hosts a given opponent equally often, so we keep the orientation
    that is still "owed" a home game in that season (first seen if both are).
    """
    from collections import Counter
    groups: dict[tuple, list[Match]] = {}
    for m in matches:
        groups.setdefault((m.competition, m.date, frozenset((m.home, m.away))), []).append(m)
    home_count = Counter((m.competition, m.season, m.home, m.away) for m in matches)
    out = []
    for ms in groups.values():
        if len(ms) == 2 and ms[0].home == ms[1].away and ms[0].away == ms[1].home:
            a, b = ms
            ka = (a.competition, a.season, a.home, a.away)
            kb = (b.competition, b.season, b.home, b.away)
            keep = b if home_count[ka] > home_count[kb] else a
            home_count[kb if keep is a else ka] -= 1
            out.append(keep)
        else:
            out.extend(ms)
    return out


def _better(a: Match, b: Match) -> Match:
    if a.finished != b.finished:
        winner = a if a.finished else b
    else:
        pa = SOURCE_PRIORITY.get(a.source, 5)
        pb = SOURCE_PRIORITY.get(b.source, 5)
        winner = a if pa <= pb else b
    other = b if winner is a else a
    # Fill gaps (kick-off time, round) from the other record.
    if not winner.time and other.time:
        winner.time = other.time
    if not winner.round and other.round:
        winner.round = other.round
    if not winner.stage and other.stage:
        winner.stage = other.stage
    return winner


def season_for(day: date) -> str:
    """European football season label for a date (season starts in July)."""
    start = day.year if day.month >= 7 else day.year - 1
    return f"{start}-{str(start + 1)[-2:]}"
