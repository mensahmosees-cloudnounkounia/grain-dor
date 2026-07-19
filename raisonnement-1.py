"""
raisonnement.py — Moteur de raisonnement agricole de Nounkoun / Grain d'Or

Ce module contient toute l'intelligence "métier" : lecture de la base
cultures_37.json, calcul d'irrigation, calcul économique (gagner plus /
dépenser moins), diagnostic de ravageurs et maladies, calendrier cultural,
analyse de sol, gestion du risque météo, et détection d'émotion simple
dans le texte du paysan.

Aucune dépendance externe : uniquement la bibliothèque standard, pour
pouvoir tourner sur un petit serveur peu puissant, hors ligne.
"""

import json
import os
import re
import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cultures_37.json")

# ---------------------------------------------------------------------------
# Chargement de la base de connaissance
# ---------------------------------------------------------------------------

_cultures_cache = None


def load_cultures(path: str = DB_PATH) -> dict:
    """Charge cultures_37.json une seule fois et le garde en mémoire."""
    global _cultures_cache
    if _cultures_cache is None:
        with open(path, "r", encoding="utf-8") as f:
            _cultures_cache = json.load(f)
    return _cultures_cache


def liste_cultures() -> list:
    return list(load_cultures().keys())


# ---------------------------------------------------------------------------
# Types de sol du Bénin et leur effet sur le besoin en eau
# ---------------------------------------------------------------------------

SOLS = {
    "argileux":       {"label": "Argileux",        "mult": 0.70, "note": "Retient bien l'eau"},
    "sableux":        {"label": "Sableux",         "mult": 1.25, "note": "Draine vite, sèche fort"},
    "limoneux":       {"label": "Limoneux",        "mult": 1.00, "note": "Équilibré, idéal"},
    "terre_de_barre": {"label": "Terre de barre",  "mult": 0.85, "note": "Plateau sud, ferralitique"},
    "ferrugineux":    {"label": "Ferrugineux",     "mult": 1.10, "note": "Nord, croûte en surface"},
    "bas_fond":       {"label": "Bas-fond",        "mult": 0.55, "note": "Zone humide, hydromorphe"},
    "sablo_argileux": {"label": "Sablo-argileux",  "mult": 0.95, "note": "Mixte, bon compromis"},
    "sol_noir":       {"label": "Sol noir",        "mult": 0.75, "note": "Vertisol, craquelle au sec"},
    "terre_rouge":    {"label": "Terre rouge",     "mult": 1.05, "note": "Latérite, riche en fer"},
    "terre_a_grain":  {"label": "Terre à grain",   "mult": 1.35, "note": "Graveleuse, draine très vite"},
}

PRIX_EAU_FCFA_L = 1.7  # coût moyen indicatif de l'eau d'irrigation, FCFA/litre


# ---------------------------------------------------------------------------
# 1) Irrigation
# ---------------------------------------------------------------------------

def conseil_irrigation(culture: str, sol: str, pluie_mm: float) -> dict:
    """Calcule la dose d'irrigation conseillée et l'économie réalisée.

    Retourne un dict structuré (pas juste une phrase) pour que main.py
    puisse l'afficher ou le sérialiser en JSON pour une appli mobile.
    """
    db = load_cultures()
    culture_data = db.get(culture)
    if not culture_data:
        return {"erreur": f"Culture inconnue: {culture}"}

    sol_data = SOLS.get(sol, SOLS["limoneux"])
    besoin_base = culture_data["eau_l_m2"]

    if pluie_mm and pluie_mm > 20:
        # Pluie suffisante : on économise l'irrigation
        economie = round(besoin_base * sol_data["mult"] * PRIX_EAU_FCFA_L * 10)  # sur 10m2 ex.
        return {
            "action": "stop",
            "message": f"Pluie de {pluie_mm}mm prévue : pas besoin d'irriguer.",
            "economie_fcfa": economie,
            "sol": sol_data["label"],
        }

    dose = round(besoin_base * sol_data["mult"], 1)
    cout = round(dose * PRIX_EAU_FCFA_L)

    return {
        "action": "irriguer",
        "dose_litres_m2": dose,
        "cout_fcfa": cout,
        "sol": sol_data["label"],
        "conseil": culture_data["irrigation_conseil"],
        "message": (
            f"Irrigue {dose} litres/m² pour {culture}. "
            f"Coût eau environ {cout} F. Sol {sol_data['label'].lower()} ({sol_data['note'].lower()})."
        ),
    }


# ---------------------------------------------------------------------------
# 2) Calcul économique — gagner plus / dépenser moins
# ---------------------------------------------------------------------------

