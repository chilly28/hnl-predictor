/* HNL Prognoza – static single-page app. Reads JSON from data/ (written by the Python package). */
(() => {
  "use strict";

  // ------------------------------------------------------------------ i18n
  const I18N = {
    hr: {
      nav_matches: "Utakmice", nav_results: "Rezultati", nav_table: "Tablica", nav_europe: "Europa", nav_accuracy: "Točnost",
      upcoming_title: "Nadolazeće utakmice",
      upcoming_lead: "Vjerojatnosti ishoda iz statističkog modela (Elo + Dixon-Coles), uz vidljive „meke” faktore.",
      no_upcoming: "Trenutno nema rasporeda utakmica u sljedećih 45 dana.",
      results_title: "Rezultati i prognoze",
      results_lead: "Konačni rezultat uz prognozu koja je prethodila utakmici. Bez naknadnog uljepšavanja.",
      no_results: "Još nema odigranih utakmica s prognozom.",
      table_title: "Tablica i projekcija",
      table_lead: "Trenutni poredak i projekcija kraja sezone iz {n} simulacija ostatka prvenstva.",
      europe_title: "Hrvatski klubovi u Europi",
      europe_lead: "Snaga HNL klubova kalibrirana prema stranim protivnicima pomoću svih UEFA utakmica od 2011.",
      accuracy_title: "Koliko smo točni?",
      accuracy_lead: "Model se provjerava na prošlim sezonama tako da za svaku utakmicu koristi samo podatke prije nje.",
      about_title: "Kako radi prognoza",
      all: "Sve", hnl: "HNL", europe: "Europa",
      home: "Domaći", draw: "Neriješeno", away: "Gosti",
      h1: "1", hx: "X", h2: "2",
      xg: "Očekivani golovi", likely: "Najvjerojatniji", over25: "Više od 2,5", btts: "Oba daju gol",
      details: "Detalji", top_scores: "Najvjerojatniji rezultati", soft_factors: "Meki faktori",
      factor_effect: "utjecaj na pobjedu domaćih",
      no_factors: "Nema aktivnih mekih faktora.",
      base_model: "Samo statistika",
      with_factors: "S mekim faktorima",
      prematch: "prognoza prije utakmice", reconstructed: "rekonstruirano",
      reconstructed_help: "Rekonstruirano: model pokrenut samo s podacima dostupnima prije utakmice (prije nego što je stranica počela arhivirati prognoze).",
      hit: "✓ pogođen favorit", miss: "✗ favorit nije pobijedio",
      pos: "#", team: "Klub", pl: "U", w: "P", d: "N", l: "I", gd: "GR", pts: "Bod",
      exp_pts: "Oček. bod", p_title: "Prvak", p_top2: "Top 2", p_top4: "Top 4", p_last: "Zadnji",
      position_dist: "Vjerojatnost konačnog mjesta",
      sim_note: "Preostale utakmice simuliraju se iz modela; neobjavljeni termini dopunjuju se prema formatu 4 × 9 kola. Kod jednakog broja bodova odlučuje gol-razlika (službeno: međusobni susreti).",
      club_rating: "Elo rejting", rank: "rang u ligi", euro_strength: "Europska snaga",
      elo_history: "Kretanje Elo rejtinga", form: "Forma", next_matches: "Sljedeće utakmice", recent: "Zadnje utakmice",
      euro_matches: "Utakmice ove sezone", country_strength: "Snaga liga (europski model)",
      country_note: "Neto snaga u golovima po utakmici u odnosu na prosjek, iz svih UEFA utakmica (vremenski ponderirano). HNL prosjek je niži od hrvatskog prosjeka u Europi jer u Europi igraju najjači klubovi.",
      hnl_avg: "HNL prosjek", cro_euro: "Hrvatski klubovi u Europi",
      model: "Naš model", elo_only: "Samo Elo", dixon_coles_only: "Samo Dixon-Coles", base_rate: "Povijesni omjer 1/X/2", uniform: "Nasumično (⅓ svaki)",
      brier: "Brier", logloss: "Log loss", rps: "RPS", accuracy: "Pogođen favorit",
      lower_better: "manje je bolje", higher_better: "više je bolje",
      calibration: "Kalibracija", calibration_lead: "Kad model kaže 60 %, događa li se to u 60 % slučajeva? Točke na isprekidanoj liniji = savršena kalibracija.",
      forecast: "Prognoza", observed: "Ostvareno", n: "Broj",
      per_season: "Po sezonama", season: "Sezona", matches: "utakmica",
      tuned_note: "Parametri su podešeni samo na sezonama {s}; ostale su potpuno izvan uzorka.",
      table_view: "Prikaži kao tablicu",
      updated: "Ažurirano", last_result: "zadnji rezultat",
      disclaimer: "Samo analitika i zabava. Bez kladioničarskih oglasa i poveznica. Prognoze su vjerojatnosti, ne jamstva.",
      sources: "Izvori", method: "Metoda", install: "Instaliraj aplikaciju", install_text: "Dodaj HNL Prognozu na početni zaslon.",
      kickoff_tbc: "termin tbd", round: "kolo", vs: "–",
      offline: "Prikaz iz predmemorije (offline).",
      theme: "Tema",
      stage_qualifying: "kvalifikacije", "stage_league phase": "ligaška faza", stage_knockout: "nokaut faza", "stage_play-off": "doigravanje",
      comp_HNL: "SuperSport HNL", comp_UEL: "Europska liga", comp_UECL: "Konferencijska liga", comp_UCL: "Liga prvaka",
      learn_more: "Kako radi prognoza →",
      no_data: "Podaci još nisu dostupni.",
    },
    en: {
      nav_matches: "Matches", nav_results: "Results", nav_table: "Table", nav_europe: "Europe", nav_accuracy: "Accuracy",
      upcoming_title: "Upcoming matches",
      upcoming_lead: "Outcome probabilities from a statistical model (Elo + Dixon-Coles), with visible soft factors.",
      no_upcoming: "No fixtures scheduled in the next 45 days.",
      results_title: "Results vs. forecasts",
      results_lead: "Final scores next to the forecast made before the match. No retrospective polishing.",
      no_results: "No played matches with a forecast yet.",
      table_title: "Table & projection",
      table_lead: "Current standings and the projected final table from {n} simulations of the rest of the season.",
      europe_title: "Croatian clubs in Europe",
      europe_lead: "HNL club strength calibrated against foreign opponents using every UEFA match since 2011.",
      accuracy_title: "How accurate are we?",
      accuracy_lead: "The model is tested on past seasons using, for each match, only data available before it.",
      about_title: "How the forecasts work",
      all: "All", hnl: "HNL", europe: "Europe",
      home: "Home", draw: "Draw", away: "Away",
      h1: "1", hx: "X", h2: "2",
      xg: "Expected goals", likely: "Most likely", over25: "Over 2.5", btts: "Both score",
      details: "Details", top_scores: "Most likely scores", soft_factors: "Soft factors",
      factor_effect: "effect on home win",
      no_factors: "No active soft factors.",
      base_model: "Statistics only",
      with_factors: "With soft factors",
      prematch: "pre-match forecast", reconstructed: "reconstructed",
      reconstructed_help: "Reconstructed: the model re-run with only the data available before the match (from before the site started archiving forecasts).",
      hit: "✓ favourite won", miss: "✗ favourite did not win",
      pos: "#", team: "Club", pl: "P", w: "W", d: "D", l: "L", gd: "GD", pts: "Pts",
      exp_pts: "Exp. pts", p_title: "Title", p_top2: "Top 2", p_top4: "Top 4", p_last: "Last",
      position_dist: "Final position probabilities",
      sim_note: "Remaining matches are simulated from the model; unpublished dates are filled in from the 4 × 9 round format. Ties on points are broken by goal difference (officially: head-to-head).",
      club_rating: "Elo rating", rank: "league rank", euro_strength: "European strength",
      elo_history: "Elo rating over time", form: "Form", next_matches: "Next matches", recent: "Recent matches",
      euro_matches: "This season's matches", country_strength: "League strength (European model)",
      country_note: "Net strength in goals per match vs. average, from every UEFA match (time-weighted). The HNL average is below Croatia's European average because only the strongest clubs play in Europe.",
      hnl_avg: "HNL average", cro_euro: "Croatian clubs in Europe",
      model: "Our model", elo_only: "Elo only", dixon_coles_only: "Dixon-Coles only", base_rate: "Historical 1/X/2 rates", uniform: "Random (⅓ each)",
      brier: "Brier", logloss: "Log loss", rps: "RPS", accuracy: "Favourite won",
      lower_better: "lower is better", higher_better: "higher is better",
      calibration: "Calibration", calibration_lead: "When the model says 60%, does it happen 60% of the time? Points on the dashed line = perfect calibration.",
      forecast: "Forecast", observed: "Observed", n: "Count",
      per_season: "By season", season: "Season", matches: "matches",
      tuned_note: "Parameters were tuned on seasons {s} only; all other seasons are fully out-of-sample.",
      table_view: "Show as table",
      updated: "Updated", last_result: "last result",
      disclaimer: "Analytics and entertainment only. No betting ads or bookmaker links. Forecasts are probabilities, not guarantees.",
      sources: "Sources", method: "Method", install: "Install app", install_text: "Add HNL Prognoza to your home screen.",
      kickoff_tbc: "time tbc", round: "round", vs: "–",
      offline: "Showing cached data (offline).",
      theme: "Theme",
      stage_qualifying: "qualifying", "stage_league phase": "league phase", stage_knockout: "knockout", "stage_play-off": "play-off",
      comp_HNL: "SuperSport HNL", comp_UEL: "Europa League", comp_UECL: "Conference League", comp_UCL: "Champions League",
      learn_more: "How the forecasts work →",
      no_data: "Data not available yet.",
    },
  };
  const COUNTRY = {
    hr: { ENG: "Engleska", ITA: "Italija", ESP: "Španjolska", GER: "Njemačka", POR: "Portugal", FRA: "Francuska", NED: "Nizozemska", BEL: "Belgija", TUR: "Turska", GRE: "Grčka", AUT: "Austrija", SUI: "Švicarska", SCO: "Škotska", DEN: "Danska", NOR: "Norveška", SWE: "Švedska", CZE: "Češka", POL: "Poljska", CRO: "Hrvatska", SRB: "Srbija", UKR: "Ukrajina", RUS: "Rusija", CYP: "Cipar", HUN: "Mađarska", ROU: "Rumunjska", ISR: "Izrael", SVN: "Slovenija", SVK: "Slovačka", BUL: "Bugarska", AZE: "Azerbajdžan", MCO: "Monako", KAZ: "Kazahstan", BIH: "BiH", ALB: "Albanija", ARM: "Armenija", IRL: "Irska", ISL: "Island", LVA: "Latvija", MDA: "Moldavija", GEO: "Gruzija", MKD: "S. Makedonija", MNE: "Crna Gora", KOS: "Kosovo", FIN: "Finska", EST: "Estonija", LTU: "Litva", BLR: "Bjelorusija", NIR: "S. Irska", WAL: "Wales", LUX: "Luksemburg", MLT: "Malta", GIB: "Gibraltar", FRO: "Farski otoci", AND: "Andora", SMR: "San Marino", LIE: "Lihtenštajn" },
    en: { ENG: "England", ITA: "Italy", ESP: "Spain", GER: "Germany", POR: "Portugal", FRA: "France", NED: "Netherlands", BEL: "Belgium", TUR: "Turkey", GRE: "Greece", AUT: "Austria", SUI: "Switzerland", SCO: "Scotland", DEN: "Denmark", NOR: "Norway", SWE: "Sweden", CZE: "Czechia", POL: "Poland", CRO: "Croatia", SRB: "Serbia", UKR: "Ukraine", RUS: "Russia", CYP: "Cyprus", HUN: "Hungary", ROU: "Romania", ISR: "Israel", SVN: "Slovenia", SVK: "Slovakia", BUL: "Bulgaria", AZE: "Azerbaijan", MCO: "Monaco", KAZ: "Kazakhstan", BIH: "Bosnia & H.", ALB: "Albania", ARM: "Armenia", IRL: "Ireland", ISL: "Iceland", LVA: "Latvia", MDA: "Moldova", GEO: "Georgia", MKD: "N. Macedonia", MNE: "Montenegro", KOS: "Kosovo", FIN: "Finland", EST: "Estonia", LTU: "Lithuania", BLR: "Belarus", NIR: "N. Ireland", WAL: "Wales", LUX: "Luxembourg", MLT: "Malta", GIB: "Gibraltar", FRO: "Faroe Is.", AND: "Andorra", SMR: "San Marino", LIE: "Liechtenstein" },
  };
  const FACTOR_TYPES = {
    hr: { coach_change: "Promjena trenera", tactical: "Taktika", injury: "Ozljeda", suspension: "Suspenzija", media: "Mediji", unrest: "Nemiri / prosvjedi", fatigue: "Umor / raspored", other: "Ostalo" },
    en: { coach_change: "Coach change", tactical: "Tactics", injury: "Injury", suspension: "Suspension", media: "Media", unrest: "Unrest / protests", fatigue: "Fatigue / schedule", other: "Other" },
  };

  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : v; } catch { return d; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch { /* private mode */ } },
  };
  let lang = store.get("lang", "hr");  // Croatian is the default language
  if (!I18N[lang]) lang = "hr";
  const t = (k, vars) => {
    let s = (I18N[lang][k] ?? I18N.hr[k] ?? k);
    if (vars) for (const [a, b] of Object.entries(vars)) s = s.replace(`{${a}}`, b);
    return s;
  };

  // ------------------------------------------------------------------ data
  const FILES = ["meta", "teams", "upcoming", "results", "table", "clubs", "europe", "backtest"];
  const D = {};
  let offline = false;
  async function loadData() {
    await Promise.all(FILES.map(async (f) => {
      try {
        const r = await fetch(`data/${f}.json`, { cache: "no-cache" });
        if (!r.ok) throw new Error(r.status);
        D[f] = await r.json();
        if (r.headers.get("x-from-cache")) offline = true;
      } catch (e) {
        D[f] = null;
      }
    }));
  }

  // --------------------------------------------------------------- helpers
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pct = (p, digits = 0) => `${(p * 100).toFixed(digits)}%`;
  const locale = () => (lang === "hr" ? "hr-HR" : "en-GB");
  const team = (id) => (D.teams && D.teams[id]) || { id, name: id, short: id.slice(0, 3).toUpperCase(), country: "" };
  const isHnl = (id) => !!(D.teams && D.teams[id] && D.teams[id].hnl);
  const teamLink = (id) => {
    const tm = team(id);
    const name = esc(tm.name);
    const country = tm.country && tm.country !== "CRO" ? `<small>${esc(COUNTRY[lang][tm.country] || tm.country)}</small>` : "";
    return isHnl(id) ? `<a href="#/club/${encodeURIComponent(id)}">${name}</a>${country}` : `${name}${country}`;
  };
  const fmtDate = (iso, opts = { weekday: "long", day: "numeric", month: "long" }) => {
    const [y, m, d] = iso.split("-").map(Number);
    return new Intl.DateTimeFormat(locale(), opts).format(new Date(y, m - 1, d));
  };
  const shortDate = (iso) => fmtDate(iso, { day: "numeric", month: "short" });
  const compTag = (c) => `<span class="tag ${c === "HNL" ? "" : "eu"}">${esc(t("comp_" + c))}</span>`;
  const roundLabel = (m) => {
    if (m.competition === "HNL") return m.round ? esc(m.round.replace("kolo", t("round"))) : "";
    const st = m.stage ? t("stage_" + m.stage) : "";
    return esc(st);
  };
  const signed = (x, digits = 1) => `${x > 0 ? "+" : x < 0 ? "−" : "±"}${Math.abs(x).toFixed(digits)}`;

  // Tooltip shared by all charts.
  const tip = document.getElementById("tooltip");
  function showTip(html, x, y) {
    tip.innerHTML = html;
    tip.hidden = false;
    const r = tip.getBoundingClientRect();
    let left = x + 12, top = y - r.height - 10;
    if (left + r.width > window.innerWidth - 8) left = x - r.width - 12;
    if (top < 8) top = y + 14;
    tip.style.left = `${Math.max(8, left)}px`;
    tip.style.top = `${top}px`;
  }
  const hideTip = () => { tip.hidden = true; };
  document.addEventListener("scroll", hideTip, { passive: true });

  // ---------------------------------------------------------- components
  function probBar(prob, outcome) {
    const parts = [["h", prob.home, "H"], ["d", prob.draw, "D"], ["a", prob.away, "A"]];
    const bar = parts.map(([c, p, r]) =>
      `<span class="${c}${outcome === r ? " hit-outline" : ""}" style="flex-grow:${Math.max(p, 0.01)}" title="${pct(p)}"></span>`).join("");
    const labels = `
      <span><i class="sw" style="background:var(--home)"></i>${t("h1")} <b>${pct(prob.home)}</b></span>
      <span><i class="sw" style="background:var(--draw)"></i>${t("hx")} <b>${pct(prob.draw)}</b></span>
      <span><i class="sw" style="background:var(--away)"></i>${t("h2")} <b>${pct(prob.away)}</b></span>`;
    return `<div class="pbar" role="img" aria-label="${t("home")} ${pct(prob.home)}, ${t("draw")} ${pct(prob.draw)}, ${t("away")} ${pct(prob.away)}">${bar}</div>
            <div class="plabels">${labels}</div>`;
  }

  function factorList(factors, homeId) {
    if (!factors || !factors.length) return `<p class="note">${t("no_factors")}</p>`;
    return factors.map((f) => {
      const eff = f.effect ? f.effect.home : 0;
      const cls = eff > 0 ? "pos" : eff < 0 ? "neg" : "";
      const src = f.source ? ` · <a href="${esc(f.source)}" rel="noopener nofollow" target="_blank">${lang === "hr" ? "izvor" : "source"}</a>` : "";
      const auto = f.origin === "auto" ? ` <span class="tag">auto ${Math.round((f.confidence || 1) * 100)}%</span>` : "";
      return `<div class="factor">
        <b>${esc(team(f.team).name)}</b> · ${esc(FACTOR_TYPES[lang][f.type] || f.type)}${auto}<br>
        ${esc(f.note)}${src}<br>
        <span class="note">${signed(f.applied, 0)} Elo · ${t("factor_effect")}: <span class="delta ${cls}">${signed(eff * 100)} pp</span></span>
      </div>`;
    }).join("");
  }

  function matchCard(p, opts = {}) {
    const res = opts.result;
    const scoreMid = res ? `<span class="score">${res.score.home}:${res.score.away}</span>` : `<span class="vs">${esc(p.time || t("kickoff_tbc"))}</span>`;
    const meta = `<div class="match-meta"><span>${compTag(p.competition)} ${roundLabel(p)}</span>
      <span>${res ? `<span class="tag ${res.forecast_type === "reconstructed" ? "recon" : ""}" title="${esc(res.forecast_type === "reconstructed" ? t("reconstructed_help") : "")}">${t(res.forecast_type === "reconstructed" ? "reconstructed" : "prematch")}</span>` : (opts.showDate ? esc(shortDate(p.date)) : "")}</span></div>`;
    const top = (p.scores || [])[0];
    let facts = "";
    if (p.xg) {
      facts = `<div class="facts">
        <span>${t("xg")} <b>${p.xg.home.toFixed(1)} – ${p.xg.away.toFixed(1)}</b></span>
        ${top ? `<span>${t("likely")} <b>${esc(top.score.replace("-", ":"))}</b> (${pct(top.p)})</span>` : ""}
        ${p.over25 != null ? `<span>${t("over25")} <b>${pct(p.over25)}</b></span>` : ""}
        ${p.btts != null ? `<span>${t("btts")} <b>${pct(p.btts)}</b></span>` : ""}
      </div>`;
    }
    const nf = (p.factors || []).length;
    const detailBits = [];
    if (p.scores && p.scores.length) {
      detailBits.push(`<h3 style="margin-top:8px">${t("top_scores")}</h3><div class="scorelist">${p.scores.map((s) => `<span>${esc(s.score.replace("-", ":"))} · ${pct(s.p, 1)}</span>`).join("")}</div>`);
    }
    if (nf && p.base_prob) {
      detailBits.push(`<h3 style="margin-top:10px">${t("base_model")}</h3>${probBar(p.base_prob)}`);
    }
    detailBits.push(`<h3 style="margin-top:10px">${t("soft_factors")}${nf ? ` (${nf})` : ""}</h3>${factorList(p.factors, p.home)}`);
    if (p.elo) detailBits.push(`<p class="note">Elo: ${p.elo.home} – ${p.elo.away}</p>`);
    const flag = res ? `<div style="margin-top:6px" class="result-flag ${res.hit ? "ok" : "miss"}">${t(res.hit ? "hit" : "miss")}</div>` : "";
    return `<article class="card match">
      ${meta}
      <div class="teams"><div class="team">${teamLink(p.home)}</div>${scoreMid}<div class="team away">${teamLink(p.away)}</div></div>
      ${probBar(p.prob, res ? res.result : null)}
      ${flag}
      ${facts}
      <details class="more"><summary>${t("details")}${nf ? ` · ${t("soft_factors").toLowerCase()} ${nf}` : ""}</summary>${detailBits.join("")}</details>
    </article>`;
  }

  function groupByDate(items, render) {
    let html = "", last = null;
    for (const it of items) {
      if (it.date !== last) { html += `<div class="date-head">${esc(fmtDate(it.date))}</div>`; last = it.date; }
      html += `<div class="stack">${render(it)}</div>`;
    }
    return html;
  }

  function filterChips(current, onto) {
    const opts = [["all", t("all")], ["HNL", t("hnl")], ["EU", t("europe")]];
    return `<div class="chips" role="group">${opts.map(([v, l]) => `<button class="chip" data-filter="${v}" aria-pressed="${current === v}">${l}</button>`).join("")}</div>`;
  }
  const passFilter = (f, c) => f === "all" || (f === "HNL" ? c === "HNL" : c !== "HNL");

  // ------------------------------------------------------------- charts
  function lineChart(points, { width = Math.max(320, Math.min(820, (document.getElementById("app").clientWidth || 360) - 30)), height = 220, yLabel = "", fmtX = (x) => x, fmtY = (y) => y } = {}) {
    if (!points.length) return "";
    const pad = { l: 40, r: 12, t: 12, b: 26 };
    const xs = points.map((p) => p.x), ys = points.map((p) => p.y);
    const x0 = Math.min(...xs), x1 = Math.max(...xs);
    let y0 = Math.min(...ys), y1 = Math.max(...ys);
    const span = Math.max(y1 - y0, 40);
    y0 = Math.floor((y0 - span * 0.1) / 25) * 25; y1 = Math.ceil((y1 + span * 0.1) / 25) * 25;
    const X = (x) => pad.l + ((x - x0) / Math.max(x1 - x0, 1)) * (width - pad.l - pad.r);
    const Y = (y) => height - pad.b - ((y - y0) / Math.max(y1 - y0, 1)) * (height - pad.t - pad.b);
    const ticks = [];
    const step = (y1 - y0) / 4;
    for (let i = 0; i <= 4; i++) ticks.push(y0 + step * i);
    const grid = ticks.map((v) => `<line class="gridline" x1="${pad.l}" x2="${width - pad.r}" y1="${Y(v)}" y2="${Y(v)}"/><text x="${pad.l - 6}" y="${Y(v) + 4}" text-anchor="end">${Math.round(v)}</text>`).join("");
    // Break the line across long gaps (e.g. seasons missing from the data) instead of bridging them.
    const GAP = 120 * 86400000;
    const path = points.map((p, i) => `${i && p.x - points[i - 1].x < GAP ? "L" : "M"}${X(p.x).toFixed(1)},${Y(p.y).toFixed(1)}`).join("");
    const xt = [points[0], points[Math.floor(points.length / 2)], points[points.length - 1]]
      .map((p, i) => `<text x="${X(p.x)}" y="${height - 8}" text-anchor="${["start", "middle", "end"][i]}">${esc(fmtX(p.x))}</text>`).join("");
    const id = "c" + Math.random().toString(36).slice(2, 8);
    const svg = `<svg class="chart" id="${id}" viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(yLabel)}">
      ${grid}<line class="baseline" x1="${pad.l}" x2="${width - pad.r}" y1="${height - pad.b}" y2="${height - pad.b}"/>
      <path class="line" d="${path}"/>${xt}
      <line class="cross" x1="0" x2="0" y1="${pad.t}" y2="${height - pad.b}" visibility="hidden"/>
      <circle class="dot" r="4.5" visibility="hidden"/>
      <rect x="${pad.l}" y="0" width="${width - pad.l - pad.r}" height="${height}" fill="transparent"/>
    </svg>`;
    requestAnimationFrame(() => {
      const el = document.getElementById(id);
      if (!el) return;
      const cross = el.querySelector(".cross"), dot = el.querySelector(".dot");
      const move = (ev) => {
        const r = el.getBoundingClientRect();
        const sx = ((ev.clientX - r.left) / r.width) * width;
        let best = points[0];
        for (const p of points) if (Math.abs(X(p.x) - sx) < Math.abs(X(best.x) - sx)) best = p;
        cross.setAttribute("x1", X(best.x)); cross.setAttribute("x2", X(best.x)); cross.setAttribute("visibility", "visible");
        dot.setAttribute("cx", X(best.x)); dot.setAttribute("cy", Y(best.y)); dot.setAttribute("visibility", "visible");
        showTip(`<b>${esc(fmtY(best.y))}</b><br>${esc(fmtX(best.x))}${best.label ? "<br>" + esc(best.label) : ""}`, ev.clientX, ev.clientY);
      };
      const leave = () => { cross.setAttribute("visibility", "hidden"); dot.setAttribute("visibility", "hidden"); hideTip(); };
      el.addEventListener("pointermove", move);
      el.addEventListener("pointerdown", move);
      el.addEventListener("pointerleave", leave);
    });
    return svg;
  }

  function calibrationChart(allRows) {
    // Bins with very few forecasts are noise; they stay in the table view only.
    const rows = allRows.filter((r) => r.n >= 15);
    const W = 360, H = 300, pad = { l: 40, r: 14, t: 12, b: 34 };
    const X = (v) => pad.l + v * (W - pad.l - pad.r);
    const Y = (v) => H - pad.b - v * (H - pad.t - pad.b);
    const maxN = Math.max(...rows.map((r) => r.n));
    let g = "";
    for (let i = 0; i <= 5; i++) {
      const v = i / 5;
      g += `<line class="gridline" x1="${pad.l}" x2="${W - pad.r}" y1="${Y(v)}" y2="${Y(v)}"/>`;
      g += `<text x="${pad.l - 6}" y="${Y(v) + 4}" text-anchor="end">${Math.round(v * 100)}%</text>`;
      g += `<text x="${X(v)}" y="${H - pad.b + 16}" text-anchor="middle">${Math.round(v * 100)}%</text>`;
    }
    const id = "cal" + Math.random().toString(36).slice(2, 7);
    const dots = rows.map((r, i) => `<circle class="dot" data-i="${i}" cx="${X(r.forecast)}" cy="${Y(r.observed)}" r="${4 + 6 * Math.sqrt(r.n / maxN)}"/>`).join("");
    requestAnimationFrame(() => {
      const el = document.getElementById(id);
      if (!el) return;
      el.querySelectorAll("circle").forEach((c) => {
        const r = rows[+c.dataset.i];
        const h = (ev) => showTip(`${t("forecast")}: <b>${pct(r.forecast, 1)}</b><br>${t("observed")}: <b>${pct(r.observed, 1)}</b><br>${t("n")}: ${r.n}`, ev.clientX, ev.clientY);
        c.addEventListener("pointerenter", h); c.addEventListener("pointerdown", h); c.addEventListener("pointerleave", hideTip);
      });
    });
    return `<svg class="chart" id="${id}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${t("calibration")}" style="max-width:420px">
      ${g}<line class="baseline" x1="${pad.l}" x2="${W - pad.r}" y1="${Y(0)}" y2="${Y(0)}"/>
      <line class="ref" x1="${X(0)}" y1="${Y(0)}" x2="${X(1)}" y2="${Y(1)}"/>
      ${dots}
      <text x="${(pad.l + W - pad.r) / 2}" y="${H - 4}" text-anchor="middle">${t("forecast")}</text>
    </svg>`;
  }

  // --------------------------------------------------------------- views
  let filter = store.get("filter", "all");

  function viewUpcoming() {
    const list = (D.upcoming || []).filter((p) => passFilter(filter, p.competition));
    const body = list.length ? groupByDate(list, (p) => matchCard(p)) : `<div class="card empty">${t("no_upcoming")}</div>`;
    return `<div class="page-head"><h1>${t("upcoming_title")}</h1><p>${t("upcoming_lead")} <a href="#/about">${t("learn_more")}</a></p></div>
      ${filterChips(filter)}${body}`;
  }

  function viewResults() {
    const list = (D.results || []).filter((r) => passFilter(filter, r.competition));
    if (!list.length) return `<div class="page-head"><h1>${t("results_title")}</h1></div>${filterChips(filter)}<div class="card empty">${t("no_results")}</div>`;
    const idx = { H: "home", D: "draw", A: "away" };
    let brier = 0, hits = 0, ll = 0;
    for (const r of list) {
      const y = idx[r.result];
      for (const k of ["home", "draw", "away"]) brier += (r.prob[k] - (k === y ? 1 : 0)) ** 2;
      ll += -Math.log(Math.max(r.prob[y], 1e-9));
      if (r.hit) hits++;
    }
    const n = list.length;
    const stats = `<div class="stats">
      <div class="stat"><div class="label">${t("matches")}</div><div class="value">${n}</div></div>
      <div class="stat"><div class="label">${t("accuracy")}</div><div class="value">${pct(hits / n)}</div><div class="sub">${t("higher_better")}</div></div>
      <div class="stat"><div class="label">${t("brier")}</div><div class="value">${(brier / n).toFixed(3)}</div><div class="sub">${t("lower_better")} · ⅓/⅓/⅓ = 0.667</div></div>
      <div class="stat"><div class="label">${t("logloss")}</div><div class="value">${(ll / n).toFixed(3)}</div><div class="sub">${t("lower_better")} · 1.099</div></div>
    </div>`;
    const body = groupByDate(list, (r) => matchCard(r, { result: r }));
    return `<div class="page-head"><h1>${t("results_title")}</h1><p>${t("results_lead")}</p></div>${filterChips(filter)}${stats}${body}`;
  }

  function heatCell(p) {
    const a = Math.min(1, p * 1.6);
    const txt = p >= 0.995 ? "100" : p >= 0.005 ? Math.round(p * 100) : "";
    const ink = a > 0.55 ? "#fff" : "var(--ink-2)";
    return `<td class="heat" style="background:rgba(var(--seq),${a.toFixed(3)});color:${ink}" title="${pct(p, 1)}">${txt}</td>`;
  }

  function viewTable() {
    const tb = D.table;
    if (!tb || !tb.rows) return `<div class="card empty">${t("no_data")}</div>`;
    const rows = tb.rows.map((r) => `<tr>
      <td>${r.position}</td>
      <td class="team-cell sticky-col">${teamLink(r.team)}</td>
      <td>${r.played}</td><td>${r.won}</td><td>${r.drawn}</td><td>${r.lost}</td>
      <td>${r.gd > 0 ? "+" : ""}${r.gd}</td><td><b>${r.points}</b></td>
      <td>${r.exp_points.toFixed(0)}<small style="color:var(--muted)"> ${r.points_p10}–${r.points_p90}</small></td>
      <td>${pct(r.p_title)}</td><td>${pct(r.p_top2)}</td><td>${pct(r.p_top4)}</td><td>${pct(r.p_last)}</td>
    </tr>`).join("");
    const n = tb.rows.length;
    const heads = Array.from({ length: n }, (_, i) => `<th style="text-align:center">${i + 1}.</th>`).join("");
    const byExp = [...tb.rows].sort((a, b) => a.exp_position - b.exp_position);
    const heat = byExp.map((r) => `<tr><td class="team-cell sticky-col">${teamLink(r.team)}</td>${r.positions.map(heatCell).join("")}</tr>`).join("");
    return `<div class="page-head"><h1>${t("table_title")}</h1><p>${t("table_lead", { n: (tb.n_sims || 0).toLocaleString(locale()) })}</p></div>
      <div class="table-wrap"><table>
        <thead><tr><th>${t("pos")}</th><th class="sticky-col">${t("team")}</th><th>${t("pl")}</th><th>${t("w")}</th><th>${t("d")}</th><th>${t("l")}</th><th>${t("gd")}</th><th>${t("pts")}</th>
        <th>${t("exp_pts")}</th><th>${t("p_title")}</th><th>${t("p_top2")}</th><th>${t("p_top4")}</th><th>${t("p_last")}</th></tr></thead>
        <tbody>${rows}</tbody></table></div>
      <div class="section"><h2>${t("position_dist")}</h2><span class="hint">%</span></div>
      <div class="table-wrap"><table><thead><tr><th class="sticky-col">${t("team")}</th>${heads}</tr></thead><tbody>${heat}</tbody></table></div>
      <p class="note">${t("sim_note")}</p>`;
  }

  function viewClub(id) {
    const c = D.clubs && D.clubs[id];
    const tm = team(id);
    if (!c) return `<div class="card empty">${t("no_data")}</div>`;
    const row = D.table && D.table.rows ? D.table.rows.find((r) => r.team === id) : null;
    const pts = c.elo_history.map((h) => ({ x: Date.parse(h.date), y: h.elo }));
    const chart = lineChart(pts, {
      yLabel: t("elo_history"),
      fmtX: (x) => new Intl.DateTimeFormat(locale(), { month: "short", year: "numeric" }).format(new Date(x)),
      fmtY: (y) => `Elo ${Math.round(y)}`,
    });
    const form = c.form.map((f) => `<span class="${f.r}" title="${esc(team(f.opp).name)} ${f.score}">${lang === "hr" ? { W: "P", D: "N", L: "I" }[f.r] : f.r}</span>`).join("");
    const next = (D.upcoming || []).filter((p) => p.home === id || p.away === id).slice(0, 4);
    const recent = (D.results || []).filter((r) => r.home === id || r.away === id).slice(0, 4);
    const dist = row ? row.positions.map((p, i) => `<div class="hbar-row hl"><span class="lbl">${i + 1}.</span><span class="track"><span class="fill" style="display:block;width:${(p * 100).toFixed(1)}%"></span></span><span class="val">${pct(p)}</span></div>`).join("") : "";
    const factors = (c.factors || []).length ? factorList(c.factors.map((f) => ({ ...f, applied: f.adjustment }))) : `<p class="note">${t("no_factors")}</p>`;
    return `<div class="page-head club-head"><div class="crest">${esc(tm.short)}</div><div><h1>${esc(tm.name)}</h1>
        <p class="note" style="margin:2px 0 0">${t("club_rating")} <b>${c.elo}</b> · ${c.elo_rank}. ${t("rank")}${c.euro_strength != null ? ` · ${t("euro_strength")} ${signed(c.euro_strength, 2)}` : ""}</p></div></div>
      <div class="stats">
        ${row ? `<div class="stat"><div class="label">${t("pts")}</div><div class="value">${row.points}</div><div class="sub">${row.position}. · ${row.played} ${t("pl")}</div></div>
        <div class="stat"><div class="label">${t("exp_pts")}</div><div class="value">${row.exp_points.toFixed(0)}</div><div class="sub">${row.points_p10}–${row.points_p90}</div></div>
        <div class="stat"><div class="label">${t("p_title")}</div><div class="value">${pct(row.p_title)}</div></div>
        <div class="stat"><div class="label">${t("p_last")}</div><div class="value">${pct(row.p_last)}</div></div>` : ""}
      </div>
      <div class="section"><h2>${t("form")}</h2></div><div class="form">${form}</div>
      <div class="section"><h2>${t("elo_history")}</h2></div><div class="card">${chart}</div>
      ${next.length ? `<div class="section"><h2>${t("next_matches")}</h2></div><div class="stack">${next.map((p) => matchCard(p, { showDate: true })).join("")}</div>` : ""}
      ${dist ? `<div class="section"><h2>${t("position_dist")}</h2></div><div class="card">${dist}</div>` : ""}
      <div class="section"><h2>${t("soft_factors")}</h2></div>${factors}
      ${recent.length ? `<div class="section"><h2>${t("recent")}</h2></div><div class="stack">${recent.map((r) => matchCard(r, { result: r })).join("")}</div>` : ""}`;
  }

  function viewEurope() {
    const e = D.europe;
    if (!e) return `<div class="card empty">${t("no_data")}</div>`;
    const ms = [...e.matches].sort((a, b) => (a.date < b.date ? 1 : -1));
    const cards = ms.map((m) => {
      if (m.forecast && m.forecast.xg) return matchCard(m.forecast, { showDate: true });
      const res = m.score ? { score: m.score, result: m.score.home > m.score.away ? "H" : m.score.home < m.score.away ? "A" : "D",
        forecast_type: (m.forecast && m.forecast.forecast_type) || "reconstructed", hit: m.forecast ? (() => { const p = m.forecast.prob; const fav = Object.keys(p).reduce((a, b) => (p[a] >= p[b] ? a : b)); return { home: "H", draw: "D", away: "A" }[fav] === (m.score.home > m.score.away ? "H" : m.score.home < m.score.away ? "A" : "D"); })() : false } : null;
      if (m.forecast && res) return matchCard({ ...m, prob: m.forecast.prob }, { result: res });
      return `<article class="card match"><div class="match-meta"><span>${compTag(m.competition)} ${roundLabel(m)}</span><span>${esc(shortDate(m.date))}</span></div>
        <div class="teams"><div class="team">${teamLink(m.home)}</div><span class="score">${m.score ? `${m.score.home}:${m.score.away}` : "–"}</span><div class="team away">${teamLink(m.away)}</div></div></article>`;
    }).join("");
    const countries = [...(e.countries || [])];
    const all = [...countries, { country: "HNL", strength: e.hnl_average_strength, hnl: true }].sort((a, b) => b.strength - a.strength);
    const lo = Math.min(...all.map((c) => c.strength), 0), hi = Math.max(...all.map((c) => c.strength));
    const bars = all.map((c) => {
      const w = ((c.strength - lo) / (hi - lo || 1)) * 100;
      const name = c.hnl ? t("hnl_avg") : (c.country === "CRO" ? t("cro_euro") : (COUNTRY[lang][c.country] || c.country));
      const cls = c.hnl ? "hl2" : c.country === "CRO" ? "hl" : "";
      return `<div class="hbar-row ${cls}" title="${esc(name)}: ${signed(c.strength, 2)}"><span class="lbl">${esc(name)}</span><span class="track"><span class="fill" style="display:block;width:${Math.max(w, 1).toFixed(1)}%"></span></span><span class="val">${signed(c.strength, 2)}</span></div>`;
    }).join("");
    const clubs = (e.clubs || []).map((c) => `<span class="tag" style="margin:2px">${esc(team(c.id).name)} ${signed(c.euro_strength, 2)}</span>`).join("");
    return `<div class="page-head"><h1>${t("europe_title")}</h1><p>${t("europe_lead")}</p></div>
      ${clubs ? `<div class="chips">${clubs}</div>` : ""}
      <div class="section"><h2>${t("euro_matches")} ${esc(e.season || "")}</h2></div>
      <div class="stack">${cards || `<div class="card empty">${t("no_upcoming")}</div>`}</div>
      <div class="section"><h2>${t("country_strength")}</h2></div>
      <div class="card">${bars}<div class="legend"><span><i style="background:var(--home)"></i>${t("cro_euro")}</span><span><i style="background:var(--away)"></i>${t("hnl_avg")}</span></div>
      <p class="note">${t("country_note")}</p></div>`;
  }

  function viewAccuracy() {
    const b = D.backtest;
    if (!b || !b.models) return `<div class="card empty">${t("no_data")}</div>`;
    const order = ["model", "elo_only", "dixon_coles_only", "base_rate", "uniform"];
    const best = Math.min(...order.map((k) => b.models[k].rps));
    const rows = order.map((k) => {
      const m = b.models[k];
      return `<tr${k === "model" ? ' style="font-weight:700"' : ""}><td>${t(k)}</td><td>${m.rps.toFixed(4)}</td><td>${m.brier.toFixed(4)}</td><td>${m.logloss.toFixed(4)}</td><td>${pct(m.accuracy, 1)}</td></tr>`;
    }).join("");
    const m = b.models.model;
    const seasons = Object.entries(b.per_season || {}).map(([s, v]) =>
      `<tr><td>${esc(s)}${(b.tuned_on || []).includes(s) ? " *" : ""}</td><td>${v.model.n}</td><td>${v.model.rps.toFixed(4)}</td><td>${v.uniform.rps.toFixed(4)}</td><td>${v.model.brier.toFixed(4)}</td><td>${pct(v.model.accuracy, 1)}</td></tr>`).join("");
    const cal = b.calibration || [];
    const calTable = cal.map((r) => `<tr><td>${esc(r.bin)}</td><td>${pct(r.forecast, 1)}</td><td>${pct(r.observed, 1)}</td><td>${r.n}</td></tr>`).join("");
    const gain = (1 - m.rps / b.models.uniform.rps) * 100;
    return `<div class="page-head"><h1>${t("accuracy_title")}</h1><p>${t("accuracy_lead")}</p></div>
      <div class="stats">
        <div class="stat"><div class="label">${t("matches")}</div><div class="value">${m.n}</div><div class="sub">${(b.seasons || []).join(", ")}</div></div>
        <div class="stat"><div class="label">RPS</div><div class="value">${m.rps.toFixed(3)}</div><div class="sub">${t("lower_better")} · ${signed(-gain, 0)}% vs ⅓</div></div>
        <div class="stat"><div class="label">${t("brier")}</div><div class="value">${m.brier.toFixed(3)}</div><div class="sub">${t("lower_better")}</div></div>
        <div class="stat"><div class="label">${t("accuracy")}</div><div class="value">${pct(m.accuracy)}</div><div class="sub">${t("higher_better")}</div></div>
      </div>
      <div class="section"><h2>${t("model")} vs. baseline</h2></div>
      <div class="table-wrap"><table><thead><tr><th></th><th>RPS</th><th>${t("brier")}</th><th>${t("logloss")}</th><th>${t("accuracy")}</th></tr></thead><tbody>${rows}</tbody></table></div>
      <p class="note">RPS = ranked probability score; Brier = (p−o)² ${lang === "hr" ? "zbrojeno preko 1/X/2" : "summed over 1/X/2"}. ${t("tuned_note", { s: (b.tuned_on || []).join(", ") })}</p>
      <div class="section"><h2>${t("calibration")}</h2></div>
      <div class="card"><p class="note" style="margin-top:0">${t("calibration_lead")}</p>${calibrationChart(cal)}
        <details class="more"><summary>${t("table_view")}</summary><div class="table-wrap" style="margin-top:8px"><table><thead><tr><th>bin</th><th>${t("forecast")}</th><th>${t("observed")}</th><th>${t("n")}</th></tr></thead><tbody>${calTable}</tbody></table></div></details>
      </div>
      <div class="section"><h2>${t("per_season")}</h2></div>
      <div class="table-wrap"><table><thead><tr><th>${t("season")}</th><th>n</th><th>RPS</th><th>RPS ⅓</th><th>${t("brier")}</th><th>${t("accuracy")}</th></tr></thead><tbody>${seasons}</tbody></table></div>
      <p class="note">* ${t("tuned_note", { s: (b.tuned_on || []).join(", ") })}</p>`;
  }

  function viewAbout() {
    const meta = D.meta || {};
    const src = (meta.sources || []).map((s) => `<li><a href="${esc(s.url)}" rel="noopener" target="_blank">${esc(s.name)}</a> — ${esc(s.licence)}. ${esc(s.use)}</li>`).join("");
    const mm = meta.model || {};
    const hr = lang === "hr";
    return `<div class="page-head"><h1>${t("about_title")}</h1></div><div class="card prose">
      ${hr ? `
      <h2>1. Snaga momčadi</h2>
      <p><b>Elo rejting</b> (K = ${mm.elo_k}, prednost domaćeg terena ${mm.elo_home_advantage} bodova) mijenja se nakon svake utakmice, više kod uvjerljivijih pobjeda. Između sezona rejting se djelomično vraća prema prosjeku; novi klubovi kreću ispod prosjeka lige.</p>
      <p><b>Dixon-Coles Poissonov model</b> procjenjuje napadačku i obrambenu snagu svakog kluba iz golova, s vremenskim ponderom (novije utakmice vrijede više) i korekcijom za rezultate 0:0, 1:0, 0:1 i 1:1.</p>
      <p>Prognoza kombinira oba modela (težina Dixon-Colesa ${mm.blend_dc_weight}). Iz očekivanih golova dobivamo cijelu matricu rezultata: 1X2, najvjerojatnije rezultate, više/manje 2,5 i oba daju gol.</p>
      <h2>2. Europske utakmice</h2>
      <p>HNL rejting ne kaže ništa o tome koliko je Hajduk jak protiv, recimo, Ajaxa. Zato imamo zaseban <b>europski model</b> na svim UEFA klupskim utakmicama od 2011.: snaga svake lige i svakog kluba na zajedničkoj skali. Hrvatski klub dobiva europsku snagu = prosjek HNL-a na europskoj skali + njegovo trenutačno odstupanje od HNL prosjeka (aktualna forma).</p>
      <h2>3. Meki faktori</h2>
      <p>Statistika ne vidi smjenu trenera, ozljedu ključnog igrača, medijski pritisak ili prosvjede navijača. Takve informacije upisuju se u <code>data/soft_factors.yaml</code> kao pomak u Elo bodovima s gornjom granicom po vrsti (npr. ozljeda ±50, mediji ±15, ukupno ±80). Svaka utakmica prikazuje koji je faktor pomaknuo prognozu i za koliko postotnih bodova. Sustav je pripremljen za automatske signale (npr. iz vijesti) u <code>data/soft_factors_auto/</code>.</p>
      <h2>4. Projekcija tablice</h2>
      <p>Ostatak sezone simulira se ${(mm.simulations || 10000).toLocaleString(locale())} puta iz prognoza pojedinih utakmica.</p>
      <h2>5. Poštenost</h2>
      <p>Točnost objavljujemo na stranici <a href="#/accuracy">Točnost</a>. Za odigrane utakmice prikazujemo prognozu spremljenu prije početka; starije su rekonstruirane bez gledanja u budućnost i jasno označene.</p>
      <h2>Automatsko ažuriranje</h2>
      <p>GitHub Actions svaki sat (na dane utakmica svakih 20 minuta) provjerava nove rezultate, ponovno računa rejtinge i objavljuje stranicu samo kad se nešto promijenilo.</p>`
      : `
      <h2>1. Team strength</h2>
      <p>An <b>Elo rating</b> (K = ${mm.elo_k}, home advantage ${mm.elo_home_advantage} points) updates after every match, more for convincing wins. Ratings partly regress to the mean between seasons; newcomers start below the league average.</p>
      <p>A <b>Dixon-Coles Poisson model</b> estimates every club's attacking and defensive strength from goals, time-weighted (recent matches count more) and corrected for 0-0, 1-0, 0-1 and 1-1 scores.</p>
      <p>The forecast blends both models (Dixon-Coles weight ${mm.blend_dc_weight}). Expected goals give the full scoreline matrix: 1X2, most likely scores, over/under 2.5 and both teams to score.</p>
      <h2>2. European matches</h2>
      <p>An HNL rating says nothing about how strong Hajduk is against, say, Ajax. A separate <b>European model</b> fitted on every UEFA club match since 2011 puts every league and club on one scale. A Croatian club's European strength = the HNL average on that scale + its current deviation from the HNL average (current form).</p>
      <h2>3. Soft factors</h2>
      <p>Statistics cannot see a coach being sacked, a key injury, media pressure or fan protests. Such information goes into <code>data/soft_factors.yaml</code> as an Elo-point shift, capped per type (e.g. injury ±50, media ±15, total ±80). Every match shows which factor moved the forecast and by how many percentage points. The system is ready for automatic (e.g. news-based) signals in <code>data/soft_factors_auto/</code>.</p>
      <h2>4. Table projection</h2>
      <p>The rest of the season is simulated ${(mm.simulations || 10000).toLocaleString(locale())} times from the match forecasts.</p>
      <h2>5. Honesty</h2>
      <p>Accuracy is published on the <a href="#/accuracy">Accuracy</a> page. For played matches we show the forecast stored before kick-off; older ones are reconstructed without looking ahead and clearly labelled.</p>
      <h2>Automatic updates</h2>
      <p>GitHub Actions checks for new results every hour (every 20 minutes on match days), refits the ratings and redeploys the site only when something changed.</p>`}
      <h2>${t("sources")}</h2><ul>${src}</ul>
      <p class="note">${t("disclaimer")}</p>
      <p class="note"><a href="https://github.com/chilly28/hnl-predictor" rel="noopener" target="_blank">GitHub</a> · data/*.json API</p>
    </div>`;
  }

  // -------------------------------------------------------------- router
  const ICONS = {
    matches: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="3" y="5" width="18" height="16" rx="3"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>',
    results: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12l5 5L20 6"/></svg>',
    table: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M4 6h16M4 12h16M4 18h16"/></svg>',
    europe: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18"/></svg>',
    accuracy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5" fill="currentColor"/></svg>',
    sun: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
    moon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M20 14.5A8 8 0 019.5 4a8 8 0 1010.5 10.5z"/></svg>',
  };
  const ROUTES = [
    ["", "matches", "nav_matches", viewUpcoming],
    ["results", "results", "nav_results", viewResults],
    ["table", "table", "nav_table", viewTable],
    ["europe", "europe", "nav_europe", viewEurope],
    ["accuracy", "accuracy", "nav_accuracy", viewAccuracy],
  ];

  function renderNav(active) {
    document.getElementById("nav").innerHTML = ROUTES.map(([path, icon, label]) =>
      `<a href="#/${path}" ${active === path ? 'aria-current="page"' : ""}>${ICONS[icon]}<span>${t(label)}</span></a>`).join("");
  }

  function renderFooter() {
    const m = D.meta;
    const f = document.getElementById("footer");
    if (!m) { f.innerHTML = ""; return; }
    const when = new Intl.DateTimeFormat(locale(), { dateStyle: "medium", timeStyle: "short" }).format(new Date(m.generated_at));
    f.innerHTML = `<p>${t("updated")}: ${esc(when)}${m.last_result_date ? ` · ${t("last_result")}: ${esc(shortDate(m.last_result_date))}` : ""}${offline ? ` · ${t("offline")}` : ""}</p>
      <p>${t("disclaimer")}</p>
      <p><a href="#/about">${t("method")}</a> · ${t("sources")}: ${(m.sources || []).map((s) => `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.name)}</a>`).join(", ")}</p>`;
  }

  function route() {
    const hash = location.hash.replace(/^#\/?/, "");
    const [head, arg] = hash.split("/");
    let html, active = head;
    if (head === "club" && arg) { html = viewClub(decodeURIComponent(arg)); active = "table"; }
    else if (head === "about") { html = viewAbout(); active = "about"; }
    else {
      const r = ROUTES.find(([p]) => p === head) || ROUTES[0];
      active = r[0];
      html = r[3]();
    }
    renderNav(active);
    const app = document.getElementById("app");
    app.innerHTML = html;
    app.querySelectorAll("[data-filter]").forEach((b) => b.addEventListener("click", () => {
      filter = b.dataset.filter; store.set("filter", filter); route();
    }));
    renderFooter();
    hideTip();
    document.title = `HNL Prognoza`;
  }

  // --------------------------------------------------------------- theme
  function applyTheme(th) {
    if (th) document.documentElement.setAttribute("data-theme", th); else document.documentElement.removeAttribute("data-theme");
    const dark = th ? th === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    const btn = document.getElementById("theme-toggle");
    btn.innerHTML = dark ? ICONS.sun : ICONS.moon;
    btn.setAttribute("aria-label", t("theme"));
  }

  function applyLang() {
    document.documentElement.lang = lang;
    document.getElementById("lang-toggle").textContent = lang === "hr" ? "EN" : "HR";
  }

  async function init() {
    applyLang();
    applyTheme(store.get("theme", ""));
    document.getElementById("theme-toggle").addEventListener("click", () => {
      const cur = document.documentElement.getAttribute("data-theme") || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      const next = cur === "dark" ? "light" : "dark";
      store.set("theme", next); applyTheme(next);
    });
    document.getElementById("lang-toggle").addEventListener("click", () => {
      lang = lang === "hr" ? "en" : "hr"; store.set("lang", lang); applyLang(); route();
    });
    window.addEventListener("hashchange", () => { route(); window.scrollTo(0, 0); });
    await loadData();
    route();
    if ("serviceWorker" in navigator && location.protocol === "https:") {
      navigator.serviceWorker.register("sw.js").catch(() => {});
    }
  }
  init();
})();
