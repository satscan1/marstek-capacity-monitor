// Settings window (0.5.5-rc3). The gear on a battery card opens this window
// in the house style (HESC v4 proefbord): own fields and buttons, two tabs,
// Standard and Experiment. It talks to the integration over the websocket
// (settings_ws.py), with the same checks as the options flow of Home
// Assistant; that flow stays as a fallback ("Settings screen of HA").

const MCW_TEXT = {
  nl: {
    title: "Instellingen", std: "Standaard", exp: "Experiment", loading: "Laden…",
    sensors: "Sensoren", battery: "Batterij en garantie", limits: "Grenzen", notify: "Meldingen",
    sign: "Vermogensensor", cells: "Celspanning (optioneel)", temps: "Celtemperatuur (optioneel)", data: "Gegevens",
    soc: "Laadtoestand (SOC)", power: "Vermogen (DC, batterijkant)",
    swap: "Wisselen", swapClose: "Sluiten", found: "Gevonden in Home Assistant", none: "Geen andere batterijsensoren gevonden.",
    manual: "Zelf kiezen", manualSub: "Zoek op naam of entity-id",
    restart: "Opnieuw beginnen met meten",
    restartSub: "Wist de metingen van deze batterij. Zonder dit blijven ze staan en gaat de meting verder met de nieuwe sensoren.",
    apply: "Uitvoeren", pickFirst: "Kies eerst een paar sensoren, of zet ‘Opnieuw beginnen’ aan.",
    ac: "Deze vermogensensor lijkt de AC-/netkant te meten, niet de batterijkant (DC). Dat geeft een verkeerde capaciteit.",
    acYes: "Toch gebruiken", applied: "Sensoren gewisseld. De meting gaat verder.", restarted: "Meting opnieuw begonnen.",
    choose: "Kiezen", clear: "Weghalen", empty: "Niet ingesteld", search: "Zoeken…", noHits: "Niets gevonden.",
    missing: "niet gevonden", noValue: "geen waarde",
    save: "Opslaan", saved: "Opgeslagen. De batterij wordt opnieuw geladen.", nothing: "Niets gewijzigd.",
    unsaved: "Niet opgeslagen. Nog een keer ✕ om toch te sluiten.",
    restore: "Back-up terugzetten", restoreSub: "In het instelscherm van Home Assistant: Configureren → Back-up terugzetten.", restoreBtn: "Instelscherm",
    wipe: "Metingen wissen", wipeSub: "Begint de meting van deze batterij opnieuw. Maak eerst een back-up via Rapport.",
    wipeAsk: "Zeker weten? Wissen", wiped: "Metingen gewist.",
    ha: "Instelscherm van Home Assistant",
    expIntro: "Proeven die nog niet af zijn. Ze staan standaard uit en tellen niet mee voor de status van de batterij.",
    weak: "Zwakke cel herkennen", weakSub: "Herkent een cel die eerder leeg is dan de rest.", later: "komt later",
    fail: "Lukt niet: ", years: "jaar",
    errors: { out_of_range: "Buiten het bereik.", not_a_number: "Geen getal.", not_a_date: "Geen datum.", not_found: "Sensor niet gevonden." },
    sensorsInfo: "De monitor rekent met twee sensoren van de batterij: de laadtoestand (SOC, in %) en het vermogen aan de batterijkant (DC, in W).\n\n**Wisselen** laat zien welke paren Home Assistant nu heeft, met de waarde van dit moment. Een vermogensensor die nooit 0 W laat zien als de batterij stilstaat, meet waarschijnlijk de netkant.\n\nDe metingen blijven bij de batterij, ook na wisselen.",
  },
  en: {
    title: "Settings", std: "Standard", exp: "Experiment", loading: "Loading…",
    sensors: "Sensors", battery: "Battery and warranty", limits: "Limits", notify: "Messages",
    sign: "Power sensor", cells: "Cell voltage (optional)", temps: "Cell temperature (optional)", data: "Data",
    soc: "State of charge (SOC)", power: "Power (DC, battery side)",
    swap: "Change", swapClose: "Close", found: "Found in Home Assistant", none: "No other battery sensors found.",
    manual: "Choose yourself", manualSub: "Search by name or entity id",
    restart: "Start measuring over",
    restartSub: "Clears the measurements of this battery. Without this they stay, and measuring continues with the new sensors.",
    apply: "Run", pickFirst: "First choose a pair of sensors, or switch on ‘Start over’.",
    ac: "This power sensor seems to measure the AC / grid side, not the battery side (DC). That gives a wrong capacity.",
    acYes: "Use it anyway", applied: "Sensors changed. Measuring continues.", restarted: "Measuring started over.",
    choose: "Choose", clear: "Remove", empty: "Not set", search: "Search…", noHits: "Nothing found.",
    missing: "not found", noValue: "no value",
    save: "Save", saved: "Saved. The battery is reloaded.", nothing: "Nothing changed.",
    unsaved: "Not saved. Press ✕ again to close anyway.",
    restore: "Restore a back-up", restoreSub: "In the settings screen of Home Assistant: Configure → Restore a back-up.", restoreBtn: "Settings screen",
    wipe: "Clear measurements", wipeSub: "Starts measuring this battery over. Make a back-up first via Report.",
    wipeAsk: "Sure? Clear", wiped: "Measurements cleared.",
    ha: "Settings screen of Home Assistant",
    expIntro: "Trials that are not finished yet. They are off by default and do not count for the status of the battery.",
    weak: "Detect a weak cell", weakSub: "Spots a cell that runs empty before the rest.", later: "coming later",
    fail: "Did not work: ", years: "years",
    errors: { out_of_range: "Out of range.", not_a_number: "Not a number.", not_a_date: "Not a date.", not_found: "Sensor not found." },
    sensorsInfo: "The monitor works with two sensors of the battery: the state of charge (SOC, in %) and the power on the battery side (DC, in W).\n\n**Change** shows which pairs Home Assistant has now, with the value of this moment. A power sensor that never shows 0 W while the battery is idle probably measures the grid side.\n\nThe measurements stay with the battery, also after a change.",
  },
  de: {
    title: "Einstellungen", std: "Standard", exp: "Experiment", loading: "Laden…",
    sensors: "Sensoren", battery: "Batterie und Garantie", limits: "Grenzen", notify: "Meldungen",
    sign: "Leistungssensor", cells: "Zellspannung (optional)", temps: "Zelltemperatur (optional)", data: "Daten",
    soc: "Ladezustand (SOC)", power: "Leistung (DC, Batterieseite)",
    swap: "Wechseln", swapClose: "Schließen", found: "In Home Assistant gefunden", none: "Keine anderen Batteriesensoren gefunden.",
    manual: "Selbst wählen", manualSub: "Suche nach Name oder Entity-ID",
    restart: "Messung neu beginnen",
    restartSub: "Löscht die Messungen dieser Batterie. Ohne dies bleiben sie erhalten und die Messung läuft mit den neuen Sensoren weiter.",
    apply: "Ausführen", pickFirst: "Wähle zuerst ein Sensorpaar oder schalte ‚Neu beginnen‘ ein.",
    ac: "Dieser Leistungssensor scheint die AC-/Netzseite zu messen, nicht die Batterieseite (DC). Das ergibt eine falsche Kapazität.",
    acYes: "Trotzdem verwenden", applied: "Sensoren gewechselt. Die Messung läuft weiter.", restarted: "Messung neu begonnen.",
    choose: "Wählen", clear: "Entfernen", empty: "Nicht eingestellt", search: "Suchen…", noHits: "Nichts gefunden.",
    missing: "nicht gefunden", noValue: "kein Wert",
    save: "Speichern", saved: "Gespeichert. Die Batterie wird neu geladen.", nothing: "Nichts geändert.",
    unsaved: "Nicht gespeichert. Noch einmal ✕, um trotzdem zu schließen.",
    restore: "Back-up zurückspielen", restoreSub: "Im Einstellungsfenster von Home Assistant: Konfigurieren → Back-up zurückspielen.", restoreBtn: "Einstellungsfenster",
    wipe: "Messungen löschen", wipeSub: "Beginnt die Messung dieser Batterie neu. Erst ein Back-up über Bericht machen.",
    wipeAsk: "Sicher? Löschen", wiped: "Messungen gelöscht.",
    ha: "Einstellungsfenster von Home Assistant",
    expIntro: "Versuche, die noch nicht fertig sind. Sie sind standardmäßig aus und zählen nicht für den Status der Batterie.",
    weak: "Schwache Zelle erkennen", weakSub: "Erkennt eine Zelle, die früher leer ist als der Rest.", later: "kommt später",
    fail: "Hat nicht geklappt: ", years: "Jahre",
    errors: { out_of_range: "Außerhalb des Bereichs.", not_a_number: "Keine Zahl.", not_a_date: "Kein Datum.", not_found: "Sensor nicht gefunden." },
    sensorsInfo: "Der Monitor rechnet mit zwei Sensoren der Batterie: dem Ladezustand (SOC, in %) und der Leistung auf der Batterieseite (DC, in W).\n\n**Wechseln** zeigt, welche Paare Home Assistant jetzt hat, mit dem Wert dieses Moments. Ein Leistungssensor, der nie 0 W zeigt, wenn die Batterie ruht, misst wahrscheinlich die Netzseite.\n\nDie Messungen bleiben bei der Batterie, auch nach dem Wechsel.",
  },
};

