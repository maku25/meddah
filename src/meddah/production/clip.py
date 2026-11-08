"""Montage, briques 1 à 4 : un plan = un clip vidéo (étalonnage + caméra + surimpressions).

Un plan peut aussi partir d'une animation générée (animation.py) au lieu d'une image fixe.
Les voix et le volume sont gérés par assemble.py.
Usage de test (depuis la racine du repo) :
    python src/meddah/clip.py            -> tous les plans
    python src/meddah/clip.py 1 3 4      -> seulement les plans 1, 3 et 4
"""
import subprocess
import sys
from pathlib import Path

from PIL import Image

# Imports « frères » : fonctionnent quand on lance le fichier directement
# (python src/meddah/clip.py). Seront remplacés par `from meddah.episode import ...`
# le jour où le projet sera installé comme un vrai paquet.
from episode import charger_episode, duree_plan
from animation import chemin_animation
from etalonnage import etalonner
from surimpression import rendre

DOSSIER_PAR_DEFAUT = "series/enzo/episodes/ep01"
SORTIE = Path("output/clips")
TMP = Path("output/tmp")  # images des textes, une par surimpression

# L'image est agrandie 4 fois plus que la vidéo avant le zoom. Le filtre zoompan
# arrondit la position de la fenêtre au pixel entier : sur une image agrandie,
# l'erreur d'arrondi vaut 1/4 de pixel de sortie, donc le zoom ne saccade pas.
SURECHANTILLONNAGE = 4

# Tremblement (champ "shake" d'episode.json) : amplitude en fraction de l'image et
# fréquences en Hz. Deux fréquences différentes sur x et y pour éviter un va-et-vient
# régulier. Elles restent sous 15 Hz (la moitié de 30 i/s), sinon le mouvement
# serait mal échantillonné et paraîtrait lent ou à l'envers.
TREMBLEMENT_AMPLITUDE = (0.006, 0.004)
TREMBLEMENT_FREQUENCES = (11, 13)

# Durée du glissement de la carte (animation "slide_down") si fade_in vaut 0.
GLISSEMENT_PAR_DEFAUT = 0.3


def expression_camera(camera, nb_images, fps, tremblement=None):
    """Traduit la caméra d'episode.json en expressions ffmpeg (z, x, y).

    ffmpeg évalue ces expressions pour chaque image de sortie. `on` est le numéro
    de l'image (0, 1, 2...) ; `iw` et `ih` sont la taille de l'image agrandie ;
    `zoom` est le zoom de l'image courante.
    """
    z0, z1 = camera["zoom"]
    (x0, y0), (x1, y1) = camera["center"]

    # Progression p : 0 sur la première image, 1 sur la dernière.
    p = f"on/{max(nb_images - 1, 1)}"

    z = f"{z0}+({z1}-{z0})*{p}"
    cx = f"({x0}+({x1}-{x0})*{p})"  # centre voulu, en fraction de la largeur
    cy = f"({y0}+({y1}-{y0})*{p})"  # centre voulu, en fraction de la hauteur

    if tremblement:
        # Temps en secondes, puis « fenêtre » valant 1 pendant la secousse et 0 ailleurs.
        t = f"on/{fps}"
        debut = tremblement["start"]
        fin = debut + tremblement["duration"]
        actif = f"between({t},{debut},{fin})"
        ax, ay = TREMBLEMENT_AMPLITUDE
        fx, fy = TREMBLEMENT_FREQUENCES
        cx = f"({cx}+{ax}*sin(2*PI*{fx}*{t})*{actif})"
        cy = f"({cy}+{ay}*sin(2*PI*{fy}*{t}+1)*{actif})"

    # Coin haut-gauche de la fenêtre = centre - demi-fenêtre. La fenêtre mesure
    # iw/zoom de large : on la borne pour qu'elle ne sorte jamais de l'image.
    x = f"max(0,min(iw-iw/zoom,{cx}*iw-iw/zoom/2))"
    y = f"max(0,min(ih-ih/zoom,{cy}*ih-ih/zoom/2))"
    return z, x, y


def chaine_camera(camera, nb_images, largeur, hauteur, fps, tremblement=None):
    """Filtres « cover » + zoompan. Sert à l'image ET aux textes posés sur l'image :
    même chaîne = même géométrie, donc le texte reste collé au papier."""
    grande_l = largeur * SURECHANTILLONNAGE
    grande_h = hauteur * SURECHANTILLONNAGE
    z, x, y = expression_camera(camera, nb_images, fps, tremblement)
    return ",".join([
        # « Cover » : remplit exactement le format 9:16 puis rogne l'excédent,
        # quelle que soit la taille de l'image source (pas de déformation).
        f"scale={grande_l}:{grande_h}:force_original_aspect_ratio=increase",
        f"crop={grande_l}:{grande_h}",
        f"zoompan=z='{z}':x='{x}':y='{y}':d={nb_images}:s={largeur}x{hauteur}:fps={fps}",
    ])


