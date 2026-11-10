"""llm.py : point d'entrée unique vers le modèle de texte.

Tous les agents de Meddah appellent le modèle par appeler(). Cette fonction :
- envoie un prompt (et un system prompt facultatif) au modèle ;
- mesure les tokens, le coût et la durée, et les écrit dans un journal ;
- peut forcer une sortie JSON conforme à un schéma Pydantic ;
- transforme chaque échec en une erreur claire de la famille ErreurLLM.

Test manuel (payant, quelques millièmes de dollar) : python src\\meddah\\llm.py
Tests unitaires (gratuits, sans réseau) : python -m pytest -v
"""

import csv
import time
import warnings
from dataclasses import dataclass, replace
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx
from google import genai
from pydantic import BaseModel, Field, ValidationError

# --- Réglages ---------------------------------------------------------------

MODELE = "gemini-4-argon"

# Table de correspondance : nos noms simples -> l'énumération du SDK.
# Elle sert de liste des valeurs autorisées ET de traducteur.
NIVEAUX_REFLEXIONS = {
    "low": genai.types.ThinkingLevel.LOW,
    "medium": genai.types.ThinkingLevel.MEDIUM,
    "high": genai.types.ThinkingLevel.HIGH,
}
NIVEAU_PAR_DEFAUT = "medium"

# Plafond de tokens de sortie. Il compte la réflexion ET la réponse.
# Il sert aussi de garde-fou de coût : à 10 $ le million de tokens de
# sortie (prix d'introduction), un appel ne peut pas dépasser ~0,16 $.
MAX_TOKENS_SORTIE = 16384

# Réseau : le SDK rejoue seul les erreurs passagères. UNE seule couche de
# nouvelles tentatives : ne pas en ajouter une autre par-dessus.
ESSAIS_MAX = 3  # tentatives au total, requête d'origine comprise (vérifié dans le SDK)
CODES_REESSAYABLES = [408, 429, 500, 502, 503, 504]
# Délai d'attente par appel. Nos appels sont plafonnés à 16 384 tokens, donc
# loin des très longues générations pour lesquelles la doc d'Argon
# recommande 20 minutes. À relever si MAX_TOKENS_SORTIE augmente.
TIMEOUT_S = 600

# Prix en dollars par million de tokens.
# Pour chaque modèle : liste de (dernier jour du tarif, prix entrée, prix sortie).
# Argon : prix d'introduction jusqu'au 30 novembre 2026, puis tarif normal.
# Les tokens de réflexion sont facturés au prix de sortie.
PRIX = {
    "gemini-4-argon": [
        (date(2026, 11, 30), 2.00, 10.00),
        (date.max, 4.00, 20.00),
    ],
}

# Racine du dépôt : llm.py est dans src/meddah/, donc deux dossiers plus haut.
# Le dossier output/ est ignoré par git.
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


# --- Objet de réponse -------------------------------------------------------

@dataclass(frozen=True)
class Reponse:
    """Résultat d'un appel au modèle. Lecture seule (frozen)."""

    # None seulement dans la Reponse jointe à une ErreurReponseVide :
    # un appel qui réussit renvoie toujours du texte.
    texte: str | None
    modele: str
    niveau: str
    tokens_entree: int
    tokens_sortie: int
    tokens_reflexion: int
    cout: float  # en dollars
    duree_s: float  # durée de l'appel, en secondes
    donnees: Any = None  # objet du schéma (Pydantic) si un schéma est demandé

    @property
    def tokens_total(self) -> int:
        return self.tokens_entree + self.tokens_sortie + self.tokens_reflexion

    def resume(self) -> str:
        """Une ligne lisible : tokens, coût, durée."""
        return (
            f"[{self.modele} {self.niveau}] entree={self.tokens_entree} "
            f"sortie={self.tokens_sortie} reflexion={self.tokens_reflexion} "
            f"total={self.tokens_total} | cout={self.cout:.5f} $ "
            f"| {self.duree_s:.1f} s"
        )


# --- Erreurs ----------------------------------------------------------------

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


# --- Coût -------------------------------------------------------------------

def tarif(modele: str, jour: date | None = None) -> tuple[float, float]:
    """Renvoie (prix entrée, prix sortie) en $ par million de tokens."""
    jour = jour or date.today()
    for dernier_jour, prix_entree, prix_sortie in PRIX[modele]:
        if jour <= dernier_jour:
            return prix_entree, prix_sortie
    # Inatteignable tant que la liste finit par date.max.
    raise ValueError(f"aucun tarif pour {modele!r} au {jour}")


