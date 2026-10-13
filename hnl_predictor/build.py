"""Fit the models and write every JSON output the website (and future apps) need.

Outputs (site/data/):
  meta.json       generation time, data freshness, sources, model settings
  teams.json      every club referenced by any output (names, country, short code)
  upcoming.json   forecasts for scheduled HNL and European matches
  results.json    finished matches with the forecast that preceded them
  table.json      current HNL table + Monte Carlo projection of the final table
  clubs.json      per-club ratings, rating history, form and fixtures
  europe.json     Croatian clubs in Europe + cross-league strength table
  backtest.json   walk-forward accuracy on past seasons
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import __version__
from .backtest import run_backtest
from .matches import EUROPEAN, HNL, Match, merge_matches, read_matches, season_for
from .model.forecaster import Forecaster, ModelConfig
from .model.simulate import simulate_season
from .paths import Paths
from .soft_factors import load_soft_factors
from .update import load_registry, local_matches

log = logging.getLogger(__name__)
ZAGREB = ZoneInfo("Europe/Zagreb")
UPCOMING_DAYS = 45
TUNED_ON = ["2019-20", "2020-21", "2021-22", "2022-23"]  # seasons used to choose model parameters
RESULTS_DAYS = 120

SOURCES = [
    {"name": "openfootball", "url": "https://github.com/openfootball", "licence": "CC0 1.0 (public domain)",
     "use": "HNL 2018-2025 and UEFA club competitions 2011-2026 (historical results)"},
    {"name": "TheSportsDB", "url": "https://www.thesportsdb.com", "licence": "Free API (crowd-sourced data), attribution",
     "use": "Current fixtures and results (HNL, Europa League, Conference League)"},
]


def _kickoff(m: Match) -> datetime:
    t = m.time or "12:00"
    hh, mm = (int(x) for x in t.split(":")[:2])
    d = m.day
    return datetime(d.year, d.month, d.day, hh, mm, tzinfo=ZAGREB)


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def build(paths: Paths, now: datetime | None = None, n_sims: int = 10000,
          config: ModelConfig | None = None) -> dict:
    now = (now or datetime.now(timezone.utc)).astimezone(ZAGREB)
    today = now.date()
    config = config or ModelConfig()
    reg = load_registry(paths)
    matches = read_matches(paths.matches)
    factors = load_soft_factors(paths.soft_factors, paths.soft_factors_auto, resolve=reg.resolve)
    _, all_uefa = local_matches(paths, reg)
    euro_all = merge_matches(all_uefa, [m for m in matches if m.competition in EUROPEAN])

    hnl = [m for m in matches if m.competition == HNL]
    seasons = sorted({m.season for m in hnl})
    season = season_for(today)
    if season not in seasons and seasons:
        # Before the new season's fixtures appear, keep showing the latest season.
        season = seasons[-1]
    season_matches = [m for m in hnl if m.season == season]
    season_teams = sorted({t for m in season_matches for t in (m.home, m.away)})

    fc = Forecaster(reg, config).fit(hnl, euro_all, today + timedelta(days=1), season)

    # ---------------------------------------------------------- upcoming
    horizon = today + timedelta(days=UPCOMING_DAYS)
    croatian_euro = [m for m in matches if m.competition in EUROPEAN
                     and (reg.is_croatian(m.home) or reg.is_croatian(m.away))]
    upcoming_matches = [m for m in hnl + croatian_euro
                        if not m.finished and m.status != "PST" and today <= m.day <= horizon]
    upcoming_matches.sort(key=lambda m: (m.date, m.time))
    upcoming = [fc.predict(m, factors) for m in upcoming_matches]

    # ------------------------------------------------- forecast archive
    archive = json.loads(paths.forecast_archive.read_text(encoding="utf-8")) if paths.forecast_archive.exists() else {}
    for m, p in zip(upcoming_matches, upcoming):
        if _kickoff(m) > now:
            rec = {k: p[k] for k in ("prob", "xg", "over25", "btts", "scores", "factors")}
            rec["made_at"] = now.isoformat(timespec="minutes")
            archive[m.id] = rec
    paths.forecast_archive.write_text(json.dumps(archive, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")

    # ---------------------------------------------------------- backtest
    test_seasons = [s for s in seasons[1:] if sum(1 for m in hnl if m.season == s and m.finished) >= 30]
    bt = run_backtest(hnl, reg, test_seasons, config)
    reconstructed = {p["id"]: p for p in bt.predictions}

    # ----------------------------------------------------------- results
    since = today - timedelta(days=RESULTS_DAYS)
    finished = [m for m in hnl + croatian_euro if m.finished and m.day >= since]
    finished.sort(key=lambda m: (m.date, m.time), reverse=True)
    euro_recon = _reconstruct_euro([m for m in finished if m.competition in EUROPEAN and m.id not in archive],
                                   hnl, euro_all, reg, config, factors)
    results = []
    for m in finished:
        if m.id in archive:
            p, kind = archive[m.id], "pre-match"
        elif m.id in reconstructed:
            p, kind = reconstructed[m.id], "reconstructed"
        elif m.id in euro_recon:
            p, kind = euro_recon[m.id], "reconstructed"
        else:
            continue
        results.append({
            "id": m.id, "competition": m.competition, "season": m.season, "date": m.date, "time": m.time,
            "round": m.round, "stage": m.stage, "home": m.home, "away": m.away,
            "score": {"home": m.home_goals, "away": m.away_goals}, "result": m.result(),
            "prob": p["prob"], "xg": p.get("xg"), "scores": p.get("scores", [])[:3],
            "factors": p.get("factors", []), "forecast_type": kind,
            "hit": max(p["prob"], key=p["prob"].get) == {"H": "home", "D": "draw", "A": "away"}[m.result()],
        })

    # -------------------------------------------------------------- table
    sim = simulate_season(fc, season_matches, season_teams, season, factors, n_sims=n_sims) if season_teams else {}

    # -------------------------------------------------------------- clubs
    clubs = {}
    for t in season_teams:
        played = sorted([m for m in hnl + croatian_euro if m.finished and t in (m.home, m.away)],
                        key=lambda m: m.date)
        form = []
        for m in played[-5:]:
            gf, ga = (m.home_goals, m.away_goals) if m.home == t else (m.away_goals, m.home_goals)
            form.append({"id": m.id, "r": "W" if gf > ga else ("D" if gf == ga else "L"), "score": f"{gf}-{ga}",
                         "opp": m.away if m.home == t else m.home, "home": m.home == t, "date": m.date,
                         "competition": m.competition})
        hist = fc.elo.history.get(t, [])
        clubs[t] = {
            "id": t,
            "elo": round(fc.elo.rating(t)),
            "elo_rank": 0,
            "elo_history": [{"date": d, "elo": e} for d, e in hist[-150:]],
            "attack": round(fc.goals.att.get(t, 0.0), 3) if fc.goals.fitted else None,
            "defence": round(fc.goals.dfn.get(t, 0.0), 3) if fc.goals.fitted else None,
            "euro_strength": round(fc.euro_rating(t), 3) if fc.euro and fc.euro.fitted else None,
            "form": form,
            "upcoming": [p["id"] for p in upcoming if t in (p["home"], p["away"])],
            "factors": [f for f in (f.__dict__ for f in factors) if f["team"] == t],
        }
    for rank, t in enumerate(sorted(clubs, key=lambda x: -clubs[x]["elo"]), 1):
        clubs[t]["elo_rank"] = rank

    # ------------------------------------------------------------- europe
    europe = _europe_output(fc, reg, croatian_euro, upcoming, results, season, factors)

    # -------------------------------------------------------------- teams
    referenced = set(season_teams)
    for p in upcoming + results:
        referenced |= {p["home"], p["away"]}
    for c in clubs.values():
        referenced |= {f["opp"] for f in c["form"]}
    for e in europe["matches"]:
        referenced |= {e["home"], e["away"]}
    teams_out = {}
    for t in sorted(referenced):
        info = reg.get(t)
        teams_out[t] = {"id": t, "name": info.name, "short": info.short or info.name[:3].upper(),
                        "country": info.country, "hnl": t in season_teams}

    last_result = max((m.date for m in matches if m.finished), default=None)
    meta = {
        "version": __version__,
        "generated_at": now.isoformat(timespec="minutes"),
        "season": season,
        "last_result_date": last_result,
        "matches_in_database": len(matches),
        "hnl_matches": sum(1 for m in hnl if m.finished),
        "european_matches": len(euro_all),
        "sources": SOURCES,
        "model": {
            "elo_k": config.elo.k, "elo_home_advantage": config.elo.home_adv,
            "dc_time_decay_per_day": config.goals.xi, "dc_ridge": config.goals.ridge,
            "dc_rho": round(fc.goals.rho, 3) if fc.goals.fitted else None,
            "dc_home_advantage": round(fc.goals.home, 3) if fc.goals.fitted else None,
            "blend_dc_weight": config.blend, "elo_goal_slope": config.g, "simulations": n_sims,
        },
        "soft_factors_active": sum(1 for f in factors if f.start <= today <= f.end),
    }
    out = paths.output
    _write(out / "meta.json", meta)
    _write(out / "teams.json", teams_out)
    _write(out / "upcoming.json", upcoming)
    _write(out / "results.json", results)
    _write(out / "table.json", sim)
    _write(out / "clubs.json", clubs)
    _write(out / "europe.json", europe)
    oos = [s for s in bt.per_season if s not in TUNED_ON]
    oos_summary = {}
    for k in ("model", "elo_only", "dixon_coles_only", "base_rate", "uniform"):
        n = sum(bt.per_season[s][k]["n"] for s in oos)
        if n:
            oos_summary[k] = {"n": n, **{mt: round(sum(bt.per_season[s][k][mt] * bt.per_season[s][k]["n"] for s in oos) / n, 4)
                                        for mt in ("rps", "brier", "logloss", "accuracy")}}
    _write(out / "backtest.json", bt.to_dict() | {"tuned_on": TUNED_ON, "out_of_sample": oos_summary,
                                                    "out_of_sample_seasons": oos})
    log.info("build: %d upcoming, %d results, %d clubs", len(upcoming), len(results), len(clubs))
    return meta


def _reconstruct_euro(ms: list[Match], hnl, euro_all, reg, config, factors) -> dict:
    """Forecasts for past European matches using only data available before each match day."""
    out = {}
    by_day = defaultdict(list)
    for m in ms:
        by_day[m.date].append(m)
    for day, group in by_day.items():
        d = date.fromisoformat(day)
        fc = Forecaster(reg, config).fit([m for m in hnl if m.day < d], [m for m in euro_all if m.day < d],
                                         d, season_for(d))
        for m in group:
            out[m.id] = fc.predict(m, factors)
    return out


def _europe_output(fc: Forecaster, reg, croatian_euro: list[Match], upcoming: list[dict],
                   results: list[dict], season: str, factors=None) -> dict:
    up = {p["id"]: p for p in upcoming}
    res = {r["id"]: r for r in results}
    rows = []
    for m in sorted([m for m in croatian_euro if m.season == season], key=lambda m: (m.date, m.time)):
        row = {"id": m.id, "competition": m.competition, "date": m.date, "time": m.time, "round": m.round,
               "stage": m.stage, "home": m.home, "away": m.away,
               "score": {"home": m.home_goals, "away": m.away_goals} if m.finished else None}
        if m.id in up:
            row["forecast"] = up[m.id]
        elif not m.finished and m.status != "PST":
            row["forecast"] = fc.predict(m, factors)
        elif m.id in res:
            row["forecast"] = {"prob": res[m.id]["prob"], "forecast_type": res[m.id]["forecast_type"]}
        rows.append(row)
    countries = fc.euro.country_table() if fc.euro and fc.euro.fitted else []
    base = fc._euro_base
    hnl_avg = round(base[0] - base[1], 3)
    clubs = sorted({t for m in croatian_euro if m.season == season for t in (m.home, m.away) if reg.is_croatian(t)})
    return {
        "season": season,
        "matches": rows,
        "clubs": [{"id": t, "euro_strength": round(fc.euro_rating(t), 3)} for t in clubs] if fc.euro and fc.euro.fitted else [],
        "countries": countries[:30],
        "hnl_average_strength": hnl_avg,
        "croatia_country_strength": next((c["strength"] for c in countries if c["country"] == "CRO"), None),
    }
