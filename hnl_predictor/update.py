"""Fetch new data from all sources and merge it into data/matches.csv.

Request budget (free TheSportsDB key, ~30 requests/minute):
* hourly run: the current HNL round +-1 and last/next event of every Croatian
  club active in Europe (~5-15 calls, well under a minute);
* once per day ("full"): the whole current HNL season and all UEFA rounds
  (~70 calls, ~2.5 minutes);
* once ever: backfill of past HNL seasons not covered by openfootball.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path

from .matches import EUROPEAN, HNL, UCL, UECL, UEL, Match, merge_matches, read_matches, season_for, write_matches
from .paths import Paths
from .sources import openfootball, thesportsdb
from .teams import TeamRegistry

log = logging.getLogger(__name__)

BACKFILL_SEASONS = ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
HNL_ROUNDS = 36
UEFA_ROUNDS = 12


def load_registry(paths: Paths) -> TeamRegistry:
    reg = TeamRegistry.load(paths.teams_yaml)
    if paths.teams_seen.exists():
        from .teams import Team
        for tid, info in json.loads(paths.teams_seen.read_text(encoding="utf-8")).items():
            if tid not in reg.teams:
                reg.teams[tid] = Team(id=tid, name=info["name"], short=info.get("short", ""),
                                      country=info.get("country", "CRO"))
                if reg.teams[tid].country == "CRO":
                    reg._index(reg.teams[tid])
    return reg


def save_registry(reg: TeamRegistry, paths: Paths, matches: list[Match] | None = None) -> None:
    yaml_ids = set(TeamRegistry.load(paths.teams_yaml).teams)
    hnl_teams = {t for m in matches or [] if m.competition == HNL for t in (m.home, m.away)}
    seen = {tid: {"name": t.name, "short": t.short, "country": t.country}
            for tid, t in sorted(reg.teams.items())
            # An auto-registered "Croatian" club that never played in the HNL was a failed lookup.
            if tid not in yaml_ids and (t.country != "CRO" or matches is None or tid in hnl_teams)}
    paths.teams_seen.write_text(json.dumps(seen, ensure_ascii=False, indent=1), encoding="utf-8")


def local_matches(paths: Paths, reg: TeamRegistry) -> tuple[list[Match], list[Match]]:
    """Croatian-relevant matches and *all* UEFA matches (for the European model) from the openfootball cache."""
    all_uefa: list[Match] = []
    croatian: list[Match] = []
    for path in sorted(paths.openfootball.glob("*.txt")):
        comp, season = openfootball._comp_season_from_name(path.stem)
        if comp is None:
            continue
        ms = openfootball.parse_text(path.read_text(encoding="utf-8"), comp, season, reg)
        if comp == HNL:
            croatian += ms
        else:
            all_uefa += ms
            croatian += [m for m in ms if reg.is_croatian(m.home) or reg.is_croatian(m.away)]
    return croatian, all_uefa


def _state(paths: Paths) -> dict:
    if paths.state.exists():
        return json.loads(paths.state.read_text(encoding="utf-8"))
    return {}


def current_hnl_round(matches: list[Match], season: str, today: date) -> int:
    rounds = []
    for m in matches:
        if m.competition == HNL and m.season == season and m.round:
            try:
                n = int(m.round.split(".")[0].split()[-1])
            except ValueError:
                continue
            rounds.append((m.date, n, m.finished))
    played = [n for d, n, f in rounds if f]
    return max(played) + 1 if played else 1


def update(paths: Paths, today: date | None = None, offline: bool = False, force_full: bool = False) -> bool:
    """Update data/matches.csv. Returns True if any match data changed."""
    today = today or datetime.now(timezone.utc).date()
    reg = load_registry(paths)
    before = paths.matches.read_text(encoding="utf-8") if paths.matches.exists() else ""
    existing = read_matches(paths.matches)
    season = season_for(today)
    state = _state(paths)

    if not offline:
        # openfootball (public domain): refresh files for the current and previous season.
        prev = season_for(date(today.year - (1 if today.month >= 7 else 2), 8, 1))
        openfootball.fetch_remote([prev, season], paths.openfootball)

    of_matches, _ = local_matches(paths, reg)
    fresh: list[Match] = []

    if not offline:
        countries = thesportsdb.TeamCountryCache(paths.raw / "thesportsdb_team_countries.json")
        full = force_full or state.get("last_full") != today.isoformat()
        # One-off backfill of past HNL seasons.
        have = {}
        for m in existing + of_matches:
            if m.competition == HNL and m.finished:
                have[m.season] = have.get(m.season, 0) + 1
        for s in BACKFILL_SEASONS:
            if s < season and have.get(s, 0) < 170:
                fresh += thesportsdb.fetch_rounds(HNL, s, range(1, HNL_ROUNDS + 1), reg)
        # Current HNL season.
        if full:
            fresh += thesportsdb.fetch_rounds(HNL, season, range(1, HNL_ROUNDS + 1), reg)
        else:
            r = current_hnl_round(existing, season, today)
            fresh += thesportsdb.fetch_rounds(HNL, season, range(max(1, r - 1), min(HNL_ROUNDS, r + 1) + 1), reg)
        # European competitions.
        if full:
            for comp in (UEL, UECL, UCL):
                fresh += thesportsdb.fetch_rounds(comp, season, range(1, UEFA_ROUNDS + 1), reg, countries,
                                                  croatian_only=True)
        europe_teams = {m.home for m in existing if m.competition in EUROPEAN and m.season == season} | \
                       {m.away for m in existing if m.competition in EUROPEAN and m.season == season}
        ids = {t: i for t, i in thesportsdb.CROATIAN_TEAM_IDS.items() if t in europe_teams}
        fresh += [m for m in thesportsdb.fetch_team_window(ids, reg, countries)
                  if m.competition in EUROPEAN or m.competition == HNL]
        countries.save()
        if full:
            state["last_full"] = today.isoformat()

    merged = merge_matches(existing, of_matches, fresh)
    write_matches(paths.matches, merged)
    save_registry(reg, paths, merged)
    state["last_update"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    after = paths.matches.read_text(encoding="utf-8")
    changed = after != before
    if changed:
        state["last_change"] = state["last_update"]
    paths.state.write_text(json.dumps(state, indent=1), encoding="utf-8")
    log.info("update: %d matches (%s)", len(merged), "changed" if changed else "no change")
    return changed

