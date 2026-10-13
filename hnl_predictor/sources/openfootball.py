"""Parser and fetcher for openfootball Football.TXT files (public domain, CC0).

Two layouts exist in the openfootball repositories:

Legacy (2018-2021)::

    Round 1
    [Fri Jul/27]
      GNK Dinamo Zagreb         1-1  NK Rudeš

Current (2023-)::

    ▪ Matchday 1
      Fri Jul 21 2023
        20:00  Dinamo Zagreb           v Hajduk Split             1-2 (1-0)
               NK Osijek               v HNK Šibenik              1-2 (0-1)

European files add the country code: ``Hajduk Split (CRO) v Zira FK (AZE)``.
For extra time the 90-minute score is the first value in brackets:
``2-1 a.e.t. (1-1, 1-0)``.
"""

from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path

from ..matches import STATUS_FINISHED, STATUS_SCHEDULED, Match
from ..teams import TeamRegistry
from .http import fetch_text

log = logging.getLogger(__name__)

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}

RAW_BASE = "https://raw.githubusercontent.com/openfootball"

# (competition, repo path template). {s} = "2025-26".
REMOTE_FILES = {
    "HNL": ["europe/master/croatia/{s}_hr1.txt"],
    "UEL": ["champions-league/master/{s}/elq.txt", "champions-league/master/{s}/el.txt"],
    "UECL": ["champions-league/master/{s}/confq.txt", "champions-league/master/{s}/conf.txt"],
    "UCL": ["champions-league/master/{s}/clq.txt", "champions-league/master/{s}/cl.txt"],
}

_ROUND_RE = re.compile(r"^(?:▪\s*)?((?:Matchday|Round|Spieltag)\s+\d+|Group\s+[A-Z]\b.*|\d+\.\s*Round.*|[A-Z][\w\- ]*(?:phase|round|Round|final|Final|[Pp]lay-?offs?).*)$")
_DATE_NEW_RE = re.compile(r"^\s*(?:[A-Z][a-z]{2}\s+)?([A-Z][a-z]{2})\s+(\d{1,2})(?:\s+(\d{4}))?\s*$")
_DATE_OLD_RE = re.compile(r"^\s*\[(?:[A-Z][a-z]{2}\s+)?([A-Z][a-z]{2})/(\d{1,2})(?:\s+(\d{4}))?\]\s*$")
_MATCH_NEW_RE = re.compile(r"^\s+(?:(\d{1,2}[:.]\d{2})\s+)?(\S.*?)\s+v\s+(\S.*?)(?:\s{2,}(\S.*))?\s*$")
_MATCH_OLD_RE = re.compile(r"^\s+(?:(\d{1,2}[:.]\d{2})\s+)?(\S.*?)\s{2,}(?:(\d+)-(\d+)|-)\s{2,}(\S.*?)\s*$")
_SCORE_RE = re.compile(r"^(\d+)-(\d+)(.*)$")


def _season_years(season: str) -> tuple[int, int]:
    start = int(season[:4])
    return start, start + 1


def _make_date(season: str, mon: str, day: str, year: str | None) -> str:
    y1, y2 = _season_years(season)
    month = MONTHS[mon.lower()[:3]]
    if year:
        y = int(year)
    else:
        y = y1 if month >= 7 else y2
    return date(y, month, int(day)).isoformat()


def parse_score(text: str) -> tuple[int | None, int | None, str]:
    """Return the 90-minute score and a note ('aet', 'pen' or '') from a score string."""
    text = (text or "").strip()
    m = _SCORE_RE.match(text)
    if not m:
        return None, None, ""
    h, a, rest = int(m.group(1)), int(m.group(2)), m.group(3)
    note = ""
    if "pen" in rest or "a.e.t" in rest:
        note = "pen" if "pen" in rest else "aet"
        brackets = re.search(r"\((\d+)-(\d+)", rest)
        if "pen" in rest:
            # "4-5 pen. 2-2 a.e.t. (2-2, 2-0)" -> 90 min = first bracket value.
            if brackets:
                h, a = int(brackets.group(1)), int(brackets.group(2))
            else:
                aet = re.search(r"(\d+)-(\d+)", rest)
                if aet:
                    h, a = int(aet.group(1)), int(aet.group(2))
        elif brackets:
            h, a = int(brackets.group(1)), int(brackets.group(2))
    return h, a, note


