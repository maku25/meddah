import json
import sys
from pathlib import Path

from mutagen.mp3 import MP3

DOSSIER_PAR_DEFAUT = "series/enzo/episodes/ep01"


def charger_episode(dossier):
    """Lit episode.json dans le dossier de l'épisode et renvoie son contenu."""
    texte = (dossier / "episode.json").read_text(encoding="utf-8")
    return json.loads(texte)


def fichiers_manquants(episode, dossier):
    """Liste des fichiers cités par l'épisode qui n'existent pas sur le disque."""
    manquants = []
    for plan in episode["shots"]:
        fichiers = [plan["image"]]
        if "voice" in plan:
            fichiers.append(plan["voice"])
        for nom in fichiers:
            if not (dossier / nom).exists():
                manquants.append(f"plan {plan['id']:02d} : {nom}")
    return manquants


def duree_plan(plan, timing, dossier):
    """Durée d'un plan, en secondes."""
    if "voice" not in plan:
        return plan["duration"]
    voix = MP3(str(dossier / plan["voice"])).info.length
    return timing["lead_in"] + voix + timing["tail"] + plan.get("extra_hold", 0.0)


def main():
    dossier = Path(sys.argv[1] if len(sys.argv) > 1 else DOSSIER_PAR_DEFAUT)

    try:
        episode = charger_episode(dossier)
    except FileNotFoundError:
        print(f"ERREUR : {dossier / 'episode.json'} introuvable.")
        return 1

    print(episode["title"])
    print(len(episode["shots"]), "plans")

    manquants = fichiers_manquants(episode, dossier)
    if manquants:
        print("Fichiers manquants :")
        for ligne in manquants:
            print("  -", ligne)
        return 1

    print("Tous les fichiers sont présents.")

    debut = 0.0
    for plan in episode["shots"]:
        duree = duree_plan(plan, episode["timing"], dossier)
        print(f"Plan {plan['id']:02d} : début {debut:5.2f} s | durée {duree:5.2f} s")
        debut += duree

    print(f"Durée totale : {debut:.2f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
