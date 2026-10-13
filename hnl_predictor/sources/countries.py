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


def country_code(name: str | None) -> str | None:
    if not name:
        return None
    return COUNTRY_CODES.get(name.strip())
