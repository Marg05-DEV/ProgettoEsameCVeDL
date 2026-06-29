#!/usr/bin/env python3
"""
ground_truth_extractor.py

Modulo per l'estrazione automatica del Ground Truth di sincronizzazione.
Utilizza il Metodo 1 (Template Matching basato su OpenCV) per identificare l'esatto
frame di inizio del video sincronizzato all'interno del video originale grezzo.

[REFAC STRUCT]: Le funzioni elaborano un SINGOLO ID alla volta. 
L'iterazione su liste o range è delegata interamente al controllo del main().
"""

from __future__ import annotations

import os
import sys
import argparse
from pathlib import Path
from typing import Optional, Any

import cv2
import numpy as np
import pandas as pd

# Configurazione delle viste del dataset PRIN
VIEWS = ["TOP", "TPV", "FPV"]


def find_original_video(id_dir: Path, view: str) -> Optional[Path]:
    """Cerca il video originale all'interno della cartella della vista (es. ID_0/TOP/)."""
    view_dir = id_dir / view
    if not view_dir.is_dir():
        return None
    candidates = [f for f in view_dir.glob("*") if f.suffix.lower() in [".mp4", ".mov", ".avi"]]
    if not candidates:
        return None
    return max(candidates, key=lambda f: f.stat().st_size)


def find_synchronized_video(id_dir: Path, view: str) -> Optional[Path]:
    """Cerca il video sincronizzato di riferimento nella root dell'ID (es. ID_0/TOP_synchronized.mp4)."""
    candidates = [f for f in id_dir.glob(f"{view}_synchronized*") if f.suffix.lower() in [".mp4", ".mov", ".avi"]]
    return candidates[0] if candidates else None


def find_exact_start_cut_seconds(orig_path: Path, sync_path: Path, max_search_seconds: float = 60.0) -> float:
    """
    METODO 1: Identifica il punto di minimo assoluto della differenza visiva sulla ROI.
    """
    anchor_seconds = 10.0
    
    cap_sync = cv2.VideoCapture(str(sync_path))
    sync_fps = cap_sync.get(cv2.CAP_PROP_FPS) or 30.0
    anchor_frame_sync = int(anchor_seconds * sync_fps)
    
    cap_sync.set(cv2.CAP_PROP_POS_FRAMES, anchor_frame_sync)
    ret_s, frame_sync = cap_sync.read()
    cap_sync.release()
    
    if not ret_s:
        return 0.0
        
    gray_sync = cv2.cvtColor(frame_sync, cv2.COLOR_BGR2GRAY)
    gray_sync = cv2.resize(gray_sync, (0, 0), fx=0.5, fy=0.5)
    h, w = gray_sync.shape[:2]
    
    start_y, end_y = int(h * 0.2), int(h * 0.8)
    start_x, end_x = int(w * 0.2), int(w * 0.8)
    roi_sync = gray_sync[start_y:end_y, start_x:end_x]
    
    cap_orig = cv2.VideoCapture(str(orig_path))
    orig_fps = cap_orig.get(cv2.CAP_PROP_FPS) or 30.0
    max_search_frames = int((max_search_seconds + anchor_seconds) * orig_fps)
    
    best_match_frame = 0
    min_difference = float('inf')
    
    count = 0
    while count < max_search_frames:
        ret_o, frame_orig = cap_orig.read()
        if not ret_o:
            break
            
        gray_orig = cv2.cvtColor(frame_orig, cv2.COLOR_BGR2GRAY)
        gray_orig_resized = cv2.resize(gray_orig, (w, h))
        roi_orig = gray_orig_resized[start_y:end_y, start_x:end_x]
        
        diff = cv2.absdiff(roi_sync, roi_orig)
        mean_diff = np.mean(diff)
        
        if mean_diff < min_difference:
            min_difference = mean_diff
            best_match_frame = count
            
        count += 1
        
    cap_orig.release()
    
    anchor_seconds_in_orig = best_match_frame / orig_fps
    real_start_seconds_in_orig = anchor_seconds_in_orig - anchor_seconds
    
    return -real_start_seconds_in_orig


