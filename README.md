# Markt-Analysen (WTI · Gold · Silber)

Statische, dunkel gestylte Tagesanalysen. Pro Instrument eine neue datierte Seite pro Handelstag;
alte Seiten bleiben liegen und werden automatisch im Archiv verlinkt.

## Aufbau
```
index.html            Startseite (Kachel je Instrument, neueste Analyse)
wti/ gold/ silber/    je Instrument: index.html (neueste + Archiv) + <datum>.html
assets/style.css      gemeinsames Design
data/<slug>/<datum>.json   Inhalt einer Tagesanalyse (Quelle der Wahrheit)
data/manifest.json    automatisch erzeugtes Register
build_site.py         baut alle HTML-Seiten aus den JSON-Dateien
```

## Neue Analyse hinzufügen
1. JSON-Datei `data/<slug>/<JJJJ-MM-TT>.json` anlegen (Schema siehe vorhandene Dateien).
2. `python3 build_site.py` ausführen.
3. Committen & pushen – GitHub Pages (oder anderer Host) liefert automatisch aus.

## Neues Instrument hinzufügen
In `build_site.py` die Liste `INSTRUMENTS` um `("slug", "Anzeigename")` ergänzen,
Ordner `data/<slug>/` anlegen, JSON hinterlegen, `build_site.py` ausführen.

## Automatischer täglicher Lauf
Eine geplante Aufgabe (Mo–Fr) recherchiert die Werte, schreibt je ein JSON pro Instrument,
baut die Seite neu und pusht ins Repo. Details siehe `DEPLOY.md`.