# Couleurs du fond : le JPEG est en plage complète (0-255) avec la matrice BT.601 ;
# la vidéo standard est en plage limitée (16-235) avec BT.709.
COULEURS_IMAGE = "zscale=rangein=full:range=limited:matrixin=470bg:matrix=709,setsar=1,format=yuv420p"

# Même conversion pour un texte (RGBA -> YUV avec transparence), pour que ses
# couleurs soient lues avec la même matrice que le fond.
COULEURS_TEXTE = "scale=out_color_matrix=bt709:out_range=tv,format=yuva420p"


def source_animee(plan, dossier):
    """Chemin de l'animation générée pour ce plan, ou None (le plan reste fixe)."""
    if "animation" not in plan:
        return None
    fichier = chemin_animation(plan, dossier)
    return fichier if fichier.exists() else None


def chaine_animation(largeur, hauteur, fps):
    """Filtres pour une vidéo source : « cover » 9:16, 30 i/s, dernière image figée si besoin."""
    return ",".join([
        f"scale={largeur}:{hauteur}:force_original_aspect_ratio=increase:flags=lanczos",
        f"crop={largeur}:{hauteur}",
        # Les modèles vidéo sortent en 24 i/s : on passe à la cadence de l'épisode (30).
        f"fps={fps}",
        # Si l'animation est plus courte que le plan, on fige sa dernière image (-frames:v coupe le surplus).
        "tpad=stop_mode=clone:stop_duration=3",
        "setsar=1",
        "format=yuv420p",
    ])


def preparer_surimpressions(plan, largeur, hauteur, dossier):
    """Dessine chaque surimpression dans un PNG (dossier output/tmp).

    Renvoie une liste de dicts : la surimpression, son PNG, sa position (x, y),
    et son espace ("screen" : fixe à l'écran ; "image" : collé à l'image).
    """
    TMP.mkdir(parents=True, exist_ok=True)
    taille_image = Image.open(dossier / plan["image"]).size
    resultat = []
    for k, s in enumerate(plan.get("overlays", [])):
        png = TMP / f"plan{plan['id']:02d}_texte{k}.png"
        if s["space"] == "image":
            # PNG de la taille de l'image source : le texte est à sa place sur une
            # feuille transparente, qui passera dans la même caméra que l'image.
            calque, position = rendre(s, taille_image)
            feuille = Image.new("RGBA", taille_image, (0, 0, 0, 0))
            feuille.alpha_composite(calque, position)
            feuille.save(png)
            resultat.append({"spec": s, "png": png, "pos": (0, 0), "espace": "image"})
        else:
            calque, position = rendre(s, (largeur, hauteur))
            calque.save(png)
            resultat.append({"spec": s, "png": png, "pos": position,
                             "taille": calque.size, "espace": "screen"})
    return resultat


def filtre_fondu(spec):
    """Fondu d'apparition sur la transparence (alpha), à partir de `start`."""
    fondu = spec.get("fade_in", 0.0)
    if fondu <= 0:
        return None
    return f"fade=t=in:st={spec.get('start', 0.0)}:d={fondu}:alpha=1"


def expression_y(entree):
    """Position verticale du texte ; animée si "animation" vaut "slide_down"."""
    spec = entree["spec"]
    x, y = entree["pos"]
    if spec.get("animation") != "slide_down":
        return str(y)
    debut = spec.get("start", 0.0)
    duree = spec.get("fade_in") or GLISSEMENT_PAR_DEFAUT
    distance = y + entree["taille"][1]  # part de juste au-dessus de l'écran
    # Progression 0 -> 1 pendant `duree`, puis (1-p)^2 : arrivée qui ralentit en douceur.
    progression = f"min(1,max(0,(t-{debut})/{duree}))"
    return f"{y}-{distance}*pow(1-{progression},2)"


