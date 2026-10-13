import json
from pathlib import Path

import pytest

from hnl_predictor.matches import Match, merge_matches, read_matches, season_for, write_matches
from hnl_predictor.sources import thesportsdb
from hnl_predictor.sources.openfootball import parse_score, parse_text
from hnl_predictor.teams import TeamRegistry, slugify

FIX = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).parent.parent


@pytest.fixture
def reg():
    return TeamRegistry.load(ROOT / "data" / "teams.yaml")


def test_slugify_strips_prefixes_and_accents():
    assert slugify("HNK Šibenik") == "sibenik"
    assert slugify("GNK Dinamo Zagreb") == "dinamo-zagreb"
    assert slugify("NK Varaždin") == "varazdin"


def test_registry_aliases(reg):
    assert reg.resolve("HNK Hajduk Split") == "hajduk-split"
    assert reg.resolve("Hajduk Split (CRO)") == "hajduk-split"
    assert reg.resolve("NK Lokomotiva") == "lokomotiva-zagreb"
    assert reg.resolve("Slaven Belupo Koprivnica") == "slaven-belupo"


def test_registry_foreign_variants(reg):
    a = reg.resolve("AFC Ajax", "NED")
    assert a == "ajax-ned"
    assert reg.resolve("Ajax", "NED") == a
    assert reg.get(a).country == "NED"
    # Same name in another country is a different club.
    assert reg.resolve("Dinamo City (ALB)") != reg.resolve("Dinamo Minsk (BLR)")


@pytest.mark.parametrize("text,expected", [
    ("1-2 (1-0)", (1, 2, "")),
    ("0-0", (0, 0, "")),
    ("2-1 a.e.t. (1-1, 1-0)", (1, 1, "aet")),
    ("4-5 pen. 2-2 a.e.t. (2-2, 2-0)", (2, 2, "pen")),
    ("", (None, None, "")),
])
def test_parse_score_uses_90_minute_result(text, expected):
    assert parse_score(text) == expected


def test_parse_new_format(reg):
    ms = parse_text((FIX / "openfootball_new.txt").read_text(), "HNL", "2024-25", reg)
    assert len(ms) == 4
    first = ms[0]
    assert (first.home, first.away, first.home_goals, first.away_goals) == ("dinamo-zagreb", "istra-1961", 5, 0)
    assert first.date == "2024-08-02" and first.time == "21:00"
    assert ms[2].time == "21:00"  # time carried over from the previous line
    assert ms[2].home == "hajduk-split"
    # January belongs to the second calendar year of the season; no score -> scheduled
    assert ms[3].date == "2025-01-18" and not ms[3].finished


def test_parse_legacy_format(reg):
    ms = parse_text((FIX / "openfootball_old.txt").read_text(), "HNL", "2018-19", reg)
    assert [m.date for m in ms] == ["2018-07-27", "2018-07-28", "2019-02-16"]
    assert ms[0].home == "dinamo-zagreb" and ms[0].away == "rudes" and ms[0].result() == "D"
    assert ms[1].home_goals == 4 and ms[1].away == "inter-zapresic"
    assert not ms[2].finished


def test_parse_uefa_filters_croatian(reg):
    ms = parse_text((FIX / "openfootball_uefa.txt").read_text(), "UECL", "2025-26", reg, croatian_only=True)
    assert len(ms) == 2
    assert ms[0].away == "hajduk-split" and ms[0].home.endswith("-aze")
    assert (ms[1].home_goals, ms[1].away_goals) == (1, 1)
    assert ms[1].stage == "qualifying"


def test_thesportsdb_events(reg):
    data = json.loads((FIX / "thesportsdb_round.json").read_text())
    countries = thesportsdb.TeamCountryCache(Path("/nonexistent/cache.json"))
    countries.data = {"133600": "NED"}
    ms = [thesportsdb.event_to_match(e, reg, countries) for e in data["events"]]
    upcoming, finished, euro, postponed = ms
    assert upcoming.home == "rudes" and upcoming.status == "NS" and upcoming.season == "2026-27"
    assert upcoming.time == "18:00"  # 16:00 UTC -> 18:00 Zagreb (CEST)
    assert upcoming.round == "10. kolo"
    assert finished.home == "slaven-belupo" and finished.home_goals == 4 and finished.finished
    assert euro.competition == "UECL" and euro.away == "ajax-ned"
    assert postponed.status == "PST"


def test_merge_prefers_finished_and_priority():
    a = Match("HNL", "2026-27", "2026-10-16", "rudes", "rijeka", source="openfootball")
    b = Match("HNL", "2026-27", "2026-10-17", "rudes", "rijeka", 1, 2, "FT", source="thesportsdb")
    c = Match("HNL", "2026-27", "2027-03-01", "rudes", "rijeka", source="thesportsdb")  # second meeting
    merged = merge_matches([a], [b, c])
    assert len(merged) == 2
    assert any(m.finished and m.home_goals == 1 for m in merged)


def test_csv_roundtrip(tmp_path):
    m = Match("UECL", "2026-27", "2026-10-15", "hajduk-split", "ajax-ned", time="18:45", stage="league phase")
    n = Match("HNL", "2026-27", "2026-10-11", "slaven-belupo", "rijeka", 4, 1, "FT", neutral=True)
    write_matches(tmp_path / "m.csv", [m, n])
    back = read_matches(tmp_path / "m.csv")
    assert {x.id for x in back} == {m.id, n.id}
    f = next(x for x in back if x.finished)
    assert f.home_goals == 4 and f.neutral


def test_season_for():
    from datetime import date
    assert season_for(date(2026, 10, 13)) == "2026-27"
    assert season_for(date(2027, 3, 1)) == "2026-27"
    assert season_for(date(2026, 6, 30)) == "2025-26"
