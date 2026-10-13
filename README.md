# HNL Prognoza / HNL Predictor

**🇭🇷 Hrvatski** · [🇬🇧 English below](#english)

Statističke prognoze utakmica **SuperSport HNL-a** i **hrvatskih klubova u europskim natjecanjima**
(Liga prvaka, Europska liga, Konferencijska liga, uključujući kvalifikacije). Prognoze se automatski
ažuriraju nakon svake utakmice.

🌐 **Stranica:** https://chilly28.github.io/hnl-predictor/ (radi kao aplikacija na Androidu: *Izbornik → Dodaj na početni zaslon*)

Što stranica prikazuje:

- **Utakmice:** vjerojatnosti 1 / X / 2, očekivani golovi, najvjerojatniji rezultati, više/manje 2,5, oba daju gol,
  i koji su „meki” faktori pomaknuli prognozu i za koliko.
- **Rezultati:** konačni rezultat uz prognozu koja je bila objavljena **prije** utakmice.
- **Tablica:** trenutni poredak + projekcija kraja sezone (10 000 Monte Carlo simulacija), vjerojatnost svakog mjesta.
- **Klub:** Elo rejting kroz vrijeme, forma, sljedeće utakmice, vjerojatnosti konačnog mjesta.
- **Europa:** utakmice hrvatskih klubova u Europi i usporedba snage liga.
- **Točnost:** javni backtest (Brier, log loss, RPS, kalibracija) na prošlim sezonama.

Samo analitika – **bez kladioničarskih oglasa i poveznica**.

## Kako radi prognoza

1. **Elo rejting** s prednošću domaćeg terena; promjena ovisi o gol-razlici, između sezona djelomičan povratak prema prosjeku.
2. **Dixon-Coles Poissonov model** (napad/obrana svakog kluba, vremenski ponderiran, korekcija niskih rezultata).
3. Oba modela se kombiniraju u očekivane golove → matrica rezultata → 1X2, rezultati, više/manje, BTTS.
4. **Europa:** zaseban hijerarhijski model (liga + klub) na svim UEFA klupskim utakmicama od 2011. stavlja sve lige na
   zajedničku skalu. Hrvatski klub = HNL prosjek na europskoj skali + njegova trenutna forma u HNL-u.
5. **Meki faktori** (trener, ozljede, mediji, prosvjedi…) – transparentan pomak u Elo bodovima s gornjim granicama.
6. **Backtest** „korak po korak”: za svaku utakmicu model vidi samo podatke prije nje. Parametri su podešeni samo na
   sezonama 2019-20 i 2023-24; ostale sezone su izvan uzorka.

## Izvori podataka i licence

| Izvor | Što | Licenca / uvjeti |
|---|---|---|
| [openfootball](https://github.com/openfootball) (`europe`, `champions-league`) | HNL 2018-19, 2019-20, 2023-24, 2024-25; sve UEFA klupske utakmice 2011–2026 | **CC0 1.0** (javno vlasništvo) – kopija u `data/raw/openfootball/` |
| [TheSportsDB](https://www.thesportsdb.com) | Aktualni raspored i rezultati: HNL (od 2020.), Europska i Konferencijska liga, Liga prvaka | Besplatni javni API ključ (`123`), podaci zajednice; koristimo ga nekomercijalno uz navođenje izvora i uz ograničenje brzine (≤ 30 zahtjeva/min) |

Ne koristimo plaćene podatke ni scraping stranica čiji uvjeti to zabranjuju.

## Tajni ključevi (GitHub Secrets)

**Nijedan nije potreban.** Sve radi s besplatnim izvorima.

Opcionalno: `THESPORTSDB_KEY` – ako ikad kupite TheSportsDB Patreon ključ (veća ograničenja), dodajte ga u
*Settings → Secrets and variables → Actions → New repository secret*.

## Kako dodati meki faktor

Uredite [`data/soft_factors.yaml`](data/soft_factors.yaml) (izravno na GitHubu: ikona olovke) i dodajte npr.:

```yaml
factors:
  - team: hajduk-split          # id kluba ili ime ("Hajduk Split")
    date: 2026-10-14            # od kada vrijedi
    until: 2026-10-30           # do kada (opcionalno, zadano 14 dana)
    type: injury                # coach_change | tactical | injury | suspension | media | unrest | fatigue | other
    note: "Prvi napadač ozlijeđen 2-3 tjedna"
    adjustment: -25             # Elo bodovi (+ jače, − slabije)
    source: https://...         # opcionalno
```

Granice po vrsti: trener ±40, taktika ±25, ozljeda ±50, suspenzija ±40, mediji ±15, nemiri ±40, umor ±25, ostalo ±25;
ukupno najviše ±80 po klubu i utakmici. 25 Elo bodova ≈ 3–4 postotna boda vjerojatnosti pobjede.
Nakon spremanja (commit) GitHub Actions automatski ponovno izračuna prognoze i objavi stranicu.
Automatski signali (npr. iz vijesti) mogu se kasnije dodavati kao JSON u `data/soft_factors_auto/`.

## Pokretanje lokalno

```bash
pip install -r requirements-dev.txt
python -m hnl_predictor update            # dohvati nove podatke (bez mreže: --offline)
python -m hnl_predictor build             # izračunaj prognoze → site/data/*.json
python -m http.server -d site 8000        # otvori http://localhost:8000
python -m pytest                          # testovi
python -m hnl_predictor backtest          # metrike točnosti
```

## Automatizacija

`.github/workflows/update.yml`: svaki sat (a na dane utakmica, čet–pon 15–23 UTC, svakih 20 min) dohvaća nove rezultate.
Stranica se ponovno gradi i objavljuje **samo ako su se podaci promijenili** (plus jednom dnevno, te nakon svake promjene
koda ili mekih faktora). Ručno: *Actions → Update forecasts → Run workflow* (opcija *full* = osvježi cijelu sezonu).

## Struktura

```
hnl_predictor/          Python paket (jezgra, bez UI-a – piše JSON, pogodan za buduće desktop/Android aplikacije)
  sources/              openfootball, TheSportsDB, HTTP pomoćnik
  model/                elo.py, goals.py (Dixon-Coles), europe.py, forecaster.py, simulate.py
  soft_factors.py       sloj mekih faktora
  backtest.py           walk-forward evaluacija
  update.py / build.py  dohvat podataka / izrada izlaza
data/                   matches.csv, teams.yaml, soft_factors.yaml, arhiva prognoza, sirovi podaci
site/                   statična web-stranica (PWA); site/data/*.json = javni „API”
tests/                  testovi modela i parsiranja
```

---

<a id="english"></a>
## 🇬🇧 English

Statistical forecasts for the Croatian top division (**SuperSport HNL**) and for **Croatian clubs in UEFA competitions**
(Champions League, Europa League, Conference League, including qualifying). Updated automatically after every match.

🌐 **Site:** https://chilly28.github.io/hnl-predictor/ (installable PWA on Android: *menu → Add to Home screen*)

Pages: upcoming matches (1X2, expected goals, likely scorelines, over/under 2.5, both teams to score, and which soft
factors moved the forecast), results vs. the **pre-match** forecast, league table with a Monte Carlo projection
(10,000 simulations), a page per club, Croatian clubs in Europe, and a public accuracy report. Croatian is the default
language; there is an English toggle. Analytics only – **no betting ads or bookmaker links**.

### How the forecasts work

1. **Elo ratings** with home advantage, goal-difference weighted, partial regression to the mean between seasons.
2. **Dixon-Coles Poisson model** (attack/defence per club, time-decayed, low-score correction), fitted with numpy only.
3. The two are blended in log-goal space → expected goals → scoreline matrix → 1X2, scores, O/U 2.5, BTTS.
4. **European matches:** a hierarchical country + club Poisson model fitted on every UEFA club match since 2011 puts all
   leagues on one scale (a data-driven analogue of UEFA coefficients). A Croatian club = the HNL average on that scale +
   its current HNL deviation (domestic form). This corrects for the fact that only the strongest HNL clubs play in Europe.
5. **Soft factors** – a transparent, capped Elo-point adjustment layer (coach changes, tactics, injuries, suspensions,
   media, unrest, fatigue). The site shows each factor's effect in percentage points.
6. **Walk-forward backtest**: every forecast uses only data from before the match. Parameters were tuned on 2019-20 and
   2023-24 only; all other seasons are out-of-sample. Results are published on the Accuracy page.

### Data sources and licences

| Source | What | Licence / terms |
|---|---|---|
| [openfootball](https://github.com/openfootball) | HNL 2018-19, 2019-20, 2023-24, 2024-25; all UEFA club matches 2011–2026 | **CC0 1.0** (public domain), cached in `data/raw/openfootball/` |
| [TheSportsDB](https://www.thesportsdb.com) | Current fixtures and results: HNL (2020–), Europa League, Conference League, Champions League | Free public API key (`123`), community data; used non-commercially with attribution and rate limiting (≤ 30 req/min) |

No paid data and no scraping of sites whose terms forbid it.

### Secrets

**None required.** Optional: `THESPORTSDB_KEY` (a TheSportsDB Patreon key, higher limits) under
*Settings → Secrets and variables → Actions*.

### Adding soft factors

Edit [`data/soft_factors.yaml`](data/soft_factors.yaml) (see the example in the file and the Croatian section above).
Caps per type: coach ±40, tactical ±25, injury ±50, suspension ±40, media ±15, unrest ±40, fatigue ±25, other ±25;
±80 total per team and match. Committing the file triggers a rebuild. Automatic signal providers can drop JSON files
into `data/soft_factors_auto/` (`SignalProvider` protocol in `hnl_predictor/soft_factors.py`).

### Run locally

```bash
pip install -r requirements-dev.txt
python -m hnl_predictor update     # fetch new data (--offline to skip network, --full for a full season refresh)
python -m hnl_predictor build      # fit models, write site/data/*.json
python -m http.server -d site 8000
python -m pytest
```

### Automation

`.github/workflows/update.yml` runs hourly and every 20 minutes during match windows (Thu–Mon 15–23 UTC). It rebuilds and
redeploys only when the data changed (plus once a day, and on code / soft-factor changes). Manual run:
*Actions → Update forecasts → Run workflow*. Within the GitHub free tier (public repository).

### Reusing the core

`hnl_predictor` is UI-agnostic and writes plain JSON (`site/data/*.json`: `upcoming`, `results`, `table`, `clubs`,
`europe`, `backtest`, `teams`, `meta`), so a desktop or Android app can consume the same files or import the package.

Licence: code MIT. Data: see sources above.
