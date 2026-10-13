"""Cross-league calibration for European matches.

HNL ratings only describe strength *inside* the Croatian league. To compare a
Croatian club with a Portuguese or Azerbaijani opponent we need a common scale.
We build one from every UEFA club competition match in our data (openfootball,
public domain, 2011 onwards): a hierarchical, time-weighted Poisson model

    log(lambda_home) = c + h + att[country(home)] + att[home] + dfn[country(away)] + dfn[away]

where club effects are shrunk strongly towards their country's effect. A club
that has never played in Europe in our data therefore gets its country's
average. (This is a data-driven analogue of UEFA country coefficients.)

Croatian clubs: only the strongest HNL clubs play in Europe, so the Croatian
country effect is biased upwards relative to an *average* HNL team. We correct
for that by comparing each Croatian club's European strength with its HNL
strength, which yields the European-scale strength of the HNL average. A
Croatian club's European strength is then

    HNL average on the European scale + its current HNL deviation (domestic form).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date

import numpy as np

from ..matches import Match


@dataclass
class EuroParams:
    xi: float = 0.0012            # time decay per day (half-life ~ 1.6 years)
    ridge_country: float = 1.0
    ridge_club: float = 6.0
    newcomer_penalty: float = 0.05  # log-goals: clubs new to Europe are a bit weaker than their country average


@dataclass
class EuroModel:
    params: EuroParams = field(default_factory=EuroParams)
    intercept: float = math.log(1.3)
    home: float = 0.25
    c_att: dict[str, float] = field(default_factory=dict)
    c_dfn: dict[str, float] = field(default_factory=dict)
    t_att: dict[str, float] = field(default_factory=dict)
    t_dfn: dict[str, float] = field(default_factory=dict)
    country_of: dict[str, str] = field(default_factory=dict)
    games: dict[str, float] = field(default_factory=dict)
    fitted: bool = False

    def fit(self, matches: list[Match], country_of, as_of: date) -> "EuroModel":
        ms = [m for m in matches if m.finished and m.day < as_of]
        if len(ms) < 50:
            return self
        clubs = sorted({m.home for m in ms} | {m.away for m in ms})
        self.country_of = {t: country_of(t) for t in clubs}
        countries = sorted(set(self.country_of.values()))
        ci = {c: i for i, c in enumerate(countries)}
        ti = {t: i for i, t in enumerate(clubs)}
        nc, nt = len(countries), len(clubs)
        # columns: 0 c, 1 h, [2, 2+nc) country att, [2+nc, 2+2nc) country dfn,
        #          then club att, club dfn
        o_ca, o_cd, o_ta, o_td = 2, 2 + nc, 2 + 2 * nc, 2 + 2 * nc + nt
        p = 2 + 2 * nc + 2 * nt
        rows = []
        y, w = [], []
        for m in ms:
            wt = math.exp(-self.params.xi * (as_of - m.day).days)
            ch, ca = ci[self.country_of[m.home]], ci[self.country_of[m.away]]
            th, ta = ti[m.home], ti[m.away]
            hcol = [1] if not m.neutral else []
            rows.append([0, *hcol, o_ca + ch, o_cd + ca, o_ta + th, o_td + ta])
            y.append(m.home_goals)
            w.append(wt)
            rows.append([0, o_ca + ca, o_cd + ch, o_ta + ta, o_td + th])
            y.append(m.away_goals)
            w.append(wt)
            for t in (m.home, m.away):
                self.games[t] = self.games.get(t, 0.0) + wt
        y = np.array(y, float)
        w = np.array(w, float)
        pen = np.zeros(p)
        pen[o_ca:o_ta] = self.params.ridge_country
        pen[o_ta:] = self.params.ridge_club
        pen[:2] = 1e-6
        # Sparse row representation -> fast Newton steps.
        lens = np.array([len(r) for r in rows])
        maxlen = lens.max()
        idx = np.zeros((len(rows), maxlen), int)
        mask = np.zeros((len(rows), maxlen), bool)
        for i, r in enumerate(rows):
            idx[i, :len(r)] = r
            mask[i, :len(r)] = True
        beta = np.zeros(p)
        beta[0] = math.log(max(np.average(y, weights=w), 0.3))
        for _ in range(40):
            eta = np.clip((beta[idx] * mask).sum(axis=1), -5, 3)
            mu = np.exp(eta)
            r = w * (y - mu)
            grad = -pen * beta
            np.add.at(grad, idx[mask], np.repeat(r, lens))
            hw = w * mu
            hess = np.diag(pen.copy())
            for a in range(maxlen):
                for b in range(maxlen):
                    sel = mask[:, a] & mask[:, b]
                    np.add.at(hess, (idx[sel, a], idx[sel, b]), hw[sel])
            step = np.linalg.solve(hess, grad)
            beta += step
            if np.max(np.abs(step)) < 1e-6:
                break
        self.intercept, self.home = float(beta[0]), float(beta[1])
        self.c_att = {c: float(beta[o_ca + i]) for c, i in ci.items()}
        self.c_dfn = {c: float(beta[o_cd + i]) for c, i in ci.items()}
        self.t_att = {t: float(beta[o_ta + i]) for t, i in ti.items()}
        self.t_dfn = {t: float(beta[o_td + i]) for t, i in ti.items()}
        self.fitted = True
        return self

    def club_effects(self, team: str, country: str) -> tuple[float, float]:
        """(att, dfn) on the European scale; unseen clubs get the country average minus a penalty."""
        c = country if country in self.c_att else None
        ca = self.c_att.get(c, min(self.c_att.values(), default=0.0)) if c else min(self.c_att.values(), default=0.0)
        cd = self.c_dfn.get(c, max(self.c_dfn.values(), default=0.0)) if c else max(self.c_dfn.values(), default=0.0)
        if team in self.t_att:
            return ca + self.t_att[team], cd + self.t_dfn[team]
        pen = self.params.newcomer_penalty
        return ca - pen, cd + pen

    def strength(self, team: str, country: str) -> float:
        a, d = self.club_effects(team, country)
        return a - d

    def country_table(self) -> list[dict]:
        rows = [{"country": c, "strength": round(self.c_att[c] - self.c_dfn[c], 3)} for c in self.c_att]
        return sorted(rows, key=lambda r: -r["strength"])


def hnl_average_on_euro_scale(euro: EuroModel, hnl_att: dict[str, float], hnl_dfn: dict[str, float]) -> tuple[float, float]:
    """European-scale (att, dfn) of an average HNL team.

    For each Croatian club with European games: European effect minus its HNL
    effect (HNL effects are centred on the league average). Weighted by
    (time-decayed) European games played.
    """
    num_a = num_d = den = 0.0
    for team, g in euro.games.items():
        if euro.country_of.get(team) != "CRO" or team not in hnl_att:
            continue
        a, d = euro.club_effects(team, "CRO")
        wgt = min(g, 15.0)
        num_a += wgt * (a - hnl_att[team])
        num_d += wgt * (d - hnl_dfn[team])
        den += wgt
    if den == 0:
        return euro.c_att.get("CRO", 0.0), euro.c_dfn.get("CRO", 0.0)
    return num_a / den, num_d / den