// Which sensors the search offers, by unit
const MCW_UNITS = {
  soc: ["%"], power: ["W", "kW"],
  cell_max_entity: ["V", "mV"], cell_min_entity: ["V", "mV"],
  temp_max_entity: ["°C", "°F"], temp_min_entity: ["°C", "°F"],
};

const MCW_INFO_CSS = `.ib{flex:none;width:26px;height:26px;border-radius:50%;border:1.5px solid var(--secondary-text-color,#9aa0aa);background:none;
  color:var(--secondary-text-color,#9aa0aa);font:italic 600 14px/1 Georgia,serif;cursor:pointer;padding:0}
.ib:hover,.ib[aria-expanded=true]{border-color:var(--primary-color);color:var(--primary-color)}
.tip{background:var(--secondary-background-color,#262932);border-left:3px solid var(--primary-color);border-radius:8px;
  padding:10px 14px;font-size:14px;line-height:1.45;color:var(--primary-text-color);grid-column:1/-1}
.tip p{margin:0 0 6px}.tip p:last-child,.tip ul:last-child{margin-bottom:0}.tip ul{margin:0 0 6px;padding-left:18px}`;

const MCW_CSS = `
:host{--line:var(--divider-color,#30333c);--muted:var(--secondary-text-color,#9aa0aa);--card2:var(--secondary-background-color,#262932);
  --dot:#ff9800;--c:var(--primary-color);--bad:var(--error-color,#ef5350);font-family:var(--paper-font-body1_-_font-family,Roboto,sans-serif)}
button:focus-visible{outline:2px solid var(--primary-color);outline-offset:2px}
button:disabled{opacity:.45;cursor:default}
.ov{position:fixed;inset:0;background:rgba(0,0,0,.6);display:flex;align-items:flex-start;justify-content:center;
  padding:40px 16px 24px;z-index:999;overflow:auto;box-sizing:border-box}
.win{background:var(--ha-card-background,var(--card-background-color,#1c1c1c));color:var(--primary-text-color);border:1px solid var(--line);
  border-radius:14px;width:100%;max-width:1120px;padding:16px 18px 20px;display:grid;gap:12px;box-sizing:border-box;min-width:0;container-type:inline-size}
header{display:flex;align-items:center;gap:10px}
h3{margin:0;font-size:17px;font-weight:500}h3 small{color:var(--muted);font-weight:400;font-size:14px}
.x{margin-left:auto;background:none;border:0;color:var(--muted);font-size:20px;cursor:pointer;width:36px;height:36px;border-radius:50%}
.x:hover{background:var(--card2);color:var(--primary-text-color)}
.tabs{display:grid;grid-auto-flow:column;grid-auto-columns:1fr;background:var(--card2);border-radius:12px;padding:4px;gap:4px}
.tab{font:inherit;font-size:14px;border:0;border-radius:9px;background:none;color:var(--muted);padding:8px 6px;cursor:pointer}
.tab.on{background:var(--primary-color);color:var(--text-primary-color,#fff);font-weight:600}
.intro{margin:0;color:var(--muted);font-size:14px;line-height:1.45}
.sec{font-size:15px;font-weight:500;margin:10px 0 0;padding-top:12px;border-top:2px solid var(--line);display:flex;align-items:center;gap:8px}
.sec .ib{margin-left:auto}
.cols{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;align-items:start}
.col{display:grid;gap:12px;min-width:0}.cols>.intro{grid-column:1/-1}
.grp{border:1px solid var(--line);border-radius:12px;padding:12px 14px 4px;min-width:0}
.grp>.sec{border-top:0;padding-top:0;margin:0 0 2px}
@container (max-width:760px){.cols{grid-template-columns:minmax(0,1fr)}}
.f{display:grid;grid-template-columns:minmax(110px,1fr) minmax(0,auto);gap:6px 16px;align-items:center;padding:12px 0;border-top:1px solid var(--line)}
.sec+.f,.sec+.tip+.f{border-top:0}
.f>.nm{font-size:14px;line-height:1.3;display:flex;gap:8px;align-items:flex-start}.f>.nm>span{flex:1;min-width:0}
.f>.nm small{display:block;color:var(--muted);font-size:12px}
.f>.nm .ib{width:22px;height:22px;font-size:12px}
.f.wide{grid-template-columns:minmax(0,1fr)}
.f.na{opacity:.45}
.f .err{grid-column:1/-1;color:var(--bad);font-size:12px}
.right{display:flex;gap:8px;align-items:center;justify-content:flex-end;flex-wrap:wrap}
.stp{display:inline-flex;align-items:center;border:1.5px solid var(--line);border-radius:999px;background:var(--card2);height:36px}
.stp button{width:36px;height:36px;border:0;background:none;color:var(--primary-text-color);font-size:19px;cursor:pointer;border-radius:50%}
.stp button:hover{background:color-mix(in srgb,var(--c) 25%,transparent)}
.stp b{min-width:84px;text-align:center;font-size:15px;font-weight:600;font-variant-numeric:tabular-nums;white-space:nowrap;cursor:text}
.stp input{width:84px;font:inherit;font-size:15px;font-weight:600;text-align:center;border:0;background:none;color:var(--primary-text-color);outline:none}
.sl{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:center;min-width:180px}
.sl output{font-size:15px;font-weight:600;min-width:64px;text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.sl input{-webkit-appearance:none;appearance:none;width:100%;height:10px;border-radius:999px;margin:0;cursor:pointer;
  background:linear-gradient(90deg,var(--c) 0 var(--v),var(--card2) var(--v) 100%);border:1px solid var(--line)}
.sl input::-webkit-slider-thumb{-webkit-appearance:none;width:22px;height:22px;border-radius:50%;background:#fff;border:3px solid var(--c);box-shadow:0 1px 4px rgba(0,0,0,.4)}
.sl input::-moz-range-thumb{width:18px;height:18px;border-radius:50%;background:#fff;border:3px solid var(--c)}
.tg{width:48px;height:28px;border-radius:999px;border:0;background:var(--card2);box-shadow:inset 0 0 0 1.5px var(--line);position:relative;cursor:pointer;flex:none}
.tg::after{content:"";position:absolute;top:4px;left:4px;width:20px;height:20px;border-radius:50%;background:var(--muted);transition:left .15s,background .15s}
.tg.on{background:var(--c);box-shadow:none}.tg.on::after{left:24px;background:#fff}
.chips{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
.chip{font:inherit;font-size:13px;border-radius:999px;border:1.5px solid var(--line);background:none;color:var(--primary-text-color);padding:6px 12px;cursor:pointer}
.chip.on{border-color:var(--c);background:color-mix(in srgb,var(--c) 25%,transparent);font-weight:600}
.btn{font:inherit;font-size:13px;border-radius:999px;border:1.5px solid var(--c);background:none;color:var(--primary-text-color);padding:7px 16px;cursor:pointer;white-space:nowrap}
.btn:hover:not(:disabled){background:color-mix(in srgb,var(--c) 22%,transparent)}
.btn.pri{background:var(--c);color:var(--text-primary-color,#fff);font-weight:600}
.btn.bad{border-color:var(--bad)}.btn.bad:hover{background:color-mix(in srgb,var(--bad) 22%,transparent)}
.btn.sm{padding:5px 12px;font-size:12px;border-color:var(--line)}
.val{font-size:14px;font-weight:600;text-align:right;min-width:0;overflow-wrap:anywhere}
.val small{display:block;color:var(--muted);font-weight:400;font-size:12px}
.val.none{color:var(--muted);font-weight:400;font-style:italic}
.tag{font-size:11px;font-weight:500;border:1px solid var(--line);border-radius:999px;padding:2px 9px;color:var(--muted);white-space:nowrap}
.date{font:inherit;font-size:14px;font-weight:600;border-radius:10px;border:1.5px solid var(--line);background:var(--card2);color:var(--primary-text-color);padding:6px 10px}
.box{display:grid;gap:10px;background:color-mix(in srgb,var(--card2) 60%,transparent);border:1.5px solid var(--line);border-radius:14px;padding:12px;margin:4px 0 8px}
.lbl{font-size:12px;color:var(--muted)}
.opt{font:inherit;border-radius:14px;border:1.5px solid var(--line);background:none;color:var(--primary-text-color);padding:10px 12px;cursor:pointer;text-align:left;display:grid;gap:3px;width:100%}
.opt b{font-size:15px}.opt span{font-size:12px;color:var(--muted);overflow-wrap:anywhere}
.opt.on{border-color:var(--c);background:color-mix(in srgb,var(--c) 22%,transparent)}
.q{font:inherit;font-size:14px;width:100%;box-sizing:border-box;border-radius:10px;border:1.5px solid var(--c);background:var(--card2);color:var(--primary-text-color);padding:7px 12px;outline:none}
.hits{display:grid;gap:4px;max-height:240px;overflow:auto}
.hit{font:inherit;text-align:left;border:0;border-radius:10px;background:none;color:var(--primary-text-color);padding:7px 10px;cursor:pointer;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 12px}
.hit:hover,.hit.on{background:color-mix(in srgb,var(--c) 22%,transparent)}
.hit small{grid-column:1;color:var(--muted);font-size:12px;overflow-wrap:anywhere}.hit i{font-style:normal;font-weight:600;grid-row:1/3;grid-column:2;align-self:center}
.warn{border-left:3px solid var(--dot);background:color-mix(in srgb,var(--dot) 12%,transparent);border-radius:8px;padding:8px 12px;font-size:13px;line-height:1.4}
.bar{position:sticky;bottom:-20px;margin:4px -18px -20px;padding:12px 18px;background:var(--ha-card-background,var(--card-background-color,#1c1c1c));
  border-top:1px solid var(--line);border-radius:0 0 14px 14px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.bar .msg{flex:1;min-width:160px;font-size:13px;color:var(--muted)}.bar .msg.bad{color:var(--bad)}
.link{font:inherit;font-size:12px;background:none;border:0;color:var(--muted);text-decoration:underline;cursor:pointer;padding:0}
@container (max-width:460px){.f{grid-template-columns:minmax(0,1fr)}.right,.chips{justify-content:flex-start}.val{text-align:left}}
${MCW_INFO_CSS}`;

