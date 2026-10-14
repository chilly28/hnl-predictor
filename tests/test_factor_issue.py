from pathlib import Path

import pytest
import yaml

from hnl_predictor.factor_issue import (FIELDS, parse_issue_body, render_issue_template, result_markdown,
                                        validate, write_factor)
from hnl_predictor.soft_factors import load_soft_factors
from hnl_predictor.teams import TeamRegistry

ROOT = Path(__file__).parent.parent


def body(**values):
    parts = []
    for key, label in FIELDS.items():
        parts.append(f"### {label}\n\n{values.get(key, '_No response_')}\n")
    return "\n".join(parts)


@pytest.fixture
def reg():
    return TeamRegistry.load(ROOT / "data" / "teams.yaml")


@pytest.fixture
def hnl_ids(reg):
    return {tid for tid, t in reg.teams.items() if t.country == "CRO"}


def test_parse_issue_body_maps_labels():
    f = parse_issue_body(body(team="Hajduk Split", type="injury – ozljeda / injury (max ±50)", adjustment="-25",
                              date="2026-10-15", note="Napadač ozlijeđen"))
    assert f["team"] == "Hajduk Split" and f["adjustment"] == "-25"
    assert f["until"] == "" and f["source"] == ""  # "_No response_" -> empty


def test_validate_good_entry(reg, hnl_ids):
    f = parse_issue_body(body(team="Hajduk Split", type="injury – ozljeda / injury (max ±50)", adjustment="−25",
                              date="15.10.2026.", until="2026-10-30", note="  Napadač   ozlijeđen ",
                              source="https://example.com/a"))
    r = validate(f, reg, hnl_ids, issue=7)
    assert r.ok, r.errors
    assert r.entry == {"team": "hajduk-split", "date": "2026-10-15", "until": "2026-10-30", "type": "injury",
                       "note": "Napadač ozlijeđen", "adjustment": -25, "source": "https://example.com/a", "issue": 7}


def test_validate_caps_and_errors(reg, hnl_ids):
    r = validate(parse_issue_body(body(team="Hajduk Split", type="media – mediji / media (max ±15)", adjustment="-40",
                                       date="2026-10-15", note="x")), reg, hnl_ids)
    assert r.ok and r.entry["adjustment"] == -15 and r.warnings
    bad = validate(parse_issue_body(body(team="Real Madrid", type="magic", adjustment="a lot", date="yesterday",
                                         until="2026-01-01", note="", source="not a link")), reg, hnl_ids)
    assert not bad.ok
    assert len(bad.errors) == 5  # club, date, type, note, adjustment
    assert "❌" in result_markdown(bad)


def test_write_factor_keeps_header_and_updates_same_issue(tmp_path, reg, hnl_ids):
    p = tmp_path / "soft_factors.yaml"
    p.write_text("# My comments\n# more\n\nfactors: []\n", encoding="utf-8")
    e1 = validate(parse_issue_body(body(team="Rijeka", type="coach_change – x", adjustment="15", date="2026-10-15",
                                        note='New coach: "bounce"')), reg, hnl_ids, issue=3).entry
    assert write_factor(p, e1) == "added"
    e2 = dict(e1, adjustment=10)
    assert write_factor(p, e2) == "updated"
    e3 = validate(parse_issue_body(body(team="Osijek", type="unrest – x", adjustment="-20", date="2026-10-16",
                                        note="Prosvjed navijača")), reg, hnl_ids, issue=4).entry
    write_factor(p, e3)
    text = p.read_text(encoding="utf-8")
    assert text.startswith("# My comments\n# more\n")
    data = yaml.safe_load(text)["factors"]
    assert [d["issue"] for d in data] == [3, 4] and data[0]["adjustment"] == 10
    assert data[0]["note"] == 'New coach: "bounce"'
    # The model loads the file.
    fs = load_soft_factors(p, resolve=reg.resolve)
    assert {f.team for f in fs} == {"rijeka", "osijek"}


def test_issue_template_matches_parser():
    tpl = yaml.safe_load(render_issue_template(["Hajduk Split", "Dinamo Zagreb"]))
    labels = {b["attributes"]["label"] for b in tpl["body"] if b["type"] != "markdown"}
    assert labels == set(FIELDS.values())
    clubs = next(b for b in tpl["body"] if b.get("id") == "team")["attributes"]["options"]
    assert clubs == ["Dinamo Zagreb", "Hajduk Split"]
