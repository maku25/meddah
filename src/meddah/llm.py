from google import genai

MODELE = "gemini-4-argon"
NIVEAUX_REFLEXIONS = {
    "low": genai.types.ThinkingLevel.LOW,
    "medium": genai.types.ThinkingLevel.MEDIUM,
    "high": genai.types.ThinkingLevel.HIGH,
}
NIVEAU_PAR_DEFAUT = "medium"
MAX_TOKENS_SORTIE = 16384


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

    return reponse.text


if __name__ == "__main__":
    print(appeler("en une phrase d'accroche, présente une série sur un jeune de 18 ans qui doit réunir 3 400 euros en trois mois"))

    print(appeler(
        "Écris en une phrase l'accroche de l'épisode 2.",
        system_prompt=(
            "Tu es le scénariste de la série Enzo, l'histoire d'un jeune de 18 ans "
            "qui doit réunir 3 400 euros en trois mois, uniquement par des moyens "
            "légaux. Ton réaliste, voix off à la première personne, jamais de "
            "discours « deviens riche vite »."
        ),
        niveau="low"
    ))

