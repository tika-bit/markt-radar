#!/usr/bin/env python3
"""
Baut die statische Analyse-Seite aus den JSON-Dateien unter data/<slug>/<datum>.json.
Instrumente sind Kategorien zugeordnet (Rohstoffe, Index, Aktien, Waehrungen, ETFs).
Erzeugt:
  index.html                 -> Startseite, nach Kategorien gruppiert (Kachel je Instrument)
  <slug>/index.html          -> Instrument-Uebersicht: neueste Analyse + Archivliste
  <slug>/<datum>.html        -> feste Tagesseite (bleibt liegen = Archiv)
  data/manifest.json         -> Register aller Seiten
Aufruf: python3 build_site.py
"""
import json, glob, os, re as _re
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))

# Kategorien in Anzeige-Reihenfolge.
CATEGORIES = [
    ("rohstoffe",  "Rohstoffe"),
    ("index",      "Index"),
    ("aktien",     "Aktien"),
    ("waehrungen", "Währungen"),
    ("etf",        "ETFs"),
]

# Instrumente: (slug, Anzeigename, Kategorie). Neue Instrumente hier ergaenzen.
INSTRUMENTS = [
    ("wti",    "WTI Crude Oil", "rohstoffe"),
    ("gold",   "Gold",          "rohstoffe"),
    ("silber", "Silber",        "rohstoffe"),
    ("dax",    "DAX",           "index"),
    ("nas100", "Nasdaq 100",    "index"),
    ("aapl",   "Apple",         "aktien"),
    ("msft",   "Microsoft",     "aktien"),
    ("eurusd", "EUR/USD",       "waehrungen"),
    ("euraud", "EUR/AUD",       "waehrungen"),
]

# TradingView-Symbole je Instrument (Live-Chart).
TV_SYMBOL = {
    "wti": "TVC:USOIL", "gold": "OANDA:XAUUSD", "silber": "OANDA:XAGUSD",
    "dax": "XETR:DAX", "nas100": "NASDAQ:NDX",
    "aapl": "NASDAQ:AAPL", "msft": "NASDAQ:MSFT",
    "eurusd": "FX:EURUSD", "euraud": "OANDA:EURAUD",
}

BIAS_CLASS = {"bullish": "bullish", "bearish": "bearish", "neutral": "neutral"}
DIR_CLASS  = {"up": "up", "down": "down", "flat": "flat"}

def parse_num(s):
    """Extrahiert einen Zahlenwert aus deutschen Preis-Strings ('~82,50 $', '25.000', '1,1380 – 1,1480')."""
    if not isinstance(s, str):
        return None
    t = s
    for ch in ["~", "≈", "$", "%", "−", "€"]:
        t = t.replace(ch, " ")
    parts = _re.split(r"[–]", t)
    vals = []
    for p in parts:
        p2 = p.strip().replace(".", "").replace(",", ".")
        m = _re.search(r"-?\d+(?:\.\d+)?", p2)
        if m:
            try:
                vals.append(float(m.group()))
            except ValueError:
                pass
    if not vals:
        return None
    return sum(vals) / len(vals)

def de_date(iso):
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d.%m.%Y")
    except Exception:
        return iso

def cat_of(slug):
    for s, n, c in INSTRUMENTS:
        if s == slug:
            return c
    return None

def load(slug):
    files = sorted(glob.glob(os.path.join(ROOT, "data", slug, "*.json")), reverse=True)
    out = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            out.append(json.load(fh))
    return out  # neueste zuerst

def page_head(title, css_path, base):
    nav = ['<a href="%sindex.html">Übersicht</a>' % base]
    for cslug, cname in CATEGORIES:
        nav.append('<a href="%sindex.html#cat-%s">%s</a>' % (base, cslug, cname))
    return """<!DOCTYPE html>
<html lang="de"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>%s</title>
<link rel="stylesheet" href="%s">
</head><body>
<div class="topbar">
  <div class="sub"><a href="%sindex.html">markt-radar</a> · tägliche Analysen</div>
  <div class="nav">%s</div>
</div>
""" % (title, css_path, base, " ".join(nav))

FOOTER = """<div class="footer">
Automatisch generierte Tagesanalysen · alle Preise sind Näherungswerte · keine Anlageberatung.
Zuletzt gebaut: %s
</div></body></html>"""

