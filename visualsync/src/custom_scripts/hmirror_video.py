#!/usr/bin/env python3
"""
mirror_video_horizontal.py

Specchia orizzontalmente un video (hflip: sinistra <-> destra, alto e basso
INVARIATI) usando ffmpeg e salva il risultato nella stessa cartella del
file originale.

Uso tipico per correggere un singolo file (es. il TPV_synchronized di ID_4
che risulta specchiato orizzontalmente rispetto al video originale):

    python3 mirror_video_horizontal.py /path/to/ID_4/TPV_synchronized.mp4

Di default NON sovrascrive il file originale: crea un nuovo file con
suffisso "_mirrored" nella stessa cartella, cosi' puoi controllare il
risultato prima di sostituire quello vecchio.

Per sovrascrivere direttamente il file originale (mantenendo un backup
".bak" per sicurezza), usa --overwrite:

    python3 mirror_video_horizontal.py /path/to/ID_4/TPV_synchronized.mp4 --overwrite

Per processare più file in un colpo solo:

    python3 mirror_video_horizontal.py /path/to/PRIN_DATASET/*/TPV_synchronized.mp4 --overwrite
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def mirror_video_horizontal(input_path: Path, output_path: Path, crf: int = 18, preset: str = "medium") -> None:
    """
    Specchia un video orizzontalmente (hflip) con ffmpeg. Il video viene
    ri-codificato in H.264 (necessario: lo specchiamento dei pixel richiede
    una nuova codifica, non e' un'operazione "copy"). L'audio, se presente,
    viene copiato senza ri-codifica per preservarne la qualità originale.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", "hflip",         # specchio orizzontale puro: SOLO sinistra/destra
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", str(crf),
        "-c:a", "copy",         # traccia audio invariata, se presente
        "-map_metadata", "0",   # preserva i metadati originali (es. timestamp)
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg ha fallito su {input_path.name}:\n{result.stderr[-2000:]}")


def process_file(input_path: Path, overwrite: bool, crf: int, preset: str) -> None:
    if not input_path.is_file():
        print(f"[!] Saltato (non trovato): {input_path}", file=sys.stderr)
        return

    if overwrite:
        # Prima specchiamo su un file temporaneo, e solo se ha successo
        # sostituiamo l'originale (che nel frattempo viene salvato come .bak).
        tmp_output = input_path.with_name(input_path.stem + "_tmp_mirrored" + input_path.suffix)
        backup_path = input_path.with_suffix(input_path.suffix + ".bak")

        print(f"[*] Specchio {input_path.name} ...")
        mirror_video_horizontal(input_path, tmp_output, crf=crf, preset=preset)

        if not backup_path.exists():
            shutil.copy2(input_path, backup_path)
        tmp_output.replace(input_path)  # sostituzione atomica
        print(f"    -> Sovrascritto. Backup dell'originale salvato in: {backup_path.name}")
    else:
        output_path = input_path.with_name(input_path.stem + "_mirrored" + input_path.suffix)
        print(f"[*] Specchio {input_path.name} -> {output_path.name} ...")
        mirror_video_horizontal(input_path, output_path, crf=crf, preset=preset)
        print(f"    -> Creato: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Specchia orizzontalmente uno o più video, salvandoli nella stessa cartella.")
    parser.add_argument("videos", type=Path, nargs="+", help="Percorso/i del video da specchiare.")
    parser.add_argument("--overwrite", action="store_true",
                         help="Sovrascrive il file originale (con backup .bak) invece di creare un nuovo file _mirrored.")
    parser.add_argument("--crf", type=int, default=18,
                         help="Qualità H.264 (più basso = migliore, 18 è visivamente lossless; default: 18).")
    parser.add_argument("--preset", type=str, default="medium",
                         help="Preset di velocità/compressione ffmpeg (default: medium).")
    args = parser.parse_args()

    if shutil.which("ffmpeg") is None:
        print("[!] ffmpeg non trovato nel PATH. Installalo (es. 'apt install ffmpeg') prima di procedere.", file=sys.stderr)
        sys.exit(1)

    for video_path in args.videos:
        try:
            process_file(video_path, overwrite=args.overwrite, crf=args.crf, preset=args.preset)
        except Exception as e:
            print(f"[!] Errore su {video_path}: {e}", file=sys.stderr)

    print("[+] Completato.")


if __name__ == "__main__":
    main()