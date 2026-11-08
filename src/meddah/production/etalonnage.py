"""Montage, brique 4 : étalonnage automatique des images (Pillow).

Pour chaque plan, on MESURE l'image source (dominante bleue, luminance moyenne), puis
on applique des corrections bornées :
  - si l'image est trop bleue, on réduit le canal bleu ;
  - si elle est trop sombre, on remonte les ombres (courbe gamma).
L'image corrigée est enregistrée dans output/tmp/ et sert d'entrée à ffmpeg ; l'image
d'origine n'est jamais modifiée. Un plan déjà dans les clous n'est pas touché.

Usage (depuis la racine du repo) :
    python src/meddah/etalonnage.py          -> tableau des mesures + comparaisons avant/après
Résultat : output/etalonnage/planXX.png (avant à gauche, après à droite)

Réglage au cas par cas dans episode.json, sur un plan :
    "grade": false                              -> aucune correction
    "grade": {"blue": 0.85, "gamma": 0.9}       -> valeurs imposées (l'une ou l'autre)
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageStat

# Import « frère », comme dans clip.py.
from episode import charger_episode

DOSSIER_PAR_DEFAUT = "series/enzo/episodes/ep01"
TMP = Path("output/tmp")
COMPARAISONS = Path("output/etalonnage")

# --- Réglages : à ajuster en regardant les comparaisons --------------------------------
# Rapport bleu/rouge maximal toléré (mesuré sur tes plans de nuit : 0,97 à 1,09).
# Au-delà, on réduit le bleu pour revenir à cette valeur.
BLEU_SUR_ROUGE_MAX = 1.08
# Luminance moyenne visée (sur 255) : sous cette valeur, on remonte les ombres.
LUMINANCE_CIBLE = 52
# Remontée maximale : 1,0 = aucun changement ; plus on descend, plus l'image s'éclaircit.
GAMMA_MIN = 0.80


def mesurer_image(image):
    """Mesures d'une image chargée : moyennes R, V, B et rapport bleu/rouge."""
    miniature = image.copy()
    miniature.thumbnail((256, 256))  # inutile de parcourir 4 millions de pixels
    r, v, b = ImageStat.Stat(miniature).mean
    return {"r": r, "v": v, "b": b, "bleu_sur_rouge": b / r}


def mesurer(chemin):
    return mesurer_image(Image.open(chemin).convert("RGB"))


def luminance(r, v, b):
    """Luminance perçue (pondération standard : le vert pèse le plus)."""
    return 0.2126 * r + 0.7152 * v + 0.0722 * b


def calculer_corrections(mesure, reglage=None):
    """Renvoie (gain_bleu, gamma). (1.0, 1.0) = rien à faire."""
    if reglage is False:
        return 1.0, 1.0
    reglage = reglage or {}

    # 1. Dominante bleue : on ne fait jamais que RÉDUIRE le bleu.
    gain_bleu = min(1.0, BLEU_SUR_ROUGE_MAX / mesure["bleu_sur_rouge"])
    gain_bleu = reglage.get("blue", gain_bleu)

    # 2. Ombres : luminance après correction du bleu, puis gamma borné.
    lum = luminance(mesure["r"], mesure["v"], mesure["b"] * gain_bleu)
    gamma = 1.0
    if lum < LUMINANCE_CIBLE:
        # Un gamma g envoie une luminance L (sur 255) vers 255*(L/255)**g : on résout pour la cible.
        gamma = max(GAMMA_MIN, math.log(LUMINANCE_CIBLE / 255) / math.log(lum / 255))
    gamma = reglage.get("gamma", gamma)
    return gain_bleu, gamma


def appliquer(image, gain_bleu, gamma):
    """Applique les corrections avec une table de correspondance par canal (rapide)."""
    tables = []
    for canal in range(3):  # 0 = rouge, 1 = vert, 2 = bleu
        gain = gain_bleu if canal == 2 else 1.0
        tables += [min(255, round(255 * min(1.0, i * gain / 255) ** gamma)) for i in range(256)]
    return image.point(tables)


def etalonner(plan, dossier):
    """Chemin de l'image à donner à ffmpeg : l'originale si elle est bonne, sinon une
    copie corrigée dans output/tmp/ (JPEG qualité 95, même chemin de décodage que les
    images d'origine pour que la conversion des couleurs de clip.py reste valable)."""
    source = dossier / plan["image"]
    gain_bleu, gamma = calculer_corrections(mesurer(source), plan.get("grade"))
    if gain_bleu == 1.0 and gamma == 1.0:
        return source

    TMP.mkdir(parents=True, exist_ok=True)
    corrigee = TMP / f"plan{plan['id']:02d}_etalonne.jpg"
    appliquer(Image.open(source).convert("RGB"), gain_bleu, gamma).save(
        corrigee, quality=95, subsampling=0)
    return corrigee


def main():
    dossier = Path(DOSSIER_PAR_DEFAUT)
    episode = charger_episode(dossier)
    COMPARAISONS.mkdir(parents=True, exist_ok=True)

    print("plan | B/R avant | lum. avant | gain bleu | gamma | B/R après | lum. après")
    for plan in episode["shots"]:
        source = dossier / plan["image"]
        avant = mesurer(source)
        gain_bleu, gamma = calculer_corrections(avant, plan.get("grade"))
        lum_avant = luminance(avant["r"], avant["v"], avant["b"])

        image = Image.open(source).convert("RGB")
        apres_image = appliquer(image, gain_bleu, gamma)
        apres = mesurer_image(apres_image)
        lum_apres = luminance(apres["r"], apres["v"], apres["b"])
        print(f" {plan['id']:02d}  |   {avant['bleu_sur_rouge']:4.2f}    |   {lum_avant:5.1f}   |"
              f"   {gain_bleu:4.2f}    | {gamma:4.2f}  |   {apres['bleu_sur_rouge']:4.2f}    |   {lum_apres:5.1f}")

        # Comparaison avant | après, côte à côte.
        largeur = 360
        hauteur = round(image.height * largeur / image.width)
        planche = Image.new("RGB", (2 * largeur + 8, hauteur), (255, 255, 255))
        planche.paste(image.resize((largeur, hauteur)), (0, 0))
        planche.paste(apres_image.resize((largeur, hauteur)), (largeur + 8, 0))
        planche.save(COMPARAISONS / f"plan{plan['id']:02d}.png")
    print(f"Comparaisons : {COMPARAISONS}\\planXX.png (avant à gauche, après à droite)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
