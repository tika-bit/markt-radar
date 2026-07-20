#!/usr/bin/env python3
"""
Baut die statische Analyse-Seite aus den JSON-Dateien unter data/<slug>/<datum>.json.
Erzeugt:
  index.html                 -> Startseite mit Kachel je Instrument (neueste Analyse)
  <slug>/index.html          -> Instrument-Übersicht: neueste Analyse + Archivliste
  <slug>/<datum>.html        -> feste Tagesseite (bleibt liegen = Archiv)
  data/manifest.json         -> Register aller Seiten
Aufruf: python3 build_site.py
"""
import json, glob, os
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))

# Reihenfolge + Anzeigenamen der Instrumente. Neue Instrumente hier ergaenzen.
INSTRUMENTS = [
    ("wti",    "WTI Crude Oil"),
    ("gold",   "Gold"),
    ("silber", "Silber"),
]

BIAS_CLASS = {"bullish": "bullish", "bearish": "bearish", "neutral": "neutral"}
DIR_CLASS  = {"up": "up", "down": "down", "flat": "flat"}

def de_date(iso):
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d.%m.%Y")
    except Exception:
        return iso

def load(slug):
    files = sorted(glob.glob(os.path.join(ROOT, "data", slug, "*.json")), reverse=True)
    out = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        out.append(d)
    return out  # neueste zuerst

def page_head(title, css_path, nav_active=None):
    nav = []
    nav.append(('<a href="%sindex.html">Übersicht</a>' % css_path.replace("assets/style.css","")))
    for slug, name in INSTRUMENTS:
        base = css_path.replace("assets/style.css","")
        nav.append('<a href="%s%s/index.html">%s</a>' % (base, slug, name))
    return """<!DOCTYPE html>
<html lang="de"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>%s</title>
<link rel="stylesheet" href="%s">
</head><body>
<div class="topbar">
  <div class="sub">Tägliche Markt-Analysen · dunkel</div>
  <div class="nav">%s</div>
</div>
""" % (title, css_path, " ".join(nav))

FOOTER = """<div class="footer">
Automatisch generierte Tagesanalysen · alle Preise sind Näherungswerte · keine Anlageberatung.
Zuletzt gebaut: %s
</div></body></html>"""

DISCLAIMER = """<div class="disc">
<span class="tag">Keine Anlageberatung</span><span class="tag">CFDs sind gehebelt</span><span class="tag">Live-Kurse prüfen</span><br>
Diese Analyse dient ausschließlich Informations- und Bildungszwecken und stellt <b>keine Anlage-, Finanz- oder Handelsberatung</b> dar.
Alle Preise und Level sind <b>Näherungswerte</b> auf Basis öffentlich recherchierter Quellen (%s) und können vom aktuellen Marktpreis abweichen.
CFDs sind gehebelte Produkte mit hohem Verlustrisiko – ein Totalverlust des eingesetzten Kapitals ist möglich.
Prüfe stets die <b>Live-Kurse und Kontraktspezifikationen in deiner Pepperstone-Plattform</b>, bevor du handelst. Eigene Verantwortung, eigenes Risikomanagement.
</div>"""