function mcwInfo(text) {
  const esc = (t) => mcEsc(t).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
  return String(text || "").split(/\n\s*\n/).map((blk) => {
    const lines = blk.split("\n");
    return lines.every((l) => l.startsWith("- "))
      ? `<ul>${lines.map((l) => `<li>${esc(l.slice(2))}</li>`).join("")}</ul>`
      : `<p>${esc(blk)}</p>`;
  }).join("");
}

class MarstekSettingsWindow {
  constructor(card, entryId, lang, haUrl) {
    this.card = card;
    this.entryId = entryId;
    this.lang = MCW_TEXT[lang] ? lang : "en";
    this.T = MCW_TEXT[this.lang];
    this.haUrl = haUrl;
    this.s = { tab: "std", info: {}, errors: {}, msg: "", bad: false };
    this.host = document.createElement("div");
    this.host.setAttribute("data-mc-settings", "");
    this.root = this.host.attachShadow({ mode: "open" });
    this.root.addEventListener("click", (e) => this._click(e));
    this.root.addEventListener("input", (e) => this._input(e));
    this.root.addEventListener("change", (e) => this._change(e));
    this.root.addEventListener("keydown", (e) => this._key(e));
    this.root.addEventListener("focusout", (e) => { if (e.target.dataset && e.target.dataset.e) this._commitEdit(e.target); });
    this._esc = (e) => { if (e.key === "Escape") this.close(); };
    document.addEventListener("keydown", this._esc);
    document.body.appendChild(this.host);
    this._render();
    this._load();
  }

