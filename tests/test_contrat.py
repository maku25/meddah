"""Tests du schéma d'episode.json : l'épisode 1 réel sert de référence."""

import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import contrat

EPISODE_1 = (
    Path(__file__).resolve().parents[1]
    / "series" / "enzo" / "episodes" / "ep01" / "episode.json"
)


@pytest.fixture
def brut():
    """L'épisode 1 sous forme de dictionnaire, relu à chaque test (jamais modifié sur disque)."""
    return json.loads(EPISODE_1.read_text(encoding="utf-8-sig"))


def test_episode_1_est_valide():
    episode = contrat.charger_episode(EPISODE_1)
    assert (episode.series, episode.episode) == ("enzo", 1)
    assert len(episode.shots) == 10
    assert episode.shots[9].voice_text is None  # le plan 10 est muet


def test_aller_retour_sans_perte(brut):
    # Lire puis réécrire l'épisode doit redonner exactement le même JSON :
    # le schéma ne perd et n'invente aucun champ.
    episode = contrat.Episode.model_validate(brut)
    assert episode.model_dump(mode="json", exclude_unset=True) == brut


def test_fichier_avec_bom_accepte(tmp_path):
    # Le piège de Set-Content sous PowerShell : un BOM en tête de fichier.
    chemin = tmp_path / "episode.json"
    chemin.write_text(EPISODE_1.read_text(encoding="utf-8-sig"), encoding="utf-8-sig")
    assert contrat.charger_episode(chemin).episode == 1


# Chaque défaut abîme une copie de l'épisode 1 d'une seule façon.
def champ_inconnu(e): e["shots"][0]["voice_txt"] = "faute de frappe"
def style_inconnu(e): e["shots"][0]["overlays"][0]["style"] = "counter_medium"
def space_inconnu(e): e["shots"][0]["overlays"][0]["space"] = "ecran"
def label_inconnu(e): e["shots"][0]["overlays"][0]["label"] = "Argent"
def zoom_trop_fort(e): e["shots"][0]["camera"]["zoom"] = [1.0, 2.0]
def centre_hors_image(e): e["shots"][0]["camera"]["center"] = [[0.5, 0.5], [0.5, 1.2]]
def box_a_trois_valeurs(e): e["shots"][0]["overlays"][0]["box"] = [0.25, 0.045, 0.75]
def resolution_inconnue(e): e["shots"][0]["animation"]["resolution"] = "1080p"
def texte_vide(e): e["shots"][0]["overlays"][0]["text"] = ""
def camera_absente(e): del e["shots"][0]["camera"]
def aucun_plan(e): e["shots"] = []
def duree_negative(e): e["shots"][9]["duration"] = -1.0


DEFAUTS = [
    champ_inconnu, style_inconnu, space_inconnu, label_inconnu, zoom_trop_fort,
    centre_hors_image, box_a_trois_valeurs, resolution_inconnue, texte_vide,
    camera_absente, aucun_plan, duree_negative,
]


@pytest.mark.parametrize("abimer", DEFAUTS, ids=lambda f: f.__name__)
def test_defaut_refuse(brut, abimer):
    episode = copy.deepcopy(brut)
    abimer(episode)
    with pytest.raises(ValidationError):
        contrat.Episode.model_validate(episode)