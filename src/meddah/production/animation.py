"""Montage, brique 6 : animer un plan fixe (image -> vidéo) avec Gemini Omni.

Un plan qui contient une clé "animation" dans episode.json peut être animé :

    "animation": {"prompt": "Slow push-in on Enzo's face, he blinks...", "resolution": "720p"}

Le résultat est enregistré dans <dossier de l'épisode>/animations/planXX.mp4. clip.py l'utilise
à la place du zoom sur image fixe ; s'il n'existe pas, le plan reste fixe (le montage ne casse jamais).

Usage (depuis la racine du repo) :
    python src/meddah/animation.py --estimer      -> coût estimé, SANS appeler l'API ni dépenser
    python src/meddah/animation.py 1 4 10         -> génère ces plans (demande confirmation) ;
                                                     une erreur sur un plan n'arrête pas les autres
    python src/meddah/animation.py 1 --forcer     -> regénère même si le fichier existe (nouveau coût)
    python src/meddah/animation.py 1 4 --oui      -> pas de confirmation

Pré-requis : pip install -U google-genai ; clé API dans la variable d'environnement
GEMINI_API_KEY ; facturation activée sur le compte (ce modèle n'a pas de palier gratuit).
"""
import base64
import csv
import math
import sys
import time
from datetime import datetime
from pathlib import Path

from episode import charger_episode, duree_plan
from etalonnage import etalonner

DOSSIER_PAR_DEFAUT = "series/enzo/episodes/ep01"
JOURNAL_COUTS = Path("output/couts.csv")

# Modèle utilisé. Les noms de la documentation (1.2, 1.1) ont répondu « 404 : modèle introuvable » pour
# ce compte. La liste des modèles visibles avec sa clé ne contient que "gemini-omni-flash-preview" (la
# préversion d'origine, sortie le 30 juin 2026). Si ce nom répond aussi 404, ou quand 1.1 / 1.2 deviennent
# accessibles, il suffit de changer cette ligne.
MODELE = "gemini-omni-flash-preview"

# Limites et prix par modèle (dollars par seconde de vidéo). Tous ces prix sont des ESTIMATIONS à
# vérifier sur la facturation Google : 1.2 d'après l'annonce du 5 nov. 2026 (environ 0,07 en 720p) ;
# 1.1 déduit de « 1.2 est 30 % moins chère » (environ 0,10 en 720p) ; la préversion : tarif non trouvé,
# on suppose celui de la 1.1. La préversion n'accepte que le 720p et 10 s maximum (documentation Google Cloud).
PARAMETRES_MODELES = {
    "gemini-omni-1.2-flash": {"duree_max": 15,
                              "resolutions": ["360p", "720p", "1080p", "4k"],
                              "prix": {"360p": 0.023, "720p": 0.07, "1080p": 0.104, "4k": 0.209}},
    "gemini-omni-1.1-flash": {"duree_max": 10,
                              "resolutions": ["360p", "720p", "1080p", "4k"],
                              "prix": {"360p": 0.033, "720p": 0.10, "1080p": 0.149, "4k": 0.299}},
    "gemini-omni-flash-preview": {"duree_max": 10,
                                  "resolutions": ["720p"],
                                  "prix": {"720p": 0.10}},
}
DUREE_MIN = 3  # secondes, par pas d'une seconde


def resolution_effective(plan):
    """Résolution réellement demandée : celle du JSON si le modèle la propose, sinon la plus basse
    qu'il propose (la préversion n'a que le 720p : pas de brouillon bon marché)."""
    demandee = plan["animation"].get("resolution", "720p")
    autorisees = PARAMETRES_MODELES[MODELE]["resolutions"]
    return demandee if demandee in autorisees else autorisees[0]


def prix_par_seconde(resolution):
    """Prix estimé d'une seconde de vidéo pour le modèle choisi et la résolution demandée."""
    return PARAMETRES_MODELES[MODELE]["prix"][resolution]


# Consignes ajoutées à TOUS les prompts : le scénariste n'a qu'à décrire le mouvement.
CONTRAINTES = ("Single continuous shot, no scene cuts. Same 3D animated film look as the source "
               "image; the faces, hair and clothes stay unchanged. No dialogue, no music, "
               "no extra sound effects.")


def chemin_animation(plan, dossier):
    """Où est (ou sera) rangée l'animation d'un plan."""
    return dossier / "animations" / f"plan{plan['id']:02d}.mp4"


