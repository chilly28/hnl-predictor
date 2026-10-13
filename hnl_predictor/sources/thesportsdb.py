"""TheSportsDB (https://www.thesportsdb.com) – fixtures and results.

Free public API key "123" (v1 JSON API). Limits on the free key that this
module is designed around: ~30 requests/minute, ``eventsround`` returns a full
round, ``eventsnext``/``eventslast`` return one event per team. A premium key
can be supplied via the ``THESPORTSDB_KEY`` environment variable (GitHub
secret) but is not required.

Times in the API are UTC (``strTimestamp``) and are converted to
Europe/Zagreb local time.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from ..matches import HNL, STATUS_FINISHED, STATUS_POSTPONED, STATUS_SCHEDULED, UCL, UECL, UEL, Match
from ..teams import TeamRegistry
from .countries import country_code
from .http import fetch_json

log = logging.getLogger(__name__)

BASE = "https://www.thesportsdb.com/api/v1/json/{key}/"
LEAGUES = {HNL: "4629", UEL: "4481", UECL: "5071", UCL: "4480"}
LEAGUE_TO_COMP = {v: k for k, v in LEAGUES.items()}
ZAGREB = ZoneInfo("Europe/Zagreb")
FINISHED = {"FT", "AET", "PEN", "Match Finished", "AP"}
POSTPONED = {"PST", "Postponed", "CANC", "Cancelled", "ABD"}
MIN_INTERVAL = 2.1  # seconds between calls (free key: 30/min)


def _key() -> str:
    return os.environ.get("THESPORTSDB_KEY", "").strip() or "123"


def _call(endpoint: str, **params) -> dict | None:
    url = BASE.format(key=_key()) + endpoint
    return fetch_json(url, params=params, min_interval=MIN_INTERVAL, timeout=25)


def season_label(season: str) -> str:
    """'2025-26' -> '2025-2026'."""
    start = int(season[:4])
    return f"{start}-{start + 1}"


def _local(ev: dict) -> tuple[str, str]:
    ts = ev.get("strTimestamp")
    if ts:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "")).replace(tzinfo=timezone.utc).astimezone(ZAGREB)
            return dt.date().isoformat(), dt.strftime("%H:%M")
        except ValueError:
            pass
    return ev.get("dateEvent") or "", (ev.get("strTime") or "")[:5]


class TeamCountryCache:
    """Maps TheSportsDB team ids to FIFA-style country codes (looked up once, cached on disk)."""

    def __init__(self, path: Path):
        self.path = path
        self.data: dict[str, str] = {}
        if path.exists():
            self.data = json.loads(path.read_text(encoding="utf-8"))

    def get(self, team_id: str | None, fallback: str | None = None) -> str | None:
        if not team_id:
            return fallback
        if team_id not in self.data:
            res = _call("lookupteam.php", id=team_id) or {}
            teams = res.get("teams") or []
            code = country_code(teams[0].get("strCountry")) if teams else None
            if not code:
                return fallback
            self.data[team_id] = code
        return self.data[team_id]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=1, sort_keys=True), encoding="utf-8")


def event_to_match(ev: dict, teams: TeamRegistry, countries: TeamCountryCache | None,
                   croatian_only: bool = False) -> Match | None:
    comp = LEAGUE_TO_COMP.get(str(ev.get("idLeague")))
    if not comp or not ev.get("strHomeTeam") or not ev.get("strAwayTeam"):
        return None
    if comp == HNL:
        home = teams.resolve(ev["strHomeTeam"], "CRO")
        away = teams.resolve(ev["strAwayTeam"], "CRO")
    else:
        if croatian_only and not (teams.known_croatian(ev["strHomeTeam"]) or teams.known_croatian(ev["strAwayTeam"])):
            return None  # skip before any (rate-limited) country lookup
        hc = _country(ev, "Home", teams, countries)
        ac = _country(ev, "Away", teams, countries)
        if croatian_only and "CRO" not in (hc, ac):
            return None
        home = teams.resolve(ev["strHomeTeam"], hc)
        away = teams.resolve(ev["strAwayTeam"], ac)
    day, time_ = _local(ev)
    if not day:
        return None
    status_raw = (ev.get("strStatus") or "").strip()
    hs, as_ = ev.get("intHomeScore"), ev.get("intAwayScore")
    if status_raw in POSTPONED or (ev.get("strPostponed") or "").lower() == "yes":
        status, hg, ag = STATUS_POSTPONED, None, None
    elif hs not in (None, "") and as_ not in (None, "") and (status_raw in FINISHED or not status_raw):
        status, hg, ag = STATUS_FINISHED, int(hs), int(as_)
    else:
        status, hg, ag = STATUS_SCHEDULED, None, None
    # Note: for ties decided after extra time the API reports the final score;
    # such matches are rare in our data and kept as reported.
    season = ev.get("strSeason") or ""
    season = f"{season[:4]}-{season[-2:]}" if len(season) == 9 else season
    rnd = str(ev.get("intRound") or "")
    stage = "league" if comp == HNL else _stage(day, rnd)
    return Match(competition=comp, season=season, date=day, time=time_, home=home, away=away,
                 home_goals=hg, away_goals=ag, status=status,
                 round=(f"{rnd}. kolo" if comp == HNL and rnd else rnd), stage=stage, source="thesportsdb")


def _stage(day: str, rnd: str) -> str:
    # UEFA: qualifying rounds are played July-August, the league phase from September.
    month = int(day[5:7])
    if month in (7, 8):
        return "qualifying"
    if month in (9, 10, 11, 12) or (month == 1 and day[8:10] < "31"):
        return "league phase"
    return "knockout"


def _country(ev: dict, side: str, teams: TeamRegistry, countries: TeamCountryCache | None) -> str | None:
    name = ev.get(f"str{side}Team", "")
    # Croatian clubs are known; avoid a lookup call.
    if teams.known_croatian(name):
        return "CRO"
    if countries is None:
        return None
    return countries.get(ev.get(f"id{side}Team"))


def fetch_rounds(comp: str, season: str, rounds, teams: TeamRegistry,
                 countries: TeamCountryCache | None = None, croatian_only: bool = False) -> list[Match]:
    out: list[Match] = []
    league = LEAGUES[comp]
    for r in rounds:
        res = _call("eventsround.php", id=league, r=r, s=season_label(season))
        events = (res or {}).get("events") or []
        if not events and comp != HNL and r > 1:
            # UEFA round numbering ends earlier than the generic range – stop at the first empty round.
            break
        for ev in events:
            m = event_to_match(ev, teams, countries, croatian_only)
            if m:
                out.append(m)
    log.info("thesportsdb: %s %s rounds %s -> %d matches", comp, season, list(rounds)[:1] + ["…"], len(out))
    return out


def fetch_team_window(team_ids: dict[str, str], teams: TeamRegistry, countries: TeamCountryCache) -> list[Match]:
    """Last and next event for each club (all competitions)."""
    out: list[Match] = []
    for tid in team_ids.values():
        for endpoint, key in (("eventslast.php", "results"), ("eventsnext.php", "events")):
            res = _call(endpoint, id=tid) or {}
            for ev in res.get(key) or []:
                m = event_to_match(ev, teams, countries)
                if m:
                    out.append(m)
    return out


# TheSportsDB team ids of HNL clubs (used for last/next event lookups).
CROATIAN_TEAM_IDS = {
    "hajduk-split": "134019",
    "dinamo-zagreb": "133961",
    "rijeka": "134399",
    "slaven-belupo": "133989",
    "lokomotiva-zagreb": "137795",
    "varazdin": "137798",
    "rudes": "141086",
    "vukovar-1991": "146467",
}
