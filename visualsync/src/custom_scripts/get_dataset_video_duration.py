#!/usr/bin/env python3
"""
compare_video_durations.py

Confronta la durata dei video FPV, TOP e TPV tra la versione "originale"
(dentro le sottocartelle FPV/TOP/TPV) e la versione sincronizzata
(file <VIEW>_synchronized.mp4 a livello della cartella ID), per ogni
cartella ID_* del dataset PRIN_DATASET.

Struttura attesa per ogni ID:

    ID_X/
        FPV/<video originale>.mp4         (es. GX010036.MP4)
        FPV_synchronized_output_video/    (ignorata: non e' un video, presumo frame estratti)
        TOP/<video originale>.mp4         (es. rgb_stream.mp4)
        TOP_synchronized_output_video/
        TPV/<video originale>.mp4         (es. merged.mp4)
        TPV_synchronized_output_video/
        FPV_synchronized.mp4
        TOP_synchronized.mp4
        TPV_synchronized.mp4

Il nome del video "originale" dentro FPV/TOP/TPV NON viene assunto fisso:
lo script prende il primo (o il piu' grande, se ce ne sono piu' di uno)
file video trovato direttamente dentro la cartella, ignorando le
sottocartelle.

Le cartelle <VIEW>_synchronized_output_video (a livello di ID_X) vengono
ignorate: la ricerca dei file guarda solo i file diretti, non le cartelle.

La durata dei video viene letta con OpenCV (frame_count / fps).

Uso:
    python3 compare_video_durations.py --root /percorso/PRIN_DATASET
    python3 compare_video_durations.py --root /percorso/PRIN_DATASET --ids ID_0 ID_2
    python3 compare_video_durations.py --root /percorso/PRIN_DATASET --tolerance 1.0

Se non si passa --root, lo script usa la variabile d'ambiente RAW_ROOT
(quella esportata da set_globals_variables.sh), se presente.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

import cv2

VIEWS = ["FPV", "TOP", "TPV"]
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".m4v"}


# --------------------------------------------------------------------------- #
# Durata video
# --------------------------------------------------------------------------- #

def get_duration(path: Optional[Path]) -> Optional[float]:
    """Durata in secondi = frame_count / fps, via OpenCV. None se il file
    manca o non e' leggibile."""
    if path is None:
        return None
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        cap.release()
        return None
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    cap.release()
    if fps and fps > 0 and frame_count and frame_count > 0:
        return frame_count / fps
    return None


# --------------------------------------------------------------------------- #
# Ricerca file
# --------------------------------------------------------------------------- #

def find_video(directory: Path, name_prefix: Optional[str] = None) -> Optional[Path]:
    """Trova un file video direttamente dentro `directory` (non ricorsivo).
    Se name_prefix e' specificato, filtra per nome che inizia con quel prefisso
    (case-insensitive). Se ci sono piu' candidati, ritorna il piu' grande
    e avvisa su stderr."""
    if not directory.is_dir():
        return None

    candidates = []
    for f in directory.iterdir():
        if not f.is_file():
            continue
        if f.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        if name_prefix and not f.name.lower().startswith(name_prefix.lower()):
            continue
        candidates.append(f)

    if not candidates:
        return None
    if len(candidates) > 1:
        names = ", ".join(c.name for c in candidates)
        print(f"  [!] Piu' di un video trovato in {directory} ({names}); uso il piu' grande.",
              file=sys.stderr)
    return max(candidates, key=lambda f: f.stat().st_size)


def find_original_video(id_dir: Path, view: str) -> Optional[Path]:
    return find_video(id_dir / view)


def find_synchronized_video(id_dir: Path, view: str) -> Optional[Path]:
    return find_video(id_dir, name_prefix=f"{view}_synchronized")


# --------------------------------------------------------------------------- #
# Formattazione
# --------------------------------------------------------------------------- #

def format_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "N/A"
    m, s = divmod(seconds, 60)
    h, m = divmod(int(m), 60)
    return f"{int(h):02d}:{int(m):02d}:{s:05.2f}"


def compute_status(orig_video, sync_video, orig_duration, sync_duration, tolerance) -> tuple[str, Optional[float]]:
    if orig_video is None and sync_video is None:
        return "ENTRAMBI MANCANTI", None
    if orig_video is None:
        return "ORIGINALE MANCANTE", None
    if sync_video is None:
        return "SINCRONIZZATO MANCANTE", None
    if orig_duration is None or sync_duration is None:
        return "ERRORE LETTURA DURATA", None
    diff = sync_duration - orig_duration
    status = "OK" if abs(diff) <= tolerance else "DIFFERENZA"
    return status, diff


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main():
    parser = argparse.ArgumentParser(
        description="Confronta durata video originali vs sincronizzati per ogni ID del dataset.")
    parser.add_argument("--root", type=Path, default=os.environ.get("RAW_ROOT"),
                         help="Cartella che contiene le sottocartelle ID_*. "
                              "Default: variabile d'ambiente RAW_ROOT, se impostata.")
    parser.add_argument("--ids", nargs="*", default=None,
                         help="Lista di ID specifici da controllare (es. ID_0 ID_2). "
                              "Default: tutte le cartelle ID_* trovate in --root.")
    parser.add_argument("--tolerance", type=float, default=0.5,
                         help="Soglia in secondi di differenza oltre la quale segnalare "
                              "una DIFFERENZA invece di OK. Default: 0.5s")
    args = parser.parse_args()

    if args.root is None:
        parser.error("Specifica --root (o esporta RAW_ROOT nell'ambiente).")
    if not args.root.is_dir():
        parser.error(f"Cartella non trovata: {args.root}")

    if args.ids is not None:
        print("Id inseriti da visualizzare", args.ids)
        id_dirs = [args.root / id_name for id_name in args.ids]
    else:
        print(args.root)
        for d in args.root.iterdir():
            print(d)
        id_dirs = sorted(
            (d for d in args.root.iterdir() if d.is_dir() and d.name.startswith("ID_")),
            key=lambda d: d.name,
        )

    if not id_dirs:
        print(f"Nessuna cartella ID_* trovata in {args.root}", file=sys.stderr)
        sys.exit(1)

    status_counts: dict[str, int] = {}

    for id_dir in id_dirs:
        if not id_dir.is_dir():
            print(f"[!] Cartella ID non trovata: {id_dir}", file=sys.stderr)
            continue

        print(f"\n=== {id_dir.name} ===")
        for view in VIEWS:
            orig_video = find_original_video(id_dir, view)
            sync_video = find_synchronized_video(id_dir, view)

            orig_duration = get_duration(orig_video)
            sync_duration = get_duration(sync_video)

            status, diff = compute_status(orig_video, sync_video, orig_duration, sync_duration, args.tolerance)
            status_counts[status] = status_counts.get(status, 0) + 1

            diff_str = f"{diff:+.2f}s" if diff is not None else "N/A"
            print(f"  {view:4s} | orig: {format_duration(orig_duration):10s} "
                  f"| sync: {format_duration(sync_duration):10s} "
                  f"| diff: {diff_str:9s} | {status}")

    print("\n=== Riepilogo ===")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")


if __name__ == "__main__":
    main()