def duree_demandee(duree_du_plan):
    """Durée à demander à l'API : on arrondit à la seconde SUPÉRIEURE (pour couvrir tout le plan)
    et on respecte les bornes du modèle."""
    return min(PARAMETRES_MODELES[MODELE]["duree_max"],
               max(DUREE_MIN, math.ceil(duree_du_plan - 1e-6)))


def construire_prompt(plan, duree):
    """Prompt complet : image = première image (balise <FIRST_FRAME>), puis mouvement, durée, consignes."""
    texte = plan["animation"]["prompt"].strip()
    if "<FIRST_FRAME>" not in texte:
        texte = f"<FIRST_FRAME> {texte}"
    return f"{texte} The shot lasts {duree} seconds. {CONTRAINTES}"


def plans_a_animer(episode, voulus=()):
    """Plans qui ont une clé "animation" (et sont demandés, si `voulus` n'est pas vide)."""
    return [p for p in episode["shots"]
            if "animation" in p and (not voulus or p["id"] in voulus)]


def estimer(episode, dossier, voulus=()):
    """Une ligne par plan : id, durée demandée, résolution, coût estimé, fichier déjà là ?"""
    lignes = []
    for plan in plans_a_animer(episode, voulus):
        resolution = resolution_effective(plan)
        duree = duree_demandee(duree_plan(plan, episode["timing"], dossier))
        lignes.append({"id": plan["id"], "duree": duree, "resolution": resolution,
                       "demandee": plan["animation"].get("resolution", "720p"),
                       "cout": duree * prix_par_seconde(resolution),
                       "existe": chemin_animation(plan, dossier).exists()})
    return lignes


def noter_cout(plan, resolution, duree, cout):
    """Ajoute une ligne au journal des coûts (output/couts.csv)."""
    JOURNAL_COUTS.parent.mkdir(parents=True, exist_ok=True)
    nouveau = not JOURNAL_COUTS.exists()
    with JOURNAL_COUTS.open("a", newline="", encoding="utf-8") as f:
        ecrivain = csv.writer(f)
        if nouveau:
            ecrivain.writerow(["date", "plan", "modele", "resolution", "secondes", "cout_estime_usd"])
        ecrivain.writerow([datetime.now().isoformat(timespec="seconds"), plan["id"], MODELE,
                           resolution, duree, f"{cout:.3f}"])


def creer_client():
    """Client de l'API Gemini (lit GEMINI_API_KEY dans l'environnement)."""
    try:
        from google import genai
    except ImportError:
        raise RuntimeError("Bibliothèque manquante : pip install -U google-genai")
    return genai.Client()


def enregistrer_video(client, video, sortie):
    """Écrit la vidéo reçue : soit en base64 dans la réponse, soit via une URI à télécharger."""
    sortie.parent.mkdir(parents=True, exist_ok=True)
    if getattr(video, "data", None):
        sortie.write_bytes(base64.b64decode(video.data))
        return
    if getattr(video, "uri", None):
        # Livraison par URI (vidéos lourdes) : on attend que le fichier soit prêt, puis on le télécharge.
        nom = video.uri.split("/")[-1].split(":")[0].split("?")[0]
        for _ in range(120):  # 10 minutes maximum
            etat = client.files.get(name=f"files/{nom}").state.name
            if etat == "ACTIVE":
                client.files.download(file=video.uri, destination=str(sortie))
                return
            if etat == "FAILED":
                raise RuntimeError("La génération de la vidéo a échoué côté Google.")
            time.sleep(5)
        raise RuntimeError("Délai dépassé en attendant la vidéo.")
    raise RuntimeError("Réponse de l'API sans vidéo (filtre de sécurité ? prompt refusé ?).")


