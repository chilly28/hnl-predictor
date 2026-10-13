"""Combine Elo, Dixon-Coles, European calibration and soft factors into forecasts.

Domestic (HNL) match:
    log lambda = w * log lambda_DC + (1 - w) * log lambda_Elo
where lambda_Elo splits the Dixon-Coles expected total goals according to the
Elo difference (``g`` log-goals per Elo point).

European match: see ``europe.py``. Croatian clubs get their European-scale
strength from the HNL average on that scale plus their current (blended)
HNL deviation; foreign clubs from the European model.

Soft factors shift a team's rating by Elo points, translated with the same
``g`` into log-goal shifts for both sides.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date

import numpy as np

from ..matches import EUROPEAN, HNL, Match
from ..soft_factors import SoftFactor, active_factors, factor_to_dict, total_adjustment
from ..teams import TeamRegistry
from .elo import EloModel, EloParams
from .europe import EuroModel, EuroParams, hnl_average_on_euro_scale
from .goals import GoalsModel, GoalsParams, score_matrix, summarise


@dataclass
class ModelConfig:
    elo: EloParams = field(default_factory=EloParams)
    goals: GoalsParams = field(default_factory=GoalsParams)
    euro: EuroParams = field(default_factory=EuroParams)
    # Tuned by grid search on the 2019-20 and 2023-24 seasons only (walk-forward RPS);
    # later seasons are out-of-sample. The optimum is flat, so moderate values were chosen.
    blend: float = 0.35           # weight of Dixon-Coles vs Elo in log-goal space
    g: float = 0.0039             # log-goal ratio per Elo point (home vs away)
    europe_rho: float = -0.05


@dataclass
class Forecaster:
    teams: TeamRegistry
    config: ModelConfig = field(default_factory=ModelConfig)
    elo: EloModel | None = None
    goals: GoalsModel | None = None
    euro: EuroModel | None = None
    as_of: date | None = None
    hnl_active: list[str] = field(default_factory=list)
    _euro_base: tuple[float, float] = (0.0, 0.0)

    # ------------------------------------------------------------------ fit
    def fit(self, hnl_matches: list[Match], euro_matches: list[Match], as_of: date,
            current_season: str | None = None) -> "Forecaster":
        self.as_of = as_of
        past = [m for m in hnl_matches if m.finished and m.day < as_of]
        self.elo = EloModel(params=self.config.elo).fit(past)
        if current_season:
            self.elo.start_season(current_season)
        self.goals = GoalsModel(params=self.config.goals).fit(past, as_of)
        season_teams = sorted({t for m in hnl_matches if m.season == current_season for t in (m.home, m.away)})
        self.hnl_active = season_teams or sorted(self.elo.ratings)
        if euro_matches:
            self.euro = EuroModel(params=self.config.euro).fit(euro_matches, lambda t: self.teams.get(t).country, as_of)
            if self.euro.fitted:
                att, dfn = self._hnl_devs()
                self._euro_base = hnl_average_on_euro_scale(self.euro, att, dfn)
        return self

    def _hnl_mean_elo(self) -> float:
        vals = [self.elo.rating(t) for t in self.hnl_active] if self.hnl_active else list(self.elo.ratings.values())
        return sum(vals) / len(vals) if vals else 1500.0

    def _hnl_devs(self) -> tuple[dict[str, float], dict[str, float]]:
        """Blended HNL attack/defence deviations from the league average (log-goals)."""
        teams = set(self.elo.ratings) | set(self.goals.att if self.goals else {})
        mean_elo = self._hnl_mean_elo()
        w = self.config.blend if self.goals and self.goals.fitted else 0.0
        active = [t for t in self.hnl_active if t in teams] or list(teams)
        mean_att = np.mean([self.goals.att.get(t, 0.0) for t in active]) if w else 0.0
        mean_dfn = np.mean([self.goals.dfn.get(t, 0.0) for t in active]) if w else 0.0
        att, dfn = {}, {}
        for t in teams:
            e = self.config.g * (self.elo.rating(t) - mean_elo) / 2
            a = (self.goals.att.get(t, 0.0) - mean_att) if w else 0.0
            d = (self.goals.dfn.get(t, 0.0) - mean_dfn) if w else 0.0
            att[t] = w * a + (1 - w) * e
            dfn[t] = w * d + (1 - w) * -e
        return att, dfn

    # -------------------------------------------------------------- predict
    def base_lambdas(self, m: Match) -> tuple[float, float, float]:
        """Expected goals before soft factors and the Dixon-Coles rho to use."""
        if m.competition in EUROPEAN:
            return self._europe_lambdas(m)
        return self._hnl_lambdas(m)

    def _hnl_lambdas(self, m: Match) -> tuple[float, float, float]:
        g = self.config.g
        dr = self.elo.diff(m.home, m.away, m.neutral)
        if self.goals and self.goals.fitted:
            lh_dc, la_dc = self.goals.lambdas(m.home, m.away, m.neutral)
            total = lh_dc + la_dc
            rho = self.goals.rho
        else:
            lh_dc = la_dc = None
            total, rho = 2.7, -0.05
        # Elo: split the expected total by the rating difference.
        ratio = math.exp(g * dr)
        lh_elo = total * ratio / (1 + ratio)
        la_elo = total / (1 + ratio)
        if lh_dc is None:
            return lh_elo, la_elo, rho
        w = self.config.blend
        lh = math.exp(w * math.log(lh_dc) + (1 - w) * math.log(lh_elo))
        la = math.exp(w * math.log(la_dc) + (1 - w) * math.log(la_elo))
        return lh, la, rho

    def euro_effects(self, team: str) -> tuple[float, float]:
        t = self.teams.get(team)
        if t.country == "CRO":
            att, dfn = self._hnl_devs()
            base_a, base_d = self._euro_base
            return base_a + att.get(team, -0.05), base_d + dfn.get(team, 0.05)
        return self.euro.club_effects(team, t.country)

    def _europe_lambdas(self, m: Match) -> tuple[float, float, float]:
        if not self.euro or not self.euro.fitted:
            return self._hnl_lambdas(m)
        ah, dh = self.euro_effects(m.home)
        aa, da = self.euro_effects(m.away)
        h = 0.0 if m.neutral else self.euro.home
        lh = math.exp(self.euro.intercept + h + ah + da)
        la = math.exp(self.euro.intercept + aa + dh)
        return lh, la, self.config.europe_rho

    def euro_rating(self, team: str) -> float:
        """Net European-scale strength (att - dfn) for display."""
        a, d = self.euro_effects(team)
        return a - d

    def predict(self, m: Match, factors: list[SoftFactor] | None = None) -> dict:
        lh, la, rho = self.base_lambdas(m)
        base = summarise(score_matrix(lh, la, rho))
        fh = active_factors(factors or [], m.home, m.day, m.away)
        fa = active_factors(factors or [], m.away, m.day, m.home)
        result = base
        applied = []
        if fh or fa:
            result = self._with_factors(lh, la, rho, total_adjustment(fh), total_adjustment(fa))
            for f in fh + fa:
                # Marginal effect of this factor: full forecast minus forecast without it.
                rest_h = [x for x in fh if x is not f]
                rest_a = [x for x in fa if x is not f]
                without = self._with_factors(lh, la, rho, total_adjustment(rest_h), total_adjustment(rest_a))
                d = factor_to_dict(f)
                d["effect"] = {k: round(result[k] - without[k], 4) for k in ("home", "draw", "away")}
                applied.append(d)
        out = {
            "id": m.id,
            "competition": m.competition,
            "season": m.season,
            "date": m.date,
            "time": m.time,
            "round": m.round,
            "stage": m.stage,
            "home": m.home,
            "away": m.away,
            "neutral": m.neutral,
            "prob": {k: round(result[k], 4) for k in ("home", "draw", "away")},
            "xg": {"home": round(result["xg_home"], 2), "away": round(result["xg_away"], 2)},
            "over25": round(result["over25"], 4),
            "btts": round(result["btts"], 4),
            "scores": [{"score": s["score"], "p": round(s["p"], 4)} for s in result["scores"]],
            "base_prob": {k: round(base[k], 4) for k in ("home", "draw", "away")},
            "factors": applied,
        }
        if m.competition == HNL:
            out["elo"] = {"home": round(self.elo.rating(m.home)), "away": round(self.elo.rating(m.away))}
        return out

    def _with_factors(self, lh, la, rho, adj_home: float, adj_away: float) -> dict:
        shift = self.config.g * (adj_home - adj_away) / 2
        return summarise(score_matrix(lh * math.exp(shift), la * math.exp(-shift), rho))

    def matrix(self, m: Match, factors: list[SoftFactor] | None = None) -> np.ndarray:
        lh, la, rho = self.base_lambdas(m)
        fh = active_factors(factors or [], m.home, m.day, m.away)
        fa = active_factors(factors or [], m.away, m.day, m.home)
        shift = self.config.g * (total_adjustment(fh) - total_adjustment(fa)) / 2
        return score_matrix(lh * math.exp(shift), la * math.exp(-shift), rho)