def parse_text(text: str, competition: str, season: str, teams: TeamRegistry,
               croatian_only: bool = False) -> list[Match]:
    matches: list[Match] = []
    current_date: str | None = None
    current_round = ""
    stage = ""
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith(("#", "=")):
            continue
        stripped = line.strip()
        rm = _ROUND_RE.match(stripped)
        if rm and not line.startswith(" "):
            current_round = rm.group(1).strip()
            low = current_round.lower()
            stage = "qualifying" if ("round" in low and low[0].isdigit()) or "qualif" in low else \
                ("play-off" if "play" in low else ("league phase" if "phase" in low or "group" in low else "knockout"))
            if competition == "HNL":
                stage = "league"
            continue
        dm = _DATE_OLD_RE.match(line) or _DATE_NEW_RE.match(line)
        if dm:
            try:
                current_date = _make_date(season, dm.group(1), dm.group(2), dm.group(3))
            except (KeyError, ValueError):
                pass
            continue
        if current_date is None:
            continue
        mm = _MATCH_NEW_RE.match(line)
        if mm and " v " in line:
            time_, home_raw, away_raw, score_raw = mm.groups()
            hg, ag, _ = parse_score(score_raw or "")
        else:
            mo = _MATCH_OLD_RE.match(line)
            if not mo:
                continue
            time_, home_raw, h, a, away_raw = mo.groups()
            hg = int(h) if h is not None else None
            ag = int(a) if a is not None else None
        home = teams.resolve(home_raw)
        away = teams.resolve(away_raw)
        if croatian_only and not (teams.is_croatian(home) or teams.is_croatian(away)):
            continue
        matches.append(Match(
            competition=competition,
            season=season,
            date=current_date,
            home=home,
            away=away,
            home_goals=hg,
            away_goals=ag,
            status=STATUS_FINISHED if hg is not None else STATUS_SCHEDULED,
            round=current_round,
            time=(time_ or "").replace(".", ":"),
            stage=stage,
            source="openfootball",
        ))
    return matches


def load_local(raw_dir: str | Path, teams: TeamRegistry) -> list[Match]:
    """Parse every cached file in data/raw/openfootball (name: <comp>_<season>.txt)."""
    out: list[Match] = []
    for path in sorted(Path(raw_dir).glob("*.txt")):
        comp, season = _comp_season_from_name(path.stem)
        if comp is None:
            continue
        out += parse_text(path.read_text(encoding="utf-8"), comp, season, teams,
                          croatian_only=comp != "HNL")
    return out


_FILE_COMP = {"hr1": "HNL", "elq": "UEL", "el": "UEL", "confq": "UECL", "conf": "UECL", "clq": "UCL", "cl": "UCL"}


def _comp_season_from_name(stem: str) -> tuple[str | None, str]:
    # hr1_2024-25 / uefa_confq_2025-26
    parts = stem.split("_")
    season = parts[-1]
    key = parts[-2] if len(parts) >= 2 else ""
    return _FILE_COMP.get(key), season


def fetch_remote(seasons: list[str], raw_dir: str | Path) -> list[Path]:
    """Download season files from openfootball into the local cache. Missing files are skipped."""
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for season in seasons:
        for comp, templates in REMOTE_FILES.items():
            for tpl in templates:
                rel = tpl.format(s=season)
                text = fetch_text(f"{RAW_BASE}/{rel}", quiet_404=True)
                if not text:
                    continue
                fname = rel.rsplit("/", 1)[-1].removesuffix(".txt")
                if comp == "HNL":
                    out = raw_dir / f"hr1_{season}.txt"
                else:
                    out = raw_dir / f"uefa_{fname}_{season}.txt"
                if not out.exists() or out.read_text(encoding="utf-8") != text:
                    out.write_text(text, encoding="utf-8")
                    log.info("openfootball: updated %s", out.name)
                saved.append(out)
    return saved
