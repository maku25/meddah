"""Outil à usage unique : ajoute les libellés des compteurs dans episode.json.

    python scripts/ajouter_libelles.py [dossier_de_l_episode]

- counter_small et counter_big  -> "label": "ARGENT"
- goal_big                      -> "label": "OBJECTIF"
- la boîte du petit compteur est élargie (la pastille s'ajuste ensuite au contenu).
Une copie de sauvegarde est faite dans episode.json.bak.
"""
import json
import shutil
import sys
from pathlib import Path

LIBELLES = {"counter_small": "ARGENT", "counter_big": "ARGENT", "goal_big": "OBJECTIF"}
BOITE_PETIT_COMPTEUR = [0.25, 0.045, 0.75, 0.1]


def main():
    dossier = Path(sys.argv[1] if len(sys.argv) > 1 else "series/enzo/episodes/ep01")
    fichier = dossier / "episode.json"
    episode = json.loads(fichier.read_text(encoding="utf-8"))

    modifies = 0
    for plan in episode["shots"]:
        for s in plan.get("overlays", []):
            libelle = LIBELLES.get(s["style"])
            if libelle and "label" not in s:
                s["label"] = libelle
                if s["style"] == "counter_small":
                    s["box"] = BOITE_PETIT_COMPTEUR
                modifies += 1

    if modifies == 0:
        print("Rien à modifier : les libellés sont déjà présents.")
        return
    shutil.copy(fichier, fichier.with_suffix(".json.bak"))
    fichier.write_text(json.dumps(episode, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{modifies} surimpression(s) modifiée(s). Sauvegarde : {fichier.with_suffix('.json.bak')}")


if __name__ == "__main__":
    main()
