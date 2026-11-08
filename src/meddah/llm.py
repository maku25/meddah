from datetime import date

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

    reponse = client.models.generate_content(
        model=MODELE,
        contents=prompt,
        config=config
    )

    usage = reponse.usage_metadata
    if usage is not None:
        tokens_entree = usage.prompt_token_count or 0
        tokens_sortie = usage.candidates_token_count or 0
        tokens_reflexion = usage.thoughts_token_count or 0
        cout = calculer_cout(tokens_entree, tokens_sortie, tokens_reflexion)
        print(
            f"[tokens] entree={tokens_entree} sortie={tokens_sortie} "
            f"reflexion={tokens_reflexion} total_api={usage.total_token_count} "
            f"| cout={cout:.5f} $ ({niveau})"
        )

    return reponse.text


if __name__ == "__main__":
    SYSTEM_PROMPT_TEST = (
        "Tu es le scénariste de la série Enzo, l'histoire d'un jeune de 18 ans "
        "qui doit réunir 3 400 euros en trois mois, uniquement par des moyens "
        "légaux. Ton réaliste, voix off à la première personne, jamais de "
        "discours « deviens riche vite »."
    )

    PROMPT_TEST = "Écris en une phrase l'accroche de l'épisode 2."

    for niveau in ("low", "medium", "high"):
        print(f"--- {niveau} ---")
        print(appeler(PROMPT_TEST, system_prompt=SYSTEM_PROMPT_TEST, niveau=niveau))
        print()


