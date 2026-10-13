"""Dixon-Coles Poisson goals model with time decay and ridge shrinkage.

log(lambda_home) = c + h + att[home] + dfn[away]
log(lambda_away) = c     + att[away] + dfn[home]

``att`` is attacking strength, ``dfn`` is defensive weakness (higher = concedes
more). Parameters are fitted by penalised, time-weighted Poisson maximum
likelihood (Newton-Raphson, numpy only). The Dixon-Coles ``rho`` term, which
corrects the frequency of 0-0, 1-0, 0-1 and 1-1, is fitted afterwards by a
one-dimensional search.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date

import numpy as np

from ..matches import Match

MAX_GOALS = 10


@dataclass
class GoalsParams:
    xi: float = 0.0022          # time decay per day (half-life ~ 315 days)
    ridge: float = 4.0          # shrinkage of team effects towards the average
    max_age_days: int = 1100    # ignore older matches


@dataclass
class GoalsModel:
    params: GoalsParams = field(default_factory=GoalsParams)
    teams: list[str] = field(default_factory=list)
    att: dict[str, float] = field(default_factory=dict)
    dfn: dict[str, float] = field(default_factory=dict)
    intercept: float = math.log(1.3)
    home: float = 0.25
    rho: float = -0.05
    fitted: bool = False

    def fit(self, matches: list[Match], as_of: date) -> "GoalsModel":
        ms = [m for m in matches if m.finished and 0 <= (as_of - m.day).days <= self.params.max_age_days]
        if len(ms) < 20:
            self.fitted = False
            return self
        teams = sorted({m.home for m in ms} | {m.away for m in ms})
        idx = {t: i for i, t in enumerate(teams)}
        n = len(teams)
        # Parameter vector: [c, h, att_0..att_n-1, dfn_0..dfn_n-1]
        p = 2 + 2 * n
        rows = 2 * len(ms)
        X = np.zeros((rows, p))
        y = np.zeros(rows)
        w = np.zeros(rows)
        for k, m in enumerate(ms):
            wt = math.exp(-self.params.xi * (as_of - m.day).days)
            hi, ai = idx[m.home], idx[m.away]
            r = 2 * k
            X[r, 0] = 1
            X[r, 1] = 0 if m.neutral else 1
            X[r, 2 + hi] = 1
            X[r, 2 + n + ai] = 1
            y[r] = m.home_goals
            w[r] = wt
            X[r + 1, 0] = 1
            X[r + 1, 2 + ai] = 1
            X[r + 1, 2 + n + hi] = 1
            y[r + 1] = m.away_goals
            w[r + 1] = wt
        pen = np.full(p, self.params.ridge)
        pen[:2] = 1e-6
        beta = np.zeros(p)
        beta[0] = math.log(max(np.average(y, weights=w), 0.3))
        for _ in range(50):
            eta = np.clip(X @ beta, -5, 3)
            mu = np.exp(eta)
            grad = X.T @ (w * (y - mu)) - pen * beta
            hess = (X * (w * mu)[:, None]).T @ X + np.diag(pen)
            step = np.linalg.solve(hess, grad)
            beta += step
            if np.max(np.abs(step)) < 1e-7:
                break
        self.teams = teams
        self.intercept = float(beta[0])
        self.home = float(beta[1])
        self.att = {t: float(beta[2 + i]) for t, i in idx.items()}
        self.dfn = {t: float(beta[2 + n + i]) for t, i in idx.items()}
        # Fit rho on the low-score correction.
        mu = np.exp(np.clip(X @ beta, -5, 3))
        lh, la = mu[0::2], mu[1::2]
        hg, ag = y[0::2].astype(int), y[1::2].astype(int)
        wts = w[0::2]
        best, best_ll = 0.0, -1e18
        for rho in np.arange(-0.25, 0.101, 0.01):
            tau = _tau_vec(hg, ag, lh, la, rho)
            if np.any(tau <= 0):
                continue
            ll = float(np.sum(wts * np.log(tau)))
            if ll > best_ll:
                best, best_ll = float(rho), ll
        self.rho = best
        self.fitted = True
        return self

    def lambdas(self, home: str, away: str, neutral: bool = False) -> tuple[float, float]:
        h = 0.0 if neutral else self.home
        lh = math.exp(self.intercept + h + self.att.get(home, 0.0) + self.dfn.get(away, 0.0))
        la = math.exp(self.intercept + self.att.get(away, 0.0) + self.dfn.get(home, 0.0))
        return lh, la

    def strength(self, team: str) -> float:
        """Net goal strength per match vs an average team (att - dfn, in log-goals)."""
        return self.att.get(team, 0.0) - self.dfn.get(team, 0.0)


def _tau_vec(hg, ag, lh, la, rho):
    tau = np.ones_like(lh)
    m00 = (hg == 0) & (ag == 0)
    m01 = (hg == 0) & (ag == 1)
    m10 = (hg == 1) & (ag == 0)
    m11 = (hg == 1) & (ag == 1)
    tau[m00] = 1 - lh[m00] * la[m00] * rho
    tau[m01] = 1 + lh[m01] * rho
    tau[m10] = 1 + la[m10] * rho
    tau[m11] = 1 - rho
    return tau


def _poisson_pmf(lam: float, n: int = MAX_GOALS) -> np.ndarray:
    k = np.arange(n + 1)
    logp = -lam + k * math.log(max(lam, 1e-9)) - np.array([math.lgamma(i + 1) for i in k])
    return np.exp(logp)


def score_matrix(lh: float, la: float, rho: float = 0.0, n: int = MAX_GOALS) -> np.ndarray:
    """Probability matrix P[home_goals, away_goals] with the Dixon-Coles correction."""
    m = np.outer(_poisson_pmf(lh, n), _poisson_pmf(la, n))
    if rho:
        m[0, 0] *= max(1 - lh * la * rho, 0)
        m[0, 1] *= max(1 + lh * rho, 0)
        m[1, 0] *= max(1 + la * rho, 0)
        m[1, 1] *= max(1 - rho, 0)
    return m / m.sum()


def summarise(matrix: np.ndarray, top: int = 5) -> dict:
    """1X2, over/under 2.5, both teams to score and the most likely scorelines."""
    n = matrix.shape[0]
    hg, ag = np.indices(matrix.shape)
    p_home = float(matrix[hg > ag].sum())
    p_draw = float(np.trace(matrix))
    p_away = float(matrix[hg < ag].sum())
    over25 = float(matrix[(hg + ag) > 2].sum())
    btts = float(matrix[1:, 1:].sum())
    flat = [(float(matrix[i, j]), i, j) for i in range(n) for j in range(n)]
    flat.sort(reverse=True)
    return {
        "home": p_home,
        "draw": p_draw,
        "away": p_away,
        "over25": over25,
        "btts": btts,
        "xg_home": float((matrix.sum(axis=1) * np.arange(n)).sum()),
        "xg_away": float((matrix.sum(axis=0) * np.arange(n)).sum()),
        "scores": [{"score": f"{i}-{j}", "p": p} for p, i, j in flat[:top]],
    }