  get hass() { return this.card._hass; }

  async _load() {
    try {
      const d = await this.hass.callWS({ type: `${MC_DOMAIN}/settings`, entry_id: this.entryId, lang: this.lang });
      this.d = d;
      this.vals = JSON.parse(JSON.stringify(d.values));
      this.orig = JSON.parse(JSON.stringify(d.values));
      this.s.pick = null;
    } catch (err) {
      this.s.msg = this.T.fail + ((err && err.message) || err);
      this.s.bad = true;
    }
    this._render();
  }

  close(force) {
    if (!force && this._dirty() && !this.s.closeAsk) {
      this.s.closeAsk = true;
      this._say(this.T.unsaved, true);
      return;
    }
    document.removeEventListener("keydown", this._esc);
    this.host.remove();
    if (window.__mcSettings === this) window.__mcSettings = null;
  }

  _dirty() { return !!this.vals && JSON.stringify(this.vals) !== JSON.stringify(this.orig); }

  _say(msg, bad) {
    this.s.msg = msg;
    this.s.bad = !!bad;
    const el = this.root.querySelector(".bar .msg");
    if (el) { el.textContent = msg; el.classList.toggle("bad", !!bad); } else this._render();
  }

  // -- the parts of a row ---------------------------------------------------

  _label(key) { return (this.d.texts.label || {})[key] || key; }

