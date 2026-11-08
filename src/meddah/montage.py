"""Montage complet d'un épisode, en une commande.

    python src/meddah/montage.py

Enchaîne : étalonnage + clips de tous les plans (clip.py), puis assemblage vidéo,
piste audio, normalisation du volume et fusion (assemble.py).
Résultat : output/<serie>_ep<NN>_brut.mp4
"""
import sys
import time
from pathlib import Path

from assemble import assembler_episode
from clip import generer_clips
from episode import charger_episode

DOSSIER_PAR_DEFAUT = "series/enzo/episodes/ep01"


def main():
    debut = time.time()
    dossier = Path(sys.argv[1] if len(sys.argv) > 1 else DOSSIER_PAR_DEFAUT)
    try:
        episode = charger_episode(dossier)
    except FileNotFoundError:
        print(f"ERREUR : {dossier / 'episode.json'} introuvable.")
        return 1

    code = generer_clips(episode, dossier)
    if code != 0:
        return code
    code = assembler_episode(episode, dossier)
    if code == 0:
        minutes, secondes = divmod(round(time.time() - debut), 60)
        print(f"Terminé en {minutes} min {secondes:02d} s.")
    return code


if __name__ == "__main__":
    sys.exit(main())
