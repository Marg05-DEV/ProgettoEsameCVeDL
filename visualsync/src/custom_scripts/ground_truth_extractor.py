#!/usr/bin/env python3
"""
sync_ground_truth_extractor.py

Modulo scientifico per l'estrazione e il calcolo del Ground Truth (GT) temporale
(Pairwise e Global in SECONDI) nel dataset PRIN_DATASET, basato sul confronto 
tra video originali (grezzi) e video sincronizzati di riferimento.

Dispone di due modalità:
1. API Mode: Esporta funzioni per l'integrazione in pipeline esterne.
2. Print Mode (CLI): Esegue il parsing da terminale e stampa tabelle riassuntive.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional, Any

import cv2

VIEWS = ["FPV", "TOP", "TPV"]
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".m4v"}


# --------------------------------------------------------------------------- #
# Low-Level Video Utilities
# --------------------------------------------------------------------------- #

def get_duration(path: Optional[Path]) -> Optional[float]:
    """Calcola la durata in secondi (frame_count / fps) via OpenCV."""
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


def find_video(directory: Path, name_prefix: Optional[str] = None) -> Optional[Path]:
    """Trova il file video principale direttamente dentro una directory."""
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
        print(f"  [!] Più di un video trovato in {directory} ({names}); uso il più grande.",
              file=sys.stderr)
    return max(candidates, key=lambda f: f.stat().st_size)


def find_original_video(id_dir: Path, view: str) -> Optional[Path]:
    return find_video(id_dir / view)


def find_synchronized_video(id_dir: Path, view: str) -> Optional[Path]:
    return find_video(id_dir, name_prefix=f"{view}_synchronized")


def format_duration_mm_ss(seconds: Optional[float]) -> str:
    """Formatta i secondi nel formato richiesto mm:ss.centesimi (es. 01:45.00)"""
    if seconds is None:
        return "N/A"
    minutes, secs = divmod(seconds, 60)
    return f"{int(minutes):02d}:{secs:05.2f}"


# --------------------------------------------------------------------------- #
# CORE API: Funzioni Modulari di Calcolo del Ground Truth (In Secondi)
# --------------------------------------------------------------------------- #

def get_durations(root_path: str | Path, ids: list[str]) -> dict[str, dict[str, dict[str, float]]]:
    """
    1. Ritorna un dizionario con la durata originale, sincronizzata e la loro differenza (in secondi).
    Output: 
    { 
        'ID_2': {
            'FPV': {'orig_dur': 107.97, 'sync_dur': 105.00, 'diff': -2.97}, 
            'TOP': {'orig_dur': 124.47, 'sync_dur': 104.87, 'diff': -19.60},
            'TPV': {'orig_dur': 113.60, 'sync_dur': 104.13, 'diff': -9.47}
        }, ... 
    }
    """
    root = Path(root_path)
    if not root.is_dir():
        raise FileNotFoundError(f"La cartella root specificata non esiste: {root}")
        
    dataset_cuts = {}
    
    for id_name in ids:
        id_dir = root / id_name
        if not id_dir.is_dir():
            continue
            
        dataset_cuts[id_name] = {}
        
        for view in VIEWS:
            orig_video = find_original_video(id_dir, view)
            sync_video = find_synchronized_video(id_dir, view)
            
            orig_dur = get_duration(orig_video)
            sync_dur = get_duration(sync_video)
            
            o_val = orig_dur if orig_dur is not None else 0.0
            s_val = sync_dur if sync_dur is not None else 0.0
            diff_val = s_val - o_val if (orig_dur is not None and sync_dur is not None) else 0.0
            
            dataset_cuts[id_name][view] = {
                "orig_dur": o_val,
                "sync_dur": s_val,
                "diff": diff_val
            }
                
    return dataset_cuts


def get_pairwise_offsets(root_path: str | Path, ids: list[str]) -> dict[str, dict[str, float]]:
    """
    2. Calcola gli offset pairwise reali di Ground Truth (espressi in SECONDI).
    Formula: Offset(A -> B) = Taglio_B - Taglio_A
    Output: { 'ID_2': {'TOP_to_TPV': -10.13, 'TPV_to_FPV': -6.50, 'TOP_to_FPV': -16.63}, ... }
    """
    durations = get_durations(root_path, ids)
    pairwise_offsets = {}
    
    for id_name in ids:
        if id_name not in durations:
            continue
            
        # Otteniamo i secondi assoluti rimossi (rimuovendo il segno negativo della differenza)
        taglio_top = abs(durations[id_name]["TOP"]["diff"])
        taglio_tpv = abs(durations[id_name]["TPV"]["diff"])
        taglio_fpv = abs(durations[id_name]["FPV"]["diff"])
        
        # Calcolo dei delta temporali relativi in secondi
        t_top_tpv = taglio_tpv - taglio_top
        t_tpv_fpv = taglio_fpv - taglio_tpv
        t_top_fpv = taglio_fpv - taglio_top
        
        pairwise_offsets[id_name] = {
            "TOP_to_TPV": t_top_tpv,
            "TPV_to_FPV": t_tpv_fpv,
            "TOP_to_FPV": t_top_fpv
        }
        
    return pairwise_offsets


def get_global_offsets(root_path: str | Path, ids: list[str]) -> dict[str, dict[str, float]]:
    """
    3. Calcola gli offset globali reali di Ground Truth (in SECONDI) ponendo la vista TPV come Pivot (0).
    Formula: Offset_Global_C = Taglio_C - Taglio_TPV
    Output: { 'ID_2': {'TPV': 0.0, 'TOP': 10.13, 'FPV': -6.50}, ... }
    """
    pairwise = get_pairwise_offsets(root_path, ids)
    global_offsets = {}
    
    for id_name in ids:
        if id_name not in pairwise:
            continue
            
        # Relazione matematica coerente in secondi col pivot TPV = 0
        top_global = -pairwise[id_name]["TOP_to_TPV"]
        fpv_global = pairwise[id_name]["TPV_to_FPV"]
        
        global_offsets[id_name] = {
            "TPV": 0.0,
            "TOP": top_global,
            "FPV": fpv_global
        }
        
    return global_offsets


def get_all_synchronization_data(root_path: str | Path, ids: list[str]) -> dict[str, dict[str, Any]]:
    """
    4. Funzione Omnicomprensiva: Aggrega i dati di durate, pairwise e global offsets (TUTTI IN SECONDI).
    """
    durs = get_durations(root_path, ids)
    pairs = get_pairwise_offsets(root_path, ids)
    globals_data = get_global_offsets(root_path, ids)
    
    all_data = {}
    for id_name in ids:
        if id_name not in durs:
            continue
        all_data[id_name] = {
            "durations_data": durs[id_name],
            "pairwise_offsets_secondi": pairs.get(id_name, {}),
            "global_offsets_secondi": globals_data.get(id_name, {})
        }
    return all_data


# --------------------------------------------------------------------------- #
# Print Mode (Interfaccia CLI)
# --------------------------------------------------------------------------- #

def main():
    parser = argparse.ArgumentParser(
        description="Analisi temporale e calcolo del Ground Truth in secondi per il dataset PRIN.")
    parser.add_argument("--root", type=Path, default=os.environ.get("RAW_ROOT"),
                         help="Cartella radice contenente le sottocartelle ID_*. Default: var ambiente RAW_ROOT.")
    parser.add_argument("--ids", nargs="*", default=None,
                         help="Lista di ID specifici da elaborare e stampare (es. ID_0 ID_2). Se vuota, analizza tutti.")
    args = parser.parse_args()

    if args.root is None:
        parser.error("Specifica --root o esporta la variabile d'ambiente RAW_ROOT.")
    if not args.root.is_dir():
        parser.error(f"Cartella root non trovata: {args.root}")

    # Selezione mirata o globale degli ID
    if args.ids is not None:
        id_names = args.ids
        print(f"[*] Modalità selettiva: Elaborazione dei seguenti ID: {id_names}")
    else:
        print(f"[*] Modalità globale: Scansione di tutta la root {args.root}")
        id_names = sorted(
            [d.name for d in args.root.iterdir() if d.is_dir() and d.name.startswith("ID_")]
        )

    if not id_names:
        print(f"[!] Nessuna cartella ID_ trovata.", file=sys.stderr)
        sys.exit(1)

    # Estrazione dei dati unificata in secondi
    sync_data = get_all_synchronization_data(args.root, id_names)

    # Ciclo di stampa tabellare
    for id_name in id_names:
        if id_name not in sync_data:
            print(f"\n[!] Impossibile elaborare i video per {id_name} (Verificare i file).")
            continue
            
        print(f"\n=========================================================================")
        print(f"   REPORT METADATI E GROUND TRUTH TEMPORALE (IN SECONDI): {id_name}")
        print(f"=========================================================================")
        
        # Sezione A: Durate in formato mm:ss
        print(" [A] METADATI VIDEO (Formato mm:ss) E TAGLI:")
        for view in VIEWS:
            v_data = sync_data[id_name]["durations_data"].get(view, {"orig_dur": 0.0, "sync_dur": 0.0, "diff": 0.0})
            orig_dur = v_data["orig_dur"]
            sync_dur = v_data["sync_dur"]
            diff = v_data["diff"]
            
            print(f"   {view:4s} | Orig: {format_duration_mm_ss(orig_dur):8s} "
                  f"| Sync: {format_duration_mm_ss(sync_dur):8s} "
                  f"| Delta Taglio: {diff:+.2f}s")
            
        # Sezione B: Gli Offset Pairwise in secondi
        print("\n [B] GROUND TRUTH PAIRWISE OFFSETS (Secondi):")
        pw = sync_data[id_name]["pairwise_offsets_secondi"]
        print(f"   TOP -> TPV : {pw.get('TOP_to_TPV', 0.0):+8.2f}s")
        print(f"   TPV -> FPV : {pw.get('TPV_to_FPV', 0.0):+8.2f}s")
        print(f"   TOP -> FPV : {pw.get('TOP_to_FPV', 0.0):+8.2f}s")
        
        # Sezione C: Gli Offset Globali con TPV come Pivot (Secondi)
        print("\n [C] GROUND TRUTH GLOBAL OFFSETS (Pivot: TPV = 0.00s):")
        gl = sync_data[id_name]["global_offsets_secondi"]
        for view in VIEWS:
            marker = " (PIVOT)" if view == "TPV" else ""
            print(f"   {view:4s} : {gl.get(view, 0.0):+8.2f}s{marker}")
            
    print(f"\n=========================================================================")
    print(f" Fine Report. Elaborati con successo {len(sync_data)} gruppi video.")
    print(f"=========================================================================")


if __name__ == "__main__":
    main()