  _nm(key, name, sub) {
    const help = (this.d.texts.help || {})[key];
    return `<div class="nm"><span>${mcEsc(name || this._label(key))}${sub ? `<small>${mcEsc(sub)}</small>` : ""}</span>${
      help ? `<button class="ib" data-a="info" data-k="${key}" aria-expanded="${!!this.s.info[key]}" title="info">i</button>` : ""}</div>`;
  }

  _after(key) {
    const help = (this.d.texts.help || {})[key];
    const err = this.s.errors[key];
    const errText = err && (((this.d.texts.errors || {})[err]) || this.T.errors[err] || err);
    return `${this.s.info[key] && help ? `<div class="tip">${mcwInfo(help)}</div>` : ""}${errText ? `<div class="err">${mcEsc(errText)}</div>` : ""}`;
  }

  _fmt(key, v) {
    const step = this.d.numbers[key][2];
    const dec = step < 0.1 ? 2 : step < 1 ? 1 : 0;
    return Number(v).toLocaleString(this.lang === "en" ? "en-US" : this.lang, { minimumFractionDigits: dec, maximumFractionDigits: dec });
  }

  _unit(key) {
    return { nominal_kwh: "kWh", reserve_kwh: "kWh", warranty_years: this.T.years, cycle_eol_pct: "%", red_pct: "%", tolerance_pct: "%" }[key] || "";
  }

  _stepper(key) {
    const v = this.vals[key];
    const unit = this._unit(key);
    const shown = this.s.edit === key
      ? `<input data-e="${key}" value="${mcEsc(this._fmt(key, v))}" inputmode="decimal">`
      : `<b data-a="edit" data-k="${key}">${this._fmt(key, v)}${unit ? ` ${unit}` : ""}</b>`;
    return `<div class="f">${this._nm(key)}<div class="right"><div class="stp"><button data-a="dec" data-k="${key}" aria-label="−">−</button>${shown}<button data-a="inc" data-k="${key}" aria-label="+">+</button></div></div>${this._after(key)}</div>`;
  }

  _slider(key) {
    const [lo, hi, step] = this.d.numbers[key];
    const v = this.vals[key];
    const pct = ((v - lo) / (hi - lo)) * 100;
    return `<div class="f">${this._nm(key)}<div class="sl"><input type="range" data-k="${key}" min="${lo}" max="${hi}" step="${step}" value="${v}" style="--v:${pct}%"><output>${this._fmt(key, v)} %</output></div>${this._after(key)}</div>`;
  }

  _toggle(key, na) {
    const on = !!this.vals[key];
    return `<div class="f${na ? " na" : ""}">${this._nm(key)}<div class="right"><button class="tg${on ? " on" : ""}" data-a="tg" data-k="${key}" role="switch" aria-checked="${on}"${na ? " disabled" : ""}></button></div>${this._after(key)}</div>`;
  }

  _chips(key, names, na) {
    const opts = this.d.choices[key].map((o) => `<button class="chip${this.vals[key] === o ? " on" : ""}" data-a="chip" data-k="${key}" data-v="${o}"${na ? " disabled" : ""}>${mcEsc(names[o] || o)}</button>`).join("");
    return `<div class="f${na ? " na" : ""}">${this._nm(key)}<div class="chips">${opts}</div>${this._after(key)}</div>`;
  }

  _date(key) {
    const dark = mcDark(this.hass);
    return `<div class="f">${this._nm(key)}<div class="right"><input class="date" type="date" data-k="${key}" value="${mcEsc(this.vals[key] || "")}" style="color-scheme:${dark ? "dark" : "light"}"></div>${this._after(key)}</div>`;
  }

  _sensorVal(sensor) {
    if (!sensor) return `<div class="val none">${this.T.empty}</div>`;
    const value = sensor.missing ? this.T.missing : sensor.value == null ? this.T.noValue : sensor.value;
    return `<div class="val">${mcEsc(value)}<small>${mcEsc(sensor.name)}</small><small>${mcEsc(sensor.id)}</small></div>`;
  }

  // A sensor from the states of now, as the window shows it
  _live(id) {
    const st = id && this.hass.states[id];
    if (!id) return null;
    if (!st) return { id, name: id, missing: true };
    const unit = (st.attributes && st.attributes.unit_of_measurement) || "";
    const ok = !["unknown", "unavailable"].includes(st.state);
    return { id, name: (st.attributes && st.attributes.friendly_name) || id, value: ok ? `${st.state} ${unit}`.trim() : null };
  }

