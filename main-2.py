"""
main.py — Serveur web de Grain d'Or (ex-Nounkoun)

Sert une page HTML légère (pas de framework front, pas de build step) qui
appelle raisonnement.py pour produire :
  - un conseil d'irrigation chiffré
  - un calcul économique (gagner plus / dépenser moins)
  - un diagnostic ravageurs/maladies pour les 37 cultures
  - un calendrier cultural
  - une gestion du risque météo

Zéro dépendance externe : uniquement http.server (bibliothèque standard),
pour pouvoir tourner sur un petit hébergement (type Render, free tier).
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
import os

import raisonnement as R

PORT = int(os.environ.get("PORT", "8000"))
FRONTEND_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend.html")

_frontend_cache = None


def load_frontend() -> bytes:
    """Lit frontend.html une seule fois et le garde en mémoire (petit hébergement)."""
    global _frontend_cache
    if _frontend_cache is None:
        with open(FRONTEND_PATH, "r", encoding="utf-8") as f:
            _frontend_cache = f.read().encode("utf-8")
    return _frontend_cache


def render_options(items, selected):
    return "".join(
        f'<option value="{key}" {"selected" if key == selected else ""}>{val}</option>'
        for key, val in items
    )


def render_page(params: dict) -> str:
    culture = params.get("culture", "Maïs")
    sol = params.get("sol", "argileux")
    pluie = float(params.get("pluie", "5") or 5)
    surface = float(params.get("surface", "1") or 1)
    ph = params.get("ph", "6")
    hum = params.get("hum", "50")
    fert = params.get("fert", "moyenne")
    sympt = params.get("sympt", "")
    q = params.get("q", "")

    resultat = R.raisonner(
        culture=culture, sol=sol, pluie_mm=pluie, surface_ha=surface,
        pH=ph, humidite_pct=hum, fertilite=fert,
        symptome_texte=sympt, texte_utilisateur=q,
    )

    emo = resultat["emotion"] or R.detecter_emotion("")
    irrigation = resultat["3_economie"]["irrigation"]
    benefice = resultat["3_economie"]["benefice"]
    risque = resultat["4_risque"]["meteo"]
    diagnostic = resultat["4_risque"]["diagnostic"]
    plan = resultat["5_plan"]
    contexte = resultat["2_contexte"]

    cultures_opts = render_options(
        [(c, c) for c in R.liste_cultures()], culture
    )
    sols_opts = render_options(
        [(k, v["label"]) for k, v in R.SOLS.items()], sol
    )

    diagnostic_html = ""
    if diagnostic:
        classe = "money" if diagnostic.get("trouve") else "alert"
        diagnostic_html = f'<div class="card"><h3>📸 Diagnostic {culture}</h3><div class="{classe}"><b>{diagnostic["message"]}</b></div></div>'

    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Grain d'Or — Assistant Paysan</title>
<style>
  body{{background:#F2E9D8;font-family:sans-serif;padding:14px;color:#221A10;max-width:480px;margin:0 auto}}
  .card{{background:#FBF6EC;padding:16px;border-radius:16px;margin:12px 0;box-shadow:0 2px 8px #0001}}
  .big{{font-size:34px;text-align:center}}
  input,select{{width:100%;padding:10px;margin:5px 0;border-radius:8px;border:1px solid #ccc;box-sizing:border-box}}
  button{{background:#B5502C;color:#fff;padding:13px;border:0;border-radius:10px;width:100%;font-weight:bold;font-size:15px}}
  .alert{{background:#F7E1DC;border-left:4px solid #A6402D;padding:10px;border-radius:6px}}
  .money{{background:#E5F1E2;border-left:4px solid #4E7C4F;padding:10px;border-radius:6px}}
  h1{{text-align:center;font-size:22px}}
  label{{font-size:13px;color:#5B4C39}}
</style></head><body>

<h1>🌾 GRAIN D'OR {emo['emoji']}</h1>
<div class="card"><div class="big">{emo['emoji']}</div><p><b>{emo['message']}</b> Je suis là pour t'aider à gagner plus, dépenser moins, et gérer les risques.</p></div>

<div class="card">
  <h3>🗣️ Parle (Fon/Français) — hors ligne</h3>
  <input name="q" id="q" value="{q}" placeholder="Ex: mon maïs a des feuilles jaunes">
  <button type="button" onclick="try{{let r=new (window.webkitSpeechRecognition||window.SpeechRecognition)();r.lang='fr-FR';r.onresult=e=>{{document.getElementById('q').value=e.results[0][0].transcript}};r.start()}}catch(e){{alert('Micro non disponible sur ce navigateur/hors-ligne.')}}">🎙️ Appuie et parle</button>
</div>

<form method="get">
<div class="card">
  <h3>🌱 Ta culture (37 disponibles)</h3>
  <select name="culture">{cultures_opts}</select>
  <label>Type de sol</label>
  <select name="sol">{sols_opts}</select>
  <label>Surface (ha)</label>
  <input name="surface" type="number" step="0.1" value="{surface}">
  <label>Pluie prévue cette semaine (mm)</label>
  <input name="pluie" type="number" value="{pluie}">
  <div class="money"><b>💧 {irrigation.get('message','')}</b></div>
</div>

<div class="card">
  <h3>💰 Combien tu peux gagner</h3>
  <div class="money"><b>{benefice.get('message','')}</b></div>
</div>

<div class="card">
  <h3>📅 Calendrier</h3>
  <p>{plan.get('message','')}</p>
</div>

<div class="card">
  <h3>🧪 Sol — analyse</h3>
  <label>pH (ex: 5.5)</label><input name="ph" value="{ph}">
  <label>Humidité % (ex: 60)</label><input name="hum" value="{hum}">
  <label>Fertilité</label>
  <select name="fert">
    <option {"selected" if fert=="moyenne" else ""}>moyenne</option>
    <option {"selected" if fert=="faible" else ""}>faible</option>
    <option {"selected" if fert=="bonne" else ""}>bonne</option>
  </select>
  <p>{contexte.get('message','')}</p>
</div>

<div class="card">
  <h3>🐛 Diagnostic ravageurs / maladies</h3>
  <label>Décris ce que tu vois</label>
  <input name="sympt" value="{sympt}" placeholder="Ex: feuille jaune, trou, chenille, pourri">
  <button type="submit">🔍 Diagnostiquer</button>
</div>

<div class="card alert">
  <h3>🌪️ Risque météo</h3>
  <p>{risque.get('message','')} (niveau: {risque.get('niveau','')})</p>
</div>

<button type="submit">🔄 Actualiser mes conseils</button>
</form>

{diagnostic_html}

<div class="card" style="background:#4E7C4F;color:#fff">
  <b>Grain d'Or :</b> 37 cultures, raisonnement en 5 étapes, calcul économique,
  diagnostic ravageurs, hors ligne. Tout tourne sur ce serveur, aucune donnée
  n'est envoyée ailleurs.
</div>

</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}

        if parsed.path in ("/", "/index.html"):
            body = load_frontend()
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/legacy":
            # Ancienne page 100% rendue côté serveur, sans JS de front dédié.
            # Gardée comme repli simple si frontend.html pose problème.
            html = render_page(params)
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/raisonner":
            # Endpoint JSON, utile pour une future appli mobile / frontend séparé
            import json
            culture = params.get("culture", "Maïs")
            sol = params.get("sol", "argileux")
            pluie = float(params.get("pluie", "5") or 5)
            surface = float(params.get("surface", "1") or 1)
            resultat = R.raisonner(
                culture=culture, sol=sol, pluie_mm=pluie, surface_ha=surface,
                pH=params.get("ph", "6"), humidite_pct=params.get("hum", "50"),
                fertilite=params.get("fert", "moyenne"),
                symptome_texte=params.get("sympt", ""),
                texte_utilisateur=params.get("q", ""),
            )
            body = json.dumps(resultat, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.send_header("Content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"404 - page inconnue. Essaie / ou /api/raisonner")

    def log_message(self, format, *args):
        # Log discret dans la console du serveur (utile sur Render)
        print(f"[GRAIN D'OR] {self.address_string()} - {format % args}")


if __name__ == "__main__":
    print(f"Grain d'Or — serveur démarré sur le port {PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
