#!/usr/bin/env python3
"""
ground_truth_extractor.py

Modulo per l'estrazione automatica del Ground Truth di sincronizzazione.
Utilizza il Metodo 1 (Template Matching basato su OpenCV) per identificare l'esatto
frame di inizio del video sincronizzato all'interno del video originale grezzo.
Scongiura gli errori derivati dai tagli asimmetrici effettuati in coda ai video.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional, Any

import cv2
import numpy as np

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
    # Restituisce il file più grande (assume sia il video e non file spuri)
    return max(candidates, key=lambda f: f.stat().st_size)


def find_synchronized_video(id_dir: Path, view: str) -> Optional[Path]:
    """Cerca il video sincronizzato di riferimento nella root dell'ID (es. ID_0/TOP_synchronized.mp4)."""
    candidates = [f for f in id_dir.glob(f"{view}_synchronized*") if f.suffix.lower() in [".mp4", ".mov", ".avi"]]
    return candidates[0] if candidates else None


def find_exact_start_cut_seconds(orig_path: Path, sync_path: Path, max_search_seconds: float = 60.0) -> float:
    """
    METODO 1 - VERSIONE SENZA COMPROMESSI: MINIMO GLOBALE SULLA ROI CENTRAL
    Rimuove completamente l'early stopping. Scansiona l'intera timeline per trovare
    il punto di minimo assoluto della differenza, risolvendo i match ciclici/ripetitivi.
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
    
    # ROI Centrale (manteniamo il focus sull'area dell'azione)
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
        
        # CRUCIALE: Memorizziamo il record ma NON interrompiamo il ciclo.
        # Vogliamo trovare l'istante in cui la differenza tocca il fondo assoluto del grafico.
        if mean_diff < min_difference:
            min_difference = mean_diff
            best_match_frame = count
            
        count += 1
        
    cap_orig.release()
    
    anchor_seconds_in_orig = best_match_frame / orig_fps
    real_start_seconds_in_orig = anchor_seconds_in_orig - anchor_seconds
    
    return -real_start_seconds_in_orig


def get_durations(root_path: str | Path, ids: list[str]) -> dict[str, dict[str, dict[str, float]]]:
    """
    Analizza la struttura delle cartelle del dataset ed estrae i tagli iniziali 
    esatti (in secondi) tramite Template Matching visivo.
    """
    root = Path(root_path)
    dataset_cuts = {}
    
    for id_name in ids:
        id_dir = root / id_name
        if not id_dir.is_dir():
            continue
            
        print(f"[*] Calcolo visivo Ground Truth per {id_name} via Template Matching...")
        dataset_cuts[id_name] = {}
        
        for view in VIEWS:
            orig_video = find_original_video(id_dir, view)
            sync_video = find_synchronized_video(id_dir, view)
            
            if orig_video and sync_video:
                # Esecuzione dell'allineamento tramite immagini
                diff_val = find_exact_start_cut_seconds(orig_video, sync_video)
                print(f"    - Vista {view:4s} | Allineata al secondo: {abs(diff_val):.2f}s del file originale")
            else:
                diff_val = 0.0
                print(f"    - Vista {view:4s} | [Attenzione] File originali o sincronizzati mancanti.")
                
            dataset_cuts[id_name][view] = {
                "orig_dur": 0.0,  # Lasciati per retrocompatibilità di struttura con i moduli successivi
                "sync_dur": 0.0,
                "diff": diff_val  # Contiene l'esatto taglio iniziale calcolato sui frame
            }
                
    return dataset_cuts


def get_pairwise_offsets(durations: dict[str, dict[str, dict[str, float]]]) -> dict[str, dict[str, float]]:
    """Calcola i ritardi relativi (pairwise) tra le coppie di telecamere."""
    pairwise_offsets = {}
    for id_name, views_data in durations.items():
        pairwise_offsets[id_name] = {}
        
        t_top = views_data.get("TOP", {}).get("diff", 0.0)
        t_tpv = views_data.get("TPV", {}).get("diff", 0.0)
        t_fpv = views_data.get("FPV", {}).get("diff", 0.0)
        
        pairwise_offsets[id_name]["TOP__TPV"] = t_tpv - t_top 
        pairwise_offsets[id_name]["TOP__FPV"] = t_fpv - t_top  
        pairwise_offsets[id_name]["TPV__FPV"] = t_fpv - t_tpv
        
    return pairwise_offsets


def get_global_offsets(pairwise: dict[str, dict[str, dict[str, float]]]) -> dict[str, dict[str, float]]:
    """Calcola gli offset globali impostando la telecamera TPV come perno fisso (0.0)."""
    global_offsets = {}
    for id_name, views_data in pairwise.items():
        global_offsets[id_name] = {}
        
        t_top_tpv = views_data.get("TOP__TPV", 0.0)
        t_tpv = 0.0
        t_tpv_fpv = views_data.get("TPV__FPV", 0.0)
        
        global_offsets[id_name]["TPV"] = t_tpv
        global_offsets[id_name]["TOP"] = t_top_tpv - t_tpv
        global_offsets[id_name]["FPV"] = t_tpv - t_tpv_fpv
        
    return global_offsets


def get_all_synchronization_data(root_path: str | Path, ids: list[str]) -> dict[str, dict[str, Any]]:
    """Funzione omnicomprensiva richiamabile dagli altri script (metriche e ispezione)."""
    durations = get_durations(root_path, ids)
    print(durations)
    print("===============================")
    pairwise = get_pairwise_offsets(durations)
    print(pairwise)
    print("===============================")
    glob = get_global_offsets(pairwise)
    print(glob)
    print("===============================")
    
    complete_dataset = {}
    for id_name in durations.keys():
        complete_dataset[id_name] = {
            "tagli_iniziali_secondi": {v: durations[id_name][v]["diff"] for v in VIEWS},
            "pairwise_offsets_secondi": pairwise[id_name],
            "global_offsets_secondi": glob[id_name]
        }
    return complete_dataset


def format_seconds(seconds: float) -> str:
    """Formatta i secondi in un formato leggibile mm:ss."""
    abs_secs = abs(seconds)
    minutes = int(abs_secs // 60)
    secs = int(abs_secs % 60)
    sign = "-" if seconds < 0 else "+"
    return f"{sign}{minutes:02d}:{secs:02d}"


def print_synchronization_report(dataset_data: dict[str, dict[str, Any]]):
    """Stampa a schermo una tabella accademica riassuntiva dei Ground Truth calcolati."""
    for id_name, data in dataset_data.items():
        print("\n=========================================================================")
        print(f" GROUND TRUTH DI SINCRONIZZAZIONE (METODO 1 - IMAGES): {id_name}")
        print("=========================================================================")
        print(" [1] TAGLIO INIZIALE RISPETTO AI VIDEO ORIGINALI:")
        for view in VIEWS:
            cut = data["tagli_iniziali_secondi"][view]
            print(f"     Vista {view:4s} -> Inizio rilevato a: {abs(cut):.2f} secondi ({format_seconds(cut)})")
            
        print("\n [2] OFFSET PAIRWISE RELATIVI (Ritardi tra coppie):")
        for pair, val in data["pairwise_offsets_secondi"].items():
            print(f"     Coppia {pair:8s} -> Differenza: {val:+.2f}s")
            
        print("\n [3] OFFSET GLOBALI CONVERGENTI (Riferimento Pivot TPV = 0.0):")
        for view in VIEWS:
            val = data["global_offsets_secondi"][view]
            print(f"     Vista {view:4s} -> Offset GT Globale: {val:+.2f}s")
        print("=========================================================================")


def main():
    # Estrazione automatica dalle variabili d'ambiente esportate nel tuo tmux
    raw_root = os.environ.get("RAW_ROOT")
    group_id = os.environ.get("GROUP")
    
    if not raw_root or not group_id:
        print("[!] Errore: Assicurati che le variabili d'ambiente RAW_ROOT e GROUP siano impostate.", file=sys.stderr)
        print("    Esempio manuale: export RAW_ROOT='...' e export GROUP='ID_0'", file=sys.stderr)
        sys.exit(1)
        
    # Esecuzione sul singolo ID corrente
    sync_data = get_all_synchronization_data(raw_root, [group_id])
    print_synchronization_report(sync_data)


if __name__ == "__main__":
    main()