  _hits(kind) {
    const units = MCW_UNITS[kind] || [];
    const q = String((this.s.q && this.s.q[kind]) || "").toLowerCase().trim();
    const out = [];
    for (const [id, st] of Object.entries(this.hass.states)) {
      if (!id.startsWith("sensor.") || id.startsWith(`sensor.marstek_${this.d.battery}_`)) continue;
      const unit = st.attributes && st.attributes.unit_of_measurement;
      if (!units.includes(unit)) continue;
      const name = String((st.attributes && st.attributes.friendly_name) || "");
      if (q && !id.toLowerCase().includes(q) && !name.toLowerCase().includes(q)) continue;
      const hint = /soc|battery|batter|akku|state_of_charge|power|vermogen|leistung|cell|zell|temp/i.test(id) ? 0 : 1;
      out.push({ id, name: name || id, value: `${st.state} ${unit}`, hint });
    }
    out.sort((a, b) => a.hint - b.hint || a.id.localeCompare(b.id));
    const chosen = kind === "soc" || kind === "power" ? (this.s.manual || {})[kind] : this.vals[kind];
    const list = out.slice(0, 40).map((h) => `<button class="hit${chosen === h.id ? " on" : ""}" data-a="hit" data-k="${kind}" data-v="${mcEsc(h.id)}"><span>${mcEsc(h.name)}</span><small>${mcEsc(h.id)}</small><i>${mcEsc(h.value)}</i></button>`).join("");
    return list || `<div class="lbl">${this.T.noHits}</div>`;
  }

  _search(kind, label) {
    const q = (this.s.q && this.s.q[kind]) || "";
    return `<div class="lbl">${mcEsc(label)}</div><input class="q" data-q="${kind}" placeholder="${this.T.search}" value="${mcEsc(q)}"><div class="hits" data-hits="${kind}">${this._hits(kind)}</div>`;
  }

  _optSensor(key, na) {
    const live = this._live(this.vals[key]);
    const open = this.s.choose === key;
    return `<div class="f${na ? " na" : ""}">${this._nm(key)}<div class="right">${this._sensorVal(live)}<button class="btn sm" data-a="choose" data-k="${key}">${open ? this.T.swapClose : this.T.choose}</button>${
      this.vals[key] ? `<button class="btn sm" data-a="clearsensor" data-k="${key}">${this.T.clear}</button>` : ""}</div>${
      open ? `<div class="box" style="grid-column:1/-1">${this._search(key, this.T.manualSub)}</div>` : ""}${this._after(key)}</div>`;
  }

  // -- the sensors: plug and play -------------------------------------------

  _sensorsBlock() {
    const T = this.T;
    const d = this.d;
    const sw = this.s.swap;
    let html = `<div class="sec">${T.sensors}<button class="ib" data-a="info" data-k="_sensors" aria-expanded="${!!this.s.info._sensors}">i</button></div>${
      this.s.info._sensors ? `<div class="tip">${mcwInfo(T.sensorsInfo)}</div>` : ""}
      <div class="f"><div class="nm"><span>${T.soc}</span></div>${this._sensorVal(d.sensors.soc)}</div>
      <div class="f"><div class="nm"><span>${T.power}</span></div>${this._sensorVal(d.sensors.power)}</div>
      <div class="f"><div class="nm"><span>${T.found}<small>${d.found.length}</small></span></div><div class="right"><button class="btn" data-a="swap">${sw ? T.swapClose : T.swap}</button></div></div>`;
    if (!sw) return html;
    const pick = this.s.pick;
    const pairs = d.found.map((c, i) => `<button class="opt${pick === String(i) ? " on" : ""}" data-a="pick" data-v="${i}"><b>${mcEsc(c.name)}</b><span>SOC ${mcEsc((c.soc && c.soc.value) || "?")} · ${mcEsc((c.power && c.power.value) || "?")}</span><span>${mcEsc(c.soc.id)} + ${mcEsc(c.power.id)}</span></button>`).join("");
    const man = pick === "manual";
    html += `<div class="box"><div class="lbl">${T.found}</div>${pairs || `<div class="lbl">${T.none}</div>`}
      <button class="opt${man ? " on" : ""}" data-a="pick" data-v="manual"><b>✎ ${T.manual}</b><span>${T.manualSub}</span></button>
      ${man ? this._search("soc", T.soc) + this._search("power", T.power) : ""}
      <div class="f"><div class="nm"><span>${T.restart}<small>${T.restartSub}</small></span></div><div class="right"><button class="tg${this.s.restart ? " on" : ""}" data-a="restart" role="switch" aria-checked="${!!this.s.restart}"></button></div></div>
      ${this.s.acAsk ? `<div class="warn">${T.ac}</div>` : ""}
      <div class="right"><button class="btn${this.s.acAsk ? " bad" : " pri"}" data-a="apply">${this.s.acAsk ? T.acYes : T.apply}</button></div></div>`;
    return html;
  }

  _grp(html) { return `<section class="grp">${html}</section>`; }

