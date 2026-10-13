"""English Wikipedia season article – independent cross-check of HNL results.

The article "<season> Croatian Football League" contains a results matrix
(template ``sports results``) maintained by volunteers::

    |team1=DIN |team2=GOR ...
    | name_DIN = [[GNK Dinamo Zagreb|Dinamo Zagreb]]
    | match1_DIN_GOR = 1–0                       first time DIN hosts GOR
    | match2_HAJ_DIN = [[Eternal derby (Croatia)|2–1]]   second time HAJ hosts DIN
    | match1_RIJ_DIN = [[...|a]]                  not played yet

The matrix has no dates, so it is used to *verify* scores from the primary
source and to fill in a score the primary source has not published yet for a
match whose date has passed. Text is CC BY-SA 4.0; we only use the scores
(facts) and credit Wikipedia on the site.

Fetched through the MediaWiki API with a descriptive User-Agent, one request
per run, as the API etiquette asks.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date

from ..matches import HNL, STATUS_FINISHED, Match
from ..teams import TeamRegistry
from .http import fetch_json

log = logging.getLogger(__name__)

API = "https://en.wikipedia.org/w/api.php"
_LINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
_KEY_RE = re.compile(r"^(name|match(\d))_([A-Z]{2,4})(?:_([A-Z]{2,4}))?$")
_SCORE_RE = re.compile(r"(\d+)\s*[–\-−]\s*(\d+)")


def article_title(season: str) -> str:
    start = int(season[:4])
    return f"{start}–{str(start + 1)[-2:]} Croatian Football League"


def fetch_wikitext(season: str) -> str | None:
    data = fetch_json(API, params={"action": "parse", "page": article_title(season), "prop": "wikitext",
                                   "format": "json", "formatversion": "2", "redirects": "1", "maxlag": "5"},
                      min_interval=1.0, timeout=25)
    if not data or "parse" not in data:
        return None
    return data["parse"].get("wikitext")


def _flatten_links(text: str) -> str:
    """[[Target|Shown]] -> Shown, [[Target]] -> Target."""
    return _LINK_RE.sub(lambda m: (m.group(2) or m.group(1)).strip(), text)


@dataclass
class WikiResult:
    home: str
    away: str
    leg: int          # 1 = first time this club hosts that opponent in the season, 2 = second
    home_goals: int
    away_goals: int


def parse_results(wikitext: str, teams: TeamRegistry) -> list[WikiResult]:
    start = wikitext.find("sports results")
    if start < 0:
        return []
    end = wikitext.find("\n}}", start)
    block = _flatten_links(wikitext[start:end if end > 0 else None])
    names: dict[str, str] = {}
    raw: list[tuple[int, str, str, str]] = []
    for part in block.split("|"):
        if "=" not in part:
            continue
        key, _, val = part.partition("=")
        km = _KEY_RE.match(key.strip())
        if not km:
            continue
        if km.group(1) == "name":
            names[km.group(3)] = teams.resolve(re.sub(r"<[^>]+>", "", val).strip(), "CRO")
        elif km.group(4):
            raw.append((int(km.group(2)), km.group(3), km.group(4), val))
    out = []
    for leg, h, a, val in raw:
        sm = _SCORE_RE.search(val)
        if h in names and a in names and sm:
            out.append(WikiResult(names[h], names[a], leg, int(sm.group(1)), int(sm.group(2))))
    return out


def reconcile(matches: list[Match], results: list[WikiResult], season: str, today: date) -> dict:
    """Compare with the primary data and fill missing scores of past matches in place.

    Returns a small data-quality report.
    """
    by_pair: dict[tuple[str, str], list[Match]] = {}
    for m in sorted((m for m in matches if m.competition == HNL and m.season == season), key=lambda m: (m.date, m.time)):
        if m.status != "PST":
            by_pair.setdefault((m.home, m.away), []).append(m)
    checked, agree, filled = 0, 0, []
    mismatches = []
    for r in results:
        ms = by_pair.get((r.home, r.away), [])
        if len(ms) < r.leg:
            mismatches.append({"home": r.home, "away": r.away, "leg": r.leg, "issue": "missing in primary data",
                               "wikipedia": f"{r.home_goals}-{r.away_goals}"})
            continue
        m = ms[r.leg - 1]
        if m.finished:
            checked += 1
            if (m.home_goals, m.away_goals) == (r.home_goals, r.away_goals):
                agree += 1
            else:
                mismatches.append({"id": m.id, "date": m.date, "home": r.home, "away": r.away, "leg": r.leg,
                                   "issue": "different score", "primary": f"{m.home_goals}-{m.away_goals}",
                                   "wikipedia": f"{r.home_goals}-{r.away_goals}"})
        elif m.day <= today:
            m.home_goals, m.away_goals = r.home_goals, r.away_goals
            m.status = STATUS_FINISHED
            m.source = "wikipedia"
            filled.append(m.id)
    report = {"season": season, "source": "en.wikipedia.org – " + article_title(season),
              "checked": checked, "agree": agree, "filled": len(filled), "issues": mismatches[:50]}
    log.info("wikipedia: %d checked, %d agree, %d filled, %d issues", checked, agree, len(filled), len(mismatches))
    return report
