# Série Enzo — Épisode 1 « 37 euros »

Durée : environ 45 secondes visées, 48,89 s une fois calé sur les voix. Compteur de départ : 37 €. Objectif : 3 400 €.

## Script

| Plan | Temps | Image | Voix off | Texte en surimpression / compteur |
|---|---|---|---|---|
| 1 | 0–3 s | Gros plan sur Enzo, visage éclairé par une bougie sur un petit gâteau de supermarché, cuisine HLM | Le jour de mes 18 ans, j'avais 37 euros en poche. | Compteur 37 € apparaît |
| 2 | 3–8 s | La famille autour de la table : père avec béquille, mère en tenue d'aide-soignante prête à partir | Mon père ne peut plus bosser depuis son accident. Ma mère enchaîne les nuits à l'hôpital. | 37 € |
| 3 | 8–12 s | Jade tend à Enzo une carte dessinée à la main | Et Jade, ma petite sœur, est persuadée que je vais devenir millionnaire. | 37 € |
| 4 | 12–17 s | Cuisine dans le noir, Enzo fouille un tiroir à la lumière de son téléphone | Cette nuit-là, je cherchais juste un chargeur. | 37 € |
| 5 | 17–21 s | Gros plan sur une enveloppe cachée sous des papiers | Je suis tombé sur ça. | 37 € |
| 6 | 21–27 s | Gros plan sur les mains d'Enzo tenant la lettre | Trois mille quatre cents euros de loyers en retard. Ma mère le cachait depuis des mois. | Texte de la lettre : « Retard de loyer : 3 400 € » |
| 7 | 27–33 s | Enzo assis par terre, lettre à la main, lumières de la cité derrière la fenêtre | Le bailleur nous laisse trois mois. Après, c'est la procédure. | 37 € |
| 8 | 33–38 s | Enzo fixe la lettre, espace vide en haut de l'image | Trente-sept euros. Il m'en manque trois mille trois cent soixante-trois. | Grand compteur : 37 € / 3 400 € |
| 9 | 38–42 s | Téléphone qui vibre sur la table | Et là, mon téléphone a vibré. | Message de Jordan : « Joyeux anniv frère. Passe me voir, j'ai un plan pour toi. » |
| 10 | 42–45 s | Visage d'Enzo éclairé par l'écran du téléphone, hésitant | (silence) | « À suivre » |

Les temps du tableau sont les temps théoriques d'origine. Les durées réelles sont calculées par le monteur à partir des voix (voir episode.json et meddah_projet.md).

Les textes (lettre, carte, message) ne sont jamais générés dans les images : ils sont ajoutés au montage.

## Fichiers de production
- Références : enzo_reference.png, famille_reference.png, plan02.jpg (référence du décor, soir), plan04 puis plan07 (références du décor, nuit)
- Images : plan01.jpg à plan10.jpg (format 9:16, pleine taille 1438×2576)
- Voix : voix01.mp3 à voix09.mp3 (un fichier par plan, le plan 10 est silencieux)
- Description de l'épisode : episode.json (images, voix, caméra, surimpressions)

## Statut des plans

| Plan | Statut | Remarque |
|---|---|---|
| 1 | Validé | Plan poitrine plutôt que gros plan : lent zoom avant au montage |
| 2 | Validé | Référence du décor (soir). Prompt d'origine non conservé |
| 3 | Validé | Enzo bouche ouverte, sweat un peu clair. Régénération optionnelle (« mouth closed, soft touched smile ») |
| 4 | Validé | Possible évier en double (« next to the sink » à retirer du prompt) |
| 5 | Validé avec réserve | Main trop pâle. Régénération optionnelle |
| 6 | Validé | Dominante bleue trop forte (B/R 1,23) : étalonnage au montage |
| 7 | Validé | Meilleure référence de nuit |
| 8 | Validé | |
| 9 | Validé | Téléphone avec encoche, proche d'un iPhone |
| 10 | Validé (2e essai) | B/R 1,40, téléphone visible en bas du cadre |

## Règles apprises pour les prompts d'images
- Lumière : toujours préciser SOIR ou NUIT. Éviter « at night » seul (ambigu). Ajouter « natural dark grey-blue tones, not saturated navy blue » pour la nuit.
- Teint : « warm medium-brown skin tone » et, sous lumière froide, « keep this skin tone even under the cold light ». Les gros plans de mains dérivent vers une peau pâle.
- Netteté : écrire « sharp focus on the face, only the background softly blurred » plutôt que « shallow depth of field », qui floute tout le cadre.
- Textes : feuilles, cartes et écrans toujours demandés vierges. Rien d'écrit dans l'image.
- Téléphones : « rounded-rectangle phone with a tiny punch-hole camera, no notch », sans logo.
- Zones vides : prévoir dans chaque prompt l'espace réservé aux surimpressions (voir tableau ci-dessous).
- Références : joindre une référence par condition d'éclairage (plan02 pour le soir, plan07 pour la nuit) et la fiche d'Enzo.
- Toujours télécharger l'image en taille originale (1438×2576), jamais l'aperçu (572×1024).