  _std() {
    const T = this.T;
    const tx = this.d.texts;
    const hasCells = !!(this.vals.cell_max_entity && this.vals.cell_min_entity);
    const left = [
      this._sensorsBlock(),
      `<div class="sec">${T.sign}</div>${this._chips("power_sign", tx.choices.power_sign)}`,
      `<div class="sec">${T.cells}</div>${this._optSensor("cell_max_entity")}${this._optSensor("cell_min_entity")}${this._chips("cell_sensitivity", tx.choices.sensitivity, !hasCells)}`,
      `<div class="sec">${T.data}</div>
      <div class="f"><div class="nm"><span>${T.restore}<small>${T.restoreSub}</small></span></div><div class="right"><button class="btn" data-a="ha">${T.restoreBtn}</button></div></div>
      <div class="f"><div class="nm"><span>${T.wipe}<small>${T.wipeSub}</small></span></div><div class="right"><button class="btn${this.s.wipeAsk ? " bad" : ""}" data-a="wipe">${this.s.wipeAsk ? T.wipeAsk : T.apply}</button></div></div>`,
    ];
    const right = [
      `<div class="sec">${T.battery}</div>${this._stepper("nominal_kwh")}${this._stepper("reserve_kwh")}${this._date("purchase_date")}${this._stepper("warranty_years")}${this._stepper("cycle_life")}${this._stepper("cycle_eol_pct")}${this._stepper("initial_cycles")}`,
      `<div class="sec">${T.limits}</div>${this._slider("red_pct")}${this._slider("tolerance_pct")}`,
      `<div class="sec">${T.notify}</div>${this._toggle("notify")}${this._toggle("sidebar")}${this._chips("soc_sensitivity", tx.choices.sensitivity)}`,
    ];
    return this._cols(left, right);
  }

  _cols(left, right, intro) {
    const col = (list) => `<div class="col">${list.map((g) => this._grp(g)).join("")}</div>`;
    return `<div class="cols">${intro || ""}${col(left)}${col(right)}</div>`;
  }

  _exp() {
    const T = this.T;
    return this._cols(
      [`<div class="sec">${T.temps}</div>${this._optSensor("temp_max_entity")}${this._optSensor("temp_min_entity")}`],
      [`<div class="sec">${T.weak}</div>
      <div class="f na"><div class="nm"><span>${T.weak}<small>${T.weakSub}</small></span></div><div class="right"><span class="tag">${T.later}</span><button class="tg" disabled role="switch" aria-checked="false"></button></div></div>`],
      `<p class="intro">${T.expIntro}</p>`,
    );
  }

  _render() {
    const T = this.T;
    const d = this.d;
    const body = !d ? `<p class="intro">${this.s.msg ? "" : T.loading}</p>` : this.s.tab === "exp" ? this._exp() : this._std();
    const scroll = this.root.querySelector(".ov");
    const top = scroll ? scroll.scrollTop : 0;
    this.root.innerHTML = `<style>${MCW_CSS}</style>
      <div class="ov" data-a="ov"><div class="win" role="dialog" aria-modal="true">
        <header><h3>${T.title}${d ? ` <small>· ${mcEsc(d.name)}</small>` : ""}</h3><button class="x" data-a="close" aria-label="✕">✕</button></header>
        <div class="tabs"><button class="tab${this.s.tab === "std" ? " on" : ""}" data-a="tab" data-v="std">${T.std}</button><button class="tab${this.s.tab === "exp" ? " on" : ""}" data-a="tab" data-v="exp">${T.exp}</button></div>
        <div class="body">${body}</div>
        <div class="bar"><button class="btn pri" data-a="save"${d && this._dirty() ? "" : " disabled"}>${T.save}</button><span class="msg${this.s.bad ? " bad" : ""}">${mcEsc(this.s.msg || "")}</span><button class="link" data-a="ha">${T.ha}</button></div>
      </div></div>`;
    const ov = this.root.querySelector(".ov");
    if (ov) ov.scrollTop = top;
    const ed = this.root.querySelector("input[data-e]");
    if (ed) { ed.focus(); ed.select(); }
    if (this._focusQ) {
      const q = this.root.querySelector(`input[data-q="${this._focusQ}"]`);
      if (q) { q.focus(); q.setSelectionRange(q.value.length, q.value.length); }
      this._focusQ = null;
    }
  }

  // -- events ---------------------------------------------------------------

  _set(key, value) {
    this.vals[key] = value;
    delete this.s.errors[key];
    this.s.closeAsk = false;
    this.s.msg = "";
  }

  _commitEdit(input) {
    const key = input.dataset.e;
    if (this.s.edit !== key) return;
    const n = parseFloat(String(input.value).replace(/\s/g, "").replace(",", "."));
    this.s.edit = null;
    if (!Number.isNaN(n)) {
      const [lo, hi] = this.d.numbers[key];
      this._set(key, Math.min(hi, Math.max(lo, n)));
    }
    this._render();
  }

  _key(e) {
    const t = e.target;
    if (t.dataset && t.dataset.e) {
      if (e.key === "Enter") this._commitEdit(t);
      if (e.key === "Escape") { e.stopPropagation(); this.s.edit = null; this._render(); }
    }
  }

  _input(e) {
    const t = e.target;
    if (t.type === "range") {
      const key = t.dataset.k;
      const [lo, hi] = this.d.numbers[key];
      const v = Number(t.value);
      this._set(key, v);
      t.style.setProperty("--v", `${((v - lo) / (hi - lo)) * 100}%`);
      t.nextElementSibling.textContent = `${this._fmt(key, v)} %`;
      const save = this.root.querySelector('[data-a="save"]');
      if (save) save.disabled = !this._dirty();
    } else if (t.dataset.q) {
      this.s.q = { ...(this.s.q || {}), [t.dataset.q]: t.value };
      const list = this.root.querySelector(`[data-hits="${t.dataset.q}"]`);
      if (list) list.innerHTML = this._hits(t.dataset.q);
    }
  }