def get_durations(root_path: str | Path, id_name: str) -> dict[str, dict[str, float]]:
    """Estrae i tagli iniziali (in secondi) via Template Matching per un singolo ID."""
    root = Path(root_path)
    id_dir = root / id_name
    views_data = {}
    
    if not id_dir.is_dir():
        raise FileNotFoundError(f"La cartella dell'ID specificato non esiste: {id_dir}")
        
    print(f"[*] Calcolo visivo Ground Truth per {id_name} via Template Matching...")
    
    for view in VIEWS:
        orig_video = find_original_video(id_dir, view)
        sync_video = find_synchronized_video(id_dir, view)
        
        if orig_video and sync_video:
            diff_val = find_exact_start_cut_seconds(orig_video, sync_video)
            print(f"    - Vista {view:4s} | Allineata al secondo: {abs(diff_val):.2f}s del file originale")
        else:
            diff_val = 0.0
            print(f"    - Vista {view:4s} | [Attenzione] File originali o sincronizzati mancanti.")
            
        views_data[view] = {
            "orig_dur": 0.0,
            "sync_dur": 0.0,
            "diff": diff_val
        }
            
    return views_data


def get_global_offsets(views_data: dict[str, float]) -> dict[str, float]:
    """Calcola gli offset globali per il singolo ID (Pivot TPV = 0.0)."""
    t_top_tpv = views_data.get("TOP__TPV", 0.0)
    t_tpv = 0.0
    t_tpv_fpv = views_data.get("TPV__FPV", 0.0)
    
    
    return {
        "TPV": t_tpv,
        "TOP": t_top_tpv - t_tpv,
        "FPV": t_tpv - t_tpv_fpv
    }


def get_pairwise_offsets(views_data: dict[str, dict[str, float]]) -> dict[str, float]:
    """Calcola i ritardi relativi (pairwise) tra le coppie per il singolo ID."""
    t_top = views_data.get("TOP", {}).get("diff", 0.0)
    t_tpv = views_data.get("TPV", {}).get("diff", 0.0)
    t_fpv = views_data.get("FPV", {}).get("diff", 0.0)
    
    return {
        "TOP__TPV": t_tpv - t_top,
        "TOP__FPV": t_fpv - t_top,
        "TPV__FPV": t_fpv - t_tpv
    }


def get_all_synchronization_data(root_path: str | Path, id_name: str) -> dict[str, Any]:
    """Funzione atomica omnicomprensiva per preservare la retrocompatibilità con altri script."""
    durations = get_durations(root_path, id_name)
    pairwise = get_pairwise_offsets(durations)
    glob = get_global_offsets(pairwise)
    
    return {
        "tagli_iniziali_secondi": {v: durations[v]["diff"] for v in VIEWS},
        "pairwise_offsets_secondi": pairwise,
        "global_offsets_secondi": glob
    }


def save_single_id_to_csv(id_name: str, single_dataset_data: dict[str, Any], csv_path: Path):
    """
    Inserisce o aggiorna (Upsert) i dati di un singolo ID nel CSV centralizzato.
    """
    glob_offsets = single_dataset_data["global_offsets_secondi"]
    new_row = {
        "id": id_name,
        "top_offset": glob_offsets.get("TOP", 0.0),
        "tpv_offset": 0.0,
        "fpv_offset": glob_offsets.get("FPV", 0.0)
    }
    new_df = pd.DataFrame([new_row])
    
    if csv_path.is_file():
        try:
            old_df = pd.read_csv(csv_path)
            # Logica di Upsert: elimina la riga vecchia se esistente
            old_df = old_df[old_df['id'] != id_name]
            combined_df = pd.concat([old_df, new_df], ignore_index=True)
            combined_df = combined_df.sort_values(by='id').reset_index(drop=True)
            combined_df.to_csv(csv_path, index=False)
        except Exception as e:
            print(f"[!] Errore durante l'aggiornamento parziale del CSV: {e}. Tento riscrittura forzata.")
            new_df.to_csv(csv_path, index=False)
    else:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        new_df.to_csv(csv_path, index=False)


