import csv
import time
import warnings
from dataclasses import dataclass, replace
from typing import Any

from datetime import date, datetime
from pathlib import Path

import httpx
from google import genai
from pydantic import BaseModel, Field, ValidationError

MODELE = "gemini-4-argon"
NIVEAUX_REFLEXIONS = {
    "low": genai.types.ThinkingLevel.LOW,
    "medium": genai.types.ThinkingLevel.MEDIUM,
    "high": genai.types.ThinkingLevel.HIGH,
}
NIVEAU_PAR_DEFAUT = "medium"
MAX_TOKENS_SORTIE = 16384
ESSAIS_MAX = 3
CODES_REESSAYABLES = [408, 429, 500, 502, 503, 504]
TIMEOUT_S = 600

PRIX = {
    "gemini-4-argon": [
        (date(2026, 11, 30), 2.00, 10.00),
        (date.max, 4.00, 20.00),
    ],
}

RACINE = Path(__file__).resolve().parents[2]
JOURNAL = RACINE / "output" / "couts_llm.csv"

COLONNES = [
    "horodatage",
    "agent",
    "modele",
    "niveau",
    "tokens_entree",
    "tokens_sortie",
    "tokens_reflexion",
    "cout_usd",
    "duree_s",
]

@dataclass(frozen=True)
class Reponse:
    texte: str | None
    modele: str
    niveau: str
    tokens_entree: int
    tokens_sortie: int
    tokens_reflexion: int
    cout: float
    duree_s: float
    donnees: Any = None

    @property
    def tokens_total(self) -> int:
        return self.tokens_entree + self.tokens_sortie + self.tokens_reflexion

    def resume(self) -> str:
        return (
            f"[{self.modele} {self.niveau}] entree={self.tokens_entree} "
            f"sortie={self.tokens_sortie} reflexion={self.tokens_reflexion} "
            f"total={self.tokens_total} | cout={self.cout:.5f} $ "
            f"| {self.duree_s:.1f} s"
        )

class ErreurLLM(Exception):
    """Base de toutes les erreurs de llm.py : un agent n'attrape que celle-ci."""


class ErreurAPI(ErreurLLM):
    """L'appel a échoué (réseau, quota, serveur, modèle) malgré les essais.
    Rien n'a été facturé, donc rien n'est journalisé."""


class ErreurReponse(ErreurLLM):
    """L'appel a abouti et a été facturé, mais la réponse est inutilisable.
    L'objet Reponse (tokens, coût, texte brut) est joint pour l'agent."""

    def __init__(self, message: str, reponse: Reponse) -> None:
        super().__init__(message)
        self.reponse = reponse


class ErreurReponseVide(ErreurReponse):
    """Le texte est None (réponse bloquée ou coupée)."""


class ErreurSortieInvalide(ErreurReponse):
    """Le texte ne respecte pas le schéma demandé (JSON tronqué, champ manquant)."""


def _raison_arret(reponse: genai.types.GenerateContentResponse) -> str:
    """Pourquoi le modèle s'est arrêté (STOP, MAX_TOKENS, SAFETY...), pour le diagnostic."""
    candidats = reponse.candidates or []
    if candidats and candidats[0].finish_reason is not None:
        return candidats[0].finish_reason.name
    retour = reponse.prompt_feedback
    if retour is not None and retour.block_reason is not None:
        return f"prompt bloqué ({retour.block_reason.name})"
    return "inconnue"

def tarif(modele: str, jour: date | None = None):
    jour = jour or date.today()

    for dernier_jour, prix_entree, prix_sortie in PRIX[modele]:
        if jour <= dernier_jour:
            return prix_entree, prix_sortie
    raise ValueError(f"aucun tarif pour {modele!r} au {jour}")

def calculer_cout(
    tokens_entree: int,
    tokens_sortie: int,
    tokens_reflexion: int = 0,
    modele: str = MODELE,
    jour: date | None = None,
) -> float:
    prix_entree, prix_sortie = tarif(modele, jour)
    return (
        tokens_entree * prix_entree
        + (tokens_sortie + tokens_reflexion) * prix_sortie
    ) / 1_000_000

