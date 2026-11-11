"""Tests des règles métier : l'épisode 1 réel est conforme, chaque défaut est détecté."""

import copy
import json
from pathlib import Path

import pytest

import contrat
import regles

EPISODE_1 = (
    Path(__file__).resolve().parents[1]
    / "series" / "enzo" / "episodes" / "ep01" / "episode.json"
)


@pytest.fixture
def brut():
    """L'épisode 1 sous forme de dictionnaire, relu à chaque test."""
    return json.loads(EPISODE_1.read_text(encoding="utf-8-sig"))


def test_episode_1_est_conforme(brut):
    episode = contrat.Episode.model_validate(brut)
    assert regles.verifier(episode, depart_attendu=37, objectif_attendu=3400) == []


def test_mesures_de_l_episode_1(brut):
    episode = contrat.Episode.model_validate(brut)
    assert regles.compter_mots(episode) == 93
    assert regles.compteur_depart(episode) == 37
    assert regles.compteur_final(episode) == 37  # le départ de l'épisode 2


@pytest.mark.parametrize("euros, texte", [
    (37, "37\u00a0€"),
    (3400, "3\u00a0400\u00a0€"),
    (-120, "-120\u00a0€"),  # le compteur peut passer dans le rouge
])
def test_formater_puis_lire_un_montant(euros, texte):
    assert regles.formater_montant(euros) == texte
    assert regles.lire_montant(texte) == euros


def test_lire_montant_tolere_les_espaces_normales_et_refuse_le_reste():
    assert regles.lire_montant("3 400 €") == 3400
    assert regles.lire_montant("trente-sept euros") is None
    assert regles.lire_montant("37") is None


# Chaque défaut abîme une copie de l'épisode 1 d'une seule façon. Tous
# passent le schéma de contrat.py : seule une règle métier peut les voir.
def trop_peu_de_plans(e): del e["shots"][3:6]
def trop_de_mots(e): e["shots"][0]["voice_text"] += " et" * 30
def numerotation_fausse(e): e["shots"][2]["id"] = 7
def voix_et_duree(e): e["shots"][0]["duration"] = 2.0
def ni_voix_ni_duree(e): del e["shots"][9]["duration"]
def nom_d_image_faux(e): e["shots"][0]["image"] = "images/plan1.jpg"
def texte_image_sur_plan_anime(e): e["shots"][0]["overlays"][0]["space"] = "image"
def boite_inversee(e): e["shots"][0]["overlays"][0]["box"] = [0.75, 0.045, 0.25, 0.1]
def libelle_manquant(e): del e["shots"][0]["overlays"][0]["label"]
def libelle_mal_place(e): e["shots"][7]["overlays"][1]["label"] = "ARGENT"
def expediteur_manquant(e): del e["shots"][8]["overlays"][0]["sender"]
def pas_de_a_suivre(e): e["shots"][9]["overlays"] = []
def montant_illisible(e): e["shots"][0]["overlays"][0]["text"] = "trente-sept euros"


DEFAUTS = [
    (trop_peu_de_plans, "plans"),
    (trop_de_mots, "mots"),
    (numerotation_fausse, "numérotés"),
    (voix_et_duree, "duration"),
    (ni_voix_ni_duree, "duration"),
    (nom_d_image_faux, "images/plan01.jpg"),
    (texte_image_sur_plan_anime, "plan animé"),
    (boite_inversee, "boîte"),
    (libelle_manquant, "libellé"),
    (libelle_mal_place, "libellé"),
    (expediteur_manquant, "sender"),
    (pas_de_a_suivre, "À suivre"),
    (montant_illisible, "montant"),
]


@pytest.mark.parametrize("abimer, mot_cle", DEFAUTS, ids=lambda p: getattr(p, "__name__", None))
def test_defaut_detecte(brut, abimer, mot_cle):
    copie = copy.deepcopy(brut)
    abimer(copie)
    episode = contrat.Episode.model_validate(copie)  # la forme reste valide
    erreurs = regles.verifier(episode)
    assert any(mot_cle in message for message in erreurs), erreurs


def test_compteur_de_depart_faux(brut):
    episode = contrat.Episode.model_validate(brut)
    erreurs = regles.verifier(episode, depart_attendu=70)
    assert len(erreurs) == 1 and "démarrer" in erreurs[0]


def test_objectif_faux(brut):
    episode = contrat.Episode.model_validate(brut)
    erreurs = regles.verifier(episode, objectif_attendu=5000)
    assert len(erreurs) == 1 and "objectif" in erreurs[0]


def test_toutes_les_erreurs_sont_remontees_ensemble(brut):
    # Deux défauts indépendants -> deux erreurs, en un seul passage.
    copie = copy.deepcopy(brut)
    voix_et_duree(copie)
    boite_inversee(copie)
    erreurs = regles.verifier(contrat.Episode.model_validate(copie))
    assert len(erreurs) == 2