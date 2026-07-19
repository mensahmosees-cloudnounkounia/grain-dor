"""
fon_audio.py — Interface voix Fon / Français pour Grain d'Or

IMPORTANT — à lire avant d'utiliser ce module :
Il n'existe pas aujourd'hui de moteur de reconnaissance vocale (STT) ou de
synthèse vocale (TTS) Fon gratuit, léger et fiable, prêt à l'emploi hors
ligne. Ce fichier ne prétend donc PAS faire de la reconnaissance vocale Fon
« par magie ». Il fait deux choses honnêtes :

  1. Il définit une interface stable (transcrire, synthetiser) que le reste
     du code (main.py) peut appeler sans se soucier du moteur utilisé.
  2. Il fournit un mode de secours (fallback) qui s'appuie sur le
     reconnaissance vocale du NAVIGATEUR (Web Speech API, déjà utilisée
     dans main.py côté HTML avec r.lang='fr-FR') pour le français, et
     documente comment brancher un vrai moteur Fon plus tard.

Pistes réelles pour un moteur Fon hors-ligne, à évaluer par l'équipe :
  - Vosk (https://alphacephei.com/vosk/) : supporte peu de langues
    africaines à ce jour ; il faudrait entraîner/adapter un modèle Fon.
  - Coqui STT / Common Voice : Mozilla Common Voice a des campagnes de
    collecte pour des langues africaines ; vérifier si le Fon y est présent
    ou lancer une collecte communautaire.
  - Google Cloud Speech-to-Text : ne supporte pas le Fon nativement au
    moment de l'écriture de ce fichier ; à revérifier, ça évolue vite.
  - Solution pragmatique à court terme : liste de mots-clés Fon fréquents
    (voir FON_KEYWORDS ci-dessous) reconnus par correspondance texte, une
    fois qu'un premier passage de transcription brute (même approximative)
    a été fait.

Ce module est volontairement simple pour rester lisible et modifiable par
une petite équipe.
"""

from dataclasses import dataclass


# Quelques mots-clés Fon courants utiles au diagnostic, à compléter avec de
# vrais locuteurs Fon avant mise en production (liste non validée).
FON_KEYWORDS = {
    "vévi": "problème / souci",
    "jì": "pluie",
    "gle": "champ",
    "nú ɖuɖu": "nourriture / récolte",
}


@dataclass
class TranscriptionResult:
    texte: str
    langue_detectee: str
    confiance: float
    mode: str  # "navigateur", "mots_cles", "non_disponible"


def transcrire_audio(chemin_fichier_audio: str = None, texte_brut: str = None) -> TranscriptionResult:
    """Point d'entrée unique pour transcrire une entrée vocale.

    Dans l'état actuel du projet, la transcription se fait côté navigateur
    (Web Speech API en français, voir le bouton micro dans main.py). Cette
    fonction sert de point d'extension pour brancher un vrai moteur Fon
    plus tard sans changer le reste du code.
    """
    if texte_brut:
        return TranscriptionResult(
            texte=texte_brut,
            langue_detectee="fr",
            confiance=1.0,
            mode="navigateur",
        )

    if chemin_fichier_audio:
        # TODO: brancher ici un vrai moteur STT (Vosk / Coqui / autre) une
        # fois qu'un modèle Fon fiable existe. Pour l'instant on ne peut pas
        # transcrire de fichier audio côté serveur.
        return TranscriptionResult(
            texte="",
            langue_detectee="inconnue",
            confiance=0.0,
            mode="non_disponible",
        )

    return TranscriptionResult(texte="", langue_detectee="inconnue", confiance=0.0, mode="non_disponible")


def synthetiser_reponse(texte: str, langue: str = "fr") -> dict:
    """Prépare le texte pour une lecture à voix haute.

    Retourne les paramètres à donner à la synthèse vocale du navigateur
    (window.speechSynthesis côté JS) plutôt qu'un fichier audio, car aucun
    moteur TTS Fon fiable n'est disponible à ce jour.
    """
    return {
        "texte": texte,
        "langue": "fr-FR" if langue == "fr" else langue,
        "mode": "navigateur_web_speech_api",
        "note": "Pas de TTS Fon natif disponible ; utiliser le français en attendant un modèle Fon.",
    }


def cherche_mots_cles_fon(texte: str) -> list:
    """Repère les mots Fon connus dans un texte, pour amorcer un diagnostic
    même quand la transcription automatique n'est pas fiable à 100%.
    """
    texte = (texte or "").lower()
    return [mot for mot in FON_KEYWORDS if mot in texte]
