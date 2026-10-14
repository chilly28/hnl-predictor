import math
from datetime import date, timedelta

import numpy as np
import pytest

from hnl_predictor.backtest import brier, calibration_table, logloss, rps, run_backtest
from hnl_predictor.matches import Match
from hnl_predictor.model.elo import EloModel, EloParams, expected_score, goal_multiplier
from hnl_predictor.model.forecaster import Forecaster
from hnl_predictor.model.goals import GoalsModel, score_matrix, summarise
from hnl_predictor.model.simulate import league_table, remaining_fixtures, simulate_season
from hnl_predictor.soft_factors import SoftFactor, TOTAL_CAP, total_adjustment
from hnl_predictor.teams import TeamRegistry

TEAMS = ["a", "b", "c", "d"]


def synthetic_league(seasons=2, seed=1, strengths=None):
    """Double round-robin leagues with known strengths."""
    rng = np.random.default_rng(seed)
    strengths = strengths or {"a": 0.5, "b": 0.15, "c": -0.15, "d": -0.5}
    out = []
    day = date(2023, 8, 1)
    for s in range(seasons):
        season = f"{2023 + s}-{str(24 + s)[-2:]}"
        for rep in range(4):
            for h in TEAMS:
                for a in TEAMS:
                    if h == a:
                        continue
                    lh = math.exp(0.2 + 0.25 + strengths[h] - strengths[a])
                    la = math.exp(0.2 + strengths[a] - strengths[h])
                    out.append(Match("HNL", season, day.isoformat(), h, a, int(rng.poisson(lh)),
                                     int(rng.poisson(la)), "FT", round=f"{rep}. kolo"))
                    day += timedelta(days=2)
        day = date(2024 + s, 8, 1)
    return out


def test_expected_score_symmetry():
    assert expected_score(0) == pytest.approx(0.5)
    assert expected_score(100) + expected_score(-100) == pytest.approx(1.0)
    assert goal_multiplier(1) == 1.0 and goal_multiplier(3) > goal_multiplier(2) > 1


def test_elo_zero_sum_and_ordering():
    ms = synthetic_league()
    elo = EloModel(EloParams(season_regress=0.0, promoted_offset=0.0)).fit(ms)
    assert sum(elo.ratings.values()) == pytest.approx(1500 * 4, abs=1e-6)
    ranked = sorted(elo.ratings, key=elo.ratings.get, reverse=True)
    assert ranked[0] == "a" and ranked[-1] == "d"


def test_score_matrix_is_distribution():
    m = score_matrix(1.6, 1.1, rho=-0.08)
    assert m.sum() == pytest.approx(1.0)
    assert (m >= 0).all()
    s = summarise(m)
    assert s["home"] + s["draw"] + s["away"] == pytest.approx(1.0)
    assert s["home"] > s["away"]
    assert 0 < s["over25"] < 1 and 0 < s["btts"] < 1
    assert s["scores"][0]["p"] >= s["scores"][1]["p"]


def test_dixon_coles_recovers_strengths():
    ms = synthetic_league(seasons=3, seed=4)
    g = GoalsModel().fit(ms, date(2026, 8, 1))
    assert g.fitted
    order = sorted(TEAMS, key=g.strength, reverse=True)
    assert order == ["a", "b", "c", "d"]
    assert 0.1 < g.home < 0.45


def test_forecaster_probabilities_and_soft_factors():
    reg = TeamRegistry()
    ms = synthetic_league()
    fc = Forecaster(reg).fit(ms, [], date(2025, 8, 1), "2025-26")
    m = Match("HNL", "2025-26", "2025-08-10", "a", "d")
    p = fc.predict(m)
    assert sum(p["prob"].values()) == pytest.approx(1.0, abs=1e-3)
    assert p["prob"]["home"] > 0.6
    assert p["factors"] == []
    # A negative factor for the home side lowers its win probability, and is reported.
    f = SoftFactor(team="a", date="2025-08-05", type="injury", note="striker out", adjustment=-40)
    q = fc.predict(m, [f])
    assert q["prob"]["home"] < p["prob"]["home"]
    assert q["base_prob"] == p["prob"]
    assert len(q["factors"]) == 1 and q["factors"][0]["effect"]["home"] < 0
    # Factor outside its date window does nothing.
    late = Match("HNL", "2025-26", "2025-09-30", "a", "d")
    assert fc.predict(late, [f])["factors"] == []


def test_soft_factor_caps():
    f = SoftFactor(team="a", date="2025-01-01", type="media", note="", adjustment=-100)
    assert f.capped == -15
    many = [SoftFactor(team="a", date="2025-01-01", type="injury", note="", adjustment=-50) for _ in range(4)]
    assert total_adjustment(many) == -TOTAL_CAP
    half = SoftFactor(team="a", date="2025-01-01", type="injury", note="", adjustment=-40, confidence=0.5)
    assert half.capped == -20


