# Meddah — Production vidéo (référence)

Statut : terminé. Cette partie est un outil au service des agents : ne la retravailler que sur demande. Ce fichier sert de mémoire technique (commandes, réglages, pièges rencontrés).

## Ce que ça fait
À partir d'un `episode.json`, d'images et de voix, une seule commande produit la vidéo finale :

```
python src\meddah\production\montage.py
```

Résultat : `output/<serie>_ep<NN>_brut.mp4`. Épisode 1 : 1080×1920, 30 i/s, 48,90 s, -14,4 LUFS, crête -1,4 dBTP, environ 2 min de calcul, 0 $ pour le montage lui-même.

Prérequis : Python et `.venv` activé, `pip install -r requirements.txt` (mutagen, pillow, google-genai), ffmpeg 9.0.2 (`winget install Gyan.FFmpeg`, PATH rechargé), polices dans `assets/fonts/`.

## Le contrat : `episode.json`
Dossier d'un épisode : `series/<nom>/episodes/epXX/`, avec `episode.json`, `images/planXX.jpg`, `audio/voixXX.mp3` et `animations/planXX.mp4` (facultatif, hors git).

Champs d'un plan (`shots`) :
- `id`, `image`, `voice`, `voice_text` ; `extra_hold` (pause en secondes après la voix) ; `duration` (plan sans voix).
- `camera` : `zoom` [début, fin] (limite 1,3×) et `center` [[x, y] de départ, [x, y] d'arrivée], en fractions de l'image.
- `overlays` : liste de textes. Champs : `style` (`counter_small`, `counter_big`, `goal_big`, `letter`, `message_card`, `to_be_continued`), `text`, `label` (libellé du compteur : ARGENT, OBJECTIF), `sender` (carte de message), `space` (`screen` fixe à l'écran, `image` collé à l'image), `box` [x0, y0, x1, y1] en fractions, `start` et `fade_in` en secondes depuis le début du plan, `animation` (`slide_down`).
- `shake` : `start`, `duration` (tremblement de caméra d'un plan fixe).
- `animation` : `prompt` (le mouvement seulement), `resolution`.
- `grade` : `false` (aucune correction) ou `{"blue": 0.85, "gamma": 0.9}` (valeurs imposées).

Règles :
- Durée d'un plan avec voix = 0,10 s d'avance + voix + 0,25 s de marge + `extra_hold`. Aucune durée n'est écrite dans le JSON : le monteur les calcule à partir des mp3 (`mutagen`).
- Coupes franches, durées additionnées, arrondies à l'image près (30 i/s). `assemble.py` lit la durée réelle de chaque clip.
- Les textes ne sont jamais générés dans les images. Les images sont générées avec des zones vides pour eux.
- Un plan animé ne peut pas porter un texte `space: image` (il ne pourrait pas suivre la caméra) : le code refuse.

## Les modules (`src/meddah/production/`)
| Module | Rôle |
|---|---|
| `episode.py` | Lit `episode.json`, vérifie les fichiers, calcule les durées |
| `clip.py` | Un plan = un clip : zoom, panoramique, tremblement, surimpressions, ou source animée |
| `surimpression.py` | Dessine les textes avec Pillow, produit des aperçus fixes |
| `etalonnage.py` | Étalonnage automatique de l'image source (dominante bleue, ombres) |
| `animation.py` | Anime un plan fixe (image vers vidéo), estime le coût, garde un cache et un journal (`output/couts.csv`) |
| `assemble.py` | Colle les clips, construit la piste audio calée, normalise le volume, fusionne |
| `montage.py` | Enchaîne tout |
| `outils/ajouter_libelles.py`, `outils/ajouter_animations.py` | Outils à usage unique qui modifient `episode.json` (sauvegarde `.bak`) |

Les imports entre modules sont des imports « frères » : on lance chaque fichier directement, depuis la racine du dépôt.

## Commandes (depuis la racine du dépôt)
| Pour | Commande |
|---|---|
| Monter l'épisode complet | `python src\meddah\production\montage.py` |
| Régénérer un ou plusieurs clips | `python src\meddah\production\clip.py 1 3 4` |
| Aperçus fixes des textes | `python src\meddah\production\surimpression.py [plans]` (résultat dans `output\apercus\`) |
| Mesures et comparaisons d'étalonnage | `python src\meddah\production\etalonnage.py` (résultat dans `output\etalonnage\`) |
| Estimer le coût d'animation, sans dépenser | `python src\meddah\production\animation.py --estimer` |
| Générer des animations | `python src\meddah\production\animation.py 1 4 10` (demande confirmation ; `--forcer` regénère et repaie ; `--oui` supprime la confirmation) |
| Assembler seulement | `python src\meddah\production\assemble.py` |

## Réglages (constantes en tête de fichier)
- `clip.py` : `SURECHANTILLONNAGE` (4), `TREMBLEMENT_AMPLITUDE` (0,006 ; 0,004), `TREMBLEMENT_FREQUENCES` (11 et 13 Hz, à garder sous 15), `GLISSEMENT_PAR_DEFAUT` (0,3 s).
- `surimpression.py` : `STYLES` (police, couleur, taille maximale, ombre, pastille), `ETIQUETTE_RATIO` (0,50 en ligne, 0,34 au-dessus).
- `etalonnage.py` : `BLEU_SUR_ROUGE_MAX` (1,08), `LUMINANCE_CIBLE` (52), `GAMMA_MIN` (0,80).
- `assemble.py` : `CIBLE_LUFS` (-14), `CIBLE_CRETE` (-1,5 dBTP), `CIBLE_LRA` (11).
- `animation.py` : `MODELE`, `PARAMETRES_MODELES` (durée maximale, résolutions, prix).

## Chaîne technique
1. Étalonnage : Pillow mesure l'image source ; si elle est trop bleue ou trop sombre, une copie corrigée est enregistrée dans `output/tmp/` (l'originale n'est jamais modifiée).
2. Plan fixe : recadrage « cover » 9:16, agrandissement ×4, `zoompan` (le centre demandé est borné pour ne jamais sortir de l'image), conversion des couleurs (JPEG plein BT.601 vers vidéo limité BT.709 avec `zscale`).
3. Plan animé : la vidéo source est recadrée, passée de 24 à 30 i/s, et sa dernière image est figée si elle est plus courte que le plan.
4. Surimpressions : chaque texte est dessiné en PNG par Pillow, avec un fondu sur la transparence. Un texte `screen` est superposé tel quel, un texte `image` traverse la même chaîne de caméra que l'image.
5. Assemblage : concaténation des clips sans ré-encodage, piste audio construite par segments de la durée exacte de chaque clip, normalisation du volume en deux passes (`loudnorm`), fusion avec `faststart`.

## Animation : état, coûts, risques
- Modèle accessible avec ce compte : `gemini-omni-flash-preview` (720p uniquement, 10 s maximum). Les noms de la documentation (`gemini-omni-1.2-flash`, `gemini-omni-1.1-flash`) ont répondu 404. Les requêtes en 404 ne sont pas facturées.
- Requête : `response_format` avec `type: video`, `aspect_ratio: 9:16`, `resolution` et `duration` sous forme de chaîne (`"4s"`, pas un entier). Le prompt commence par `<FIRST_FRAME>` pour partir de l'image du plan. L'image envoyée est l'image étalonnée.
- Plans animés de l'épisode 1 : 1, 2, 3, 4, 5, 7, 8, 9, 10. Le plan 6 reste fixe, car la lettre doit suivre le papier. Les plans 2 et 3, avec un personnage de 11 ans, ont été acceptés depuis la France.
- Coût : 10 générations notées (plan 3 deux fois), 53 s au total, estimées à 5,30 $ avec un tarif supposé de 0,10 $/s. Le solde du compte (5,00 € rechargés, 3,59 € restants) suggère une consommation réelle nettement plus basse, à confirmer. Un épisode complet animé (47 s) : environ 1,40 $ si le coût réel est de 0,03 $/s, environ 4,70 $ au tarif supposé.
- Risque : un guide de migration (source secondaire) annonçait le retrait de ce modèle préliminaire au 30 septembre 2026. Il répond toujours. Les animations sont sauvegardées hors du dépôt.
- Les prompts doivent demander une caméra quasi fixe : sinon le modèle zoome de 1,5× et le texte du haut finit sur la tête. Le hook (plan 1) et le cliffhanger (plan 10) animés rendent bien.

## Pièges rencontrés
- Problème : le chemin réel est `series/<nom>/episodes/epXX/` et les images mesurent 1536×2752, pas 1438×2576. Solution : le code ne suppose aucune taille.
- Problème : ffmpeg est installé par winget mais le terminal ne le reconnaît pas. Solution : recharger le PATH, en fermant VS Code complètement.
- Problème : accents cassés (`Ã©`) dans le terminal. Cause : `Get-Content` lit en ANSI. Les fichiers sont bien en UTF-8, à vérifier dans VS Code.
- Problème : le filtre `scale` ne change pas la matrice de couleur d'un YUV vers un autre. Solution : `zscale` (écart moyen mesuré : 1,1 contre 2,3 niveaux).
- Problème : vidéo sans aucun texte. Cause probable : ancien `clip.py` encore en place, ou fichier non sauvegardé. Solution : sauvegarder dans VS Code, puis relancer `montage.py`.
- Problème : `ModuleNotFoundError` sur `episode`. Cause : `episode.py` absent du dossier du script. Solution : le remettre à côté des autres modules.
- Problème : le dossier `static` de google/fonts n'existe pas pour Montserrat. Solution : prendre les fichiers statiques du dépôt officiel JulietaUla/Montserrat (licence OFL, usage commercial permis) et garder `OFL.txt`.
- Problème : les gros plans de mains dérivent vers une peau pâle. Solution : règles dans les prompts d'images (voir `series/enzo/episodes/ep01/serie_enzo_ep01.md`).
- Problème : un `duration` entier donne une erreur 400 côté API vidéo. Solution : une chaîne, `"4s"`. Des noms de modèles de la documentation peuvent aussi être indisponibles pour un compte : vérifier avec `client.models.list()`.

## Résultats de l'épisode 1 (référence)
- 10 plans, 48,90 s ; coupes à 3,83 / 9,43 / 15,33 / 19,67 / 22,83 / 29,23 / 35,30 / 40,47 / 45,90 s.
- Étalonnage : plan 6 de B/R 1,20 à 1,06, plan 10 de 1,34 à 1,05 ; plans de nuit de luminance 37-50 à 50-58.
- Volume : -21,1 LUFS avant, -14,4 LUFS après ; écart de volume de 9,6 à 4,9 LU ; crête -1,4 dBTP.
- `voix03.mp3` : environ 5,3 s de parole et une pause d'environ 0,55 s ; aucune coupe à faire.

## Idées non réalisées
- Sous-titres à partir de `voice_text`.
- Nappe musicale ou bruit d'ambiance pour donner de la vie aux plans fixes.
- Régénérer le plan 5 (main trop pâle).
- Fiche de décor (cuisine vide, versions soir et nuit) pour figer la géométrie.
