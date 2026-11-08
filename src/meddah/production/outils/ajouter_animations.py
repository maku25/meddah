"""Outil : ajoute une clé "animation" à tous les plans animables d'episode.json.

    python scripts/ajouter_animations.py

Tous les plans sauf le 6 : la lettre du plan 6 est collée à l'image au montage et ne pourrait pas
suivre le papier dans une vidéo générée (si on l'animait, il faudrait la passer en texte d'écran
fixe, qui dériverait hors du papier). Les plans qui ont déjà une clé "animation" (1, 4, 10 chez toi)
ne sont pas modifiés.

Les prompts décrivent UNIQUEMENT le mouvement. Les consignes communes (plan unique, pas de dialogue,
même style, visages inchangés) sont ajoutées par animation.py. Leçon du plan 10 : le modèle a poussé
la caméra de 1,5x et le texte du haut a fini sur les cheveux. D'où, ici, la consigne « caméra
quasi fixe » et « le haut de l'image reste vide » : chaque plan a un texte ou un compteur en haut.
Une copie de sauvegarde est faite dans episode.json.bak (une seule fois).
"""
import json
import shutil
from pathlib import Path

# Consigne ajoutée aux plans dont le haut de l'image reçoit un texte au montage.
CAMERA = ("The camera stays almost locked off, with at most a very slight drift: no zoom and no "
          "push-in. The empty dark space at the top of the frame stays empty and unchanged.")

PROMPTS = {
    1: ("Slow, subtle push-in on Enzo's face, lit only by the flickering flame of the small candle in "
        "the foreground. He blinks slowly, his half-smile fades into a thoughtful look, and he exhales "
        "softly so the candle flame flickers."),
    2: ("Nobody speaks. The father, seated, rests his hand on the table and exhales tiredly. The mother, "
        "standing near the fridge in her scrubs, shifts the strap of her bag on her shoulder and glances "
        "toward the door, ready to leave for her night shift. Enzo slowly uncrosses his arms and looks "
        "down at the table. Jade swings her feet under her chair. " + CAMERA),
    3: ("Jade, smiling proudly, slides a blank handmade birthday card across the table toward Enzo. "
        "Enzo takes it with both hands, looks at it, then looks up at her and breaks into a soft, "
        "touched smile with his mouth closed. The card stays completely blank: no text and no drawing "
        "appear on it. " + CAMERA),
    4: ("Enzo, crouched in front of the open drawer in the dark kitchen, rummages through it with his "
        "free hand while the narrow beam of his phone flashlight sweeps across the contents. He glances "
        "once over his shoulder toward the doorway, then turns back to the drawer. Very gentle "
        "handheld camera movement."),
    5: ("Extreme close-up inside the open drawer. Enzo's fingers slowly lift the edge of the pile of "
        "papers, revealing the cream envelope hidden underneath, while the cold beam of the phone "
        "flashlight shifts slightly across the papers. All the papers and the envelope stay completely "
        "blank: no printed text. " + CAMERA),
    7: ("Enzo sits on the kitchen floor against the wooden cabinets, crushed and exhausted. His shoulders "
        "rise and fall with heavy breathing; he lowers his head a little further and lets the hand "
        "holding the blank sheet of paper sink down to his knee. The lights of the tower blocks in the "
        "window flicker faintly. The phone lying on the floor keeps casting a steady cold light. "
        + CAMERA),
    8: ("Close-up of Enzo in the lower half of the frame, staring at the blank sheet of paper at the "
        "very bottom of the frame. His jaw tightens, his eyes narrow with determination, and he takes "
        "one slow deep breath. His head stays in the lower half of the frame; the upper half remains an "
        "empty dark blurred wall. " + CAMERA),
    9: ("[0-1.8s] The smartphone lies still on the wooden kitchen table at night, its blank screen "
        "glowing softly, a folded blank sheet of paper next to it. [1.8-2.8s] The phone starts to "
        "buzz: it vibrates and shifts a few millimetres across the wood, its glow pulsing, and the "
        "sheet of paper trembles slightly. [2.8s-end] The vibration stops and the phone settles. The "
        "screen stays blank: no text, no icons, no notification. " + CAMERA),
}


def main():
    fichier = Path("series/enzo/episodes/ep01/episode.json")
    episode = json.loads(fichier.read_text(encoding="utf-8"))

    ajoutes = []
    for plan in episode["shots"]:
        if plan["id"] in PROMPTS and "animation" not in plan:
            plan["animation"] = {"prompt": PROMPTS[plan["id"]], "resolution": "720p"}
            ajoutes.append(plan["id"])

    if not ajoutes:
        print("Rien à modifier : tous les plans animables sont déjà déclarés.")
        return
    sauvegarde = fichier.with_suffix(".json.bak")
    if not sauvegarde.exists():
        shutil.copy(fichier, sauvegarde)
    fichier.write_text(json.dumps(episode, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Plans déclarés pour l'animation : " + ", ".join(f"{i:02d}" for i in ajoutes))
    print("Le plan 06 reste fixe (la lettre doit suivre le papier).")


if __name__ == "__main__":
    main()