## Zones réservées aux textes (coordonnées mesurées)

| Plan | Zone libre |
|---|---|
| 1 à 5, 7 | Haut de l'image (plafond sombre), compteur « 37 € » |
| 6 | Feuille : x 20–79 %, y 36–78 %. Pli à environ 56 % de la hauteur : placer le texte dans la moitié haute de la feuille |
| 8 | 40 % du haut |
| 9 | 20 % du haut |
| 10 | 33 % du haut |

## Prompts d'images (Gemini, format 9:16)

### Préfixe SOIR (plans 1 à 3)

```
Use the attached character sheet for Enzo and the attached family scene as exact references.
Enzo must be identical to the sheet: very short black hair with a sharp low fade, dark brown eyes, dark grey heather tech-fleece zip hoodie with a vertical zipped chest pocket, black crossbody bag strap. No beard, no hat, no logo.
Same kitchen as the family scene: small social-housing kitchen, beige walls, wooden wall cabinet, white fridge with magnets, window showing a dark blue dusk sky.
Same 3D animation style as the references. Vertical 9:16, cinematic lighting, no text, no logos, no writing anywhere.
```

### Plan 1 (références : enzo_reference.png + plan02.jpg)

Préfixe SOIR, puis :

```
Close-up of Enzo's face in the evening, lit only by a single candle on a small supermarket birthday cake in the foreground. The ceiling light is off. A faint blue dusk glow from the window and the blurred fridge and cabinets are visible behind him. Thoughtful, slightly sad half-smile. Leave some empty dark space in the top fifth of the frame.
```

### Plan 3 (références : enzo_reference.png + famille_reference.png + plan02.jpg)

Préfixe SOIR, puis :

```
Medium shot in the same kitchen, same wooden table. Jade (11 years old, black ponytail, colorful patterned hoodie, as in the family sheet) smiles proudly and hands Enzo a handmade birthday card across the table. The card is blank, with no writing or drawing. Enzo looks touched. The ceiling bulb is on, warm interior light, the window shows a dark blue dusk sky.
```

### Plan 4 (références : enzo_reference.png + plan02.jpg)

```
Use the attached character sheet for Enzo and the attached family scene as exact references.
Enzo must be identical to the sheet: very short black hair with a sharp low fade, dark brown eyes, dark grey heather tech-fleece zip hoodie with a vertical zipped chest pocket, black crossbody bag strap. No beard, no hat, no logo.
Same kitchen as the family scene: small social-housing kitchen, beige walls, wooden wall cabinet, white fridge with magnets, wooden drawer unit under the counter next to the sink. It is now the middle of the night: the ceiling light is off, the room is almost completely dark, and the window shows a black night sky with a few distant lights.
The only light sources are a narrow beam from Enzo's phone flashlight and a very faint cold blue glow from the window.
Same 3D animation style as the references. Vertical 9:16, cinematic lighting, no text, no logos, no writing anywhere.

Medium shot of Enzo alone in the dark kitchen, crouching in front of the open wooden drawer under the counter, searching inside it. He holds a generic smartphone with no logo in one hand, its flashlight beam pointing into the drawer. Focused, slightly tired expression, mouth closed. Leave some empty dark space in the top fifth of the frame.
```

### Plan 5 (référence : plan04)

```
Use the attached night scene as the exact reference for the wooden drawer, the kitchen and the lighting.
It is the middle of the night: the room is almost completely dark. The only light is a narrow cold-white beam from a phone flashlight, plus a very faint blue glow from the window.
Same 3D animation style as the reference. Vertical 9:16, cinematic lighting, shallow depth of field, no text, no logos, no writing anywhere.

Extreme close-up inside the open wooden kitchen drawer. A plain cream envelope is half hidden under a pile of papers and bills. Enzo's fingers (sleeve of a dark grey heather hoodie) lift the edge of the papers to reveal it. The envelope and all the papers are completely blank: no printed text, no address, no stamp, no logo. Tense, mysterious mood. Leave some empty dark space in the top fifth of the frame.
```

### Plan 6 (références : plan04 + enzo_reference.png)

```
Use the attached night scene as the exact reference for the kitchen, the lighting and the 3D animation style, and the attached character sheet for Enzo's skin tone and hoodie.
It is the middle of the night: the room is almost completely dark. The only light is a narrow cold-white beam from a phone flashlight, plus a very faint blue glow from the window.
Vertical 9:16, cinematic lighting, shallow depth of field, no text, no logos, no writing anywhere.

Close-up of Enzo's two hands holding up an open official letter, a single sheet of white paper facing the camera, filling the center of the frame. The sheet is completely blank: no printed text, no letterhead, no lines, no logo, no stamp. Both hands have the same warm medium-brown skin tone as Enzo's face on the character sheet, five fingers each, with the cuffs of a dark grey heather hoodie visible. His hands grip the page tensely. The background is dark and out of focus. Leave some empty dark space in the top fifth of the frame.
```

