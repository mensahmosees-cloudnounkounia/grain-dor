# Grain d'Or — version statique (sans backend)

Cette version tourne **entièrement dans le navigateur**. Tous les calculs
(irrigation, économie, diagnostic, calendrier) qui étaient avant faits par
`main.py` + `raisonnement.py` sur un serveur sont maintenant faits par
`reasoning-engine.js`, directement sur le téléphone du paysan. Testé pour
donner exactement les mêmes résultats que la version serveur.

## Fichiers (les 5 doivent rester ensemble, mêmes noms)
- `index.html` — l'application
- `reasoning-engine.js` — le moteur de calcul (copie fidèle de raisonnement.py)
- `cultures_37.json` — les 37 cultures (même base que la version serveur)
- `manifest.json` — pour installer l'app comme une icône sur le téléphone (PWA)
- `sw.js` — fait fonctionner l'app hors-ligne après la première visite

## Déployer — 3 options gratuites

### Option A — Render Static Site
1. Upload ces 5 fichiers sur un dépôt GitHub (comme avant)
2. Sur Render : **New → Static Site**
3. **Build Command** : laisser vide
4. **Publish Directory** : `.`
5. Deploy

### Option B — GitHub Pages (encore plus simple, pas besoin de Render)
1. Dans le dépôt GitHub → **Settings → Pages**
2. Source : **Deploy from a branch** → `main` → `/ (root)`
3. Save. Le site est en ligne en 1-2 minutes à une adresse du type
   `https://tonpseudo.github.io/nom-du-depot/`

### Option C — Test local via Termux
```
cd nounkoun_static
python -m http.server 8000
```
Puis ouvrir `http://localhost:8000` dans le navigateur du téléphone.

## Ce qui a changé par rapport à la version serveur
- Plus besoin de payer Render ($0/mois garanti, pas de mise en veille)
- Fonctionne même sans connexion internet après la première visite (PWA)
- Les calculs sont strictement identiques (même formules, testées)
- Pour mettre à jour les cultures ou les savoirs paysans plus tard :
  modifier `cultures_37.json` et re-uploader — aucun code à toucher
