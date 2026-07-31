# Grain d'Or / Nounkoun

Assistant agricole pour paysans béninois — 37 cultures, raisonnement en 5 étapes,
diagnostic ravageurs, marketplace communautaire, forum, panneau admin.

Ce dépôt contient **deux versions indépendantes** de l'app. Choisis celle qui
correspond à ton besoin — les deux peuvent coexister, mais elles ne partagent
pas les mêmes fonctionnalités.

## Version A — App complète (serveur), déployée sur Render

C'est **la version principale**, en ligne sur Render, avec tout le fonctionnel :

- Fichiers : `main.py`, `raisonnement.py`, `cultures_37.json`, `frontend.html`, `admin.html`
- **Marketplace, Catalogue et Forum en direct** via Supabase (partagés entre tous les visiteurs)
- **Panneau admin** (`/admin`) pour ajouter/modifier/supprimer annonces, cultures, savoirs — sans coder
- Raisonnement agricole calculé côté serveur par `main.py` + `raisonnement.py`

**Déploiement** (déjà fait, pour référence si tu redéploies ailleurs) :
- Render → New → Web Service → connecter ce dépôt
- Build Command : `pip install -r requirements.txt`
- Start Command : `python main.py`
- App publique : `/` — Panneau admin : `/admin`

⚠️ Sur le plan gratuit Render, le serveur s'endort après 15 min d'inactivité
(~30-50s pour redémarrer au premier accès suivant).

## Version B — App statique hors-ligne (PWA), déployée sur GitHub Pages

Une version **allégée, installable comme une icône**, qui fonctionne **sans
connexion internet** après la première visite — pratique en zone rurale mal
couverte.

- Fichiers : `index.html`, `reasoning-engine.js`, `cultures_37.json`, `manifest.json`, `sw.js`
- Le raisonnement agricole tourne **directement dans le téléphone du paysan**
  (`reasoning-engine.js` est une copie fidèle de `raisonnement.py`)
- **Pas de Marketplace/Catalogue/Forum en direct** — cette version n'est pas
  connectée à Supabase. Le Forum y est un carnet **local à l'appareil** uniquement.
- **Pas de panneau admin** — rien à administrer puisque tout est statique.

**Déploiement** (déjà fait) : GitHub → Settings → Pages → source = branche
`main`. En ligne à `https://mensahmosees-cloudnounkounia.github.io/grain-dor/`.

## Fichiers annexes (pas encore branchés)

- `fon_audio.py` — présent dans le dépôt, aucune route ne l'appelle encore dans `main.py`
- `scraper_aic_fao.py` — script pour enrichir `cultures_37.json` à partir de sources FAO/AIC

## Sécurité du panneau admin

`/admin` n'est lié nulle part dans l'app publique — seul toi connais l'URL.
Même devinée, aucune modification n'est possible sans se connecter avec le
compte Supabase créé dans Authentication → Users. Les policies RLS bloquent
toute écriture sans session valide.