DISCLAIMER = """<div class="disc">
<span class="tag">Keine Anlageberatung</span><span class="tag">Zeitverzögerte Daten</span><span class="tag">Gehebelte Produkte riskant</span><br>
Diese Analyse dient ausschließlich Informations- und Bildungszwecken und stellt <b>keine Anlage-, Finanz- oder Handelsberatung</b> dar.
Alle Preise und Level sind <b>Näherungswerte</b> und <b>zeitverzögert</b> (nicht in Echtzeit) – sie basieren auf dem letzten verfügbaren Schlusskurs (%s) und können deutlich vom aktuellen Marktpreis abweichen.
Gehebelte Produkte (z. B. CFDs) bergen ein hohes Verlustrisiko bis zum Totalverlust des eingesetzten Kapitals.
Prüfe stets die <b>aktuellen Live-Kurse bei deinem Broker</b>, bevor du handelst. Eigene Verantwortung, eigenes Risikomanagement.
</div>"""

def render_tvchart(slug, uid):
    sym = TV_SYMBOL.get(slug)
    if not sym:
        return ""
    wrap = "wrap_" + uid
    cont = "tvw_" + uid
    js = (
        "(function(){"
        "var sym=\"" + sym + "\";var st={interval:\"15\",range:\"2D\"};"
        "var wrap=document.getElementById(\"" + wrap + "\");"
        "function build(){var c=document.getElementById(\"" + cont + "\");if(!c)return;c.innerHTML=\"\";"
        "new TradingView.widget({container_id:\"" + cont + "\",symbol:sym,interval:st.interval,range:st.range,"
        "timezone:\"Europe/Berlin\",theme:\"dark\",style:\"1\",locale:\"de\",autosize:true,"
        "hide_top_toolbar:false,hide_legend:false,allow_symbol_change:false,save_image:false,"
        "backgroundColor:\"rgba(19,26,34,1)\"});}"
        "wrap.querySelectorAll(\"button[data-int]\").forEach(function(b){b.onclick=function(){"
        "st.interval=b.getAttribute(\"data-int\");st.range=b.getAttribute(\"data-rng\");"
        "wrap.querySelectorAll(\"button[data-int]\").forEach(function(x){x.classList.remove(\"active\");});"
        "b.classList.add(\"active\");build();};});"
        "if(window.TradingView&&window.TradingView.widget){build();}"
        "else{var s=document.createElement(\"script\");s.src=\"https://s3.tradingview.com/tv.js\";s.onload=build;document.head.appendChild(s);}"
        "})();"
    )
    html = (
        '<h2>Live-Chart</h2>'
        '<div id="' + wrap + '">'
        '<div class="chart-toolbar">'
        '<span class="ct-label">Ansicht:</span>'
        '<button data-int="15" data-rng="2D" class="active">15m · 48h</button>'
        '<button data-int="60" data-rng="1M">1h · 1 Monat</button>'
        '<button data-int="240" data-rng="4M">4h · 4 Monate</button>'
        '<button data-int="D" data-rng="12M">1T · 1 Jahr</button>'
        '</div>'
        '<div class="tvchart">'
        '<button class="fs-btn" onclick="tvFull(this)" title="Vollbild">⛶ Vollbild</button>'
        '<div id="' + cont + '" style="height:100%;width:100%"></div>'
        '</div></div>'
        '<script>function tvFull(b){var c=b.closest(".tvchart");'
        'if(!document.fullscreenElement){(c.requestFullscreen||c.webkitRequestFullscreen||function(){}).call(c);}'
        'else{document.exitFullscreen();}}</script>'
        '<script>' + js + '</script>'
        '<div class="sub" style="margin-top:6px">Live-Chart via TradingView (' + sym + '). '
        'Ein Klick wählt Kerze + Zeitraum zusammen: <b>15m→48h</b>, <b>1h→1 Monat</b>, <b>4h→4 Monate</b>, <b>1T→1 Jahr</b>. Standard ist 15m/48h; ⛶ für Vollbild. '
        'Zeiträume sind Richtwerte – im Chart frei zoom-/scrollbar. '
        'Die Analyse-Werte in Karten/Tabelle sind dagegen <b>zeitverzögert</b> (letzter Schlusskurs).</div>'
    )
    return html

