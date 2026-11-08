"""Montage, brique 2 + 5 : assembler les clips et les voix en une vidéo avec son, au bon volume.

Pré-requis : les clips de tous les plans existent dans output/clips/
(python src/meddah/clip.py).
Usage (depuis la racine du repo) :
    python src/meddah/assemble.py
Résultat : output/<serie>_ep<NN>_brut.mp4 (sans surimpressions ni étalonnage).
"""
import json
import re
import subprocess
import sys
from pathlib import Path

# Import « frère », comme dans clip.py (voir le commentaire là-bas).
from episode import charger_episode

DOSSIER_PAR_DEFAUT = "series/enzo/episodes/ep01"
DOSSIER_CLIPS = Path("output/clips")
SORTIE = Path("output")
FREQUENCE_AUDIO = 48000  # Hz, standard de la vidéo

# Normalisation du volume (norme EBU R128, utilisée par les plateformes).
CIBLE_LUFS = -14.0   # volume moyen visé ; valeur courante pour la vidéo courte verticale
CIBLE_CRETE = -1.5   # dB : les pics ne dépasseront pas ce niveau (évite la saturation)
CIBLE_LRA = 11.0     # écart de volume toléré entre passages forts et faibles


def lancer(commande, message):
    """Lance une commande ; en cas d'échec, remonte l'erreur de ffmpeg."""
    resultat = subprocess.run(commande, capture_output=True, text=True, errors="replace")
    if resultat.returncode != 0:
        raise RuntimeError(f"{message}\n{resultat.stderr}")
    return resultat.stdout


def duree_fichier(fichier, flux="v:0"):
    """Durée réelle (en secondes) d'un flux, lue par ffprobe."""
    sortie = lancer(
        ["ffprobe", "-v", "error", "-select_streams", flux,
         "-show_entries", "stream=duration", "-of", "csv=p=0", str(fichier)],
        f"ffprobe a échoué sur {fichier}",
    )
    return float(sortie.strip())


def lister_clips(episode):
    """Pour chaque plan : (plan, fichier du clip, durée réelle du clip)."""
    clips = []
    for plan in episode["shots"]:
        fichier = DOSSIER_CLIPS / f"plan{plan['id']:02d}.mp4"
        if not fichier.exists():
            raise FileNotFoundError(f"{fichier} manquant : lance d'abord clip.py")
        clips.append((plan, fichier, duree_fichier(fichier)))
    return clips


def assembler_video(clips, sortie):
    """Colle les clips bout à bout, sans les ré-encoder (donc sans perte)."""
    # Le « concat demuxer » lit un fichier texte qui liste les clips dans l'ordre.
    # Les chemins y sont relatifs au fichier liste, qu'on place dans le dossier des clips.
    liste = DOSSIER_CLIPS / "liste.txt"
    liste.write_text(
        "".join(f"file '{fichier.name}'\n" for _, fichier, _ in clips),
        encoding="utf-8",
    )
    lancer(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "concat", "-safe", "0", "-i", str(liste),
            "-c", "copy", str(sortie)],
           "Assemblage vidéo échoué")


def assembler_audio(episode, dossier, clips, sortie):
    """Construit la piste audio : un segment par plan, de la durée exacte du clip.

    Chaque segment = la voix décalée de `lead_in`, complétée par du silence jusqu'à
    la durée du clip. Comme chaque segment a la durée de son clip, la piste audio
    reste calée sur l'image par construction : aucune dérive possible.
    """
    lead_in_ms = round(episode["timing"]["lead_in"] * 1000)
    entrees = []   # fichiers voix passés à ffmpeg (-i)
    filtres = []   # un filtre par plan
    nb_voix = 0

    for i, (plan, _, duree) in enumerate(clips):
        if plan.get("voice"):
            entrees += ["-i", str(dossier / plan["voice"])]
            source = (f"[{nb_voix}:a]"
                      f"aformat=sample_rates={FREQUENCE_AUDIO}:channel_layouts=stereo,"
                      f"adelay={lead_in_ms}:all=1,")
            nb_voix += 1
        else:
            # Plan sans voix (le 10) : du silence généré par ffmpeg.
            source = f"anullsrc=r={FREQUENCE_AUDIO}:cl=stereo,"
        # apad complète avec du silence, atrim coupe à la durée exacte du clip.
        filtres.append(f"{source}apad=whole_dur={duree:.6f},atrim=duration={duree:.6f}[a{i}]")

    etiquettes = "".join(f"[a{i}]" for i in range(len(clips)))
    filtres.append(f"{etiquettes}concat=n={len(clips)}:v=0:a=1[audio]")

    lancer(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *entrees,
            "-filter_complex", ";".join(filtres),
            "-map", "[audio]", "-c:a", "pcm_s16le", str(sortie)],
           "Assemblage audio échoué")


