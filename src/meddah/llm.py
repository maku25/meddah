from google import genai

MODELE = "gemini-4-argon"


def appeler(prompt: str):

    client = genai.Client()

    reponse = client.models.generate_content(
        model=MODELE,
        contents=prompt
    )

    return reponse.text


if __name__ == "__main__":
    print(appeler("en une phrase d'accroche, présente une série sur un jeune de 18 ans qui doit réunir 3 400 euros en trois mois"))