def calculer_cout(
    tokens_entree: int,
    tokens_sortie: int,
    tokens_reflexion: int = 0,
    modele: str = MODELE,
    jour: date | None = None,
) -> float:
    """Coût en dollars d'un appel. Fonction pure : aucun appel réseau."""
    prix_entree, prix_sortie = tarif(modele, jour)
    return (
        tokens_entree * prix_entree
        + (tokens_sortie + tokens_reflexion) * prix_sortie
    ) / 1_000_000


# --- Journal des coûts ------------------------------------------------------

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


# --- Appel au modèle --------------------------------------------------------

def creer_client() -> genai.Client:
    """Le vrai client : clé lue dans GEMINI_API_KEY, délai d'attente et
    nouvelles tentatives sur les erreurs passagères."""
    return genai.Client(
        http_options=genai.types.HttpOptions(
            timeout=TIMEOUT_S * 1000,  # le SDK attend des millisecondes
            retry_options=genai.types.HttpRetryOptions(
                attempts=ESSAIS_MAX,
                initial_delay=1.0,
                http_status_codes=CODES_REESSAYABLES,
            ),
        ),
    )


def appeler(
    prompt: str,
    system_prompt: str | None = None,
    niveau: str = NIVEAU_PAR_DEFAUT,
    agent: str = "inconnu",
    schema: type[BaseModel] | None = None,
    client: Any = None,
) -> Reponse:
    """Envoie un prompt au modèle, journalise le coût, renvoie une Reponse.

    prompt        : ce qu'on demande cette fois-ci (le user prompt).
    system_prompt : qui est le modèle et comment il se comporte, stable
                    d'un appel à l'autre. Facultatif.
    niveau        : profondeur de réflexion, "low", "medium" ou "high".
    agent         : nom de l'agent qui appelle (scenariste, voix...), pour
                    le journal des coûts.
    schema        : classe Pydantic décrivant le JSON attendu. Si fourni, le
                    modèle est forcé de répondre en JSON conforme et
                    Reponse.donnees contient l'objet validé.
    client        : client à utiliser. None = le vrai client. Les tests
                    passent un faux client, c'est-à-dire tout objet qui a
                    .models.generate_content().

    Lève ErreurAPI si l'appel échoue (rien de facturé), ErreurReponseVide ou
    ErreurSortieInvalide si la réponse est inutilisable (appel facturé et
    journalisé, Reponse jointe à l'erreur).
    """
    # Vérification en code AVANT l'appel : une faute de frappe ne coûte rien.
    if niveau not in NIVEAUX_REFLEXIONS:
        raise ValueError(
            f"niveau doit être l'un de {sorted(NIVEAUX_REFLEXIONS)}, reçu {niveau!r}"
        )

    if client is None:
        client = creer_client()

    # Tous les réglages de l'appel vivent dans un seul objet de configuration.
    config = genai.types.GenerateContentConfig(
        system_instruction=system_prompt,  # None = pas de system prompt
        max_output_tokens=MAX_TOKENS_SORTIE,
        thinking_config=genai.types.ThinkingConfig(
            thinking_level=NIVEAUX_REFLEXIONS[niveau],
        ),
        # Avec un schéma : JSON forcé. Sans schéma : None = texte libre.
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
        # "from erreur" garde l'erreur d'origine visible dans le message.
        raise ErreurAPI(f"appel à {MODELE} échoué : {erreur}") from erreur
    duree = time.perf_counter() - debut

    # Ces champs valent None quand il n'y a rien à compter : "or 0".
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

    # L'appel est déjà payé : une erreur d'écriture (fichier ouvert dans
    # Excel, disque plein...) ne doit pas faire perdre la réponse.
    try:
        journaliser(resultat, agent)
    except OSError as erreur:
        warnings.warn(f"Journal des coûts non écrit ({erreur}).")

    # À partir d'ici, l'appel est payé ET journalisé. Les erreurs qui suivent
    # portent la Reponse, pour que l'agent voie le coût et le texte brut.
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


# --- Test manuel (payant) ---------------------------------------------------

if __name__ == "__main__":
    # Test d'intégration contre la vraie API : python src\meddah\llm.py
    # Moins de 0,003 $ par lancement.

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

    # Test 3 : un appel normal avec schéma.
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