  _change(e) {
    const t = e.target;
    if (t.classList.contains("date")) { this._set(t.dataset.k, t.value); this._render(); }
  }

  async _click(e) {
    const el = e.target.closest("[data-a]");
    if (!el) return;
    const a = el.dataset.a;
    const k = el.dataset.k;
    const v = el.dataset.v;
    if (a === "ov") { if (e.target === el) this.close(); return; }
    if (a === "close") return this.close();
    if (!this.d && a !== "ha") return;
    switch (a) {
      case "tab": this.s.tab = v; break;
      case "info": this.s.info[k] = !this.s.info[k]; break;
      case "inc": case "dec": {
        const [lo, hi, step] = this.d.numbers[k];
        const n = Math.round((Number(this.vals[k]) + (a === "inc" ? step : -step)) / step) * step;
        this._set(k, Math.min(hi, Math.max(lo, Number(n.toFixed(4)))));
        break;
      }
      case "edit": this.s.edit = k; break;
      case "tg": this._set(k, !this.vals[k]); break;
      case "chip": this._set(k, v); break;
      case "choose": this.s.choose = this.s.choose === k ? null : k; this._focusQ = this.s.choose; break;
      case "clearsensor": this._set(k, ""); break;
      case "swap": this.s.swap = !this.s.swap; this.s.acAsk = false; break;
      case "pick": this.s.pick = v; this.s.acAsk = false; if (v === "manual") { this.s.manual = this.s.manual || {}; this._focusQ = "soc"; } break;
      case "restart": this.s.restart = !this.s.restart; break;
      case "hit":
        if (k === "soc" || k === "power") { this.s.manual = { ...(this.s.manual || {}), [k]: v }; this.s.acAsk = false; }
        else { this._set(k, v); this.s.choose = null; }
        break;
      case "apply": return this._applySensors();
      case "save": return this._save();
      case "wipe": return this._wipe();
      case "ha": {
        this.close(true);
        mcRememberBack(this.haUrl);
        history.pushState(null, "", this.haUrl);
        window.dispatchEvent(new CustomEvent("location-changed"));
        return;
      }
      default: return;
    }
    this._render();
  }

  async _applySensors() {
    const T = this.T;
    const d = this.d;
    let soc = d.sensors.soc.id;
    let power = d.sensors.power.id;
    if (this.s.pick === "manual") {
      soc = (this.s.manual || {}).soc || soc;
      power = (this.s.manual || {}).power || power;
    } else if (this.s.pick != null) {
      const c = d.found[Number(this.s.pick)];
      soc = c.soc.id; power = c.power.id;
    }
    const changed = soc !== d.sensors.soc.id || power !== d.sensors.power.id;
    if (!changed && !this.s.restart) { this._say(T.pickFirst, true); return; }
    try {
      const r = await this.hass.callWS({ type: `${MC_DOMAIN}/sensors/save`, entry_id: this.entryId, soc, power, restart: !!this.s.restart, accept_ac: !!this.s.acAsk });
      if (r.error === "looks_like_ac") { this.s.acAsk = true; this._render(); return; }
      if (r.error) { this._say(T.fail + (((d.texts.errors || {})[r.error]) || T.errors[r.error] || r.error), true); return; }
      this.s.swap = false; this.s.acAsk = false; this.s.restart = false; this.s.pick = null; this.s.manual = {};
      this.s.msg = r.restarted ? T.restarted : T.applied; this.s.bad = false;
      setTimeout(() => this._load(), 1500);
      this._render();
    } catch (err) {
      this._say(T.fail + ((err && err.message) || err), true);
    }
  }

  async _save() {
    const T = this.T;
    const changes = {};
    for (const [key, value] of Object.entries(this.vals)) {
      if (JSON.stringify(value) !== JSON.stringify(this.orig[key])) changes[key] = value;
    }
    if (!Object.keys(changes).length) { this._say(T.nothing); return; }
    try {
      const r = await this.hass.callWS({ type: `${MC_DOMAIN}/settings/save`, entry_id: this.entryId, values: changes });
      this.s.errors = r.errors || {};
      if (Object.keys(this.s.errors).length) {
        this.s.msg = Object.values(this.s.errors).map((c) => ((this.d.texts.errors || {})[c]) || T.errors[c] || c).join(" ");
        this.s.bad = true;
        this._render();
        return;
      }
      this.orig = JSON.parse(JSON.stringify(this.vals));
      this.s.closeAsk = false;
      this.s.msg = T.saved; this.s.bad = false;
      this._render();
      setTimeout(() => this._load(), 2000);
    } catch (err) {
      this._say(T.fail + ((err && err.message) || err), true);
    }
  }

  async _wipe() {
    const T = this.T;
    if (!this.s.wipeAsk) { this.s.wipeAsk = true; this._render(); return; }
    this.s.wipeAsk = false;
    try {
      await this.hass.callService(MC_DOMAIN, "reset_measurements", { config_entry_id: this.entryId });
      this.s.msg = T.wiped; this.s.bad = false;
    } catch (err) {
      this.s.msg = T.fail + ((err && err.message) || err); this.s.bad = true;
    }
    this._render();
  }
}

function mcOpenSettings(card, entryId, lang, haUrl) {
  if (window.__mcSettings) window.__mcSettings.close(true);
  window.__mcSettings = new MarstekSettingsWindow(card, entryId, lang, haUrl);
}
