"""regles.py : les règles métier d'un épisode, au-delà de la forme du JSON.

contrat.py vérifie chaque champ isolément (type, valeurs permises, bornes).
Ce fichier vérifie ce qui relie plusieurs champs, et les règles de la bible :
nombre de plans, longueur de la voix off, compteur, « À suivre »...

verifier() renvoie la liste de TOUTES les erreurs trouvées (liste vide =
épisode conforme). Les messages sont écrits pour être renvoyés tels quels
au modèle, afin qu'il corrige tout en une seule fois.

Vérifier un épisode : python src\\meddah\\agents\\regles.py [chemin/episode.json]
"""

import sys
from pathlib import Path

from pydantic import ValidationError

import contrat
from contrat import Episode

# --- Règles de la bible -------------------------------------------------------

PLANS_MIN, PLANS_MAX = 8, 10
MOTS_MIN, MOTS_MAX = 90, 110
TEXTE_FIN = "À suivre"

# Styles qui affichent un montant, et le libellé imposé pour chacun.
LIBELLES = {
    "counter_small": "ARGENT",
    "counter_big": "ARGENT",
    "goal_big": "OBJECTIF",
}
STYLES_COMPTEUR = ("counter_small", "counter_big")  # le compteur (ARGENT)
STYLES_OBJECTIF = ("goal_big",)  # le but (OBJECTIF)

ESPACE_INSECABLE = "\u00a0"


# --- Montants -----------------------------------------------------------------

def formater_montant(euros: int) -> str:
    """37 -> « 37 € », 3400 -> « 3 400 € », avec des espaces insécables
    (pour ne jamais couper le montant sur deux lignes à l'écran)."""
    signe = "-" if euros < 0 else ""
    chiffres = f"{abs(euros):,}".replace(",", ESPACE_INSECABLE)
    return f"{signe}{chiffres}{ESPACE_INSECABLE}€"


def lire_montant(texte: str) -> int | None:
    """« 3 400 € » -> 3400. Accepte les espaces normales ou insécables et un
    signe moins. Renvoie None si le texte n'est pas un montant en euros."""
    brut = "".join(texte.split())  # retire toutes les espaces, insécables comprises
    if not brut.endswith("€"):
        return None
    brut = brut[:-1].replace("−", "-")  # signe moins typographique
    try:
        return int(brut)
    except ValueError:
        return None


# --- Mesures ------------------------------------------------------------------

def compter_mots(episode: Episode) -> int:
    """Nombre de mots de voix off de tout l'épisode."""
    return sum(len(plan.voice_text.split()) for plan in episode.shots if plan.voice_text)


def _montants(episode: Episode, styles: tuple[str, ...]) -> list[int]:
    """Montants lisibles affichés avec ces styles, dans l'ordre des plans."""
    montants = []
    for plan in episode.shots:
        for texte in plan.overlays:
            if texte.style in styles:
                montant = lire_montant(texte.text)
                if montant is not None:
                    montants.append(montant)
    return montants


def compteur_depart(episode: Episode) -> int | None:
    """Premier montant du compteur ARGENT (None si l'épisode n'en affiche pas)."""
    montants = _montants(episode, STYLES_COMPTEUR)
    return montants[0] if montants else None


def compteur_final(episode: Episode) -> int | None:
    """Dernier montant du compteur ARGENT : le compteur de départ de l'épisode suivant."""
    montants = _montants(episode, STYLES_COMPTEUR)
    return montants[-1] if montants else None


# --- Les règles : chacune renvoie une liste de messages d'erreur --------------

def regle_nombre_de_plans(episode: Episode) -> list[str]:
    n = len(episode.shots)
    if PLANS_MIN <= n <= PLANS_MAX:
        return []
    return [f"L'épisode a {n} plans : il en faut entre {PLANS_MIN} et {PLANS_MAX}."]


def regle_nombre_de_mots(episode: Episode) -> list[str]:
    n = compter_mots(episode)
    if MOTS_MIN <= n <= MOTS_MAX:
        return []
    return [f"La voix off fait {n} mots : il en faut entre {MOTS_MIN} et {MOTS_MAX}."]


def regle_numerotation(episode: Episode) -> list[str]:
    ids = [plan.id for plan in episode.shots]
    attendus = list(range(1, len(ids) + 1))
    if ids == attendus:
        return []
    return [f"Les plans doivent être numérotés {attendus} dans l'ordre, reçu {ids}."]


def regle_voix_ou_duree(episode: Episode) -> list[str]:
    erreurs = []
    for plan in episode.shots:
        parle = bool(plan.voice_text)
        if parle and plan.duration is not None:
            erreurs.append(
                f"Plan {plan.id} : un plan avec voix ne doit pas avoir de « duration » "
                f"(sa durée est calculée à partir de la voix)."
            )
        if parle and not plan.voice:
            erreurs.append(f"Plan {plan.id} : « voice_text » est rempli mais « voice » manque.")
        if not parle and plan.voice:
            erreurs.append(f"Plan {plan.id} : « voice » est rempli mais « voice_text » est vide.")
        if not parle and plan.duration is None:
            erreurs.append(f"Plan {plan.id} : un plan sans voix doit avoir une « duration ».")
    return erreurs


def regle_noms_de_fichiers(episode: Episode) -> list[str]:
    erreurs = []
    for plan in episode.shots:
        image = f"images/plan{plan.id:02d}.jpg"
        if plan.image != image:
            erreurs.append(f"Plan {plan.id} : « image » doit valoir « {image} », reçu « {plan.image} ».")
        voix = f"audio/voix{plan.id:02d}.mp3"
        if plan.voice and plan.voice != voix:
            erreurs.append(f"Plan {plan.id} : « voice » doit valoir « {voix} », reçu « {plan.voice} ».")
    return erreurs