def render_levelmap(d):
    pts = []
    for l in d.get("levels", []):
        v = parse_num(l.get("value", ""))
        if v is not None:
            pts.append((v, l["type"], l["name"], l["value"]))
    price = parse_num(d.get("price", ""))
    if len(pts) < 2:
        return ""
    allv = [p[0] for p in pts] + ([price] if price is not None else [])
    vmin, vmax = min(allv), max(allv)
    if vmax == vmin:
        return ""
    pad = (vmax - vmin) * 0.08
    vmin -= pad; vmax += pad
    W, H = 620, 300
    top, bot = 24, 24
    plotH = H - top - bot
    x0, x1 = 96, 512
    def y(v):
        return top + (vmax - v) / (vmax - vmin) * plotH
    col = {"res": "#ff5b5b", "sup": "#2ecc71", "piv": "#4aa3ff"}
    svg = ['<svg viewBox="0 0 %d %d" width="100%%" role="img" aria-label="Level-Karte">' % (W, H)]
    svg.append('<rect x="0" y="0" width="%d" height="%d" rx="12" fill="#131a22" stroke="#26313d"/>' % (W, H))
    for v, typ, name, raw in pts:
        yy = round(y(v), 1)
        c = col.get(typ, "#8b98a5")
        dash = ' stroke-dasharray="2 4"' if typ == "piv" else ''
        svg.append('<line x1="%d" y1="%s" x2="%d" y2="%s" stroke="%s" stroke-width="1.4"%s opacity="0.85"/>' % (x0, yy, x1, yy, c, dash))
        svg.append('<text x="%d" y="%s" fill="%s" font-size="11" font-family="Arial" text-anchor="end" dominant-baseline="middle">%s</text>' % (x0 - 8, yy, c, raw))
        svg.append('<text x="%d" y="%s" fill="#8b98a5" font-size="10" font-family="Arial" dominant-baseline="middle">%s</text>' % (x1 + 8, yy, name))
    if price is not None:
        yy = round(y(price), 1)
        svg.append('<line x1="%d" y1="%s" x2="%d" y2="%s" stroke="#f5a623" stroke-width="1.8" stroke-dasharray="6 3"/>' % (x0, yy, x1, yy))
        svg.append('<circle cx="%d" cy="%s" r="4.5" fill="#f5a623"/>' % (x0, yy))
        svg.append('<text x="%d" y="%s" fill="#f5a623" font-size="11" font-weight="700" font-family="Arial" dominant-baseline="middle">aktuell %s</text>' % (x1 + 8, yy, d.get("price", "")))
    svg.append('</svg>')
    return ('<h2>Level-Karte</h2><div class="levelmap">' + "".join(svg) +
            '</div><div class="sub" style="margin-top:6px">Eigene Darstellung aus den Leveln oben · '
            '<span style="color:#ff5b5b">Resistance</span> · '
            '<span style="color:#4aa3ff">Pivot</span> · '
            '<span style="color:#2ecc71">Support</span> · '
            '<span style="color:#f5a623">aktueller Preis</span> · Näherungswerte.</div>')

def _levels_by_type(d, t):
    out = []
    for l in d.get("levels", []):
        if l.get("type") == t:
            v = parse_num(l.get("value", ""))
            if v is not None:
                out.append((v, l.get("value")))
    return out

