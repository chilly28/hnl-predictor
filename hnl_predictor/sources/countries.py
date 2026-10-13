"""Country name -> three-letter code (as used by openfootball / UEFA)."""

from __future__ import annotations

COUNTRY_CODES = {
    "Albania": "ALB", "Andorra": "AND", "Armenia": "ARM", "Austria": "AUT", "Azerbaijan": "AZE",
    "Belarus": "BLR", "Belgium": "BEL", "Bosnia and Herzegovina": "BIH", "Bosnia-Herzegovina": "BIH",
    "Bulgaria": "BUL", "Croatia": "CRO", "Cyprus": "CYP", "Czech Republic": "CZE", "Czechia": "CZE",
    "Denmark": "DEN", "England": "ENG", "Estonia": "EST", "Faroe Islands": "FRO", "Finland": "FIN",
    "France": "FRA", "Georgia": "GEO", "Germany": "GER", "Gibraltar": "GIB", "Greece": "GRE",
    "Hungary": "HUN", "Iceland": "ISL", "Ireland": "IRL", "Republic of Ireland": "IRL", "Israel": "ISR",
    "Italy": "ITA", "Kazakhstan": "KAZ", "Kosovo": "KOS", "Latvia": "LVA", "Liechtenstein": "LIE",
    "Lithuania": "LTU", "Luxembourg": "LUX", "Malta": "MLT", "Moldova": "MDA", "Monaco": "MCO",
    "Montenegro": "MNE", "Netherlands": "NED", "Holland": "NED", "North Macedonia": "MKD",
    "Macedonia": "MKD", "Northern Ireland": "NIR", "Norway": "NOR", "Poland": "POL", "Portugal": "POR",
    "Romania": "ROU", "Russia": "RUS", "San Marino": "SMR", "Scotland": "SCO", "Serbia": "SRB",
    "Slovakia": "SVK", "Slovenia": "SVN", "Spain": "ESP", "Sweden": "SWE", "Switzerland": "SUI",
    "Turkey": "TUR", "Türkiye": "TUR", "Ukraine": "UKR", "Wales": "WAL",
}


_NORMALISED = {k.lower(): v for k, v in COUNTRY_CODES.items()}
_NORMALISED.update({
    "the netherlands": "NED", "nederland": "NED", "netherlands, the": "NED",
    "czech rep.": "CZE", "republic of moldova": "MDA", "moldova, republic of": "MDA",
    "bosnia & herzegovina": "BIH", "bosnia": "BIH", "fyr macedonia": "MKD", "republic of north macedonia": "MKD",
    "faroe isles": "FRO", "great britain": "ENG", "united kingdom": "ENG", "uk": "ENG",
    "turkiye": "TUR", "russian federation": "RUS",
})


def country_code(name: str | None) -> str | None:
    """Map a country name (several spellings) to a three-letter code; None if unknown."""
    if not name:
        return None
    key = " ".join(name.strip().lower().split())
    if key in _NORMALISED:
        return _NORMALISED[key]
    if key.startswith("the ") and key[4:] in _NORMALISED:
        return _NORMALISED[key[4:]]
    return None
