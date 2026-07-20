# Deploy & tägliche Automatik (GitHub Pages)

## Einmalige Einrichtung (durch dich)
1. **Repo anlegen** – öffentlich (Gratis-Pages nur public), z. B. `wti-gold-silber-analysen`.
2. **GitHub Pages aktivieren** – Repo → Settings → Pages → Source: „Deploy from a branch", Branch `main`, Ordner `/ (root)`.
   URL danach: `https://<user>.github.io/<repo>/`
3. **Fine-grained Token** – GitHub → Settings → Developer settings → Fine-grained personal access tokens →
   - Repository access: **Only select repositories** → nur dieses Repo
   - Permissions → **Contents: Read and write** (optional zusätzlich **Pages: Read and write**, dann kann Pages per API aktiviert werden)
   - Ablaufdatum setzen, Token kopieren (`github_pat_…`)
4. Repo-Pfad (`user/repo`) + Token an Claude geben.

## Was der tägliche Lauf tut (Mo–Fr, 08:00 Europe/Berlin)
1. Recherchiert aktuelle Werte für WTI, Gold, Silber.
2. Schreibt je `data/<slug>/<JJJJ-MM-TT>.json`.
3. `python3 build_site.py` → neue Tagesseiten + aktualisierte Indizes + Archiv.
4. `git add -A && git commit && git push` ins Repo → Pages liefert automatisch aus.
5. Optional: Push-Nachricht aufs Handy mit Bias + Preis + Link.

## Sicherheit
Der Token wird in der geplanten Aufgabe hinterlegt. Nur auf dieses eine Repo begrenzt,
jederzeit in GitHub widerrufbar. Niemals das Account-Passwort verwenden.
