"""contrat.py : le schéma d'episode.json, le contrat entre les agents et le monteur.

Ce fichier décrit, avec des classes Pydantic, ce qu'est un episode.json
bien formé. Il vérifie la FORME de chaque champ (type, valeurs permises,
bornes). Les règles qui relient plusieurs champs (8 à 10 plans, 90 à 110
mots de voix off...) sont dans les vérifications métier, à part.

Les noms des champs sont ceux du JSON (en anglais), car le monteur les lit
tels quels.

Vérifier un épisode : python src\\meddah\\agents\\contrat.py [chemin/episode.json]
"""

import sys
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

# Racine du dépôt : contrat.py est dans src/meddah/agents/, trois dossiers plus haut.
RACINE = Path(__file__).resolve().parents[3]
EPISODE_PAR_DEFAUT = RACINE / "series" / "enzo" / "episodes" / "ep01" / "episode.json"

# --- Types réutilisables ------------------------------------------------------

# Une position ou une taille exprimée en fraction de l'image : entre 0 et 1.
Fraction = Annotated[float, Field(ge=0.0, le=1.0)]
# Un point [x, y] en fractions de l'image.
Point = tuple[Fraction, Fraction]
# Un facteur de zoom : 1.0 = image entière, 1.3 = limite du monteur.
Zoom = Annotated[float, Field(ge=1.0, le=1.3)]
# Une durée ou un instant en secondes, jamais négatif.
Secondes = Annotated[float, Field(ge=0.0)]

StyleTexte = Literal[
    "counter_small",
    "counter_big",
    "goal_big",
    "letter",
    "message_card",
    "to_be_continued",
]


class Strict(BaseModel):
    """Base de toutes les classes : un champ inconnu est refusé, pas ignoré."""

    model_config = ConfigDict(extra="forbid")


# --- Blocs d'un plan ----------------------------------------------------------

class Camera(Strict):
    """Mouvement de caméra d'un plan fixe : du premier réglage au second."""

    zoom: tuple[Zoom, Zoom]  # [début, fin]
    center: tuple[Point, Point]  # [[x, y] de départ, [x, y] d'arrivée]


class Overlay(Strict):
    """Un texte ajouté au montage (jamais généré dans l'image)."""

    style: StyleTexte
    text: str = Field(min_length=1)
    # "screen" : fixe à l'écran. "image" : collé à l'image, suit la caméra.
    space: Literal["screen", "image"]
    box: tuple[Fraction, Fraction, Fraction, Fraction]  # [x0, y0, x1, y1]
    start: Secondes  # depuis le début du plan
    fade_in: Secondes
    label: Literal["ARGENT", "OBJECTIF"] | None = None  # libellé d'un compteur
    sender: str | None = None  # expéditeur d'une carte de message
    animation: Literal["slide_down"] | None = None


class Shake(Strict):
    """Tremblement de caméra (plan fixe)."""

    start: Secondes
    duration: float = Field(gt=0.0)


class Animation(Strict):
    """Animation image-vers-vidéo du plan. Le prompt décrit le mouvement seulement."""

    prompt: str = Field(min_length=1)
    resolution: Literal["360p", "720p"]


class Grade(Strict):
    """Étalonnage imposé (sinon le monteur le calcule tout seul)."""

    blue: float | None = Field(default=None, gt=0.0)
    gamma: float | None = Field(default=None, gt=0.0)


class Plan(Strict):
    """Un plan de l'épisode : un élément de la liste "shots"."""

    id: int = Field(ge=1)
    image: str = Field(min_length=1)
    voice: str | None = None  # absent pour un plan muet
    voice_text: str | None = None  # None pour un plan muet
    extra_hold: Secondes | None = None  # pause après la voix
    duration: float | None = Field(default=None, gt=0.0)  # plan sans voix
    camera: Camera
    overlays: list[Overlay] = []
    shake: Shake | None = None
    animation: Animation | None = None
    # False = aucune correction ; un objet Grade = valeurs imposées.
    grade: Literal[False] | Grade | None = None


# --- L'épisode ----------------------------------------------------------------

class Format(Strict):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fps: int = Field(gt=0)


class Timing(Strict):
    lead_in: Secondes  # avance avant la voix
    tail: Secondes  # marge après la voix


class Episode(Strict):
    """La racine d'episode.json."""

    series: str = Field(min_length=1)
    episode: int = Field(ge=1)
    title: str = Field(min_length=1)
    format: Format
    timing: Timing
    shots: list[Plan] = Field(min_length=1)


def charger_episode(chemin: Path) -> Episode:
    """Lit un episode.json et le valide. Lève ValidationError s'il est mal formé.

    "utf-8-sig" accepte un fichier avec ou sans BOM (le piège de
    Set-Content sous PowerShell).
    """
    texte = Path(chemin).read_text(encoding="utf-8-sig")
    return Episode.model_validate_json(texte)


if __name__ == "__main__":
    chemin = Path(sys.argv[1]) if len(sys.argv) > 1 else EPISODE_PAR_DEFAUT
    try:
        episode = charger_episode(chemin)
    except ValidationError as erreur:
        print(f"INVALIDE : {chemin}")
        print(erreur)
        sys.exit(1)
    print(
        f"VALIDE : {episode.series}, épisode {episode.episode} « {episode.title} », "
        f"{len(episode.shots)} plans."
    )