"""Add a soft factor from a GitHub issue form (so it can be done from a phone).

The issue form ``.github/ISSUE_TEMPLATE/soft_factor.yml`` produces a body like::

    ### Klub / Club

    Hajduk Split

    ### Vrsta / Type

    injury – ozljeda / injury

    ...

This module parses that body, validates every field and writes the factor into
``data/soft_factors.yaml``. The workflow that calls it only runs for issues
opened by the repository owner, and the body is treated as data only.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

from .soft_factors import TYPE_CAPS

TYPE_LABELS = {
    "injury": "ozljeda / injury", "suspension": "suspenzija / suspension", "coach_change": "promjena trenera / coach change",
    "tactical": "taktika / tactics", "unrest": "nemiri, prosvjedi / unrest, protests", "media": "mediji / media",
    "fatigue": "umor, raspored / fatigue, schedule", "other": "ostalo / other",
}
from .teams import TeamRegistry

# Issue-form field labels (must match .github/ISSUE_TEMPLATE/soft_factor.yml).
FIELDS = {
    "team": "Klub / Club",
    "type": "Vrsta / Type",
    "adjustment": "Pomak u Elo bodovima / Adjustment (Elo points)",
    "date": "Vrijedi od / From (YYYY-MM-DD)",
    "until": "Vrijedi do / Until (optional)",
    "note": "Kratka bilješka / Short note",
    "source": "Izvor / Source link (optional)",
}
NO_RESPONSE = {"", "_no response_", "none", "-"}
MAX_NOTE = 300
FIELD_ORDER = ["team", "date", "until", "type", "note", "adjustment", "source", "match", "confidence", "origin", "issue"]


@dataclass
class Result:
    ok: bool
    entry: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def parse_issue_body(body: str) -> dict[str, str]:
    """Map issue-form headings ("### Label") to their (stripped) values."""
    sections: dict[str, str] = {}
    current = None
    lines: list[str] = []
    for line in (body or "").replace("\r\n", "\n").split("\n"):
        if line.startswith("### "):
            if current is not None:
                sections[current] = "\n".join(lines).strip()
            current, lines = line[4:].strip(), []
        elif current is not None:
            lines.append(line)
    if current is not None:
        sections[current] = "\n".join(lines).strip()
    out = {}
    for key, label in FIELDS.items():
        value = sections.get(label, "")
        out[key] = "" if value.strip().lower() in NO_RESPONSE else value.strip()
    return out


def _parse_date(text: str) -> date:
    text = text.strip().rstrip(".")
    m = re.fullmatch(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", text)  # Croatian 14.10.2026.
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    return date.fromisoformat(text)


def validate(fields: dict[str, str], teams: TeamRegistry, hnl_ids: set[str], issue: int | None = None) -> Result:
    res = Result(ok=False)
    entry: dict = {}
    # Club
    team_raw = fields.get("team", "")
    tid = teams.resolve(team_raw, "CRO") if team_raw else ""
    if not team_raw or tid not in hnl_ids:
        res.errors.append(f"Nepoznat klub / unknown club: `{team_raw or '–'}`")
    entry["team"] = tid
    # Dates
    try:
        start = _parse_date(fields.get("date", ""))
        entry["date"] = start.isoformat()
    except ValueError:
        start = None
        res.errors.append(f"Neispravan datum / invalid date: `{fields.get('date') or '–'}` (YYYY-MM-DD)")
    if fields.get("until"):
        try:
            end = _parse_date(fields["until"])
            if start and end < start:
                res.errors.append("Datum završetka je prije početka / 'until' is before 'from'")
            entry["until"] = end.isoformat()
        except ValueError:
            res.errors.append(f"Neispravan datum završetka / invalid until date: `{fields['until']}`")
    # Type
    typ = re.split(r"[\s–—-]", fields.get("type", "").strip(), maxsplit=1)[0].lower()
    if typ not in TYPE_CAPS:
        res.errors.append(f"Nepoznata vrsta / unknown type: `{fields.get('type') or '–'}`")
    entry["type"] = typ
    # Note
    note = " ".join(fields.get("note", "").split())
    if not note:
        res.errors.append("Bilješka je obavezna / a short note is required")
    elif len(note) > MAX_NOTE:
        res.warnings.append(f"Bilješka skraćena na {MAX_NOTE} znakova / note shortened to {MAX_NOTE} characters")
        note = note[:MAX_NOTE].rstrip() + "…"
    entry["note"] = note
    # Adjustment
    raw_adj = fields.get("adjustment", "").replace("−", "-").replace(",", ".").replace(" ", "")
    try:
        adj = float(raw_adj)
        cap = TYPE_CAPS.get(typ, TYPE_CAPS["other"])
        if abs(adj) > cap:
            res.warnings.append(f"Pomak ograničen na ±{cap} za vrstu `{typ}` / capped to ±{cap}")
            adj = cap if adj > 0 else -cap
        if adj == 0:
            res.warnings.append("Pomak je 0 – faktor neće mijenjati prognozu / adjustment is 0, no effect")
        entry["adjustment"] = int(adj) if float(adj).is_integer() else round(adj, 1)
    except ValueError:
        res.errors.append(f"Pomak mora biti broj / adjustment must be a number: `{fields.get('adjustment') or '–'}`")
    # Source
    src = fields.get("source", "")
    if src:
        if re.match(r"^https?://\S+$", src):
            entry["source"] = src
        else:
            res.warnings.append("Izvor nije poveznica pa je izostavljen / source is not a link and was left out")
    if issue is not None:
        entry["issue"] = int(issue)
    res.entry = entry
    res.ok = not res.errors
    return res


def _format_entry(e: dict) -> str:
    lines = []
    keys = [k for k in FIELD_ORDER if k in e] + [k for k in e if k not in FIELD_ORDER]
    for i, k in enumerate(keys):
        v = e[k]
        if isinstance(v, str):
            # Quote strings that YAML could misread (dates stay readable unquoted).
            text = v if re.fullmatch(r"\d{4}-\d{2}-\d{2}|[a-z0-9_-]+", v) else json.dumps(v, ensure_ascii=False)
        elif hasattr(v, "isoformat"):
            text = v.isoformat()
        else:
            text = json.dumps(v)
        lines.append(f"{'  - ' if i == 0 else '    '}{k}: {text}")
    return "\n".join(lines)


def write_factor(path: Path, entry: dict) -> str:
    """Add (or replace, for the same issue number) a factor; keeps the file's header comments.

    Returns "added" or "updated".
    """
    text = path.read_text(encoding="utf-8") if path.exists() else "factors: []\n"
    m = re.search(r"^factors:.*$", text, flags=re.M)
    header = text[:m.start()] if m else text.rstrip("\n") + "\n\n"
    data = yaml.safe_load(text) or {}
    entries = list((data.get("factors") or []) if isinstance(data, dict) else data or [])
    status = "added"
    if entry.get("issue") is not None:
        for i, e in enumerate(entries):
            if isinstance(e, dict) and e.get("issue") == entry["issue"]:
                entries[i] = entry
                status = "updated"
                break
        else:
            entries.append(entry)
    else:
        entries.append(entry)
    body = "factors:\n" + "\n\n".join(_format_entry(e) for e in entries if isinstance(e, dict)) + "\n"
    new_text = header + body
    # Round-trip check: the file must still parse and contain the entry.
    parsed = yaml.safe_load(new_text)
    assert any(str(x.get("team")) == entry["team"] and str(x.get("note")) == entry["note"] for x in parsed["factors"])
    path.write_text(new_text, encoding="utf-8")
    return status


def result_markdown(res: Result, status: str | None = None) -> str:
    if res.ok:
        e = res.entry
        lines = [f"✅ Meki faktor {'ažuriran' if status == 'updated' else 'dodan'} / soft factor {status or 'added'}:",
                 "", "```yaml", _format_entry(e), "```", "",
                 "Prognoze se upravo ponovno računaju (≈ 3 min). / Forecasts are being rebuilt now (≈ 3 min)."]
    else:
        lines = ["❌ Faktor nije dodan / the factor was not added:", ""] + [f"- {x}" for x in res.errors]
        lines += ["", "Ispravite issue (Edit) i provjera će se ponoviti. / Edit the issue to try again."]
    if res.warnings:
        lines += ["", "Napomene / notes:"] + [f"- {w}" for w in res.warnings]
    return "\n".join(lines)


def render_issue_template(club_names: list[str]) -> str:
    """The GitHub issue form; regenerated each build so the club list follows the current season."""
    def q(x: str) -> str:
        return json.dumps(x, ensure_ascii=False)
    out = [
        'name: "Meki faktor / Soft factor"',
        'description: "Dodaj meki faktor koji pomiče prognozu (samo vlasnik repozitorija) / Add a soft factor (repository owner only)"',
        'title: "[Meki faktor] "',
        'labels: ["soft-factor"]',
        "# Generated by hnl_predictor/factor_issue.py – edit there.",
        "body:",
        "  - type: markdown",
        "    attributes:",
        "      value: |",
        "        Ispunite polja i spremite. Automatika provjerava unos, dodaje ga u `data/soft_factors.yaml`,",
        "        ponovno računa prognoze i zatvara issue. Pogreške dobivate kao komentar.",
        "        Fill in the fields and submit; a workflow validates the entry, adds it to `data/soft_factors.yaml`,",
        "        rebuilds the forecasts and closes the issue. Errors come back as a comment.",
        "",
        "        25 Elo bodova ≈ 3–4 postotna boda vjerojatnosti pobjede / 25 Elo points ≈ 3–4 percentage points of win probability.",
        "  - type: dropdown",
        "    id: team",
        "    attributes:",
        f"      label: {q(FIELDS['team'])}",
        "      options:",
        *[f"        - {q(n)}" for n in sorted(club_names)],
        "    validations:",
        "      required: true",
        "  - type: dropdown",
        "    id: type",
        "    attributes:",
        f"      label: {q(FIELDS['type'])}",
        "      options:",
        *[f"        - {q(f'{k} – {lab} (max ±{TYPE_CAPS[k]})')}" for k, lab in TYPE_LABELS.items()],
        "    validations:",
        "      required: true",
        "  - type: input",
        "    id: adjustment",
        "    attributes:",
        f"      label: {q(FIELDS['adjustment'])}",
        '      description: "Negativno = slabiji, pozitivno = jači / negative = weaker, positive = stronger. Npr. / e.g. -25"',
        '      placeholder: "-25"',
        "    validations:",
        "      required: true",
        "  - type: input",
        "    id: date",
        "    attributes:",
        f"      label: {q(FIELDS['date'])}",
        '      description: "Npr. / e.g. 2026-10-15 ili / or 15.10.2026."',
        '      placeholder: "2026-10-15"',
        "    validations:",
        "      required: true",
        "  - type: input",
        "    id: until",
        "    attributes:",
        f"      label: {q(FIELDS['until'])}",
        '      description: "Prazno = 14 dana / empty = 14 days"',
        "  - type: textarea",
        "    id: note",
        "    attributes:",
        f"      label: {q(FIELDS['note'])}",
        '      description: "Prikazuje se na stranici / shown on the website (max 300)"',
        '      placeholder: "Prvi napadač ozlijeđen 2-3 tjedna / First-choice striker out for 2-3 weeks"',
        "    validations:",
        "      required: true",
        "  - type: input",
        "    id: source",
        "    attributes:",
        f"      label: {q(FIELDS['source'])}",
        '      placeholder: "https://..."',
    ]
    return "\n".join(out) + "\n"
