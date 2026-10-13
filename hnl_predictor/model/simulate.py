"""Monte Carlo simulation of the rest of the HNL season.

The HNL has 10 clubs playing each other four times (two home, two away), 36
rounds in total. Remaining fixtures are taken from the fixture list when
known; any meetings still missing (for example when the fixture list is not
yet published) are generated from that structure, so projections always cover
the full season.

Each remaining match is drawn from its forecast score distribution. Teams
level on points are ranked as in the HNL rules: points in the matches between
the tied clubs, goal difference in those matches, then overall goal
difference, overall goals scored, and finally at random.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import numpy as np

from ..matches import HNL, Match

MEETINGS_PER_PAIR = 4


@dataclass
class TableRow:
    team: str
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    gf: int = 0
    ga: int = 0

    @property
    def points(self) -> int:
        return 3 * self.won + self.drawn

    @property
    def gd(self) -> int:
        return self.gf - self.ga


def league_table(matches: list[Match], teams: list[str]) -> list[TableRow]:
    rows = {t: TableRow(t) for t in teams}
    for m in matches:
        if not m.finished or m.home not in rows or m.away not in rows:
            continue
        h, a = rows[m.home], rows[m.away]
        h.played += 1
        a.played += 1
        h.gf += m.home_goals
        h.ga += m.away_goals
        a.gf += m.away_goals
        a.ga += m.home_goals
        r = m.result()
        if r == "H":
            h.won += 1
            a.lost += 1
        elif r == "A":
            a.won += 1
            h.lost += 1
        else:
            h.drawn += 1
            a.drawn += 1
    order = list(rows)
    idx = {t: i for i, t in enumerate(order)}
    hp, hg = head_to_head(matches, idx)
    arr = lambda f: np.array([[f(rows[t]) for t in order]], float)
    alpha = np.array([[-k for k in range(len(order))]], float)  # final tiebreak: name order
    ranking = rank(arr(lambda r: r.points), arr(lambda r: r.gd), arr(lambda r: r.gf), hp[None], hg[None], alpha)
    return [rows[order[i]] for i in ranking[0]]


def head_to_head(matches: list[Match], idx: dict[str, int]) -> tuple[np.ndarray, np.ndarray]:
    """Points and goal difference of team i against team j: arrays [i, j]."""
    n = len(idx)
    hp = np.zeros((n, n))
    hg = np.zeros((n, n))
    for m in matches:
        if not m.finished or m.home not in idx or m.away not in idx:
            continue
        h, a = idx[m.home], idx[m.away]
        d = m.home_goals - m.away_goals
        hp[h, a] += 3 if d > 0 else (1 if d == 0 else 0)
        hp[a, h] += 3 if d < 0 else (1 if d == 0 else 0)
        hg[h, a] += d
        hg[a, h] -= d
    return hp, hg


def rank(pts, gd, gf, h2h_pts, h2h_gd, tiebreak) -> np.ndarray:
    """Rank teams in every simulation. Inputs are (S, n) except h2h arrays (S, n, n).

    Returns (S, n) team indices in final order (best first). The head-to-head
    criteria are computed over all clubs level on points with the team.
    """
    s_count, n = pts.shape
    tied = (pts[:, :, None] == pts[:, None, :]) & ~np.eye(n, dtype=bool)[None]
    hp = (h2h_pts * tied).sum(axis=2)
    hg = (h2h_gd * tied).sum(axis=2)
    sim = np.repeat(np.arange(s_count), n)
    order = np.lexsort((-tiebreak.ravel(), -gf.ravel(), -gd.ravel(), -hg.ravel(), -hp.ravel(), -pts.ravel(), sim))
    return order.reshape(s_count, n) % n


def remaining_fixtures(season_matches: list[Match], teams: list[str], season: str) -> list[Match]:
    """Scheduled matches plus generated placeholders for meetings not yet in the fixture list."""
    per_pair = MEETINGS_PER_PAIR // 2
    finished = Counter((m.home, m.away) for m in season_matches if m.finished)
    pending: dict[tuple, list[Match]] = {}
    for m in sorted(season_matches, key=lambda x: x.date):
        if not m.finished:
            pending.setdefault((m.home, m.away), []).append(m)
    out: list[Match] = []
    count = Counter(finished)
    for pair, ms in pending.items():
        # Keep at most the number of meetings still to be played (drops stale duplicates).
        keep = ms[-max(0, per_pair - finished[pair]):] if per_pair - finished[pair] > 0 else []
        out += keep
        count[pair] += len(keep)
    last_date = max((m.date for m in season_matches), default=f"{season[:4]}-12-31")
    for h in teams:
        for a in teams:
            if h == a:
                continue
            missing = per_pair - count[(h, a)]
            for _ in range(max(0, missing)):
                out.append(Match(competition=HNL, season=season, date=last_date, home=h, away=a,
                                 source="generated", round="?"))
    return out


def simulate_season(forecaster, season_matches: list[Match], teams: list[str], season: str,
                    factors=None, n_sims: int = 10000, seed: int = 7) -> dict:
    rng = np.random.default_rng(seed)
    table = league_table(season_matches, teams)
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    pts = np.tile(np.array([next(r.points for r in table if r.team == t) for t in teams], float), (n_sims, 1))
    gd = np.tile(np.array([next(r.gd for r in table if r.team == t) for t in teams], float), (n_sims, 1))
    gf = np.tile(np.array([next(r.gf for r in table if r.team == t) for t in teams], float), (n_sims, 1))
    hp0, hg0 = head_to_head(season_matches, idx)
    h2h_pts = np.tile(hp0, (n_sims, 1, 1))
    h2h_gd = np.tile(hg0, (n_sims, 1, 1))
    fixtures = remaining_fixtures(season_matches, teams, season)
    for m in fixtures:
        if m.home not in idx or m.away not in idx:
            continue
        mat = forecaster.matrix(m, factors)
        size = mat.shape[0]
        flat = mat.ravel()
        cdf = np.cumsum(flat)
        cdf /= cdf[-1]
        draws = np.searchsorted(cdf, rng.random(n_sims))
        hg, ag = draws // size, draws % size
        h, a = idx[m.home], idx[m.away]
        hpts = np.where(hg > ag, 3, np.where(hg == ag, 1, 0))
        apts = np.where(ag > hg, 3, np.where(hg == ag, 1, 0))
        pts[:, h] += hpts
        pts[:, a] += apts
        gd[:, h] += hg - ag
        gd[:, a] += ag - hg
        gf[:, h] += hg
        gf[:, a] += ag
        h2h_pts[:, h, a] += hpts
        h2h_pts[:, a, h] += apts
        h2h_gd[:, h, a] += hg - ag
        h2h_gd[:, a, h] += ag - hg
    order = rank(pts, gd, gf, h2h_pts, h2h_gd, rng.random((n_sims, n)))
    positions = np.empty_like(order)
    rows = np.arange(n_sims)[:, None]
    positions[rows, order] = np.arange(n)[None, :]
    pos_probs = np.zeros((n, n))
    for p in range(n):
        pos_probs[:, p] = (positions == p).mean(axis=0)
    result = []
    for t in teams:
        i = idx[t]
        r = next(r for r in table if r.team == t)
        result.append({
            "team": t,
            "played": r.played, "won": r.won, "drawn": r.drawn, "lost": r.lost,
            "gf": r.gf, "ga": r.ga, "gd": r.gd, "points": r.points,
            "exp_points": round(float(pts[:, i].mean()), 1),
            "points_p10": int(np.percentile(pts[:, i], 10)),
            "points_p90": int(np.percentile(pts[:, i], 90)),
            "exp_position": round(float(positions[:, i].mean() + 1), 2),
            "positions": [round(float(x), 4) for x in pos_probs[i]],
            "p_title": round(float(pos_probs[i, 0]), 4),
            "p_top2": round(float(pos_probs[i, :2].sum()), 4),
            "p_top4": round(float(pos_probs[i, :4].sum()), 4),
            "p_last": round(float(pos_probs[i, -1]), 4),
        })
    current = {r.team: k + 1 for k, r in enumerate(table)}
    for row in result:
        row["position"] = current[row["team"]]
    result.sort(key=lambda r: r["position"])
    return {"season": season, "n_sims": n_sims, "remaining": len(fixtures), "rows": result}