def format_seconds(seconds: float) -> str:
    abs_secs = abs(seconds)
    minutes = int(abs_secs // 60)
    secs = int(abs_secs % 60)
    sign = "-" if seconds < 0 else "+"
    return f"{sign}{minutes:02d}:{secs:02d}"


def print_single_report(id_name: str, data: dict[str, Any]):
    """Stampa il report accademico per un singolo blocco elaborato."""
    print("\n=========================================================================")
    print(f" GROUND TRUTH DI SINCRONIZZAZIONE (METODO 1): {id_name}")
    print("=========================================================================")
    print(" [1] TAGLIO INIZIALE RISPETTO AI VIDEO ORIGINALI:")
    for view in VIEWS:
        cut = data["tagli_iniziali_secondi"][view]
        print(f"     Vista {view:4s} -> Inizio a: {abs(cut):.2f}s ({format_seconds(cut)})")
        
    print("\n [2] OFFSET PAIRWISE RELATIVI:")
    for pair, val in data["pairwise_offsets_secondi"].items():
        print(f"     Coppia {pair:8s} -> Differenza: {val:+.2f}s")
        
    print("\n [3] OFFSET GLOBALI CONVERGENTI (Pivot TPV = 0.0):")
    for view in VIEWS:
        val = data["global_offsets_secondi"][view]
        print(f"     Vista {view:4s} -> Offset GT Globale: {val:+.2f}s")
    print("=========================================================================\n")


def main():
    raw_root_env = os.environ.get("RAW_ROOT")
    result_root_env = os.environ.get("RESULT_ROOT")
    group_env = os.environ.get("GROUP")
    
    parser = argparse.ArgumentParser(description="Estrattore Ground Truth Dataset PRIN con pipeline atomica.")
    parser.add_argument("--raw_root", type=Path, default=raw_root_env)
    parser.add_argument("--result_root", type=Path, default=result_root_env)
    
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--id", type=str, default=group_env)
    mode_group.add_argument("--all", action="store_true")
    mode_group.add_argument("--range", type=str, metavar="START-END")

    args = parser.parse_args()

    if not args.raw_root or not args.raw_root.is_dir() or not args.result_root:
        print("[!] Errore critico: RAW_ROOT o RESULT_ROOT non configurati correttamente.", file=sys.stderr)
        sys.exit(1)

    csv_out_path = Path("custom_out") / "ground_truths.csv"

    # Risoluzione dell'intervallo degli ID a livello del Main
    ids_to_process = []
    if args.all:
        ids_to_process = sorted([d.name for d in args.raw_root.iterdir() if d.is_dir() and d.name.startswith("ID_")],
                                key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else x)
        print(f"[*] Rilevati automaticamente {len(ids_to_process)} gruppi.")
    elif args.range:
        try:
            start_idx, end_idx = map(int, args.range.split('-'))
            ids_to_process = [f"ID_{i}" for i in range(start_idx, end_idx + 1)]
        except ValueError:
            print("[!] Errore: Il formato del range deve essere START-END (es: 0-5)", file=sys.stderr)
            sys.exit(1)
    else:
        if not args.id:
            print("[!] Errore: Nessun ID fornito tramite flag o variabile d'ambiente.", file=sys.stderr)
            sys.exit(1)
        ids_to_process = [args.id]

    # ITERAZIONE DELEGATA AL MAIN (Le funzioni core ricevono un solo ID alla volta)
    processed_count = 0
    for current_id in ids_to_process:
        try:
            id_data = get_all_synchronization_data(args.raw_root, current_id)
            print_single_report(current_id, id_data)
            save_single_id_to_csv(current_id, id_data, csv_out_path)
            processed_count += 1
        except Exception as e:
            print(f"[!] Saltato {current_id} a causa di un errore di elaborazione: {e}", file=sys.stderr)

    print(f"[+] Elaborazione completata. Aggiornati {processed_count} record in {csv_out_path}")

if __name__ == "__main__":
    main()