### Plan 7 (références : plan04 + enzo_reference.png)

```
Use the attached night scene as the exact reference for the kitchen layout, the lighting mood and the 3D animation style, and the attached character sheet for Enzo.
Enzo must be identical to the sheet: very short black hair with a sharp low fade, warm medium-brown skin, dark grey heather tech-fleece zip hoodie, black crossbody bag strap, white sneakers. No beard, no hat, no logo.
Same kitchen: small social-housing kitchen, beige walls, wooden base cabinets under the window, white fridge with magnets. It is the middle of the night and the ceiling light is off. Keep natural dark grey-blue tones as in the reference, not saturated navy blue.
The only light comes from a generic phone with no logo lying on the floor next to him with its flashlight on, casting a soft cold light on his face and the letter, plus a faint glow from the window.
Same 3D animation style as the reference. Vertical 9:16, cinematic lighting, no text, no logos, no writing anywhere.

Medium-wide shot, full body visible: Enzo sitting on the kitchen floor with his back against the wooden base cabinets, knees bent, head bowed, a blank sheet of white paper hanging loosely from one hand. His expression is crushed and exhausted, mouth closed. Behind and above him, the kitchen window shows the distant lights of tall social housing tower blocks at night: dark silhouettes with small warm lit windows. Leave some empty dark space in the top fifth of the frame.
```

### Plan 8 (références : plan07 + enzo_reference.png)

```
Use the attached night scene as the exact reference for the lighting mood, the colors and the 3D animation style, and the attached character sheet for Enzo.
Enzo must be identical to the sheet: very short black hair with a sharp low fade, warm medium-brown skin, dark grey heather tech-fleece zip hoodie. No beard, no hat, no logo.
It is the middle of the night in the same dark kitchen, the ceiling light is off. Keep natural dark grey-blue tones, not saturated navy blue. The only light is a soft cold light coming from below, faintly lighting his face and the letter.
Same 3D animation style as the reference. Vertical 9:16, cinematic lighting, shallow depth of field, no text, no logos, no writing anywhere.

Close-up of Enzo's face in the lower half of the frame, staring intensely at a blank sheet of white paper held in his hands at the very bottom of the frame. His eyes are fixed on the paper, his jaw is tense, a mix of shock and determination, mouth closed. The paper is completely blank, with no writing. The background is dark and out of focus. The upper half of the frame must be empty dark space (a dark blurred wall, nothing in it), reserved for large overlay numbers.
```

### Plan 9 (références : plan07 + plan03, ce dernier uniquement pour la table)

À ajouter lors d'une prochaine génération : « rounded-rectangle phone with a tiny punch-hole camera, no notch ».

```
Use the first attached image as the exact reference for the lighting mood, the colors and the 3D animation style. Use the second attached image only for the look of the wooden kitchen table (same warm medium-brown wood and grain).
It is the middle of the night in the same dark kitchen, the ceiling light is off. Keep natural dark grey-blue tones, not saturated navy blue. The main light comes from the glowing screen of the phone.
Same 3D animation style as the references. Vertical 9:16, cinematic lighting, shallow depth of field, no text, no logos, no writing anywhere.

Close-up, slightly high angle, of a generic smartphone with no logo lying face up on the wooden kitchen table at night. Its screen glows with a plain soft light and absolutely nothing is displayed on it: no icons, no text, no notification. A very slight motion blur on the phone's edges suggests it is buzzing. Next to the phone lies a blank white sheet of paper, partly folded. The background is a dark, out-of-focus kitchen with a window showing the night sky and a white fridge. Leave the top third of the frame as empty dark space.
```

### Plan 10 (références : plan08 + enzo_reference.png, version du 2e essai)

```
Use the first attached image as the exact reference for the lighting mood, the colors and the 3D animation style, and the second attached character sheet for Enzo.
Enzo must be identical to the sheet: very short black hair with a sharp low fade, dark brown eyes, warm medium-brown skin (keep this skin tone even under the cold light), dark grey heather tech-fleece zip hoodie with a black crossbody strap. No beard, no hat, no logo.
It is the middle of the night in the dark kitchen, the ceiling light is off. The only light is the cold blue-white glow of a phone screen held just below the frame, lighting his face from below. Natural dark grey-blue tones, not saturated navy blue.
Same 3D animation style as the references. Vertical 9:16, cinematic lighting, no text, no logos, no writing anywhere.

Close-up of Enzo's face, centered horizontally in the frame, head and both eyes fully visible, camera at eye level, facing the camera slightly turned. His face and eyes are in sharp focus; only the dark kitchen background is softly blurred. He looks down toward the glowing screen just out of frame, with a hesitant expression: eyebrows slightly raised and drawn together, lips pressed, a hint of doubt and temptation. The phone itself is not visible in the frame. Leave the top third of the frame as empty dark space.
```