def render_deep(d):
    # 1) Ausführliche Analyse (aufklappbar)
    if d.get("detail"):
        body = d["detail"]
    else:
        ps = ['<p>%s</p>' % d.get("fazit", "")]
        ps += ['<p><b>%s:</b> %s</p>' % (x["title"], x["text"]) for x in d.get("drivers", [])]
        ps.append('<p><b>Charttechnik:</b> %s</p>' % d.get("trend_note", ""))
        ps.append('<p><b>Aufwärts-Szenario:</b> %s</p>' % d.get("bull", ""))
        ps.append('<p><b>Abwärts-Szenario:</b> %s</p>' % d.get("bear", ""))
        body = "".join(ps)
    deep = ('<details class="deep"><summary>Ausführliche Analyse aufklappen</summary>'
            '<div class="deep-body">%s</div></details>' % body)

    # 2) Einstiegs-Szenarien (automatisch aus Leveln + Bias)
    res = sorted(_levels_by_type(d, "res"))            # aufsteigend – nächster Widerstand zuerst
    sup = sorted(_levels_by_type(d, "sup"), reverse=True)  # absteigend – nächste Unterstützung zuerst
    piv = _levels_by_type(d, "piv")
    piv_raw = piv[0][1] if piv else str(d.get("price", ""))
    boxes = []
    if len(res) >= 2:
        r = [x[1] for x in res]
        ziele = " → ".join(r[1:3]) if len(r) >= 3 else r[1]
        boxes.append('<div class="setup long"><h4>▲ Long-Szenario (Aufwärts)</h4>'
                     '<p><b>Auslöser:</b> bestätigter Ausbruch/Halt über <b>%s</b>.</p>'
                     '<p><b>Mögliche Ziele:</b> %s.</p>'
                     '<p><b>Invalidierung:</b> Rückfall unter <b>%s</b> – Idee hinfällig.</p></div>'
                     % (r[0], ziele, piv_raw))
    if len(sup) >= 2:
        s = [x[1] for x in sup]
        ziele = " → ".join(s[1:3]) if len(s) >= 3 else s[1]
        boxes.append('<div class="setup short"><h4>▼ Short-Szenario (Abwärts)</h4>'
                     '<p><b>Auslöser:</b> bestätigter Bruch unter <b>%s</b>.</p>'
                     '<p><b>Mögliche Ziele:</b> %s.</p>'
                     '<p><b>Invalidierung:</b> Rückeroberung von <b>%s</b>.</p></div>'
                     % (s[0], ziele, piv_raw))
    biasmap = {"bullish": "das Long-Szenario", "bearish": "das Short-Szenario", "neutral": "beide Szenarien etwa gleichrangig"}
    lean = ('<p class="sub" style="margin-top:8px">Aktueller Bias (%s): tendenziell begünstigt ist <b>%s</b>. '
            'Das Gegenszenario dient als Plan B / Absicherung.</p>' % (d.get("bias_label", "–"), biasmap.get(d.get("bias", "neutral"), "beide")))
    setups = ('<details class="deep"><summary>Mögliche Einstiegs-Szenarien – „wann könnte man kaufen?" aufklappen</summary>'
              '<div class="deep-body">'
              '<p class="warn">Hypothetische, rein <b>edukative</b> Szenarien auf Basis der Level oben – '
              '<b>keine Kauf-/Verkaufsempfehlung und keine Anlageberatung</b>. „Bestätigt" meint z. B. einen '
              'Schlusskurs jenseits des Levels. Preise sind zeitverzögerte Näherungswerte; nutze immer eigenes Risikomanagement.</p>'
              '<div class="setups">' + "".join(boxes) + '</div>' + lean + '</div></details>')
    return deep + setups

def render_analysis(d):
    cards = "".join(
        '<div class="card"><div class="label">%s</div><div class="price">%s</div><div class="chg %s">%s</div></div>'
        % (c["label"], c["price"], DIR_CLASS.get(c.get("dir", "flat"), "flat"), c["chg"])
        for c in d["cards"]
    )
    rows = "".join(
        '<tr><td class="%s">%s</td><td class="lvl %s">%s</td><td>%s</td></tr>'
        % (l["type"], l["name"], l["type"], l["value"], l["note"])
        for l in d["levels"]
    )
    drivers = "".join('<li><b>%s:</b> %s</li>' % (dr["title"], dr["text"]) for dr in d["drivers"])
    bias_cls = BIAS_CLASS.get(d["bias"], "neutral")
    h = []
    h.append('<div class="header"><div>')
    h.append('<h1>%s – Tagesanalyse</h1>' % d["instrument"])
    h.append('<div class="sub">Instrument: %s · Handelstag %s</div>' % (d["symbol"], de_date(d["date"])))
    h.append('<div class="sub">Datenstand: %s · Näherungswerte, <b>zeitverzögert</b> (keine Echtzeit)</div>' % d["datastand"])
    h.append('</div><div style="text-align:right">')
    h.append('<span class="badge %s">BIAS: %s</span>' % (bias_cls, d["bias_label"].upper()))
    h.append('<div class="sub" style="margin-top:8px">%s</div>' % d["bias_note"])
    h.append('</div></div>')
    h.append('<div class="cards">%s</div>' % cards)
    h.append('<div class="fazit"><b>Kurz-Fazit:</b> %s</div>' % d["fazit"])
    h.append(render_tvchart(d.get("slug", ""), (d.get("slug", "") + "_" + d.get("date", "")).replace("-", "")))
    h.append('<h2>Technische Level</h2>')
    h.append('<table><thead><tr><th>Typ</th><th>Level (≈)</th><th>Bedeutung</th></tr></thead><tbody>%s</tbody></table>' % rows)
    h.append('<div class="sub" style="margin-top:8px">%s</div>' % d["trend_note"])
    h.append('<h2>Fundamentale Treiber</h2><ul class="drv">%s</ul>' % drivers)
    h.append('<h2>Szenarien für den Tag</h2><div class="scen">')
    h.append('<div class="box bull"><h3>▲ Bull-Szenario</h3><p>%s</p></div>' % d["bull"])
    h.append('<div class="box bear"><h3>▼ Bär-Szenario</h3><p>%s</p></div>' % d["bear"])
    h.append('</div>')
    h.append(render_deep(d))
    h.append(DISCLAIMER % d["datastand"])
    return "\n".join(h)

