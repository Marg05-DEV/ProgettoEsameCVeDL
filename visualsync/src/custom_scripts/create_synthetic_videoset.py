#!/usr/bin/env python3
"""
create_synthetic_test_opencv.py

Genera un esperimento sintetico controllato (ID_20) partendo da ID_0 usando solo OpenCV.
1. Filtra i risultati per evitare IsADirectoryError.
2. Rinomina i file interni senza usare la parola 'synchronized' per non rompere i selettori.
"""

import os
import sys
import shutil
from pathlib import Path
import cv2

def apply_offset_with_opencv(src_path: Path, dest_path: Path, frames_to_skip: int = 0):
    """
    Legge un video sorgente e lo riscrive usando OpenCV.
    Se frames_to_skip > 0, salta i primi N frame all'inizio del flusso.
    """
    cap = cv2.VideoCapture(str(src_path))
    if not cap.isOpened():
        print(f"  [!] Errore nell'apertura del video sorgente: {src_path.name}", file=sys.stderr)
        return False

    # Estraiamo le proprietà del video originale per mantenerle identiche
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Utilizziamo il codec mp4v (compatibile MP4 standard)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(dest_path), fourcc, fps, (width, height))

    # Applichiamo l'offset artificiale saltando i primi N frame
    if frames_to_skip > 0:
        print(f"    -> RIMOZIONE di {frames_to_skip} frame iniziali...")
        cap.set(cv2.CAP_PROP_POS_FRAMES, frames_to_skip)

    count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)
        count += 1

    cap.release()
    out.release()
    return True

def main():
    raw_root = os.environ.get("RAW_ROOT")
    if not raw_root:
        print("[!] Errore: Esporta la variabile d'ambiente RAW_ROOT prima di lanciare.", file=sys.stderr)
        sys.exit(1)

    raw_root = Path(raw_root)
    id_0_dir = raw_root / "ID_0"
    id_20_dir = raw_root / "ID_20"

    if not id_0_dir.is_dir():
        print(f"[!] Errore: La cartella sorgente {id_0_dir} non esiste.", file=sys.stderr)
        sys.exit(1)

    print("\n" + "="*75)
    print(" DATASET SINTETICO CON OpenCV: GENERAZIONE ID_20")
    print("="*75)

    # Assicuriamoci che la cartella di destinazione principale esista
    id_20_dir.mkdir(parents=True, exist_ok=True)

    views = ["TOP", "TPV", "FPV"]

    for view in views:
        # Trova il file sorgente sincronizzato in ID_0
        # Escludiamo esplicitamente le cartelle usando .is_file() per evitare IsADirectoryError
        sync_candidates = [
            f for f in id_0_dir.glob(f"{view}_synchronized*") 
            if f.is_file() and f.suffix.lower() in [".mp4", ".mov", ".avi"]
        ]
        
        if not sync_candidates:
            print(f"[!] Errore: Manca il FILE video {view}_synchronized in {id_0_dir.name}", file=sys.stderr)
            continue
            
        src_sync_video = sync_candidates[0]
        ext = src_sync_video.suffix

        print(f"\n[*] Elaborazione flussi per la vista: {view}")

        # 1. NELLA ROOT DI ID_20: Copiamo i file di controllo mantenendo la parola 'synchronized'
        dest_root_sync = id_20_dir / f"{view}_synchronized{ext}"
        print(f"    [+] Copia file GT root: {dest_root_sync.name}")
        shutil.copy2(src_sync_video, dest_root_sync)

        # 2. NELLE CARTELLE INTERNE: Creiamo i video eliminando la parola 'synchronized'
        # Questo evita che ground_truth_extractor si confonda durante l'analisi
        dest_view_dir = id_20_dir / view
        dest_view_dir.mkdir(parents=True, exist_ok=True)
        
        # Nome pulito: es. ID_20/TOP/video_top.mp4
        dest_raw_video = dest_view_dir / f"video_{view.lower()}{ext}"

        if view == "TOP":
            # Per la vista TOP, tagliamo via i primi 90 frame (creando l'offset)
            print(f"    [+] Generazione file alterato in {view}/ con +90 frame di ritardo... Name: {dest_raw_video.name}")
            apply_offset_with_opencv(src_sync_video, dest_raw_video, frames_to_skip=90)
        else:
            # For TPV e FPV, copiamo semplicemente il video a specchio senza alterazioni
            print(f"    [+] Copia file specchio in {view}/... Name: {dest_raw_video.name}")
            apply_offset_with_opencv(src_sync_video, dest_raw_video, frames_to_skip=0)

    print("\n" + "="*75)
    print("[+] Struttura ID_20 completata con successo tramite OpenCV!")
    print("    I file root mantengono 'synchronized', i file interni sono puliti (video_*.mp4)")
    print("="*75 + "\n")

if __name__ == "__main__":
    main()