def calcul_economique(culture: str, surface_ha: float = 1.0, cout_intrants_fcfa: float = 15000) -> dict:
    """Estime le revenu, les coûts et le bénéfice net pour une surface donnée.

    C'est volontairement une estimation simplifiée (pas un cours du marché
    en temps réel) : elle sert de repère de décision, pas de facture.
    """
    db = load_cultures()
    culture_data = db.get(culture)
    if not culture_data:
        return {"erreur": f"Culture inconnue: {culture}"}

    rendement = culture_data["rendement_kg_ha"] * surface_ha
    prix = culture_data["prix_fcfa_kg"]
    revenu_brut = rendement * prix
    cout_total = cout_intrants_fcfa * surface_ha
    benefice_net = revenu_brut - cout_total

    def _fcfa(n):
        return f"{round(n):,}".replace(",", " ")

    return {
        "surface_ha": surface_ha,
        "rendement_kg": round(rendement),
        "revenu_brut_fcfa": round(revenu_brut),
        "cout_intrants_fcfa": round(cout_total),
        "benefice_net_fcfa": round(benefice_net),
        "message": (
            f"{culture} sur {surface_ha}ha : revenu brut {_fcfa(revenu_brut)}F, "
            f"coûts {_fcfa(cout_total)}F, bénéfice net {_fcfa(benefice_net)}F."
        ),
    }


# ---------------------------------------------------------------------------
# 3) Diagnostic ravageurs / maladies (37 cultures)
# ---------------------------------------------------------------------------

def diagnostic_maladie(culture: str, symptome_texte: str) -> dict:
    """Cherche un ravageur/maladie connu pour la culture à partir de mots-clés
    tapés ou dictés par le paysan (ex: "feuille jaune", "trou", "chenille").
    """
    db = load_cultures()
    culture_data = db.get(culture)
    if not culture_data:
        return {"erreur": f"Culture inconnue: {culture}"}

    texte = (symptome_texte or "").lower().strip()
    if not texte:
        return {
            "trouve": False,
            "message": f"Décris le symptôme sur {culture} (ex: feuille jaune, trou, chenille, pourri).",
        }

    for ravageur in culture_data.get("ravageurs", []):
        for cle in ravageur["cles"]:
            if cle in texte:
                cout_fmt = f"{ravageur['cout_evite']:,}".replace(",", " ")
                return {
                    "trouve": True,
                    "nom": ravageur["nom"],
                    "traitement": ravageur["traitement"],
                    "cout_evite_fcfa": ravageur["cout_evite"],
                    "message": (
                        f"{ravageur['nom']} probable sur {culture}. "
                        f"{ravageur['traitement']}. Économie estimée {cout_fmt}F "
                        f"vs traitement chimique systématique."
                    ),
                }

    return {
        "trouve": False,
        "message": (
            f"Symptôme non reconnu pour {culture}. Surveille 2 jours, prends une photo, "
            f"évite un traitement chimique systématique tant que le doute n'est pas levé."
        ),
    }


# ---------------------------------------------------------------------------
# 4) Calendrier cultural
# ---------------------------------------------------------------------------

def calendrier(culture: str, date_depart: datetime.date = None) -> dict:
    db = load_cultures()
    culture_data = db.get(culture)
    if not culture_data:
        return {"erreur": f"Culture inconnue: {culture}"}

    depart = date_depart or datetime.date.today()
    fertilisation = depart + datetime.timedelta(days=30)
    traitement_prevention = depart + datetime.timedelta(days=45)
    recolte = depart + datetime.timedelta(days=culture_data["cycle_jours"])

    return {
        "semis_periode": culture_data["semis"],
        "date_fertilisation": fertilisation.isoformat(),
        "engrais": culture_data["engrais"],
        "date_traitement_preventif": traitement_prevention.isoformat(),
        "date_recolte_estimee": recolte.isoformat(),
        "cycle_jours": culture_data["cycle_jours"],
        "message": (
            f"{culture} : semis {culture_data['semis']} · fertilisation le {fertilisation} "
            f"({culture_data['engrais']}) · récolte estimée le {recolte} "
            f"(dans {culture_data['cycle_jours']}j)."
        ),
    }


# ---------------------------------------------------------------------------
# 5) Analyse de sol
# ---------------------------------------------------------------------------

