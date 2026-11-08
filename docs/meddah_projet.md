# Meddah — Projet

## Vision
Meddah est un système multi-agents qui écrit, produit et publie automatiquement une histoire en série sur Instagram Reels (autres plateformes plus tard), à raison de 2 épisodes par jour.

Le nom vient du meddah, le conteur des cafés ottomans qui racontait seul des histoires en imitant la voix de tous les personnages (art inscrit au patrimoine immatériel de l'UNESCO).

Accroche : « Meddah — an autonomous multi-agent storyteller that publishes a serialized story, one episode at a time. »

## Objectifs
1. Formation : comprendre en profondeur les agents et les LLM.
2. Portfolio : projet phare d'un ingénieur IA junior.
3. Revenus : monétiser si l'audience suit.

## Principes et décisions
- Le moteur (Meddah) et le compte Instagram (nom de la série) sont distincts. Un même moteur pourra faire tourner plusieurs séries.
- Les premiers agents sont codés à la main avec des appels directs à l'API d'un LLM, avant d'adopter éventuellement un framework (LangGraph, etc.).
- Langage principal : Python.
- Repo GitHub : `meddah` (sans caractère spécial).
- Aucune vraie marque ni logo dans les images (risque juridique pour un compte monétisé, logos déformés par les générateurs).
- Ne pas publier avant d'avoir 3 à 5 épisodes prêts.
- Publication via l'API Instagram : nécessite un compte professionnel (Créateur ou Business).
- Coût par vidéo = critère clé (2 épisodes/jour ≈ 60 vidéos/mois).
- Le code du montage est écrit à la main, par petites étapes, avec les concepts expliqués (objectif formation) : pas de fichiers « tout prêts » pour les briques à comprendre.
- Structure du repo : series/<nom>/ pour les contenus (bible, episodes/epXX/ avec images/, audio/ et episode.json), src/meddah/ pour le moteur, assets/fonts/ et scripts/.
- `episode.json` est le contrat entre le scénariste et le monteur : pour chaque plan, l'image, la voix, le mouvement de caméra (zoom ≤ 1,3×, centre de départ et d'arrivée) et les surimpressions (texte, zone, moment d'apparition, style). Il ne contient aucune durée de plan avec voix : le monteur les calcule à partir des mp3.
- Règle de durée d'un plan avec voix : avance 0,10 s + voix + marge 0,25 s + pause éventuelle (plan 5 : +1,0 s ; plan 9 : +2,4 s pour lire le message). Coupes franches, les durées s'additionnent. Épisode 1 : 48,89 s (cible initiale : 45 s).
- Les textes (lettre, carte, message, compteur) ne sont jamais générés dans les images : ils sont ajoutés au montage. Les images sont générées avec des zones vides prévues pour eux.
- Images sources en pleine taille (1438×2576). Zoom maximal 1,3× pour une vidéo 1080×1920 (1438 / 1080 ≈ 1,33).
- Lumière : deux préfixes de prompt, SOIR (plans 1 à 3) et NUIT (plans 4 à 10), avec une référence d'éclairage par condition. Détails dans serie_enzo_ep01.md.

## Roadmap
1. Concept de la série et bible — FAIT
2. Production manuelle de l'épisode 1 (comprendre chaque brique) — FAIT
3. Montage automatique en Python (images + audios + script → vidéo finale : mouvements de caméra, sous-titres, compteur, textes en surimpression) — EN COURS
   - Fait : lecture de episode.json, vérification des fichiers, calcul des durées (module `src/meddah/episode.py`) — FAIT
   - Reste : ffmpeg, un plan = un clip avec zoom, surimpressions, assemblage de la piste audio, étalonnage de nuit, export 1080×1920 — FAIT
4. Animation : tests de modèles image-vers-vidéo sur quelques plans, mesure qualité/coût, choix entre tout animer ou seulement les moments forts
5. Agents : showrunner (planifie les arcs), scénariste (écrit l'épisode et produit episode.json), gardien de la continuité (vérifie la cohérence avec la bible et les références visuelles), génération images/voix, publication
6. Boucle de retour : statistiques Instagram réinjectées pour améliorer les épisodes

## Outils utilisés (prototype)
- Images : Gemini (Nano Banana), avec images de référence jointes à chaque génération
- Voix : ElevenLabs, modèle Eleven v4, langue français (vérifier la licence commerciale avant publication monétisée)
- Code : Python, environnement virtuel `.venv`, bibliothèque `mutagen` (durée des mp3). ffmpeg à installer pour la vidéo.
- Poste de travail : Windows, PowerShell, VS Code (extension Claude Code installée, non utilisée pour l'instant)
- Pillow
- ffmpeg 9.0.2
- la police Montserrat

## État d'avancement
(À mettre à jour à la fin de chaque session, puis ré-uploader ce fichier dans le projet.)

- [x] Nom du projet : Meddah
- [x] Bible de la série (voir serie_enzo_bible.md)
- [x] Script de l'épisode 1 (voir serie_enzo_ep01.md)
- [x] Fiches de référence : enzo_reference.png, famille_reference.png
- [x] Plans 1 à 10 générés et validés (plan01.jpg mesuré en 1536×2752 ; le code ne suppose aucune taille)
- [x] Voix off : 9 audios (voix01.mp3 à voix09.mp3) — nom de la voix ElevenLabs : À COMPLÉTER
- [x] episode.json de l'épisode 1 (caméra, surimpressions, libellés ARGENT / OBJECTIF)
- [x] ffmpeg 9.0.2 installé (winget Gyan.FFmpeg) et reconnu dans le PATH
- [x] src/meddah/episode.py : lecture du JSON, vérification des fichiers, durées
- [x] src/meddah/clip.py : un plan = un clip (zoom, panoramique, tremblement, surimpressions)
- [x] src/meddah/surimpression.py : textes dessinés avec Pillow (polices Montserrat dans assets/fonts/)
- [x] src/meddah/etalonnage.py : étalonnage automatique (dominante bleue, ombres)
- [x] src/meddah/assemble.py : assemblage, piste audio calée, volume normalisé à -14 LUFS
- [x] src/meddah/montage.py : épisode complet en une commande (48,90 s, 2 min 40 s de calcul)
- [x] Épisode 1 monté : output/enzo_ep01_brut.mp4 (1080×1920, 30 i/s)
- [ ] Vérifier le brut sur téléphone et en brouillon dans l'app Instagram (taille du libellé, teinte du papier au plan 6, zones masquées par l'interface)
- [ ] Vérifier que le fichier s'appelle bien .gitignore (il apparaissait sans point), puis commiter le montage
- [ ] Optionnel : regénérer le plan 5 (main trop pâle)
- [ ] Optionnel : sous-titres à partir de voice_text
- [ ] Étape 4 : tests d'animation image-vers-vidéo (modèles, qualité, coût par plan)
- [ ] Compléter : temps passé et coût de l'épisode 1, quota Gemini consommé

## Journal de bord
Noter pour chaque étape : temps passé, coût, outil, problèmes rencontrés et solutions. Temps passé et coût de l'épisode 1 : À COMPLÉTER.

- Problème : incohérence de la coiffure d'Enzo et de la cuisine entre les plans 1, 2 et 3. Solution : joindre systématiquement enzo_reference.png et plan02.jpg comme références. Idée pour plus tard : un agent de continuité qui compare chaque plan aux références avec un modèle de vision.
- Limite d'usage Gemini atteinte après 3 images au début : prévoir les quotas dans l'automatisation. Quota consommé pour les plans 1 à 10 : À COMPLÉTER.
- Plan 3 en plein jour : le mot « at night » du préfixe était ambigu. Solution : deux préfixes, SOIR (plafonnier allumé, ciel bleu crépuscule) et NUIT (plafonnier éteint, fenêtre noire). Une référence par condition : plan02 pour le soir, plan04 puis plan07 pour la nuit.
- Résolution : les exports par aperçu ou capture font 572×1024 ; il faut télécharger l'original (1438×2576).
- Teint : les gros plans de mains (plans 5 et 6) dérivent vers une peau trop claire. Solution : « same warm medium-brown skin tone as Enzo's face » et, en lumière froide, « keep this skin tone even under the cold light » (a fonctionné au plan 10).
- Flou : « shallow depth of field » a flouté tout le cadre au plan 10 (premier essai, fichier aussi dégradé : bas en aplat, 95 Ko). Solution : « sharp focus on the face, only the background softly blurred ».
- Étalonnage (rapport bleu/rouge mesuré) : soir 0,54–0,67 ; nuit 0,97–1,09 ; plan 6 = 1,23 ; plan 10 = 1,40. Les plans de nuit sont très sombres (luminance moyenne ≈ 40/255) : remonter les ombres au montage et tester sur téléphone.
- Décor : l'évier est sous la fenêtre aux plans 2 et 3, sur le comptoir de gauche aux plans 4 à 9. Idée : une fiche de décor (cuisine vide, versions soir et nuit) pour figer la géométrie.
- Le plan 9 montre un téléphone avec encoche (ressemble à un iPhone). Pour les prochains prompts : « rounded-rectangle phone with a tiny punch-hole camera, no notch ».
- Voix : durées mesurées, total 39,34 s (plan 3 : 5,56 s alors que le script en prévoyait 4). `mutagen` donne les mêmes durées que `ffprobe`. Pauses ajoutées : plan 5 (+1,0 s) et plan 9 (+2,4 s).
- Windows : si l'activation du `.venv` est bloquée par PowerShell, lancer `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. Ajouter `.venv/` et `output/` au `.gitignore`.
- Code : `episode.py` construit étape par étape (lecture JSON, vérification des fichiers, durées, fonctions, `main()`). Résultat de référence : 10 plans, 48,89 s.
- Claude Code : documentation consultée (installation Windows, style Learning, mode Manual, CLAUDE.md, extension VS Code). Décision : reporté à plus tard.
- Idée agent de continuité : premières métriques mesurables sur les images (résolution et ratio, bandes plates claires, dominante bleue, netteté par variance du laplacien, zone libre pour le texte). Attention aux faux positifs : un plafond sombre et flou est uniforme sans être corrompu.
- Chemin réel des épisodes : series/<nom>/episodes/epXX/ (et non series/<nom>/epXX/). Les images mesurent 1536×2752, pas 1438×2576.
- ffmpeg : winget l'installe mais le terminal ne le reconnaît pas tant que le PATH n'est pas rechargé (fermer VS Code complètement). Les accents cassés (Ã©) dans le terminal viennent de Get-Content (lecture en ANSI) : les fichiers sont bien en UTF-8, à vérifier dans VS Code.
- Zoom : zoompan arrondit la fenêtre au pixel entier, donc l'image est agrandie 4× avant le zoom pour qu'il ne saccade pas. Le centre demandé est borné pour que la fenêtre ne sorte jamais de l'image. Recadrage 9:16 générique (scale increase + crop), sans dépendre de la taille de l'image.
- Couleurs : les JPEG sont en plage complète BT.601 ; la vidéo est en plage limitée BT.709. Conversion avec zscale (le filtre scale ne change pas vraiment la matrice : écart moyen 2,3 contre 1,1 niveaux).
- Surimpressions : les textes « screen » sont superposés à l'écran, les textes « image » (la lettre) passent dans la même chaîne de caméra que l'image pour rester collés au papier. Fondu sur la transparence, apparition avec enable, glissement de la carte (formule en (1-p)²), tremblement du plan 9 (11 et 13 Hz, sous la moitié du taux d'images).
- Polices : Montserrat (licence OFL, usage commercial permis). Les fichiers statiques sont dans le dépôt officiel JulietaUla/Montserrat (le dossier static de google/fonts n'existe pas). Garder OFL.txt dans assets/fonts/.
- Libellés du compteur : ARGENT (compteur) et OBJECTIF (but). Champ "label" dans episode.json, à reprendre à l'identique dans la bible pour que l'agent scénariste ne les change pas d'un épisode à l'autre.
- Étalonnage automatique mesuré sur l'image source : rapport bleu/rouge plafonné à 1,08, ombres remontées vers une luminance de 52 (gamma 0,80 minimum). Résultat sur l'épisode 1 : plan 6 de 1,20 à 1,06, plan 10 de 1,34 à 1,05. Correction manuelle possible par plan ("grade": false ou {"blue", "gamma"}).
- Volume : -21,1 LUFS avant, -14,4 LUFS après (cible -14), écart de volume de 9,6 à 4,9 LU, crête -1,4 dBFS. Normalisation en deux passes (loudnorm) ; la cible de -14 LUFS est à confirmer pour Instagram.
- voix03.mp3 : aucune coupure à faire. Environ 5,3 s de parole et une pause d'environ 0,55 s au milieu de la phrase.
- Pièges rencontrés : vidéo sans aucun texte (cause probable : ancien clip.py encore en place, ou fichier non sauvegardé) ; ModuleNotFoundError sur « episode » (episode.py absent de src/meddah, à remettre en place). Toujours sauvegarder dans VS Code puis relancer montage.py.
- Coût du montage : 0 € (calcul local, 2 min 40 s pour 48,90 s de vidéo). Seuls Gemini et ElevenLabs pèsent sur le coût par vidéo.
