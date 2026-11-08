# Meddah — Projet

## Vision
Meddah est un système multi-agents qui écrit, produit et publie automatiquement une histoire en série sur Instagram Reels (autres plateformes plus tard), à raison de 2 épisodes par jour.

Le nom vient du meddah, le conteur des cafés ottomans qui racontait seul des histoires en imitant la voix de tous les personnages (art inscrit au patrimoine immatériel de l'UNESCO).

Accroche : « Meddah — an autonomous multi-agent storyteller that publishes a serialized story, one episode at a time. »

La production vidéo (montage, animation) est terminée et sert d'outil : à partir d'un `episode.json`, d'images et de voix, une commande produit la vidéo finale. Elle est décrite dans `meddah_production.md`. Le travail en cours porte sur les agents.

## Agents
Un agent est une fonction Python qui prépare une consigne, appelle un modèle de langage, vérifie le résultat avec du code, renvoie l'erreur au modèle pour qu'il corrige (nombre d'essais limité), puis écrit son résultat dans un fichier du dossier de l'épisode. Les agents se passent le relais par ces fichiers. Le contrat central est `episode.json`, que le monteur lit tel quel.

- Scénariste : écrit l'épisode suivant, son `episode.json` et les prompts des images. Lit la bible, l'épisode précédent et un brief. Vérifie le JSON (schéma, 8 à 10 plans, 90 à 110 mots de voix off, règles de la bible).
- Voix : transforme chaque `voice_text` en mp3 avec ElevenLabs. Vérifie les durées et l'absence de fichier vide.
- Gardien de continuité : contrôle chaque image (visage, décor, couleurs, zone libre pour les textes) par des mesures en code et par un modèle de vision, et demande une régénération si besoin.
- Images : génère les plans avec les fiches de référence, sous le contrôle du gardien.
- Showrunner : planifie les arcs et écrit le brief de chaque épisode.
- Publication : publie la vidéo finale sur Instagram.
- Chef d'orchestre : enchaîne les agents, tient le budget et demande une validation avant publication.

La boucle de retour (statistiques Instagram réinjectées dans les épisodes suivants) viendra ensuite.

Ordre de construction : `llm.py`, puis scénariste, voix, gardien de continuité, images, showrunner, publication, chef d'orchestre. Le scénariste passe en premier parce que son `episode.json` est déjà le contrat avec le monteur : on peut vérifier sa sortie par code sans dépenser en images ni en voix. Le gardien vient avant l'agent images, car la boucle générer, vérifier, régénérer demande que la vérification existe.

Les épisodes 2 à 5 servent à construire et tester les agents. L'épisode 1 est le seul réalisé entièrement à la main. Au début, chaque publication passe par une validation humaine.

## Principes et décisions

### Agents
- Agents codés à la main avec des appels directs à l'API d'un LLM, avant d'envisager un framework (LangGraph, etc.).
- On avance par petites étapes, avec un test après chacune.
- Tous les agents appellent le modèle par une seule fonction, `appeler()` dans `src/meddah/llm.py` : modèle en constante, mesure des jetons et du coût, sortie JSON forcée par un schéma, gestion des erreurs, journal des coûts dans `output/couts_llm.csv`. La clé reste dans une variable d'environnement.
- Modèle de texte : `gemini-4-argon` jusqu'au 30 novembre 2026 (prix d'introduction), puis comparaison avant de choisir.
- Toute sortie d'agent est vérifiée par du code avant d'être acceptée.
- Chaque appel est mesuré : le coût par vidéo est un critère clé.
- Le moteur (Meddah) et le compte Instagram (nom de la série) sont distincts. Un même moteur pourra faire tourner plusieurs séries.

### Règles de la série (détail dans `serie_enzo_bible.md`)
- Uniquement des moyens légaux pour le héros, pas de clichés ni de caricatures.
- Aucune vraie marque ni logo dans les images (risque juridique pour un compte monétisé, logos déformés par les générateurs).
- Les textes (lettre, carte, message, compteur) ne sont jamais générés dans les images : ils sont ajoutés au montage.
- Libellés du compteur : ARGENT (le compteur) et OBJECTIF (le but), identiques d'un épisode à l'autre.
- Pas de conseil financier présenté comme tel (loi influenceurs de 2023 en France).

### Publication
- Ne pas publier avant d'avoir 3 à 5 épisodes prêts.
- Publication via l'API Instagram : il faut un compte professionnel (Créateur ou Business). Une validation de l'application par Meta est probablement nécessaire, délai inconnu.
- Vérifier les règles d'Instagram sur les contenus générés par IA avant la première publication.
- Voix : ElevenLabs, modèle Eleven v4, français. Vérifier la licence commerciale avant de monétiser.

### Budget
Objectif d'environ 60 vidéos par mois (2 épisodes par jour).
- Texte : de 0,02 à 0,12 $ par appel selon le modèle et la réflexion (estimation, à mesurer).
- Images : générées pour l'instant dans l'appli Gemini. Via l'API, environ 0,07 à 0,10 $ par image d'après une page de tarifs de juin (à vérifier).
- Voix : À COMPLÉTER.
- Animation : de 1,40 à 4,70 $ par épisode selon le nombre de plans animés (estimations, voir `meddah_production.md`).
- Montage : 0 $, tout se calcule en local.

## Roadmap
1. Concept de la série et bible : FAIT
2. Production manuelle de l'épisode 1 : FAIT
3. Montage automatique en Python : FAIT (voir `meddah_production.md`)
4. Animation image-vers-vidéo : FAIT (9 plans sur 10 animés, modèle préliminaire)
5. Agents : EN COURS
   - `llm.py` en huit étapes : appel minimal, rôle et réglages, jetons et coût, objet de réponse, journal des coûts, sortie JSON avec schéma, gestion des erreurs, tests avec un faux client
   - scénariste
   - voix
   - gardien de continuité
   - images
   - showrunner
   - publication
   - chef d'orchestre
6. Boucle de retour : statistiques Instagram

## Outils utilisés
- Texte (agents) : Gemini 4 Argon via `google-genai` (3.x), clé dans `GEMINI_API_KEY`. Compte Google en pré-paiement.
- Images : Gemini (Nano Banana), avec images de référence jointes à chaque génération.
- Voix : ElevenLabs, Eleven v4, français.
- Animation : `gemini-omni-flash-preview`.
- Code : Python, `.venv`, VS Code (extension Claude Code installée, non utilisée), Windows PowerShell, git et GitHub (dépôt privé `meddah`).
- Production : ffmpeg 9.0.2, Pillow, mutagen, police Montserrat (licence OFL).

## Structure du dépôt
```
meddah/
├── README.md                  (à écrire)
├── requirements.txt
├── docs/
│   ├── meddah_projet.md
│   └── meddah_production.md
├── series/enzo/
│   ├── serie_enzo_bible.md
│   └── episodes/ep01/         (episode.json, images/, audio/, serie_enzo_ep01.md)
├── assets/fonts/              (Montserrat + licence)
└── src/meddah/
    ├── llm.py                 (à reconstruire)
    ├── agents/
    └── production/            (montage vidéo, terminé)
```
Les animations (payantes) et le dossier `output/` ne sont pas dans git.

## État d'avancement
(À mettre à jour à la fin de chaque session, puis ré-uploader ce fichier dans le projet.)

Fait :
- [x] Nom du projet, bible de la série, script et production de l'épisode 1
- [x] Production vidéo complète et validée (`meddah_production.md`)
- [x] Dépôt GitHub privé : premier commit, puis réorganisation (production séparée des agents), bible ajoutée
- [x] Clé Gemini créée, facturation en pré-paiement, accès à `gemini-4-argon` vérifié (appel de test : 37 jetons en entrée, 5 en sortie)
- [x] Modèle de texte initial : Gemini 4 Argon jusqu'au 30 novembre 2026

Agents :
- [ ] `llm.py`, étape 1 : l'appel minimal
- [ ] `llm.py`, étapes 2 à 8
- [ ] Scénariste (schéma de `episode.json`, consigne, validation, boucle de correction)
- [ ] Voix
- [ ] Gardien de continuité
- [ ] Images
- [ ] Showrunner
- [ ] Publication
- [ ] Chef d'orchestre
- [ ] Après le 30 novembre : comparaison à l'aveugle des modèles (Argon, Gemini 3.8 Flash et, si on ouvre un compte Anthropic, Claude Sonnet 5.5 et Opus 5.5)

Divers :
- [ ] `docs/meddah_production.md` ajouté au dépôt et au projet
- [ ] README du dépôt
- [ ] Point sur la consommation Gemini (animation, texte)
- [ ] Vérifier l'épisode 1 dans l'app Instagram (zones masquées par l'interface)
- [ ] Compte Anthropic non créé ; compte Instagram professionnel à créer
- [ ] Compléter : nom de la voix ElevenLabs, temps passé et coût de l'épisode 1, quota Gemini consommé

## Journal de bord

### Agents
- Choix du modèle. Prix par million de jetons relevés dans des guides tiers (à vérifier) : Gemini 4 Argon 2 $ en entrée et 10 $ en sortie jusqu'au 30 nov. 2026, puis 4 $ et 20 $ ; Gemini 3.8 Flash 0,75 $ et 3,75 $ jusqu'au 31 déc., puis 1,50 $ et 7,50 $ ; Claude Sonnet 5.5 2 $ et 10 $ ; Claude Opus 5.5 4 $ et 20 $ ; Claude Haiku 5.5 0,10 $ et 0,50 $. Google présente Argon comme un modèle phare pour le code, la science et les agents, pas pour l'écriture créative. Rien ne prouve qu'il écrive mieux qu'un autre.
- Décision : Argon jusqu'au 30 novembre, puis comparaison à l'aveugle. Même consigne, même bible, même épisode précédent ; chaque modèle écrit la voix off de l'épisode 2 ; lecture sans connaître l'auteur ; notes sur le hook, la voix d'Enzo, le respect de la bible et le cliffhanger ; le code mesure le format. Coût estimé : moins de 1 $.
- Les jetons de réflexion sont facturés comme des jetons de sortie (champ `thoughts_token_count`). Niveaux de réflexion d'Argon : low, medium, high.
- Accès vérifié : `gemini-4-argon` répond avec `generate_content`.
- Problème : `genai.Client().models.list()` sur une seule ligne donne « client has been closed ». Solution : garder le client dans une variable.
- Problème : `setx` n'est pas vu par un VS Code déjà ouvert. Solution : `$env:GEMINI_API_KEY = [Environment]::GetEnvironmentVariable("GEMINI_API_KEY","User")` dans le terminal courant, puis redémarrer VS Code.
- Anthropic : compte et clé non créés pour l'instant. Un abonnement Claude Pro n'inclut pas l'API : il faut un compte développeur (platform.claude.com) avec des crédits prépayés.
- `llm.py` sera reconstruit en huit petites étapes. La version complète donnée d'un bloc a été abandonnée.
- Compte Google en pré-paiement : 3,59 € restants le 8 nov. 2026 après une recharge de 5,00 €. La consommation réelle de l'animation est probablement inférieure à l'estimation de 5,30 $ (non confirmé).

### Dépôt
- Un seul dépôt privé, deux parties : `production/` (terminé) et `agents/` (le sujet principal). Il reste privé tant que la licence des voix et la relecture ne sont pas faites.
- Problème : le fichier `gitignore` n'avait pas de point, git l'ignorait. Solution : renommé en `.gitignore`. Contenu : `.venv/`, `output/`, `series/**/animations/`, `*.bak`, `.env`, `__pycache__/`, `*.pyc`, `meddah.docx`.
- Problème : `pip freeze > requirements.txt` écrit en UTF-16 sous PowerShell 5.1, pip ne sait pas le relire. Solution : ne lister que les bibliothèques importées (`mutagen`, `pillow`, `google-genai`) et écrire avec `-Encoding ascii`.
- Problème : `Set-Content -Encoding UTF8` ajoute un BOM qui empêche Python de lire un JSON. Solution : modifier `episode.json` dans VS Code.
- Messages de commit sans accents, pour un affichage correct sous PowerShell.

### Production
Voir `meddah_production.md`.
