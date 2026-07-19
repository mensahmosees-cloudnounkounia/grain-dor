# Grain d'Or — backend

## Fichiers

- **frontend.html** — le beau visuel (racine qui pousse, grille 37 cultures, 10 sols) **branché sur le vrai backend** via `fetch('/api/raisonner')`. Ce n'est plus une simulation JS : les chiffres viennent réellement de `raisonnement.py`.
- **cultures_37.json** — base de données des 37 cultures (eau, cycle, pH, engrais, calendrier, rendement, prix, et un diagnostic ravageurs/maladies par culture avec traitement bio et économie chiffrée).
- **raisonnement.py** — moteur de raisonnement : irrigation, calcul économique (gagner plus / dépenser moins), diagnostic ravageurs, calendrier, analyse de sol, gestion du risque météo, détection d'émotion. Zéro dépendance externe.
- **main.py** — serveur web (`http.server`, bibliothèque standard uniquement). Sert `frontend.html` sur `/`, expose `/api/raisonner` en JSON, garde `/legacy` (l'ancienne page 100% HTML sans JS) en secours.
- **fon_audio.py** — interface voix Fon/Français. **Honnête sur ses limites** : pas de vrai moteur Fon offline aujourd'hui, fallback sur la reconnaissance vocale du navigateur en français.
- **scraper_aic_fao.py** — gabarit de scraping de prix (AIC coton, FAO GIEWS). Sélecteurs à vérifier/ajuster.
- **requirements.txt** — le cœur ne dépend de rien ; `requests` + `beautifulsoup4` uniquement si tu utilises le scraper.

## Comment ça marche maintenant

1. `main.py` sert `frontend.html` tel quel sur `GET /`.
2. Quand le paysan touche « Raisonner + Irriguer », le JS de `frontend.html` appelle `GET /api/raisonner?culture=...&sol=...&pluie=...&surface=...&sympt=...` **sur le même serveur** (même origine, pas de CORS à gérer).
3. `main.py` route cet appel vers `raisonnement.raisonner()`, qui lit `cultures_37.json` et calcule tout pour de vrai.
4. Le JS anime les 5 étapes avec le texte réellement renvoyé par le serveur, puis affiche les vrais chiffres.
5. Si le serveur ne répond pas, l'interface affiche un message d'erreur clair — **elle n'invente jamais un résultat**.

⚠️ Important : `frontend.html` doit être servi PAR `main.py` (même domaine) pour que `fetch('/api/raisonner')` fonctionne. Si tu ouvres `frontend.html` seul dans un navigateur (double-clic, `file://`), le bouton affichera l'erreur de connexion — c'est normal et voulu, pas un bug caché.

## Lancer en local

```bash
cd grain-dor-backend
python3 main.py
# ouvre http://localhost:8000  → interface complète branchée sur le vrai backend
# http://localhost:8000/legacy → ancienne page simple, sans JS
```

## Déployer sur Render (comme l'ancien Nounkoun)

1. Pousse ce dossier sur un dépôt Git.
2. Sur Render : New → Web Service → connecte le repo.
3. Build command : (aucune, ou `pip install -r requirements.txt` si tu utilises le scraper)
4. Start command : `python3 main.py`
5. Render fournit automatiquement la variable `PORT` — déjà gérée dans `main.py`.

## Testé avant livraison

- `main.py` compile sans erreur (`py_compile`).
- `frontend.html` contient bien l'appel `fetch` et les tables de correspondance culture/sol.
- Serveur démarré en local : `GET /` renvoie bien `frontend.html` (200, ~31 Ko), `GET /api/raisonner` renvoie du JSON réel avec irrigation/bénéfice/diagnostic corrects, `GET /chemin-inconnu` renvoie 404.
- Testé un cas de diagnostic complet (Piment + symptôme "flétri") → retrouve bien le bon ravageur et son traitement.

## Ce qui reste à faire, honnêtement

- **fon_audio.py** : pas de vrai moteur vocal Fon branché — c'est un gabarit avec le TODO clairement indiqué. Le bouton micro de `frontend.html` reste une simulation visuelle.
- **Reconnaissance de photo (sol/culture/maladie par image)** : PAS implémentée. Aucun modèle de vision par ordinateur n'existe dans ce projet. Si un checklist ailleurs affirme que « la photo est reconnue », c'est faux tant que ce module n'existe pas.
- **scraper_aic_fao.py** : sélecteurs à vérifier sur les vraies pages (pas d'accès réseau pour les tester en direct).
- Les prix et rendements dans `cultures_37.json` sont des ordres de grandeur pour la démo, pas des cours de marché vérifiés en temps réel.
- Pas de compte paysan, pas de base de données persistante, pas de paiement (mobile money) — à construire pour une vraie mise en production.