def regle_texte_colle_a_l_image(episode: Episode) -> list[str]:
    # Un texte « space: image » suit la caméra du monteur : impossible sur un
    # plan animé, dont le mouvement vient du modèle vidéo. Le monteur refuse.
    return [
        f"Plan {plan.id} : un plan animé ne peut pas porter un texte « space: image »."
        for plan in episode.shots
        if plan.animation and any(texte.space == "image" for texte in plan.overlays)
    ]


def regle_boites(episode: Episode) -> list[str]:
    erreurs = []
    for plan in episode.shots:
        for texte in plan.overlays:
            x0, y0, x1, y1 = texte.box
            if not (x0 < x1 and y0 < y1):
                erreurs.append(
                    f"Plan {plan.id}, texte « {texte.text} » : la boîte [x0, y0, x1, y1] "
                    f"doit vérifier x0 < x1 et y0 < y1, reçu {list(texte.box)}."
                )
    return erreurs


def regle_libelles(episode: Episode) -> list[str]:
    erreurs = []
    for plan in episode.shots:
        for texte in plan.overlays:
            attendu = LIBELLES.get(texte.style)  # None pour les styles sans libellé
            if texte.label != attendu:
                erreurs.append(
                    f"Plan {plan.id}, style « {texte.style} » : le libellé doit être "
                    f"{attendu!r}, reçu {texte.label!r}."
                )
    return erreurs


def regle_expediteur(episode: Episode) -> list[str]:
    erreurs = []
    for plan in episode.shots:
        for texte in plan.overlays:
            if texte.style == "message_card" and not texte.sender:
                erreurs.append(f"Plan {plan.id} : une carte de message doit avoir un « sender ».")
            if texte.style != "message_card" and texte.sender:
                erreurs.append(f"Plan {plan.id} : « sender » est réservé au style « message_card ».")
    return erreurs


def regle_a_suivre(episode: Episode) -> list[str]:
    erreurs = []
    dernier = episode.shots[-1]
    fins = [texte for texte in dernier.overlays if texte.style == "to_be_continued"]
    if len(fins) != 1 or fins[0].text != TEXTE_FIN:
        erreurs.append(
            f"Le dernier plan doit porter un seul texte « to_be_continued » valant « {TEXTE_FIN} »."
        )
    for plan in episode.shots[:-1]:
        if any(texte.style == "to_be_continued" for texte in plan.overlays):
            erreurs.append(f"Plan {plan.id} : « to_be_continued » est réservé au dernier plan.")
    return erreurs


def regle_montants_lisibles(episode: Episode) -> list[str]:
    return [
        f"Plan {plan.id}, style « {texte.style} » : « {texte.text} » n'est pas un montant "
        f"en euros (attendu, par exemple, « {formater_montant(3400)} »)."
        for plan in episode.shots
        for texte in plan.overlays
        if texte.style in LIBELLES and lire_montant(texte.text) is None
    ]


REGLES = [
    regle_nombre_de_plans,
    regle_nombre_de_mots,
    regle_numerotation,
    regle_voix_ou_duree,
    regle_noms_de_fichiers,
    regle_texte_colle_a_l_image,
    regle_boites,
    regle_libelles,
    regle_expediteur,
    regle_a_suivre,
    regle_montants_lisibles,
]


def regle_compteur(
    episode: Episode, depart_attendu: int | None, objectif_attendu: int | None
) -> list[str]:
    """Continuité avec le reste de la série : seules règles qui ont besoin
    d'une information extérieure à l'épisode."""
    erreurs = []
    depart = compteur_depart(episode)
    if depart is None:
        erreurs.append("L'épisode n'affiche aucun compteur ARGENT : c'est la signature de la série.")
    elif depart_attendu is not None and depart != depart_attendu:
        erreurs.append(
            f"Le compteur doit démarrer à {formater_montant(depart_attendu)} "
            f"(fin de l'épisode précédent), reçu {formater_montant(depart)}."
        )
    if objectif_attendu is not None:
        for montant in _montants(episode, STYLES_OBJECTIF):
            if montant != objectif_attendu:
                erreurs.append(
                    f"L'objectif affiché doit être {formater_montant(objectif_attendu)}, "
                    f"reçu {formater_montant(montant)}."
                )
    return erreurs


def verifier(
    episode: Episode,
    depart_attendu: int | None = None,
    objectif_attendu: int | None = None,
) -> list[str]:
    """Renvoie toutes les erreurs de règles métier (liste vide = conforme).

    depart_attendu   : compteur final de l'épisode précédent (None = non vérifié).
    objectif_attendu : objectif de l'arc en cours (None = non vérifié).
    """
    erreurs = []
    for regle in REGLES:
        erreurs += regle(episode)
    erreurs += regle_compteur(episode, depart_attendu, objectif_attendu)
    return erreurs


if __name__ == "__main__":
    chemin = Path(sys.argv[1]) if len(sys.argv) > 1 else contrat.EPISODE_PAR_DEFAUT
    try:
        episode = contrat.charger_episode(chemin)
    except ValidationError as erreur:
        print(f"INVALIDE (forme) : {chemin}")
        print(erreur)
        sys.exit(1)

    depart, final = compteur_depart(episode), compteur_final(episode)
    print(f"{len(episode.shots)} plans, {compter_mots(episode)} mots de voix off.")
    if depart is not None and final is not None:
        print(f"Compteur : {formater_montant(depart)} au départ, {formater_montant(final)} à la fin.")

    erreurs = verifier(episode)
    if erreurs:
        print(f"NON CONFORME : {len(erreurs)} erreur(s)")
        for message in erreurs:
            print(" -", message)
        sys.exit(1)
    print("CONFORME : aucune règle métier enfreinte.")