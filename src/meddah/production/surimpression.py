"""Montage, brique 3a : dessiner les surimpressions (textes) avec Pillow.

Cette brique ne touche pas encore à ffmpeg. Elle transforme une entrée « overlays »
d'episode.json en image transparente (RGBA) et sait produire un APERÇU FIXE de chaque
plan avec ses textes : on règle le design en regardant des PNG, sans rendre de vidéo.

Usage (depuis la racine du repo) :
    python src/meddah/surimpression.py          -> aperçus de tous les plans
    python src/meddah/surimpression.py 6 8 9    -> seulement les plans 6, 8 et 9
Résultat : output/apercus/planXX.png
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

# Import « frère », comme dans clip.py.
from episode import charger_episode

DOSSIER_PAR_DEFAUT = "series/enzo/episodes/ep01"
POLICES = Path("assets/fonts")
APERCUS = Path("output/apercus")

# Un style = une apparence. Pour changer le design d'un texte, on ne touche qu'ici.
#  - police      : fichier dans assets/fonts/
#  - couleur     : (R, V, B, A)
#  - taille_max  : taille de départ en pixels POUR UNE LARGEUR DE 1080 (mise à l'échelle
#                  automatique pour une image plus large) ; le texte rétrécit jusqu'à
#                  tenir dans sa boîte
#  - ombre       : (décalage, flou) en pixels pour 1080 de large, ou None
#  - pastille    : couleur d'un fond arrondi derrière le texte, ou None
#  - etiquette   : (compteurs) place du libellé "label" : "avant" (sur la même ligne, dans
#                  une pastille ajustée au contenu) ou "dessus" (au-dessus du nombre)
STYLES = {
    "counter_small": {"police": "Montserrat-ExtraBold.ttf", "couleur": (255, 255, 255, 255),
                      "taille_max": 64, "ombre": (3, 4), "pastille": (0, 0, 0, 120),
                      "etiquette": "avant", "police_label": "Montserrat-SemiBold.ttf",
                      "couleur_label": (255, 255, 255, 175)},
    "counter_big": {"police": "Montserrat-ExtraBold.ttf", "couleur": (255, 255, 255, 255),
                    "taille_max": 150, "ombre": (5, 8), "pastille": None,
                    "etiquette": "dessus", "police_label": "Montserrat-SemiBold.ttf",
                    "couleur_label": (255, 255, 255, 175)},
    "goal_big": {"police": "Montserrat-ExtraBold.ttf", "couleur": (255, 201, 71, 255),
                 "taille_max": 150, "ombre": (5, 8), "pastille": None,
                 "etiquette": "dessus", "police_label": "Montserrat-SemiBold.ttf",
                 "couleur_label": (255, 201, 71, 200)},
    "letter": {"police": "Montserrat-SemiBold.ttf", "couleur": (35, 38, 48, 255),
               "taille_max": 90, "ombre": None, "pastille": None},
    "to_be_continued": {"police": "Montserrat-ExtraBold.ttf", "couleur": (255, 255, 255, 255),
                        "taille_max": 130, "ombre": (5, 8), "pastille": None},
    # La carte de message a sa propre mise en page (voir rendre_carte_message).
    "message_card": {"police": "Montserrat-Regular.ttf", "police_titre": "Montserrat-SemiBold.ttf",
                     "couleur": (28, 30, 38, 255), "couleur_titre": (95, 98, 110, 255),
                     "fond": (246, 246, 249, 238), "avatar": (120, 124, 140, 255)},
}

INTERLIGNE = 1.2  # hauteur d'une ligne = taille de police x 1,2


def charger_police(nom, taille):
    chemin = POLICES / nom
    try:
        return ImageFont.truetype(str(chemin), taille)
    except OSError:
        raise FileNotFoundError(f"Police introuvable : {chemin} (voir assets/fonts/)")


def decouper_lignes(texte, police, largeur_max, mesure):
    """Retour à la ligne automatique. Renvoie None si un mot seul dépasse la largeur.

    On coupe uniquement sur les espaces normaux : l'espace insécable (U+00A0) du JSON
    garde « 3 400 € » d'un seul bloc, donc le montant ne sera jamais coupé en deux.
    """
    lignes, courante = [], ""
    for mot in texte.split(" "):
        essai = f"{courante} {mot}" if courante else mot
        if mesure.textlength(essai, font=police) <= largeur_max:
            courante = essai
        elif courante:
            lignes.append(courante)
            courante = mot
        else:
            return None
    lignes.append(courante)
    if any(mesure.textlength(ligne, font=police) > largeur_max for ligne in lignes):
        return None
    return lignes


def ajuster_texte(texte, nom_police, largeur, hauteur, taille_max):
    """Plus grande taille de police pour laquelle le texte tient dans la boîte."""
    mesure = ImageDraw.Draw(Image.new("L", (1, 1)))
    for taille in range(int(taille_max), 7, -2):
        police = charger_police(nom_police, taille)
        lignes = decouper_lignes(texte, police, largeur, mesure)
        if lignes is not None and len(lignes) * taille * INTERLIGNE <= hauteur:
            return police, lignes
    raise ValueError(f"Le texte ne tient pas dans sa boîte : {texte!r}")


def ecrire_lignes(dessin, lignes, police, x, centre_y, taille, couleur, ancre):
    """Écrit les lignes, centrées verticalement autour de centre_y."""
    pas = taille * INTERLIGNE
    for i, ligne in enumerate(lignes):
        y = centre_y + (i - (len(lignes) - 1) / 2) * pas
        dessin.text((x, y), ligne, font=police, fill=couleur, anchor=ancre)


def rendre_texte(surimpression, style, largeur, hauteur, echelle):
    """Texte centré dans sa boîte, avec ombre portée et pastille facultatives."""
    calque = Image.new("RGBA", (largeur, hauteur), (0, 0, 0, 0))
    marge = 0.08  # on garde 8 % de marge de chaque côté
    if style["pastille"]:
        ImageDraw.Draw(calque).rounded_rectangle(
            (0, 0, largeur - 1, hauteur - 1), radius=hauteur // 2, fill=style["pastille"])
        marge = 0.16
    zone_l, zone_h = largeur * (1 - 2 * marge), hauteur * (1 - 2 * marge)

    police, lignes = ajuster_texte(surimpression["text"], style["police"], zone_l, zone_h,
                                   style["taille_max"] * echelle)
    taille = police.size
    cx, cy = largeur / 2, hauteur / 2

    if style["ombre"]:
        decalage, flou = (v * echelle for v in style["ombre"])
        ombre = Image.new("RGBA", (largeur, hauteur), (0, 0, 0, 0))
        ecrire_lignes(ImageDraw.Draw(ombre), lignes, police, cx, cy + decalage, taille,
                      (0, 0, 0, 190), "mm")
        calque.alpha_composite(ombre.filter(ImageFilter.GaussianBlur(flou)))
    ecrire_lignes(ImageDraw.Draw(calque), lignes, police, cx, cy, taille, style["couleur"], "mm")
    return calque


# Le libellé est plus petit que le nombre : ratio de taille selon la mise en page.
ETIQUETTE_RATIO = {"avant": 0.50, "dessus": 0.34}
HAUTEUR_CAPITALES = 0.70  # hauteur des majuscules et des chiffres, en fraction de la police


def rendre_texte_etiquette(surimpression, style, largeur, hauteur, echelle):
    """Libellé (petit) + nombre (grand), alignés sur la même ligne de base.

    "avant"  : sur une ligne, « ARGENT 37 € », dans une pastille ajustée au contenu ;
    "dessus" : le libellé est posé au-dessus du nombre.
    """
    calque = Image.new("RGBA", (largeur, hauteur), (0, 0, 0, 0))
    mesure = ImageDraw.Draw(calque)
    avant = style["etiquette"] == "avant"
    ratio = ETIQUETTE_RATIO[style["etiquette"]]
    libelle, nombre = surimpression["label"], surimpression["text"]

    # On cherche la plus grande taille de nombre qui tient dans la boîte.
    for taille in range(int(style["taille_max"] * echelle), 7, -2):
        taille_l = max(8, round(taille * ratio))
        police_n = charger_police(style["police"], taille)
        police_l = charger_police(style["police_label"], taille_l)
        larg_l = mesure.textlength(libelle, font=police_l)
        larg_n = mesure.textlength(nombre, font=police_n)
        if avant:
            ecart, bord = 0.35 * taille, 0.5 * taille
            larg_total = larg_l + ecart + larg_n + 2 * bord  # largeur de la pastille
            if larg_total <= largeur * 0.96 and taille * INTERLIGNE <= hauteur * 0.68:
                break
        else:
            ecart = 0.14 * taille
            haut_bloc = HAUTEUR_CAPITALES * (taille_l + taille) + ecart
            if max(larg_l, larg_n) <= largeur * 0.84 and haut_bloc <= hauteur * 0.84:
                break
    else:
        raise ValueError(f"Le texte ne tient pas dans sa boîte : {libelle!r} {nombre!r}")

    # Éléments à dessiner : (texte, police, x, y de la ligne de base, ancre, couleur).
    if avant:
        x0 = (largeur - larg_total) / 2
        if style["pastille"]:
            ImageDraw.Draw(calque).rounded_rectangle(
                (x0, 0, x0 + larg_total - 1, hauteur - 1), radius=hauteur // 2,
                fill=style["pastille"])
        base = hauteur / 2 + HAUTEUR_CAPITALES * taille / 2
        x_l = x0 + bord
        elements = [(libelle, police_l, x_l, base, "ls", style["couleur_label"]),
                    (nombre, police_n, x_l + larg_l + ecart, base, "ls", style["couleur"])]
    else:
        haut = (hauteur - haut_bloc) / 2
        base_l = haut + HAUTEUR_CAPITALES * taille_l
        base_n = base_l + ecart + HAUTEUR_CAPITALES * taille
        elements = [(libelle, police_l, largeur / 2, base_l, "ms", style["couleur_label"]),
                    (nombre, police_n, largeur / 2, base_n, "ms", style["couleur"])]

    if style["ombre"]:
        decalage, flou = (v * echelle for v in style["ombre"])
        ombre = Image.new("RGBA", (largeur, hauteur), (0, 0, 0, 0))
        for texte, police, x, y, ancre, _ in elements:
            ImageDraw.Draw(ombre).text((x, y + decalage), texte, font=police,
                                       fill=(0, 0, 0, 190), anchor=ancre)
        calque.alpha_composite(ombre.filter(ImageFilter.GaussianBlur(flou)))
    for texte, police, x, y, ancre, couleur in elements:
        ImageDraw.Draw(calque).text((x, y), texte, font=police, fill=couleur, anchor=ancre)
    return calque


def rendre_carte_message(surimpression, style, largeur, hauteur, echelle):
    """Carte de message : fond arrondi, avatar (initiale), expéditeur, texte."""
    calque = Image.new("RGBA", (largeur, hauteur), (0, 0, 0, 0))
    dessin = ImageDraw.Draw(calque)
    dessin.rounded_rectangle((0, 0, largeur - 1, hauteur - 1), radius=int(hauteur * 0.2),
                             fill=style["fond"])

    marge = int(hauteur * 0.11)
    diametre = int(hauteur * 0.36)
    dessin.ellipse((marge, marge, marge + diametre, marge + diametre), fill=style["avatar"])
    expediteur = surimpression["sender"]
    police_initiale = charger_police(style["police_titre"], int(diametre * 0.5))
    dessin.text((marge + diametre / 2, marge + diametre / 2), expediteur[0].upper(),
                font=police_initiale, fill=(255, 255, 255, 255), anchor="mm")

    x_texte = marge * 2 + diametre
    taille_titre = int(hauteur * 0.15)
    police_titre = charger_police(style["police_titre"], taille_titre)
    dessin.text((x_texte, marge), expediteur, font=police_titre,
                fill=style["couleur_titre"], anchor="lt")

    haut_message = marge + taille_titre * 1.5
    police, lignes = ajuster_texte(surimpression["text"], style["police"],
                                   largeur - x_texte - marge, hauteur - haut_message - marge,
                                   hauteur * 0.17)
    pas = police.size * INTERLIGNE
    for i, ligne in enumerate(lignes):
        dessin.text((x_texte, haut_message + i * pas), ligne, font=police,
                    fill=style["couleur"], anchor="lt")
    return calque


def rendre(surimpression, taille_reference):
    """Dessine une surimpression. Renvoie (image RGBA de la taille de la boîte, (x, y)).

    `box` dans episode.json = [x0, y0, x1, y1] en FRACTIONS de l'image de référence :
    1080x1920 pour un texte « screen », la taille de l'image source pour « image ».
    """
    ref_l, ref_h = taille_reference
    x0, y0, x1, y1 = surimpression["box"]
    x, y = round(x0 * ref_l), round(y0 * ref_h)
    largeur, hauteur = round((x1 - x0) * ref_l), round((y1 - y0) * ref_h)
    echelle = ref_l / 1080  # les tailles des styles sont données pour 1080 de large

    style = STYLES[surimpression["style"]]
    if surimpression.get("label"):
        if not style.get("etiquette"):
            raise ValueError(f"Le style {surimpression['style']!r} ne gère pas de libellé")
        calque = rendre_texte_etiquette(surimpression, style, largeur, hauteur, echelle)
    elif surimpression["style"] == "message_card":
        calque = rendre_carte_message(surimpression, style, largeur, hauteur, echelle)
    else:
        calque = rendre_texte(surimpression, style, largeur, hauteur, echelle)
    return calque, (x, y)


def apercu_plan(plan, format_video, dossier):
    """Image fixe du plan tel qu'il apparaîtra, textes tous visibles (état final)."""
    largeur, hauteur = format_video["width"], format_video["height"]
    image = Image.open(dossier / plan["image"]).convert("RGBA")

    sur_ecran = []
    for s in plan.get("overlays", []):
        if s["space"] == "image":
            # Texte posé SUR l'image (la lettre) : dessiné avant le recadrage, donc
            # il suivra les mouvements de caméra comme le papier.
            calque, position = rendre(s, image.size)
            image.alpha_composite(calque, position)
        else:
            sur_ecran.append(s)

    # Même recadrage « cover » 9:16 que dans clip.py.
    cadre = ImageOps.fit(image.convert("RGB"), (largeur, hauteur),
                         method=Image.LANCZOS, centering=(0.5, 0.5)).convert("RGBA")
    for s in sur_ecran:
        calque, position = rendre(s, (largeur, hauteur))
        cadre.alpha_composite(calque, position)
    return cadre.convert("RGB")


def main():
    dossier = Path(DOSSIER_PAR_DEFAUT)
    episode = charger_episode(dossier)
    voulus = {int(a) for a in sys.argv[1:]}  # vide = tous les plans

    APERCUS.mkdir(parents=True, exist_ok=True)
    for plan in episode["shots"]:
        if voulus and plan["id"] not in voulus:
            continue
        fichier = APERCUS / f"plan{plan['id']:02d}.png"
        try:
            apercu_plan(plan, episode["format"], dossier).save(fichier)
        except (FileNotFoundError, ValueError) as erreur:
            print(f"Plan {plan['id']:02d} : ERREUR : {erreur}")
            return 1
        print(f"Plan {plan['id']:02d} -> {fichier}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