def journaliser(reponse: Reponse, agent: str, chemin: Path = JOURNAL) -> None:
    """Ajoute une ligne au journal des coûts (crée le fichier si besoin)."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    # L'en-tête n'est écrit que si le fichier n'existe pas ou est vide.
    nouveau = not chemin.exists() or chemin.stat().st_size == 0
    with chemin.open("a", newline="", encoding="utf-8") as f:
        ecrivain = csv.DictWriter(f, fieldnames=COLONNES)
        if nouveau:
            ecrivain.writeheader()
        ecrivain.writerow({
            "horodatage": datetime.now().astimezone().isoformat(timespec="seconds"),
            "agent": agent,
            "modele": reponse.modele,
            "niveau": reponse.niveau,
            "tokens_entree": reponse.tokens_entree,
            "tokens_sortie": reponse.tokens_sortie,
            "tokens_reflexion": reponse.tokens_reflexion,
            "cout_usd": f"{reponse.cout:.6f}",
            "duree_s": f"{reponse.duree_s:.2f}",
        })


def cout_total(chemin: Path = JOURNAL) -> float:
    """Somme des coûts du journal, en dollars (0.0 s'il n'existe pas encore)."""
    if not chemin.exists():
        return 0.0
    with chemin.open(newline="", encoding="utf-8") as f:
        return sum(float(ligne["cout_usd"]) for ligne in csv.DictReader(f))

def appeler(prompt: str, system_prompt: str | None = None, niveau: str = NIVEAU_PAR_DEFAUT, agent: str = "inconnu", schema: type[BaseModel] | None = None) -> Reponse:


    if niveau not in NIVEAUX_REFLEXIONS:
        raise ValueError(
            f"niveau doit être l'un de {sorted(NIVEAUX_REFLEXIONS)}, reçu {niveau!r}"
        )

    client = genai.Client(
        http_options=genai.types.HttpOptions(
            timeout=TIMEOUT_S * 1000,
            retry_options=genai.types.HttpRetryOptions(
                attempts=ESSAIS_MAX,
                initial_delay=1.0,
                http_status_codes=CODES_REESSAYABLES,
            ),
        ),
    )

    config = genai.types.GenerateContentConfig(
        system_instruction=system_prompt,
        max_output_tokens=MAX_TOKENS_SORTIE,
        thinking_config=genai.types.ThinkingConfig(
            thinking_level=NIVEAUX_REFLEXIONS[niveau],
        ),
        response_mime_type="application/json" if schema is not None else None,
        response_schema=schema,
    )

    debut = time.perf_counter()
    try:
        reponse = client.models.generate_content(
            model=MODELE,
            contents=prompt,
            config=config,
        )
    except (genai.errors.APIError, httpx.TransportError) as erreur:
        raise ErreurAPI(f"appel à {MODELE} échoué : {erreur}") from erreur
    duree = time.perf_counter() - debut

    usage = reponse.usage_metadata
    usage = reponse.usage_metadata
    tokens_entree = (usage.prompt_token_count or 0) if usage else 0
    tokens_sortie = (usage.candidates_token_count or 0) if usage else 0
    tokens_reflexion = (usage.thoughts_token_count or 0) if usage else 0

    resultat = Reponse(
        texte=reponse.text,
        modele=MODELE,
        niveau=niveau,
        tokens_entree=tokens_entree,
        tokens_sortie=tokens_sortie,
        tokens_reflexion=tokens_reflexion,
        cout=calculer_cout(tokens_entree, tokens_sortie, tokens_reflexion),
        duree_s=duree,
    )

    try:
        journaliser(resultat, agent)
    except OSError as erreur:
        warnings.warn(f"Journal des coûts non écrit ({erreur}).")

    if resultat.texte is None:
        raise ErreurReponseVide(
            f"réponse vide (raison d'arrêt : {_raison_arret(reponse)})",
            resultat,
        )

    if schema is not None:
        try:
            donnees = schema.model_validate_json(resultat.texte)
        except ValidationError as erreur:
            raise ErreurSortieInvalide(
                f"JSON non conforme au schéma {schema.__name__} "
                f"(raison d'arrêt : {_raison_arret(reponse)}) : {erreur}",
                resultat,
            ) from erreur
        resultat = replace(resultat, donnees=donnees)

    return resultat


if __name__ == "__main__":
    # Test manuel : python src\meddah\llm.py

    class Accroche(BaseModel):
        """Schéma de test. Le vrai schéma d'episode.json viendra avec le scénariste."""

        # Les descriptions sont envoyées au modèle : un mini-prompt par champ.
        voix_off: str = Field(
            description="Une seule phrase de voix off, à la première personne."
        )
        compteur_depart: int = Field(
            description="Montant du compteur au début de l'épisode, en euros."
        )

    SYSTEM_PROMPT_TEST = (
        "Tu es le scénariste de la série Enzo, l'histoire d'un jeune de 18 ans "
        "qui doit réunir 3 400 euros en trois mois, uniquement par des moyens "
        "légaux. Ton réaliste, voix off à la première personne, jamais de "
        "discours « deviens riche vite »."
    )
    PROMPT_TEST = "Écris l'accroche de l'épisode 2. Le compteur de départ est de 37 euros."

    # Test 0 (gratuit) : un JSON incomplet est refusé, sans appel réseau.
    try:
        Accroche.model_validate_json('{"voix_off": "il manque le compteur"}')
    except ValidationError as erreur:
        print("JSON incomplet refusé :", type(erreur).__name__)

    # Test 1 (gratuit) : un modèle qui n'existe pas -> erreur 404, jamais rejouée.
    modele_reel = MODELE
    MODELE = "gemini-4-argon-inexistant"
    try:
        appeler("test", agent="test_llm")
    except ErreurAPI as erreur:
        print("ErreurAPI :", erreur)
    MODELE = modele_reel

    # Test 2 : réponse coupée (plafond de 20 tokens). L'appel est payé et
    # journalisé, mais on obtient une erreur claire, pas du texte tronqué.
    plafond_reel = MAX_TOKENS_SORTIE
    MAX_TOKENS_SORTIE = 20
    try:
        appeler(
            PROMPT_TEST,
            system_prompt=SYSTEM_PROMPT_TEST,
            niveau="low",
            agent="test_llm",
            schema=Accroche,
        )
    except ErreurReponse as erreur:
        print(type(erreur).__name__, ":", erreur)
        print(erreur.reponse.resume())
    MAX_TOKENS_SORTIE = plafond_reel

    # Test 3 : un appel normal avec schéma (le test de l'étape 6).
    r = appeler(
        PROMPT_TEST,
        system_prompt=SYSTEM_PROMPT_TEST,
        niveau="low",
        agent="test_llm",
        schema=Accroche,
    )
    print(r.texte)           # le JSON brut renvoyé par le modèle
    print(type(r.donnees))   # une instance d'Accroche : un objet, plus du texte
    print(r.donnees.voix_off)
    print(r.resume())

    # Vérification en code : le schéma garantit le type, pas le sens.
    print("Compteur OK" if r.donnees.compteur_depart == 37 else "Compteur FAUX")
    print(f"Coût cumulé du journal : {cout_total():.5f} $")