def analyse_sol(culture: str, pH, humidite_pct, fertilite: str = "moyenne") -> dict:
    db = load_cultures()
    culture_data = db.get(culture, {})
    conseils = []

    try:
        pH = float(pH)
    except (TypeError, ValueError):
        pH = 6.0
    try:
        humidite_pct = float(humidite_pct)
    except (TypeError, ValueError):
        humidite_pct = 50.0

    ph_min = culture_data.get("ph_min", 5.5)
    ph_max = culture_data.get("ph_max", 7.0)

    if pH < ph_min:
        conseils.append("pH trop acide pour cette culture : ajoute cendre de bois (500kg/ha) ou chaux agricole.")
    elif pH > ph_max:
        conseils.append("pH trop basique pour cette culture : ajoute compost acide ou fumier bien décomposé.")
    else:
        conseils.append("pH dans la bonne fourchette pour cette culture.")

    if humidite_pct < 30:
        conseils.append("Sol sec : paillage conseillé + arrosage léger d'appoint.")
    elif humidite_pct > 80:
        conseils.append("Sol très humide : vérifie le drainage pour éviter la pourriture des racines.")

    if fertilite == "faible":
        conseils.append("Fertilité faible : 5T de compost/ha + rotation avec une légumineuse (niébé, soja).")

    conseils.append("Enregistre ces mesures (traçabilité) : jusqu'à +15% de valeur à la vente.")

    return {"pH": pH, "humidite_pct": humidite_pct, "conseils": conseils, "message": " ".join(conseils)}


# ---------------------------------------------------------------------------
# 6) Gestion du risque météo
# ---------------------------------------------------------------------------

def gestion_risque(culture: str, pluie_prevue_mm: float, vent_fort: bool = False) -> dict:
    alertes = []
    niveau = "faible"

    if pluie_prevue_mm and pluie_prevue_mm > 40:
        niveau = "élevé"
        alertes.append("Pluie forte prévue (>40mm) : creuse des rigoles d'évacuation avant la pluie.")
    elif pluie_prevue_mm and pluie_prevue_mm > 20:
        niveau = "modéré"
        alertes.append("Pluie significative prévue : pas besoin d'irriguer, surveille le drainage.")

    if vent_fort:
        niveau = "élevé" if niveau != "élevé" else niveau
        alertes.append(f"Vent violent annoncé : tuteure les plants de {culture} sensibles à la casse.")

    if not alertes:
        alertes.append("Aucun risque météo majeur signalé pour le moment.")

    return {"niveau": niveau, "alertes": alertes, "message": " ".join(alertes)}


# ---------------------------------------------------------------------------
# 7) Détection d'émotion simple (pour adapter le ton de la réponse)
# ---------------------------------------------------------------------------

EMOTIONS = {
    "content": ("😊💪", "Tu es content, c'est mérité !"),
    "triste": ("😢🌱", "Je comprends, la terre est parfois dure. On avance ensemble."),
    "fier": ("😎🔥", "Bravo, continue comme ça !"),
    "inquiet": ("😰🌧️", "Pas de panique, on regarde la situation ensemble."),
    "neutre": ("🤔🌾", "Je t'écoute, parlons de ton champ."),
}

_MOTS_CONTENT = ["merci", "content", "bien", "fort"]
_MOTS_TRISTE = ["perdu", "triste", "mort", "malade", "peur"]
_MOTS_FIER = ["réussi", "reussi", "gagné", "gagne"]
_MOTS_INQUIET = ["pluie", "sécheresse", "secheresse", "vent", "inquiet"]


def detecter_emotion(texte: str) -> dict:
    t = (texte or "").lower()
    if any(m in t for m in _MOTS_CONTENT):
        cle = "content"
    elif any(m in t for m in _MOTS_TRISTE):
        cle = "triste"
    elif any(m in t for m in _MOTS_FIER):
        cle = "fier"
    elif any(m in t for m in _MOTS_INQUIET):
        cle = "inquiet"
    else:
        cle = "neutre"
    emoji, message = EMOTIONS[cle]
    return {"emotion": cle, "emoji": emoji, "message": message}


# ---------------------------------------------------------------------------
# 8) Raisonnement complet en une seule fois (utilisé par main.py)
# ---------------------------------------------------------------------------

def raisonner(culture: str, sol: str, pluie_mm: float, surface_ha: float = 1.0,
              pH=None, humidite_pct=None, fertilite: str = "moyenne",
              symptome_texte: str = "", texte_utilisateur: str = "") -> dict:
    """Assemble les 5 étapes de raisonnement de Nounkoun / Grain d'Or :
    intention -> contexte -> économie -> risque -> plan.
    """
    return {
        "1_intention": {"culture": culture, "sol": SOLS.get(sol, {}).get("label", sol)},
        "2_contexte": analyse_sol(culture, pH, humidite_pct, fertilite),
        "3_economie": {
            "irrigation": conseil_irrigation(culture, sol, pluie_mm),
            "benefice": calcul_economique(culture, surface_ha),
        },
        "4_risque": {
            "meteo": gestion_risque(culture, pluie_mm),
            "diagnostic": diagnostic_maladie(culture, symptome_texte) if symptome_texte else None,
        },
        "5_plan": calendrier(culture),
        "emotion": detecter_emotion(texte_utilisateur) if texte_utilisateur else None,
    }
