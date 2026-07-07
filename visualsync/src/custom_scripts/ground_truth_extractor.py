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

import json
import os
import subprocess
import sys
import argparse
from pathlib import Path
from typing import Optional, Any

import cv2
import numpy as np
import pandas as pd

# Configurazione delle viste del dataset PRIN
VIEWS = ["TOP", "TPV", "FPV"]

# Sotto questa soglia (second_best_mae / min_mae) il match viene considerato
# ambiguo: esistono candidati quasi equivalenti al migliore, quindi il
# risultato va verificato manualmente prima di fidarsene.
AMBIGUITY_THRESHOLD = 1.05


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
    candidates = [f for f in id_dir.glob(f"{view}_synchronized.*") if f.suffix.lower() in [".mp4", ".mov", ".avi"]]
    return candidates[0] if candidates else None


def probe_video_encoding(path: Path) -> dict[str, Any]:
    """
    Ispeziona un video con ffprobe per verificare fps reale, framerate
    variabile (VFR) e distanza tra keyframe (GOP). Utile in fase di debug
    per capire se un video "difficile" ha caratteristiche di codifica
    diverse dagli altri che potrebbero rendere inaffidabile il seek.
    Richiede ffprobe (parte di ffmpeg) installato sul sistema.
    """
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate,avg_frame_rate,nb_frames,codec_name",
        "-show_entries", "frame=pict_type",
        "-of", "json",
        str(path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        data = json.loads(result.stdout)
    except Exception as e:
        return {"error": str(e)}

    stream_info = data.get("streams", [{}])[0] if data.get("streams") else {}
    pict_types = [f.get("pict_type") for f in data.get("frames", [])]
    n_keyframes = pict_types.count("I")
    total_frames = len(pict_types)

    r_fr = stream_info.get("r_frame_rate")
    avg_fr = stream_info.get("avg_frame_rate")

    return {
        "codec": stream_info.get("codec_name"),
        "r_frame_rate": r_fr,
        "avg_frame_rate": avg_fr,
        "vfr_suspect": (r_fr != avg_fr) if (r_fr and avg_fr) else None,
        "n_keyframes": n_keyframes,
        "total_frames_sampled": total_frames,
        "avg_gop_size": (total_frames / n_keyframes) if n_keyframes else None,
    }


def _read_frame_sequential(cap: cv2.VideoCapture, target_idx: int, current_idx: int):
    """
    Legge in sequenza (senza cap.set()) fino a raggiungere target_idx.
    Ritorna (frame, nuovo_current_idx). cap.set() puo' posizionarsi sul
    keyframe piu' vicino invece che sul frame esatto su alcuni codec/GOP:
    la lettura sequenziale evita questo rischio per la firma di movimento,
    che deve essere esatta al singolo frame.
    """
    frame = None
    while current_idx <= target_idx:
        ret, f = cap.read()
        if not ret:
            return None, current_idx
        frame = f
        current_idx += 1
    return frame, current_idx


def find_exact_start_cut_seconds(
    orig_path: Path,
    sync_path: Path,
    max_search_seconds: float = 60.0,
    debug_dir: Optional[Path] = None,
) -> dict[str, Any]:
    """
    Trova l'istante di taglio iniziale identificando AUTOMATICAMENTE il picco di massimo
    movimento nel video sincronizzato, usandolo come firma dinamica per il matching nell'originale.

    Ritorna un dizionario per portare con sé anche
    la confidenza del match:
        {
            "offset_seconds": float,
            "min_mae": float | None,
            "second_best_mae": float | None,
            "confidence_ratio": float | None,   # second_best / best, piu' alto = piu' affidabile
            "ambiguous": bool,                  # True se confidence_ratio < AMBIGUITY_THRESHOLD
            "anchor_seconds": float,
            "best_match_frame": int,
        }
    """
    empty_result = {
        "offset_seconds": 0.0, "min_mae": None, "second_best_mae": None,
        "confidence_ratio": None, "ambiguous": True,
        "anchor_seconds": 0.0, "best_match_frame": 0,
    }

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
        return empty_result
    gray_prev_s = cv2.cvtColor(prev_f, cv2.COLOR_BGR2GRAY)

    # Scansione frame-by-frame per trovare il punto a massima energia cinetica
    for idx in range(1, search_sync_frames):
        ret, curr_f = cap_sync.read()
        if not ret:
            break
        gray_curr_s = cv2.cvtColor(curr_f, cv2.COLOR_BGR2GRAY)

        # Sottrazione consecutiva
        diff = cv2.absdiff(gray_curr_s, gray_prev_s)
        energy = np.mean(diff)
        motion_energies.append((energy, idx))
        gray_prev_s = gray_curr_s

    if not motion_energies:
        cap_sync.release()
        return empty_result

    # Isoliamo il frame di picco assoluto e convertiamo in secondi
    best_sync_energy, anchor_frame_sync = max(motion_energies, key=lambda x: x[0])
    anchor_seconds = anchor_frame_sync / sync_fps

    # Estraiamo la firma del movimento in quel picco usando una finestra stabile di 3 frame.
    frame_idx_b = anchor_frame_sync + 3
    cap_sync.release()
    cap_sync = cv2.VideoCapture(str(sync_path))
    frame_a, cur_idx = _read_frame_sequential(cap_sync, anchor_frame_sync, 0)
    frame_b, cur_idx = _read_frame_sequential(cap_sync, frame_idx_b, cur_idx)
    cap_sync.release()

    if frame_a is None or frame_b is None:
        return {**empty_result, "anchor_seconds": anchor_seconds}

    motion_sync = cv2.absdiff(cv2.cvtColor(frame_a, cv2.COLOR_BGR2GRAY), cv2.cvtColor(frame_b, cv2.COLOR_BGR2GRAY))
    h, w = motion_sync.shape[:2]

    # Ritaglio della ROI centrale per focalizzarci sullo scaffale/interazione
    start_y, end_y = int(h * 0.15), int(h * 0.85)
    start_x, end_x = int(w * 0.15), int(w * 0.85)
    roi_motion_sync = motion_sync[start_y:end_y, start_x:end_x]

    print(f"    [Auto-Anchor] Vista {sync_path.name.split('_')[1]}: Picco di movimento rilevato a {anchor_seconds:.2f}s")

    if debug_dir is not None:
        debug_dir = Path(debug_dir)
        debug_dir.mkdir(parents=True, exist_ok=True)
        tag = sync_path.stem
        cv2.imwrite(str(debug_dir / f"{tag}_sync_frame_a.png"), frame_a)
        cv2.imwrite(str(debug_dir / f"{tag}_sync_frame_b.png"), frame_b)
        cv2.imwrite(str(debug_dir / f"{tag}_sync_motion_roi.png"), roi_motion_sync)

    # =========================================================================
    # FASE 2: RICERCA DELLA STESSA FIRMA DI MOVIMENTO NEL VIDEO ORIGINALE GREZZO
    # =========================================================================
    cap_orig = cv2.VideoCapture(str(orig_path))
    orig_fps = cap_orig.get(cv2.CAP_PROP_FPS) or 30.0

    # Limitiamo il range di ricerca iniziale a max_search_seconds per escludere code spurie
    max_search_frames = int(max_search_seconds * orig_fps)

    best_match_frame = 0
    min_mae = float('inf')
    best_orig_frame_a = None
    best_orig_frame_b = None

    frame_count = 0
    frame_buffer = []
    all_maes: list[tuple[float, int]] = []

    BUFFER_SIZE = 4
    GAP = BUFFER_SIZE - 1

    while frame_count < max_search_frames:
        ret, curr_frame = cap_orig.read()
        if not ret:
            break

        gray_curr = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
        if gray_curr.shape[:2] != (h, w):
            gray_curr = cv2.resize(gray_curr, (w, h))

        frame_buffer.append(gray_curr)

        # Manteniamo la finestra a 4 frame  coerente col sincronizzato
        if len(frame_buffer) >= BUFFER_SIZE:
            gray_anchor_orig = frame_buffer[0]
            gray_target_orig = frame_buffer[-1]
            frame_buffer.pop(0)

            motion_orig = cv2.absdiff(gray_anchor_orig, gray_target_orig)
            roi_motion_orig = motion_orig[start_y:end_y, start_x:end_x]

            # Calcolo della Mean Absolute Error (MAE) sulla dinamica
            mae = np.mean(cv2.absdiff(roi_motion_sync, roi_motion_orig))
            matched_idx = frame_count - GAP
            all_maes.append((mae, matched_idx))

            if mae < min_mae:
                min_mae = mae
                # Allineamento matematico dell'indice compensando la lunghezza del buffer
                best_match_frame = matched_idx
                best_orig_frame_a = gray_anchor_orig
                best_orig_frame_b = gray_target_orig

        frame_count += 1

    cap_orig.release()

    # Metrica di confidenza
    second_best_mae = None
    confidence_ratio = None
    ambiguous = True
    if all_maes:
        exclusion_window = max(1, int(orig_fps))
        far_candidates = [m for m, idx in all_maes if abs(idx - best_match_frame) > exclusion_window]
        if far_candidates:
            second_best_mae = min(far_candidates)
            if min_mae > 0:
                confidence_ratio = second_best_mae / min_mae
                ambiguous = confidence_ratio < AMBIGUITY_THRESHOLD

    if debug_dir is not None and best_orig_frame_a is not None:
        tag = orig_path.stem
        cv2.imwrite(str(debug_dir / f"{tag}_orig_match_frame_a.png"), best_orig_frame_a)
        cv2.imwrite(str(debug_dir / f"{tag}_orig_match_frame_b.png"), best_orig_frame_b)

    # Calcolo dell'offset reale di taglio
    anchor_timestamp_in_orig = best_match_frame / orig_fps
    real_start_cut_seconds = anchor_timestamp_in_orig - anchor_seconds

    if ambiguous:
        print(f"    [WARNING] Match ambiguo per {orig_path.name}: "
              f"confidence_ratio={confidence_ratio}. Verifica manualmente (--debug_dir).")

    return {
        "offset_seconds": -real_start_cut_seconds,
        "min_mae": float(min_mae) if min_mae != float('inf') else None,
        "second_best_mae": float(second_best_mae) if second_best_mae is not None else None,
        "confidence_ratio": float(confidence_ratio) if confidence_ratio is not None else None,
        "ambiguous": ambiguous,
        "anchor_seconds": anchor_seconds,
        "best_match_frame": best_match_frame,
    }


def get_durations(root_path: str | Path, id_name: str, debug_dir: Optional[Path] = None) -> dict[str, dict[str, Any]]:
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
            view_debug_dir = (Path(debug_dir) / id_name) if debug_dir is not None else None
            match_result = find_exact_start_cut_seconds(orig_video, sync_video, debug_dir=view_debug_dir)
            diff_val = match_result["offset_seconds"]
            conf_str = f"{match_result['confidence_ratio']:.2f}" if match_result['confidence_ratio'] is not None else "n/d"
            flag = " [AMBIGUO]" if match_result["ambiguous"] else ""
            print(f"    - Vista {view:4s} | Allineata al secondo: {abs(diff_val):.2f}s del file originale "
                  f"(confidenza: {conf_str}){flag}")
        else:
            diff_val = 0.0
            match_result = {"confidence_ratio": None, "ambiguous": True, "min_mae": None}
            print(f"    - Vista {view:4s} | [Attenzione] File originali o sincronizzati mancanti.")
            
        views_data[view] = {
            "orig_dur": 0.0,
            "sync_dur": 0.0,
            "diff": diff_val,
            "confidence_ratio": match_result["confidence_ratio"],
            "ambiguous": match_result["ambiguous"],
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


def get_all_synchronization_data(root_path: str | Path, id_name: str, debug_dir: Optional[Path] = None) -> dict[str, Any]:
    """Funzione atomica omnicomprensiva per preservare la retrocompatibilità con altri script."""
    durations = get_durations(root_path, id_name, debug_dir=debug_dir)
    pairwise = get_pairwise_offsets(durations)
    glob = get_global_offsets(pairwise)

    return {
        "tagli_iniziali_secondi": {v: durations[v]["diff"] for v in VIEWS},
        "pairwise_offsets_secondi": pairwise,
        "global_offsets_secondi": glob,
        "confidence": {v: durations[v]["confidence_ratio"] for v in VIEWS},
        "ambiguous": {v: durations[v]["ambiguous"] for v in VIEWS},
        "any_ambiguous": any(durations[v]["ambiguous"] for v in VIEWS),
    }


def save_single_id_to_csv(id_name: str, single_dataset_data: dict[str, Any], csv_path: Path):
    """
    Inserisce o aggiorna (Upsert) i dati di un singolo ID nel CSV centralizzato.
    """
    glob_offsets = single_dataset_data["global_offsets_secondi"]
    confidence = single_dataset_data.get("confidence", {})
    ambiguous = single_dataset_data.get("ambiguous", {})
    new_row = {
        "id": id_name,
        "top_offset": glob_offsets.get("TOP", 0.0),
        "tpv_offset": 0.0,
        "fpv_offset": glob_offsets.get("FPV", 0.0),
        "top_confidence": confidence.get("TOP"),
        "tpv_confidence": confidence.get("TPV"),
        "fpv_confidence": confidence.get("FPV"),
        "flagged": bool(single_dataset_data.get("any_ambiguous", False)),
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

    if data.get("any_ambiguous"):
        print("\n [!] ATTENZIONE - MATCH AMBIGUI RILEVATI:")
        for view in VIEWS:
            if data.get("ambiguous", {}).get(view):
                conf = data.get("confidence", {}).get(view)
                conf_str = f"{conf:.2f}" if conf is not None else "n/d"
                print(f"     Vista {view:4s} -> confidence_ratio={conf_str} (soglia: {AMBIGUITY_THRESHOLD}). "
                      f"Verificare manualmente, es. con --debug_dir.")
    print("=========================================================================\n")


def main():
    raw_root_env = os.environ.get("RAW_ROOT")
    result_root_env = os.environ.get("RESULT_ROOT")
    group_env = os.environ.get("GROUP")
    
    parser = argparse.ArgumentParser(description="Estrattore Ground Truth Dataset PRIN con pipeline atomica.")
    parser.add_argument("--raw_root", type=Path, default=raw_root_env)
    parser.add_argument("--result_root", type=Path, default=result_root_env)
    parser.add_argument("--debug_dir", type=Path, default=None,
                         help="Se fornita, salva per ogni ID i frame usati per il matching "
                              "(firma sync + frame corrispondente nell'originale) per ispezione visiva.")
    
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
            id_data = get_all_synchronization_data(args.raw_root, current_id, debug_dir=args.debug_dir)
            print_single_report(current_id, id_data)
            save_single_id_to_csv(current_id, id_data, csv_out_path)
            processed_count += 1
        except Exception as e:
            print(f"[!] Saltato {current_id} a causa di un errore di elaborazione: {e}", file=sys.stderr)

    print(f"[+] Elaborazione completata. Aggiornati {processed_count} record in {csv_out_path}")

if __name__ == "__main__":
    main()