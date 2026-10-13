"""Walk-forward backtest on past HNL seasons.

For every match day the models are refitted using only matches played
*before* that day, then every match of the day is predicted. Nothing from the
future leaks into a forecast. We report:

* Brier score (sum over home/draw/away of squared error; lower is better, 0.667 = coin-flip-like uniform guess)
* log loss (lower is better)
* ranked probability score, RPS (standard for ordered football outcomes)
* accuracy of the most likely outcome
* calibration table (forecast probability bins vs. observed frequency)

and compare with naive baselines so the numbers have context.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

import numpy as np

from .matches import Match
from .model.forecaster import Forecaster, ModelConfig
from .teams import TeamRegistry

OUTCOMES = ("home", "draw", "away")
RES_IDX = {"H": 0, "D": 1, "A": 2}


def brier(p, y) -> float:
    o = np.zeros(3)
    o[y] = 1
    return float(np.sum((np.asarray(p) - o) ** 2))


def logloss(p, y) -> float:
    return -math.log(max(p[y], 1e-12))


def rps(p, y) -> float:
    o = np.zeros(3)
    o[y] = 1
    cp, co = np.cumsum(p)[:2], np.cumsum(o)[:2]
    return float(np.sum((cp - co) ** 2) / 2)


@dataclass
class ScoreCard:
    n: int = 0
    brier: float = 0.0
    logloss: float = 0.0
    rps: float = 0.0
    correct: int = 0

    def add(self, p, y) -> None:
        self.n += 1
        self.brier += brier(p, y)
        self.logloss += logloss(p, y)
        self.rps += rps(p, y)
        self.correct += int(int(np.argmax(p)) == y)

    def summary(self) -> dict:
        n = max(self.n, 1)
        return {"n": self.n, "brier": round(self.brier / n, 4), "logloss": round(self.logloss / n, 4),
                "rps": round(self.rps / n, 4), "accuracy": round(self.correct / n, 4)}


@dataclass
class BacktestResult:
    seasons: list[str]
    models: dict[str, dict] = field(default_factory=dict)
    per_season: dict[str, dict[str, dict]] = field(default_factory=dict)
    calibration: list[dict] = field(default_factory=list)
    predictions: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"seasons": self.seasons, "models": self.models, "per_season": self.per_season,
                "calibration": self.calibration}


def calibration_table(preds: list[tuple[list[float], int]], bins: int = 10) -> list[dict]:
    """Pool all three outcome probabilities; compare mean forecast with observed rate per bin."""
    acc = defaultdict(lambda: [0.0, 0.0, 0])
    for p, y in preds:
        for k in range(3):
            b = min(int(p[k] * bins), bins - 1)
            acc[b][0] += p[k]
            acc[b][1] += 1.0 if y == k else 0.0
            acc[b][2] += 1
    out = []
    for b in sorted(acc):
        s_p, s_y, n = acc[b]
        out.append({"bin": f"{b / bins:.1f}-{(b + 1) / bins:.1f}", "forecast": round(s_p / n, 4),
                    "observed": round(s_y / n, 4), "n": n})
    return out


def run_backtest(matches: list[Match], teams: TeamRegistry, test_seasons: list[str],
                 config: ModelConfig | None = None, euro_matches: list[Match] | None = None,
                 keep_predictions: bool = True) -> BacktestResult:
    config = config or ModelConfig()
    hnl = sorted([m for m in matches if m.competition == "HNL" and m.finished], key=lambda m: (m.date, m.time))
    cards = {k: ScoreCard() for k in ("model", "elo_only", "dixon_coles_only", "base_rate", "uniform")}
    season_cards: dict[str, dict[str, ScoreCard]] = defaultdict(lambda: {k: ScoreCard() for k in cards})
    pooled = []
    result = BacktestResult(seasons=test_seasons)
    elo_cfg = ModelConfig(elo=config.elo, goals=config.goals, blend=0.0, g=config.g)
    dc_cfg = ModelConfig(elo=config.elo, goals=config.goals, blend=1.0, g=config.g)

    by_day: dict[str, list[Match]] = defaultdict(list)
    for m in hnl:
        if m.season in test_seasons:
            by_day[m.date].append(m)

    for day in sorted(by_day):
        d = date.fromisoformat(day)
        season = by_day[day][0].season
        hist = [m for m in hnl if m.date < day]
        fc = Forecaster(teams, config).fit(hist, [], d, season)
        fe = Forecaster(teams, elo_cfg)
        fe.elo, fe.goals, fe.hnl_active = fc.elo, fc.goals, fc.hnl_active
        fd = Forecaster(teams, dc_cfg)
        fd.elo, fd.goals, fd.hnl_active = fc.elo, fc.goals, fc.hnl_active
        # Base rates from the previous ~3 seasons.
        recent = [m for m in hist if (d - m.day).days < 3 * 365] or hist
        counts = np.array([sum(1 for m in recent if m.result() == r) for r in "HDA"], float) + 1
        base = counts / counts.sum()
        for m in by_day[day]:
            y = RES_IDX[m.result()]
            pm = fc.predict(m)
            p_model = [pm["prob"][k] for k in OUTCOMES]
            p_elo = [fe.predict(m)["prob"][k] for k in OUTCOMES]
            p_dc = [fd.predict(m)["prob"][k] for k in OUTCOMES]
            for name, p in (("model", p_model), ("elo_only", p_elo), ("dixon_coles_only", p_dc),
                            ("base_rate", list(base)), ("uniform", [1 / 3] * 3)):
                cards[name].add(p, y)
                season_cards[season][name].add(p, y)
            pooled.append((p_model, y))
            if keep_predictions:
                pm["result"] = {"home": m.home_goals, "away": m.away_goals}
                pm["reconstructed"] = True
                result.predictions.append(pm)

    result.models = {k: v.summary() for k, v in cards.items()}
    result.per_season = {s: {k: v.summary() for k, v in c.items()} for s, c in sorted(season_cards.items())}
    result.calibration = calibration_table(pooled)
    return result