def render_analysis(d, css_path):
    cards = "".join(
        '<div class="card"><div class="label">%s</div><div class="price">%s</div><div class="chg %s">%s</div></div>'
        % (c["label"], c["price"], DIR_CLASS.get(c.get("dir","flat"),"flat"), c["chg"])
        for c in d["cards"]
    )
    rows = "".join(
        '<tr><td class="%s">%s</td><td class="lvl %s">%s</td><td>%s</td></tr>'
        % (l["type"], l["name"], l["type"], l["value"], l["note"])
        for l in d["levels"]
    )
    drivers = "".join(
        '<li><b>%s:</b> %s</li>' % (dr["title"], dr["text"]) for dr in d["drivers"]
    )
    bias_cls = BIAS_CLASS.get(d["bias"], "neutral")
    html = []
    html.append('<div class="header"><div>')
    html.append('<h1>%s – Tagesanalyse</h1>' % d["instrument"])
    html.append('<div class="sub">Instrument: %s · Handelstag %s</div>' % (d["symbol"], de_date(d["date"])))
    html.append('<div class="sub">Datenstand: %s · alle Preise Näherungswerte</div>' % d["datastand"])
    html.append('</div><div style="text-align:right">')
    html.append('<span class="badge %s">BIAS: %s</span>' % (bias_cls, d["bias_label"].upper()))
    html.append('<div class="sub" style="margin-top:8px">%s</div>' % d["bias_note"])
    html.append('</div></div>')
    html.append('<div class="cards">%s</div>' % cards)
    html.append('<div class="fazit"><b>Kurz-Fazit:</b> %s</div>' % d["fazit"])
    html.append('<h2>Technische Level</h2>')
    html.append('<table><thead><tr><th>Typ</th><th>Level (≈ $)</th><th>Bedeutung</th></tr></thead><tbody>%s</tbody></table>' % rows)
    html.append('<div class="sub" style="margin-top:8px">%s</div>' % d["trend_note"])
    html.append('<h2>Fundamentale Treiber</h2><ul class="drv">%s</ul>' % drivers)
    html.append('<h2>Szenarien für den Tag</h2><div class="scen">')
    html.append('<div class="box bull"><h3>▲ Bull-Szenario</h3><p>%s</p></div>' % d["bull"])
    html.append('<div class="box bear"><h3>▼ Bär-Szenario</h3><p>%s</p></div>' % d["bear"])
    html.append('</div>')
    html.append(DISCLAIMER % d["datastand"])
    return "\n".join(html)

def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)

def main():
    built = datetime.utcnow().strftime("%d.%m.%Y %H:%M UTC")
    manifest = {"built": built, "instruments": {}}

    for slug, name in INSTRUMENTS:
        entries = load(slug)
        manifest["instruments"][slug] = {"name": name, "pages": [e["date"] for e in entries]}
        if not entries:
            continue

        # 1) Tagesseiten
        for d in entries:
            page = page_head("%s – %s" % (name, de_date(d["date"])), "../assets/style.css")
            page += render_analysis(d, "../assets/style.css")
            page += FOOTER % built
            write(os.path.join(ROOT, slug, d["date"] + ".html"), page)

        # 2) Instrument-Index: neueste Analyse + Archiv
        latest = entries[0]
        idx = page_head("%s – Analysen" % name, "../assets/style.css")
        idx += render_analysis(latest, "../assets/style.css")
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

    # 3) Startseite mit Kacheln
    root = page_head("Markt-Analysen · Übersicht", "assets/style.css")
    root += '<div class="header"><div><h1>Tägliche Markt-Analysen</h1>'
    root += '<div class="sub">WTI · Gold · Silber – kombiniert technisch + fundamental. Neue Instrumente folgen.</div>'
    root += '</div></div>'
    tiles = []
    for slug, name in INSTRUMENTS:
        entries = load(slug)
        if not entries:
            continue
        d = entries[0]
        bias_cls = BIAS_CLASS.get(d["bias"], "neutral")
        tiles.append(
            '<a class="tile" href="%s/index.html">'
            '<div class="t-name">%s</div><div class="t-sym">%s</div>'
            '<div class="t-price">%s</div>'
            '<div class="t-foot"><span class="badge %s">%s</span>'
            '<span class="a-meta">%s</span></div></a>'
            % (slug, name, d["symbol"], d["price"], bias_cls, d["bias_label"], de_date(d["date"]))
        )
    root += '<div class="tiles">%s</div>' % "".join(tiles)
    root += FOOTER % built
    write(os.path.join(ROOT, "index.html"), root)

    with open(os.path.join(ROOT, "data", "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    print("Build OK:", built)
    print("Instrumente:", ", ".join(s for s,_ in INSTRUMENTS))

if __name__ == "__main__":
    main()