def normaliser_volume(entree, sortie):
    """Ajuste le volume à CIBLE_LUFS, en deux passes, et encode en AAC.

    Passe 1 : ffmpeg MESURE le volume de la piste (rien n'est écrit).
    Passe 2 : on lui redonne ces mesures pour qu'il applique un gain constant et précis,
    sans « pomper » le son comme le ferait une normalisation en une seule passe.
    Renvoie les mesures de la passe 1.
    """
    cible = f"loudnorm=I={CIBLE_LUFS}:TP={CIBLE_CRETE}:LRA={CIBLE_LRA}"

    passe1 = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(entree),
         "-af", cible + ":print_format=json", "-f", "null", "-"],
        capture_output=True, text=True, errors="replace")
    sortie_texte = passe1.stderr
    if passe1.returncode != 0 or "{" not in sortie_texte:
        raise RuntimeError(f"Mesure du volume échouée\n{sortie_texte}")
    # ffmpeg écrit un bloc JSON à la fin de son message : on l'isole.
    mesure = json.loads(sortie_texte[sortie_texte.rindex("{"):sortie_texte.rindex("}") + 1])

    filtre = (f"{cible}:measured_I={mesure['input_i']}:measured_TP={mesure['input_tp']}"
              f":measured_LRA={mesure['input_lra']}:measured_thresh={mesure['input_thresh']}"
              f":offset={mesure['target_offset']}:linear=true"
              # loudnorm travaille à 192 kHz en interne : on revient à 48 kHz.
              f",aresample={FREQUENCE_AUDIO}")
    lancer(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(entree),
            "-af", filtre, "-c:a", "aac", "-b:a", "192k", str(sortie)],
           "Normalisation du volume échouée")
    return mesure


def mesurer_volume(fichier):
    """Volume moyen (LUFS) et crête (dBTP) d'un fichier, pour vérifier le résultat."""
    resultat = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(fichier), "-vn",
         "-af", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True, text=True, errors="replace")
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", resultat.stderr)
    crete = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", resultat.stderr)
    return float(lufs[-1]), float(crete[-1])


def fusionner(video, audio, sortie):
    """Réunit la vidéo et l'audio dans un seul fichier, sans ré-encoder."""
    lancer(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(video), "-i", str(audio),
            "-map", "0:v", "-map", "1:a", "-c", "copy",
            "-movflags", "+faststart", str(sortie)],
           "Fusion vidéo + audio échouée")


def assembler_episode(episode, dossier):
    """Assemble l'épisode complet à partir des clips. Renvoie 0 si tout va bien."""
    nom = f"{episode['series']}_ep{episode['episode']:02d}"
    video = SORTIE / f"{nom}_video.mp4"
    audio_brut = SORTIE / f"{nom}_audio_brut.wav"
    audio = SORTIE / f"{nom}_audio.m4a"
    final = SORTIE / f"{nom}_brut.mp4"

    try:
        clips = lister_clips(episode)
        print(f"{len(clips)} clips, somme des durées : {sum(c[2] for c in clips):.2f} s")
        assembler_video(clips, video)
        print("Vidéo assemblée.")
        assembler_audio(episode, dossier, clips, audio_brut)
        mesure = normaliser_volume(audio_brut, audio)
        print(f"Piste audio construite (volume : {float(mesure['input_i']):.1f} LUFS "
              f"-> cible {CIBLE_LUFS:.1f} LUFS).")
        fusionner(video, audio, final)
    except FileNotFoundError as erreur:
        print(f"ERREUR : {erreur}")
        return 1
    except RuntimeError as erreur:
        print(f"ERREUR : {erreur}")
        return 1

    lufs, crete = mesurer_volume(final)
    print(f"-> {final}")
    print(f"   vidéo : {duree_fichier(final, 'v:0'):.2f} s | audio : {duree_fichier(final, 'a:0'):.2f} s")
    print(f"   volume final : {lufs:.1f} LUFS | crête : {crete:.1f} dBTP")
    return 0


def main():
    dossier = Path(DOSSIER_PAR_DEFAUT)
    return assembler_episode(charger_episode(dossier), dossier)


if __name__ == "__main__":
    sys.exit(main())
