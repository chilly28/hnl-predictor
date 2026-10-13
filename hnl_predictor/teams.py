"""Team name normalisation: map the spellings used by different sources to one id."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from dataclasses import dataclass, field
from pathlib import Path

import yaml

PREFIXES = {"nk", "hnk", "gnk", "fc", "fk", "sk", "hk", "hask", "cf", "ac", "afc", "sc", "ssc", "cd", "ud", "sv", "bk", "if", "ff", "kv", "rsc", "pfc", "sl", "sk", "bsc", "vfl", "vfb", "tsg", "ogc", "losc", "rc", "aik", "ks", "gnk", "cs", "csc"}


def strip_accents(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D").replace("ø", "o").replace("ß", "ss")
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def slugify(name: str) -> str:
    words = re.sub(r"[^a-z0-9]+", " ", strip_accents(name).lower()).split()
    words = [w for w in words if w not in PREFIXES] or words
    return "-".join(words)


@dataclass
class Team:
    id: str
    name: str
    short: str = ""
    city: str = ""
    country: str = "CRO"
    clubelo: str = ""
    aliases: list[str] = field(default_factory=list)


class TeamRegistry:
    """Resolves source names to canonical ids. Unknown teams are registered on the fly."""

    def __init__(self, teams: dict[str, Team] | None = None):
        self.teams: dict[str, Team] = dict(teams or {})
        self._lookup: dict[str, str] = {}
        for t in self.teams.values():
            self._index(t)

    def _index(self, t: Team) -> None:
        for alias in [t.id, t.name, *t.aliases]:
            self._lookup[slugify(alias)] = t.id

    @classmethod
    def load(cls, path: str | Path) -> "TeamRegistry":
        path = Path(path)
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
        teams = {}
        for tid, info in (raw or {}).items():
            teams[tid] = Team(
                id=tid,
                name=info.get("name", tid),
                short=info.get("short", ""),
                city=info.get("city", ""),
                country=info.get("country", "CRO"),
                clubelo=info.get("clubelo", ""),
                aliases=list(info.get("aliases", [])),
            )
        return cls(teams)

    def resolve(self, name: str, country: str | None = None) -> str:
        """Return the canonical id for a source name, registering unknown teams."""
        name = name.strip()
        m = re.match(r"^(.*?)\s*\(([A-Z]{3})\)$", name)
        if m:
            name, country = m.group(1), m.group(2)
        key = slugify(name)
        found = self._lookup.get(key)
        if found and (country is None or self.teams[found].country == country):
            return found
        if country == "UNK":
            # Country unknown (e.g. a failed lookup): reuse a known foreign club with the same name.
            for tid, t in self.teams.items():
                if t.country not in ("CRO", "UNK") and slugify(t.name) == key:
                    return tid
        country = country or "CRO"
        tid = key if country == "CRO" else f"{key}-{country.lower()}"
        if tid not in self.teams and country != "CRO":
            similar = self._similar_foreign(key, country)
            if similar:
                return similar
        if tid not in self.teams:
            t = Team(id=tid, name=name, short=_short(name), country=country)
            self.teams[tid] = t
            if country == "CRO":
                self._index(t)
        return tid

    def _similar_foreign(self, key: str, country: str) -> str | None:
        """Match spelling variants of a foreign club already known in the same country."""
        tokens = set(key.split("-"))
        best, best_score = None, 0.0
        for tid, t in self.teams.items():
            if t.country != country:
                continue
            other = tid.removesuffix(f"-{country.lower()}")
            otoks = set(other.split("-"))
            if tokens <= otoks or otoks <= tokens:
                score = 0.9
            elif other.startswith(key) or key.startswith(other):
                score = 0.88
            else:
                score = SequenceMatcher(None, key, other).ratio()
            if score > best_score:
                best, best_score = tid, score
        return best if best_score >= 0.85 else None

    def known_croatian(self, name: str) -> bool:
        tid = self._lookup.get(slugify(name))
        return bool(tid) and self.teams[tid].country == "CRO"

    def get(self, tid: str) -> Team:
        if tid not in self.teams:
            self.teams[tid] = Team(id=tid, name=tid.replace("-", " ").title(), short=_short(tid))
        return self.teams[tid]

    def is_croatian(self, tid: str) -> bool:
        return self.get(tid).country == "CRO"


def _short(name: str) -> str:
    words = [w for w in re.split(r"[^A-Za-z]+", strip_accents(name)) if w and w.lower() not in PREFIXES]
    if not words:
        return name[:3].upper()
    longest = max(words, key=len)
    return longest[:3].upper()
