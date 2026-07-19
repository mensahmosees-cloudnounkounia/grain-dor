"""
scraper_aic_fao.py — Récupération de prix de marché (AIC coton + FAO)

À LIRE AVANT D'UTILISER CE FICHIER :
Je n'ai pas d'accès réseau depuis mon environnement de développement pour
vérifier en direct la structure HTML actuelle des sites de l'AIC (Association
Interprofessionnelle du Coton, Bénin) ou des pages de prix de la FAO. Ce
fichier est donc un GABARIT fonctionnel et honnête : la logique (requêtes
HTTP, cache local, gestion d'erreur, fréquence de rafraîchissement) est
complète et prête à l'emploi, mais les sélecteurs CSS/XPath exacts doivent
être vérifiés et ajustés par quelqu'un ayant accès au site réel, car la mise
en page peut changer à tout moment. Le code ne renvoie jamais un prix
inventé : en cas d'échec de récupération, il retourne clairement
`succes: False` plutôt qu'une fausse valeur.

Deux sources visées :
  1. AIC Bénin — prix officiel du coton graine, généralement publié en
     début de campagne (autour de septembre-octobre).
  2. FAO GIEWS / FAOSTAT — prix internationaux indicatifs pour comparaison
     (maïs, riz, arachide...).

Dépendances : requests, beautifulsoup4 (voir requirements.txt).
"""

import json
import os
import time
import datetime

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None

CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prix_cache.json")
CACHE_DUREE_SECONDES = 6 * 3600  # 6h : les prix de marché ne changent pas à la minute

HEADERS = {
    "User-Agent": "GrainDor-Agri-Assistant/1.0 (usage agricole non commercial)"
}

# URLs indicatives — À VÉRIFIER ET METTRE À JOUR avant mise en production.
AIC_URL = "https://aic-benin.org/"          # page d'accueil AIC, à remplacer par l'URL exacte de la page prix
FAO_GIEWS_URL = "https://www.fao.org/giews/prices/en/"  # portail de prix FAO GIEWS


def _lire_cache() -> dict:
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _ecrire_cache(data: dict) -> None:
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _cache_valide(entree: dict) -> bool:
    if not entree or "recupere_le" not in entree:
        return False
    age = time.time() - entree["recupere_le"]
    return age < CACHE_DUREE_SECONDES


def scrape_prix_coton_aic() -> dict:
    """Récupère le prix officiel du coton graine publié par l'AIC.

    Retourne toujours un dict avec `succes` explicite. Ne jamais utiliser
    cette fonction pour AFFICHER un prix sans vérifier `succes`.
    """
    cache = _lire_cache()
    if _cache_valide(cache.get("coton_aic", {})):
        return cache["coton_aic"]

    if requests is None:
        return {"succes": False, "raison": "requests/beautifulsoup4 non installés (voir requirements.txt)"}

    try:
        reponse = requests.get(AIC_URL, headers=HEADERS, timeout=10)
        reponse.raise_for_status()
    except Exception as e:
        return {"succes": False, "raison": f"Échec de connexion à l'AIC: {e}"}

    soup = BeautifulSoup(reponse.text, "html.parser")

    # --- SÉLECTEUR À AJUSTER ---
    # Ceci est un exemple générique : chercher un élément contenant "FCFA/kg"
    # près d'un mot-clé "coton". À remplacer par le vrai sélecteur une fois
    # la page réelle inspectée (clic droit > Inspecter sur le site AIC).
    prix_element = soup.find(string=lambda s: s and "FCFA" in s and "kg" in s.lower())

    if not prix_element:
        return {
            "succes": False,
            "raison": "Élément de prix non trouvé — la structure de la page a probablement changé, sélecteur à mettre à jour.",
        }

    resultat = {
        "succes": True,
        "source": "AIC Bénin",
        "texte_brut": prix_element.strip(),
        "recupere_le": time.time(),
        "date_lisible": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    cache["coton_aic"] = resultat
    _ecrire_cache(cache)
    return resultat


def scrape_prix_fao(commodite: str = "maize", pays: str = "Benin") -> dict:
    """Récupère un prix indicatif FAO GIEWS pour une denrée et un pays.

    Comme pour l'AIC, la structure exacte du portail FAO doit être vérifiée
    en direct : ce gabarit montre la mécanique (requête, parsing, cache,
    gestion d'erreur) mais le sélecteur est à confirmer.
    """
    cle_cache = f"fao_{commodite}_{pays}"
    cache = _lire_cache()
    if _cache_valide(cache.get(cle_cache, {})):
        return cache[cle_cache]

    if requests is None:
        return {"succes": False, "raison": "requests/beautifulsoup4 non installés (voir requirements.txt)"}

    try:
        reponse = requests.get(FAO_GIEWS_URL, headers=HEADERS, timeout=10)
        reponse.raise_for_status()
    except Exception as e:
        return {"succes": False, "raison": f"Échec de connexion à la FAO: {e}"}

    soup = BeautifulSoup(reponse.text, "html.parser")

    # --- SÉLECTEUR À AJUSTER --- (le portail FAO GIEWS charge souvent les
    # données par JavaScript / API interne ; il faudra probablement passer
    # par leur API de données plutôt que scraper le HTML rendu).
    table = soup.find("table")
    if not table:
        return {
            "succes": False,
            "raison": "Tableau de prix non trouvé — le portail FAO charge peut-être les données en JavaScript ; envisager leur API officielle plutôt que le scraping HTML.",
        }

    resultat = {
        "succes": True,
        "source": "FAO GIEWS",
        "commodite": commodite,
        "pays": pays,
        "recupere_le": time.time(),
        "date_lisible": datetime.datetime.now().isoformat(timespec="seconds"),
        "note": "Contenu brut à parser précisément une fois la structure réelle confirmée.",
    }
    cache[cle_cache] = resultat
    _ecrire_cache(cache)
    return resultat


if __name__ == "__main__":
    print("Test AIC :", scrape_prix_coton_aic())
    print("Test FAO :", scrape_prix_fao())