def test_metrics():
    assert brier([1, 0, 0], 0) == 0
    assert brier([1 / 3] * 3, 0) == pytest.approx(2 / 3)
    assert logloss([0.5, 0.25, 0.25], 0) == pytest.approx(math.log(2))
    assert rps([1, 0, 0], 0) == 0
    # Predicting a draw when home wins is better (RPS) than predicting an away win.
    assert rps([0, 1, 0], 0) < rps([0, 0, 1], 0)
    cal = calibration_table([([0.65, 0.2, 0.15], 0), ([0.62, 0.2, 0.18], 2)])
    assert sum(r["n"] for r in cal) == 6


def test_backtest_beats_uniform():
    reg = TeamRegistry()
    ms = synthetic_league(seasons=3, seed=11)
    res = run_backtest(ms, reg, ["2025-26"])
    assert res.models["model"]["n"] == 48
    assert res.models["model"]["rps"] < res.models["uniform"]["rps"]
    assert all(p["reconstructed"] for p in res.predictions)


def test_simulation_full_season():
    reg = TeamRegistry()
    hist = synthetic_league()
    fc = Forecaster(reg).fit(hist, [], date(2025, 8, 1), "2025-26")
    played = [Match("HNL", "2025-26", "2025-08-02", "a", "b", 2, 0, "FT"),
              Match("HNL", "2025-26", "2025-08-02", "c", "d", 1, 1, "FT")]
    table = league_table(played, TEAMS)
    assert table[0].team == "a" and table[0].points == 3
    rem = remaining_fixtures(played, TEAMS, "2025-26")
    assert len(rem) == 4 * 3 * 2 - 2  # 24 matches in a 4-team quadruple round robin
    sim = simulate_season(fc, played, TEAMS, "2025-26", n_sims=2000)
    rows = {r["team"]: r for r in sim["rows"]}
    assert sum(r["p_title"] for r in rows.values()) == pytest.approx(1.0, abs=1e-6)
    for r in rows.values():
        assert sum(r["positions"]) == pytest.approx(1.0, abs=1e-3)
    assert rows["a"]["p_title"] > rows["d"]["p_title"]
    assert rows["a"]["exp_points"] >= rows["a"]["points"]


def test_remaining_fixtures_drops_stale_duplicates():
    played = [Match("HNL", "s", "2025-08-01", "a", "b", 1, 0, "FT")]
    sched = [Match("HNL", "s", "2025-09-01", "a", "b"), Match("HNL", "s", "2025-09-20", "a", "b")]
    rem = remaining_fixtures(played + sched, ["a", "b"], "s")
    ab = [m for m in rem if (m.home, m.away) == ("a", "b")]
    assert len(ab) == 1 and ab[0].date == "2025-09-20"
    assert len([m for m in rem if (m.home, m.away) == ("b", "a")]) == 2


def test_head_to_head_tiebreak():
    # a and b finish level on points; b won the mutual match, a has the better goal difference.
    ms = [
        Match("HNL", "s", "2025-08-01", "b", "a", 1, 0, "FT"),
        Match("HNL", "s", "2025-08-02", "a", "c", 5, 0, "FT"),
        Match("HNL", "s", "2025-08-03", "b", "d", 0, 0, "FT"),
        Match("HNL", "s", "2025-08-04", "a", "d", 0, 0, "FT"),
    ]
    table = league_table(ms, ["a", "b", "c", "d"])
    assert [r.points for r in table][:2] == [4, 4]
    assert table[0].team == "b"  # head-to-head beats goal difference
    assert table[0].gd < next(r for r in table if r.team == "a").gd


def test_rank_vectorised_matches_rules():
    from hnl_predictor.model.simulate import rank
    pts = np.array([[10, 10, 7], [7, 10, 10]], float)
    gd = np.array([[5, 1, 0], [0, 9, 1]], float)
    gf = np.zeros((2, 3))
    h2h_pts = np.zeros((2, 3, 3))
    h2h_gd = np.zeros((2, 3, 3))
    h2h_pts[0, 1, 0] = 3  # sim 0: team 1 beat team 0
    h2h_gd[0, 1, 0], h2h_gd[0, 0, 1] = 1, -1
    order = rank(pts, gd, gf, h2h_pts, h2h_gd, np.zeros((2, 3)))
    assert list(order[0]) == [1, 0, 2]
    assert list(order[1]) == [1, 2, 0]  # no head-to-head games: goal difference decides


def test_live_accuracy_scores_only_finished_archived_matches():
    from hnl_predictor.build import live_accuracy
    m1 = Match("HNL", "2026-27", "2026-10-16", "rudes", "rijeka", 0, 2, "FT")
    m2 = Match("UECL", "2026-27", "2026-10-15", "hajduk-split", "ajax-ned", 1, 1, "FT")
    m3 = Match("HNL", "2026-27", "2026-10-18", "hajduk-split", "varazdin")  # not played yet
    arch = {m.id: {"prob": {"home": .3, "draw": .3, "away": .4}} for m in (m1, m2, m3)}
    r = live_accuracy(arch, [m1, m2, m3])
    assert r["all"]["n"] == 2 and r["HNL"]["n"] == 1 and r["europe"]["n"] == 1
    assert r["since"] == "2026-10-15"
    assert live_accuracy({}, [m1])["all"]["n"] == 0
