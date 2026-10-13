"""Goal-difference weighted Elo ratings with home advantage.

Ratings are on the usual Elo scale (league average ~1500). A rating
difference ``dr`` (home rating + home advantage - away rating) maps to an
expected score ``1 / (1 + 10 ** (-dr / 400))``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..matches import Match


@dataclass
class EloParams:
    k: float = 22.0
    home_adv: float = 85.0
    initial: float = 1500.0
    promoted_offset: float = -60.0   # newcomers start below the league average
    season_regress: float = 0.25     # share pulled back to the mean between seasons


def expected_score(dr: float) -> float:
    return 1.0 / (1.0 + 10 ** (-dr / 400.0))


def goal_multiplier(gd: int) -> float:
    gd = abs(gd)
    if gd <= 1:
        return 1.0
    if gd == 2:
        return 1.5
    return (11.0 + gd) / 8.0


@dataclass
class EloModel:
    params: EloParams = field(default_factory=EloParams)
    ratings: dict[str, float] = field(default_factory=dict)
    history: dict[str, list[tuple[str, float]]] = field(default_factory=dict)
    last_played: dict[str, str] = field(default_factory=dict)
    _season: str | None = None

    def league_mean(self) -> float:
        recent = sorted(set(self.last_played.values()))[-2:]
        vals = [self.ratings[t] for t, s in self.last_played.items() if s in recent and t in self.ratings]
        if not vals:
            vals = list(self.ratings.values())
        return sum(vals) / len(vals) if vals else self.params.initial

    def rating(self, team: str) -> float:
        if team not in self.ratings:
            if self.ratings:
                self.ratings[team] = self.league_mean() + self.params.promoted_offset
            else:
                self.ratings[team] = self.params.initial
        return self.ratings[team]

    def _new_season(self, season: str) -> None:
        if self._season is not None and season != self._season and self.ratings:
            mean = self.league_mean()
            r = self.params.season_regress
            self.ratings = {t: v + r * (mean - v) for t, v in self.ratings.items()}
        self._season = season

    def diff(self, home: str, away: str, neutral: bool = False) -> float:
        hfa = 0.0 if neutral else self.params.home_adv
        return self.rating(home) + hfa - self.rating(away)

    def update(self, m: Match) -> None:
        if not m.finished:
            return
        self._new_season(m.season)
        dr = self.diff(m.home, m.away, m.neutral)
        exp = expected_score(dr)
        score = {"H": 1.0, "D": 0.5, "A": 0.0}[m.result()]
        delta = self.params.k * goal_multiplier(m.home_goals - m.away_goals) * (score - exp)
        self.ratings[m.home] += delta
        self.ratings[m.away] -= delta
        for t in (m.home, m.away):
            self.last_played[t] = m.season
            self.history.setdefault(t, []).append((m.date, round(self.ratings[t], 1)))

    def fit(self, matches: list[Match]) -> "EloModel":
        for m in sorted(matches, key=lambda x: (x.date, x.time)):
            self.update(m)
        return self

    def start_season(self, season: str) -> None:
        """Apply between-season regression when predicting a season with no results yet."""
        self._new_season(season)
