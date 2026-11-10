"""Tests de llm.py avec un faux client : aucun appel réseau, aucun coût."""

from datetime import date
from types import SimpleNamespace

import httpx
import pytest
from pydantic import BaseModel

import llm


class Accroche(BaseModel):
    voix_off: str
    compteur_depart: int


def fausse_reponse(texte, entree=100, sortie=50, reflexion=0, raison="STOP"):
    """Imite l'objet renvoyé par le SDK, avec seulement les champs lus par appeler()."""
    return SimpleNamespace(
        text=texte,
        usage_metadata=SimpleNamespace(
            prompt_token_count=entree,
            candidates_token_count=sortie,
            thoughts_token_count=reflexion,
        ),
        candidates=[SimpleNamespace(finish_reason=SimpleNamespace(name=raison))],
        prompt_feedback=None,
    )


class FauxClient:
    """Imite client.models.generate_content() : renvoie une réponse ou lève une erreur."""

    def __init__(self, reponse=None, erreur=None):
        self.reponse = reponse
        self.erreur = erreur
        self.appels = []    # ce que appeler() a envoyé, pour le vérifier
        self.models = self  # client.models.generate_content -> self.generate_content

    def generate_content(self, model, contents, config):
        self.appels.append({"model": model, "contents": contents, "config": config})
        if self.erreur is not None:
            raise self.erreur
        return self.reponse


@pytest.fixture
def journal(monkeypatch):
    """Remplace journaliser() par un espion : rien n'est écrit dans le vrai CSV."""
    lignes = []
    monkeypatch.setattr(
        llm, "journaliser", lambda reponse, agent: lignes.append((agent, reponse))
    )
    return lignes


def test_calculer_cout_selon_la_date():
    # Le 30 novembre est encore au tarif d'introduction, le 1er décembre non.
    assert llm.calculer_cout(1000, 500, 500, jour=date(2026, 11, 30)) == pytest.approx(0.012)
    assert llm.calculer_cout(1000, 500, 500, jour=date(2026, 12, 1)) == pytest.approx(0.024)


def test_niveau_invalide_refuse_avant_tout_appel():
    client = FauxClient(fausse_reponse("Bonjour"))
    with pytest.raises(ValueError):
        llm.appeler("Salut", niveau="extreme", client=client)
    assert client.appels == []  # rien n'a été envoyé


def test_appel_reussi(journal):
    client = FauxClient(fausse_reponse("Bonjour", entree=119, sortie=57))
    r = llm.appeler(
        "Salut", system_prompt="Tu es le scénariste.", agent="scenariste", client=client
    )
    assert r.texte == "Bonjour"
    assert (r.tokens_entree, r.tokens_sortie, r.tokens_reflexion) == (119, 57, 0)
    assert r.tokens_total == 176
    # Comparé à calculer_cout() : le test reste vrai après le changement de tarif.
    assert r.cout == pytest.approx(llm.calculer_cout(119, 57, 0))
    # Ce qui a été envoyé au modèle.
    envoi = client.appels[0]
    assert envoi["contents"] == "Salut"
    assert "scénariste" in str(envoi["config"].system_instruction)
    # Une ligne de journal, au nom du bon agent.
    assert [agent for agent, _ in journal] == ["scenariste"]


def test_schema_valide(journal):
    client = FauxClient(fausse_reponse('{"voix_off": "Une phrase.", "compteur_depart": 37}'))
    r = llm.appeler("Salut", schema=Accroche, client=client)
    assert r.donnees.compteur_depart == 37
    assert client.appels[0]["config"].response_mime_type == "application/json"


def test_sortie_invalide_leve_une_erreur_avec_la_reponse(journal):
    # Rejoue gratuitement ton test 2 de l'étape 7 : JSON coupé par MAX_TOKENS.
    client = FauxClient(fausse_reponse('{"voix_off":', sortie=20, raison="MAX_TOKENS"))
    with pytest.raises(llm.ErreurSortieInvalide) as info:
        llm.appeler("Salut", schema=Accroche, client=client)
    assert "MAX_TOKENS" in str(info.value)
    assert info.value.reponse.tokens_sortie == 20
    assert len(journal) == 1  # l'appel est payé, donc journalisé


def test_reponse_vide_leve_une_erreur(journal):
    # Le cas jamais observé en vrai : la réflexion consomme tout le plafond.
    client = FauxClient(fausse_reponse(None, sortie=0, reflexion=16384, raison="MAX_TOKENS"))
    with pytest.raises(llm.ErreurReponseVide) as info:
        llm.appeler("Salut", client=client)
    assert info.value.reponse.tokens_reflexion == 16384
    assert len(journal) == 1


def test_erreur_reseau_devient_erreur_api(journal):
    client = FauxClient(erreur=httpx.ConnectError("réseau coupé"))
    with pytest.raises(llm.ErreurAPI):
        llm.appeler("Salut", client=client)
    assert journal == []  # rien de facturé, rien de journalisé


def test_journal_ecrit_et_cumule(tmp_path):
    chemin = tmp_path / "couts.csv"
    r = llm.Reponse(
        texte="x", modele="m", niveau="low",
        tokens_entree=100, tokens_sortie=50, tokens_reflexion=0,
        cout=0.001, duree_s=1.0,
    )
    llm.journaliser(r, "test", chemin)
    llm.journaliser(r, "test", chemin)
    lignes = chemin.read_text(encoding="utf-8").splitlines()
    assert len(lignes) == 3  # un seul en-tête, deux lignes de données
    assert llm.cout_total(chemin) == pytest.approx(0.002)


def test_journal_verrouille_ne_perd_pas_la_reponse(monkeypatch):
    def journal_casse(reponse, agent):
        raise PermissionError("fichier ouvert dans Excel")

    monkeypatch.setattr(llm, "journaliser", journal_casse)
    client = FauxClient(fausse_reponse("Bonjour"))
    with pytest.warns(UserWarning):
        r = llm.appeler("Salut", client=client)
    assert r.texte == "Bonjour"  # la réponse payée est quand même renvoyée
