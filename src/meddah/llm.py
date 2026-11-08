from datetime import date
from dataclasses import dataclass
import time

from google import genai

MODELE = "gemini-4-argon"
NIVEAUX_REFLEXIONS = {
    "low": genai.types.ThinkingLevel.LOW,
    "medium": genai.types.ThinkingLevel.MEDIUM,
    "high": genai.types.ThinkingLevel.HIGH,
}
NIVEAU_PAR_DEFAUT = "medium"
MAX_TOKENS_SORTIE = 16384

PRIX = {
    "gemini-4-argon": [
        (date(2026, 11, 30), 2.00, 10.00),
        (date.max, 4.00, 20.00),
    ],
}

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

def appeler(prompt: str, system_prompt: str | None = None, niveau: str = NIVEAU_PAR_DEFAUT):


    if niveau not in NIVEAUX_REFLEXIONS:
        raise ValueError(
            f"niveau doit être l'un de {sorted(NIVEAUX_REFLEXIONS)}, reçu {niveau!r}"
        )

    client = genai.Client()

    config = genai.types.GenerateContentConfig(
        system_instruction=system_prompt,
        max_output_tokens=MAX_TOKENS_SORTIE,
        thinking_config=genai.types.ThinkingConfig(thinking_level=NIVEAUX_REFLEXIONS[niveau])
    )

    debut = time.perf_counter()
    reponse = client.models.generate_content(
        model=MODELE,
        contents=prompt,
        config=config
    )
    duree = time.perf_counter() - debut

    usage = reponse.usage_metadata
    usage = reponse.usage_metadata
    tokens_entree = (usage.prompt_token_count or 0) if usage else 0
    tokens_sortie = (usage.candidates_token_count or 0) if usage else 0
    tokens_reflexion = (usage.thoughts_token_count or 0) if usage else 0

    return Reponse(
        texte=reponse.text,
        modele=MODELE,
        niveau=niveau,
        tokens_entree=tokens_entree,
        tokens_sortie=tokens_sortie,
        tokens_reflexion=tokens_reflexion,
        cout=calculer_cout(tokens_entree, tokens_sortie, tokens_reflexion),
        duree_s=duree,
    )


if __name__ == "__main__":
    SYSTEM_PROMPT_TEST = (
        "Tu es le scénariste de la série Enzo, l'histoire d'un jeune de 18 ans "
        "qui doit réunir 3 400 euros en trois mois, uniquement par des moyens "
        "légaux. Ton réaliste, voix off à la première personne, jamais de "
        "discours « deviens riche vite »."
    )

    PROMPT_TEST = "Écris en une phrase l'accroche de l'épisode 2."

    r = appeler(PROMPT_TEST, niveau="low")
    print(r.texte)
    print(r.resume())
    print()

    r = appeler(PROMPT_TEST, system_prompt=SYSTEM_PROMPT_TEST, niveau="low")
    print(r.texte)
    print(r.resume())

