#!/usr/bin/env python3
"""
ground_truth_extractor.py

Modulo ottimizzato per l'estrazione automatica del Ground Truth di sincronizzazione.
Risolve l'aliasing temporale e i falsi positivi causati dagli sfondi statici (scaffali)
tramite l'algoritmo Auto-Anchor Motion Gradient Matching.

Sincronizza i video grezzi identificando il picco di massimo movimento nel video 
sincronizzato e cercandone la firma dinamica nell'originale.
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
    """Cerca il video originale all'interno della sottocartella della vista (es. ID_0/TOP/)."""
    view_dir = id_dir / view
    if not view_dir.is_dir():
        return None
    candidates = [f for f in view_dir.glob("*") if f.suffix.lower() in [".mp4", ".mov", ".avi"]]
    if not candidates:
        return None
    # Restituisce il file più grande (esclude file spuri o thumbnail)
    return max(candidates, key=lambda f: f.stat().st_size)

def find_synchronized_video(id_dir: Path, view: str) -> Optional[Path]:
    """Cerca il video sincronizzato di riferimento nella root dell'ID."""
    candidates = [f for f in id_dir.glob(f"*{view}_synchronized*") if f.suffix.lower() in [".mp4", ".mov", ".avi"]]
    return candidates[0] if candidates else None

def calculate_exact_cut_seconds(orig_path: Path, sync_path: Path, max_search_seconds: float = 45.0) -> float:
    """
    Trova l'istante di taglio iniziale identificando AUTOMATICAMENTE il picco di massimo
    movimento nel video sincronizzato, usandolo come firma dinamica per il matching nell'originale.
    """
    # =========================================================================
    # FASE 1: RILEVAMENTO DEL PICCO DI MOVIMENTO NEL SINCRONIZZATO (Auto-Anchor)
    # =========================================================================
    cap_sync = cv2.VideoCapture(str(sync_path))
    sync_fps = cap_sync.get(cv2.CAP_PROP_FPS) or 30.0
    
    # Analizziamo i primi 30 secondi del video sincronizzato per cercare l'azione
    search_sync_frames = int(min(30.0 * sync_fps, cap_sync.get(cv2.CAP_PROP_FRAME_COUNT) - 5))
    
    motion_energies = []
    ret, prev_f = cap_sync.read()
    if not ret:
        cap_sync.release()
        return 0.0
    gray_prev_s = cv2.cvtColor(prev_f, cv2.COLOR_BGR2GRAY)
    
    # Scansione frame-by-frame per trovare il punto a massima energia cinetica
    for idx in range(1, search_sync_frames):
        ret, curr_f = cap_sync.read()
        if not ret:
            break
        gray_curr_s = cv2.cvtColor(curr_f, cv2.COLOR_BGR2GRAY)
        
        # Sottrazione consecutiva (rimane acceso solo ciò che si muove)
        diff = cv2.absdiff(gray_curr_s, gray_prev_s)
        energy = np.mean(diff)
        motion_energies.append((energy, idx))
        gray_prev_s = gray_curr_s
        
    if not motion_energies:
        cap_sync.release()
        return 0.0
        
    # Isoliamo il frame di picco assoluto e convertiamo in secondi
    best_sync_energy, anchor_frame_sync = max(motion_energies, key=lambda x: x[0])
    anchor_seconds = anchor_frame_sync / sync_fps
    
    # Estraiamo la firma del movimento in quel picco usando una finestra stabile di 3 frame
    frame_idx_b = anchor_frame_sync + 3
    cap_sync.set(cv2.CAP_PROP_POS_FRAMES, anchor_frame_sync)
    _, frame_a = cap_sync.read()
    cap_sync.set(cv2.CAP_PROP_POS_FRAMES, frame_idx_b)
    _, frame_b = cap_sync.read()
    cap_sync.release()
    
    motion_sync = cv2.absdiff(cv2.cvtColor(frame_a, cv2.COLOR_BGR2GRAY), cv2.cvtColor(frame_b, cv2.COLOR_BGR2GRAY))
    h, w = motion_sync.shape[:2]
    
    # Ritaglio della ROI centrale per focalizzarci sullo scaffale/interazione
    start_y, end_y = int(h * 0.15), int(h * 0.85)
    start_x, end_x = int(w * 0.15), int(w * 0.85)
    roi_motion_sync = motion_sync[start_y:end_y, start_x:end_x]
    
    print(f"    [Auto-Anchor] Vista {sync_path.name.split('_')[1]}: Picco di movimento rilevato a {anchor_seconds:.2f}s")

    # =========================================================================
    # FASE 2: RICERCA DELLA STESSA FIRMA DI MOVIMENTO NEL VIDEO ORIGINALE GREZZO
    # =========================================================================
    cap_orig = cv2.VideoCapture(str(orig_path))
    orig_fps = cap_orig.get(cv2.CAP_PROP_FPS) or 30.0
    
    # Limitiamo il range di ricerca iniziale a 45 secondi per escludere code spurie
    max_search_frames = int(max_search_seconds * orig_fps)
    
    best_match_frame = 0
    min_mae = float('inf')
    
    frame_count = 0
    frame_buffer = []
    
    while frame_count < max_search_frames:
        ret, curr_frame = cap_orig.read()
        if not ret:
            break
            
        gray_curr = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
        if gray_curr.shape[:2] != (h, w):
            gray_curr = cv2.resize(gray_curr, (w, h))
            
        frame_buffer.append(gray_curr)
        
        # Manteniamo la finestra a 3 frame coerente con il video sincronizzato
        if len(frame_buffer) >= 3:
            gray_anchor_orig = frame_buffer[0]
            gray_target_orig = frame_buffer[-1]
            frame_buffer.pop(0)
            
            motion_orig = cv2.absdiff(gray_anchor_orig, gray_target_orig)
            roi_motion_orig = motion_orig[start_y:end_y, start_x:end_x]
            
            # Calcolo della Mean Absolute Error (MAE) sulla dinamica (lo sfondo statico vale 0)
            mae = np.mean(cv2.absdiff(roi_motion_sync, roi_motion_orig))
            
            if mae < min_mae:
                min_mae = mae
                # Allineamento matematico dell'indice compensando la lunghezza del buffer
                best_match_frame = frame_count - 3
                
        frame_count += 1
        
    cap_orig.release()
    
    # Calcolo dell'offset reale di taglio (Ground Truth temporale)
    anchor_timestamp_in_orig = best_match_frame / orig_fps
    real_start_cut_seconds = anchor_timestamp_in_orig - anchor_seconds
    
    return real_start_cut_seconds