def write(path, content):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)

def main():
    built = datetime.utcnow().strftime("%d.%m.%Y %H:%M UTC")
    manifest = {"built": built, "categories": {}, "instruments": {}}

    latest_by_slug = {}
    for slug, name, cat in INSTRUMENTS:
        entries = load(slug)
        manifest["instruments"][slug] = {"name": name, "category": cat, "pages": [e["date"] for e in entries]}
        if not entries:
            continue
        latest_by_slug[slug] = entries[0]

        # Tagesseiten
        for d in entries:
            page = page_head("%s – %s" % (name, de_date(d["date"])), "../assets/style.css", "../")
            page += render_analysis(d)
            page += FOOTER % built
            write(os.path.join(ROOT, slug, d["date"] + ".html"), page)

        # Instrument-Index: neueste + Archiv
        latest = entries[0]
        idx = page_head("%s – Analysen" % name, "../assets/style.css", "../")
        idx += render_analysis(latest)
        if len(entries) > 1:
            arch = "".join(
                '<li><a href="%s.html"><span class="a-date">%s</span></a>'
                '<span class="a-meta">%s · Bias: %s</span></li>'
                % (e["date"], de_date(e["date"]), e["price"], e["bias_label"])
                for e in entries[1:]
            )
            idx += '<h2>Archiv</h2><ul class="archive">%s</ul>' % arch
        else:
            idx += '<h2>Archiv</h2><div class="sub">Noch keine älteren Ausgaben – die erste Analyse ist oben.</div>'
        idx += FOOTER % built
        write(os.path.join(ROOT, slug, "index.html"), idx)

    # Startseite nach Kategorien
    root = page_head("markt-radar · Übersicht", "assets/style.css", "")
    root += '<div class="header"><div><h1>markt-radar</h1>'
    root += '<div class="sub">Tägliche Markt-Analysen – kombiniert technisch + fundamental. Kategorien: '
    root += " · ".join(n for _, n in CATEGORIES) + '.</div></div></div>'
    root += ('<div class="disc" style="margin-top:16px">'
             '<span class="tag">Keine Anlageberatung</span><span class="tag">Zeitverzögerte Daten</span>'
             '<span class="tag">Gehebelte Produkte riskant</span><br>'
             'Alle Inhalte dienen ausschließlich Informations- und Bildungszwecken und sind <b>keine Anlage-, '
             'Finanz- oder Handelsberatung</b>. Preise und Level sind <b>Näherungswerte</b> und <b>zeitverzögert</b> '
             '(nicht in Echtzeit), basierend auf dem letzten verfügbaren Schlusskurs. Gehebelte Produkte (z. B. CFDs) '
             'bergen ein hohes Verlustrisiko bis zum Totalverlust. Prüfe stets die aktuellen Live-Kurse bei deinem Broker. '
             'Eigene Verantwortung, eigenes Risikomanagement.</div>')

    for cslug, cname in CATEGORIES:
        slugs = [s for s, n, c in INSTRUMENTS if c == cslug]
        manifest["categories"][cslug] = {"name": cname, "instruments": slugs}
        root += '<h2 id="cat-%s">%s</h2>' % (cslug, cname)
        tiles = []
        for slug in slugs:
            d = latest_by_slug.get(slug)
            if not d:
                continue
            bias_cls = BIAS_CLASS.get(d["bias"], "neutral")
            tiles.append(
                '<a class="tile" href="%s/index.html">'
                '<div class="t-name">%s</div><div class="t-sym">%s</div>'
                '<div class="t-price">%s</div>'
                '<div class="t-foot"><span class="badge %s">%s</span>'
                '<span class="a-meta">%s</span></div></a>'
                % (slug, d["instrument"], d["symbol"], d["price"], bias_cls, d["bias_label"], de_date(d["date"]))
            )
        if tiles:
            root += '<div class="tiles">%s</div>' % "".join(tiles)
        else:
            root += '<div class="sub">Folgt in Kürze.</div>'

    root += FOOTER % built
    write(os.path.join(ROOT, "index.html"), root)

    with open(os.path.join(ROOT, "data", "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    print("Build OK:", built)
    print("Instrumente:", ", ".join(s for s, _, _ in INSTRUMENTS))

if __name__ == "__main__":
    main()