def generer_animation(plan, episode, dossier, client=None, forcer=False):
    """Génère l'animation d'un plan. Renvoie (chemin du fichier, coût estimé ; 0 si déjà là).

    `client` permet d'injecter un faux client dans les tests (aucun appel réel, aucun coût).
    """
    sortie = chemin_animation(plan, dossier)
    if sortie.exists() and not forcer:
        return sortie, 0.0

    resolution = resolution_effective(plan)
    duree = duree_demandee(duree_plan(plan, episode["timing"], dossier))
    client = client or creer_client()

    # L'image envoyée est l'image ÉTALONNÉE : l'animation part du même look que les plans fixes.
    image = etalonner(plan, dossier)
    mime = "image/jpeg" if image.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    entree = [{"type": "image", "data": base64.b64encode(image.read_bytes()).decode(),
               "mime_type": mime},
              {"type": "text", "text": construire_prompt(plan, duree)}]

    # La documentation Google Cloud demande la durée sous forme de CHAÎNE avec le suffixe « s » : "4s".
    format_reponse = {"type": "video", "aspect_ratio": "9:16", "resolution": resolution,
                      "duration": f"{duree}s"}
    if resolution in ("1080p", "4k"):
        format_reponse["delivery"] = "uri"  # vidéos lourdes : livraison par URI

    try:
        interaction = client.interactions.create(model=MODELE, input=entree,
                                                 response_format=format_reponse)
    except Exception as erreur:
        # Seule la durée est facultative dans notre requête (elle est aussi écrite dans le prompt) :
        # si le serveur rejette le format de réponse, on réessaie sans elle avant d'abandonner.
        texte = str(erreur).lower()
        if "duration" not in texte and "response_format" not in texte:
            raise
        print("(durée refusée par l'API : nouvel essai sans ce champ)", end=" ", flush=True)
        format_reponse.pop("duration")
        try:
            interaction = client.interactions.create(model=MODELE, input=entree,
                                                     response_format=format_reponse)
        except Exception as erreur2:
            raise RuntimeError(f"{erreur2} | format envoyé : {format_reponse} | "
                               f"modèle : {MODELE}") from erreur2

    enregistrer_video(client, interaction.output_video, sortie)
    cout = duree * prix_par_seconde(resolution)
    noter_cout(plan, resolution, duree, cout)
    return sortie, cout


def main():
    args = sys.argv[1:]
    seulement_estimer = "--estimer" in args
    forcer = "--forcer" in args
    sans_confirmation = "--oui" in args
    voulus = {int(a) for a in args if a.isdigit()}

    dossier = Path(DOSSIER_PAR_DEFAUT)
    episode = charger_episode(dossier)
    lignes = estimer(episode, dossier, voulus)
    if not lignes:
        print('Aucun plan avec une clé "animation" dans episode.json.')
        return 0

    print(f"Modèle : {MODELE}")
    print("plan | durée | résolution | coût estimé | déjà généré")
    for l in lignes:
        print(f" {l['id']:02d}  |  {l['duree']:2d} s |   {l['resolution']:>5}    |   {l['cout']:5.2f} $   | "
              f"{'oui (ignoré, sauf --forcer)' if l['existe'] else 'non'}")
    for l in lignes:
        if l["demandee"] != l["resolution"]:
            print(f"  (plan {l['id']:02d} : {l['demandee']} demandé, mais ce modèle ne propose que "
                  f"{l['resolution']} : coût calculé en {l['resolution']})")
    a_payer = [l for l in lignes if forcer or not l["existe"]]
    total = sum(l["cout"] for l in a_payer)
    print(f"Coût estimé de cette exécution : {total:.2f} $ (estimation, voir la facturation Google)")
    if seulement_estimer or not a_payer:
        return 0

    if not sans_confirmation and input("Lancer la génération ? [o/N] ").strip().lower() != "o":
        print("Annulé, rien n'a été dépensé.")
        return 0

    depense = 0.0
    echecs = []
    for plan in plans_a_animer(episode, voulus):
        print(f"Plan {plan['id']:02d} : génération ...", end=" ", flush=True)
        try:
            fichier, cout = generer_animation(plan, episode, dossier, forcer=forcer)
        except Exception as erreur:  # une erreur sur UN plan n'arrête pas les autres
            print(f"\nERREUR : {erreur}")
            echecs.append(plan["id"])
            texte = str(erreur).lower()
            if any(m in texte for m in ("404", "not_found", "401", "403", "api key", "permission")):
                print("Erreur d'accès (modèle ou clé) : inutile de continuer, les autres plans échoueraient aussi.")
                break
            continue
        depense += cout
        print(f"ok -> {fichier}")
    print(f"Terminé. Coût estimé ajouté à {JOURNAL_COUTS} : {depense:.2f} $")
    if echecs:
        print("Plans en échec : " + ", ".join(f"{i:02d}" for i in echecs)
              + " (ils restent fixes ; relance avec ces numéros pour réessayer, sans repayer les autres)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