def get_durations(root_path: str | Path, ids: list[str]) -> dict[str, dict[str, dict[str, float]]]:
    """Scansiona l'albero delle directory e calcola i punti di taglio per ogni vista."""
    root = Path(root_path)
    dataset_cuts = {}
    
    for id_name in ids:
        id_dir = root / id_name
        if not id_dir.is_dir():
            continue
            
        dataset_cuts[id_name] = {}
        
        for view in VIEWS:
            orig_video = find_original_video(id_dir, view)
            sync_video = find_synchronized_video(id_dir, view)
            
            if orig_video and sync_video:
                cut_val = calculate_exact_cut_seconds(orig_video, sync_video)
            else:
                cut_val = 0.0
                
            dataset_cuts[id_name][view] = {
                "orig_dur": 0.0,  # Retrocompatibilità strutturale
                "sync_dur": 0.0,  # Retrocompatibilità strutturale
                "diff": cut_val
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
        
        pairwise_offsets[id_name]["TOP__TPV"] = t_top - t_tpv
        pairwise_offsets[id_name]["TOP__FPV"] = t_top - t_fpv
        pairwise_offsets[id_name]["TPV__FPV"] = t_tpv - t_fpv
    return pairwise_offsets

def get_global_offsets(durations: dict[str, dict[str, dict[str, float]]]) -> dict[str, dict[str, float]]:
    """Calcola gli offset globali centrati sul perno TPV = 0.0 per la validazione di VisualSync."""
    global_offsets = {}
    for id_name, views_data in durations.items():
        global_offsets[id_name] = {}
        t_top = views_data.get("TOP", {}).get("diff", 0.0)
        t_tpv = views_data.get("TPV", {}).get("diff", 0.0)
        t_fpv = views_data.get("FPV", {}).get("diff", 0.0)
        
        global_offsets[id_name]["TPV"] = 0.0
        global_offsets[id_name]["TOP"] = t_top - t_tpv
        global_offsets[id_name]["FPV"] = t_fpv - t_tpv
    return global_offsets

# =========================================================================
#  INTERFACCIA CRUCIALE PER GLI SCRIPT ESTERNI (COMPATIBILITÀ PIPELINE)
# =========================================================================
def get_all_synchronization_data(root_path: str | Path, ids: list[str]) -> dict[str, dict[str, Any]]:
    """
    Funzione di interfaccia richiamata dagli altri moduli di calcolo metriche.
    Preserva le medesime chiavi associative per evitare regressioni nel codice.
    """
    durations = get_durations(root_path, ids)
    pairwise = get_pairwise_offsets(durations)
    glob = get_global_offsets(durations)
    
    complete_dataset = {}
    for id_name in durations.keys():
        complete_dataset[id_name] = {
            "tagli_iniziali_secondi": {v: durations[id_name][v]["diff"] for v in VIEWS},
            "pairwise_offsets_secondi": pairwise[id_name],
            "global_offsets_secondi": glob[id_name]
        }
    return complete_dataset

def print_synchronization_report(dataset_data: dict[str, dict[str, Any]]):
    """Genera un log strutturato dei Ground Truth calcolati."""
    for id_name, data in dataset_data.items():
        print("\n" + "="*73)
        print(f" GROUND TRUTH DEFINITIVO DI SINCRONIZZAZIONE (MOTION PICCO): {id_name}")
        print("="*73)
        print(" [1] TIMESTAMP DI TAGLIO NEI VIDEO ORIGINALI (GREZZI):")
        for view in VIEWS:
            cut = data["tagli_iniziali_secondi"][view]
            print(f"     Vista {view:4s} -> Inizia al secondo {cut:.2f}s del file grezzo")
            
        print("\n [2] OFFSET PAIRWISE INTER-CAMERA (GT RELATIVO):")
        for pair, val in data["pairwise_offsets_secondi"].items():
            print(f"     Coppia {pair:8s} -> Offset: {val:+.2f}s")
            
        print("\n [3] OFFSET GLOBALI DA MODELLO (Perno TPV = 0.0s):")
        for view in VIEWS:
            val = data["global_offsets_secondi"][view]
            print(f"     Vista {view:4s} -> Offset Globale GT: {val:+.2f}s")
        print("="*73 + "\n")

def main():
    # Fallback automatico sul path locale hard-coded di Windows se lanciato da locale
    default_root = r"C:\Users\giaco\Desktop\Marcucci Giacomo\Università\Corsi\Magistrali\Computer Vision and DL\Progetto\PRIN_DATASET\Video ed Excel"
    raw_root = os.environ.get("RAW_ROOT", default_root)
    group_id = os.environ.get("GROUP")
    
    # Se eseguito localmente (senza variabili d'ambiente esportate), richiede l'input interattivo
    if not os.environ.get("GROUP"):
        print("=== ESECUZIONE LOCALE CON RICERCA DINAMICA DEL PICCO ===")
        target_input = input("Inserisci l'ID del gruppo da elaborare (es: 0 o 4): ").strip()
        if target_input.upper().startswith("ID_"):
            target_input = target_input[3:]
        group_id = f"ID_{target_input}"
    
    root_path = Path(raw_root)
    if not (root_path / group_id).is_dir():
        print(f"[ERRORE] Directory non trovata: {root_path / group_id}", file=sys.stderr)
        return
        
    for gid in 0..18:
        sync_data = get_all_synchronization_data(root_path, [gid])
        print_synchronization_report(sync_data)

if __name__ == "__main__":
    main()