def make_clip(plan, format_video, duree, dossier, sortie):
    """Crée le clip vidéo (sans son) d'un plan. Renvoie le chemin du fichier."""
    fps = format_video["fps"]
    largeur, hauteur = format_video["width"], format_video["height"]
    nb_images = round(duree * fps)
    tremblement = plan.get("shake")
    animation = source_animee(plan, dossier)
    surimpressions = preparer_surimpressions(plan, largeur, hauteur, dossier)

    if animation:
        # Plan animé : la caméra est déjà dans la vidéo (pas de zoompan ni de tremblement), donc un
        # texte « image » ne pourrait pas la suivre.
        if any(s["space"] == "image" for s in plan.get("overlays", [])):
            raise ValueError(f"Plan {plan['id']} : un texte « image » ne peut pas suivre une animation "
                             f"(retire l'animation ou passe ce texte en « screen »).")
        camera = None
        entrees = ["-i", str(animation)]
        filtres = [f"[0:v]{chaine_animation(largeur, hauteur, fps)}[v0]"]
    else:
        camera = chaine_camera(plan["camera"], nb_images, largeur, hauteur, fps, tremblement)
        # Entrée 0 = l'image du plan, étalonnée si besoin. Les suivantes = un PNG par surimpression.
        entrees = ["-i", str(etalonner(plan, dossier))]
        filtres = [f"[0:v]{camera},{COULEURS_IMAGE}[v0]"]
    courant = "v0"

    for k, entree in enumerate(surimpressions, start=1):
        spec = entree["spec"]
        fondu = filtre_fondu(spec)
        debut = spec.get("start", 0.0)

        if entree["espace"] == "image":
            # Une seule image (sans -loop) : zoompan en fabrique `nb_images` à partir d'elle.
            entrees += ["-i", str(entree["png"])]
            etapes = [f"[{k}:v]{camera}", "format=rgba"]
        else:
            # Texte fixe : on répète le PNG pendant toute la durée du plan.
            entrees += ["-loop", "1", "-framerate", str(fps), "-t", f"{duree:.3f}",
                        "-i", str(entree["png"])]
            etapes = [f"[{k}:v]format=rgba"]
        if fondu:
            etapes.append(fondu)
        etapes.append(COULEURS_TEXTE)
        filtres.append(",".join(etapes) + f"[t{k}]")

        # Avant `start`, le texte n'existe pas encore (indispensable si fade_in vaut 0).
        activer = f":enable='gte(t,{debut})'" if debut > 0 else ""
        x = entree["pos"][0]
        filtres.append(f"[{courant}][t{k}]overlay=x={x}:y='{expression_y(entree)}'"
                       f":format=yuv420{activer}[v{k}]")
        courant = f"v{k}"

    commande = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *entrees,
        "-filter_complex", ";".join(filtres),
        "-map", f"[{courant}]", "-frames:v", str(nb_images),
        "-c:v", "libx264", "-crf", "18", "-an",
        # On déclare explicitement l'espace colorimétrique de la sortie.
        "-colorspace", "bt709", "-color_primaries", "bt709",
        "-color_trc", "bt709", "-color_range", "tv",
        str(sortie),
    ]

    # Liste d'arguments (pas une chaîne) : pas de problème de guillemets PowerShell.
    resultat = subprocess.run(commande, capture_output=True, text=True, errors="replace")
    if resultat.returncode != 0:
        raise RuntimeError(f"ffmpeg a échoué sur le plan {plan['id']} :\n{resultat.stderr}")
    return sortie


def generer_clips(episode, dossier, voulus=()):
    """Génère les clips des plans demandés (tous si `voulus` est vide). Renvoie 0 si tout va bien."""
    SORTIE.mkdir(parents=True, exist_ok=True)
    for plan in episode["shots"]:
        if voulus and plan["id"] not in voulus:
            continue
        duree = duree_plan(plan, episode["timing"], dossier)
        fichier = SORTIE / f"plan{plan['id']:02d}.mp4"
        if source_animee(plan, dossier):
            note = " [animé]"
        elif "animation" in plan:
            note = " [animation absente : plan fixe]"
        else:
            note = ""
        print(f"Plan {plan['id']:02d} : {duree:5.2f} s -> {fichier}{note} ...", end=" ", flush=True)
        try:
            make_clip(plan, episode["format"], duree, dossier, fichier)
        except FileNotFoundError as erreur:
            print(f"\nERREUR : {erreur}")
            return 1
        except (RuntimeError, ValueError) as erreur:
            print(f"\n{erreur}")
            return 1
        print("ok")
    return 0


def main():
    dossier = Path(DOSSIER_PAR_DEFAUT)
    episode = charger_episode(dossier)
    voulus = {int(a) for a in sys.argv[1:]}  # vide = tous les plans
    return generer_clips(episode, dossier, voulus)


if __name__ == "__main__":
    sys.exit(main())
