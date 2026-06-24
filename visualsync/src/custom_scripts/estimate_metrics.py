#!/usr/bin/env python3
"""
estimate_metrics.py

Modulo scientifico per il calcolo delle metriche di validazione (Mean Error, 
Median Error, Accuracy@K, AUC) confrontando le predizioni del modello 
(global_offsets.csv) con il Ground Truth calcolato da ground_truth_extractor.

Sfrutta nativamente le variabili d'ambiente del progetto (RAW_ROOT, RESULT_ROOT, GROUP, FPS)
sia in modalità autonoma che integrata.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional, Any

import numpy as np
import pandas as pd

# Importiamo la funzione dal modulo ground_truth_extractor
try:
    from ground_truth_extractor import get_all_synchronization_data
except ImportError:
    print("[!] Errore: Assicurati che 'ground_truth_extractor.py' sia nella stessa cartella o nel PYTHONPATH.", 
          file=sys.stderr)
    sys.exit(1)


def sanitize_float_value(val: Any) -> float:
    """
    Sanitizza un valore di input convertendolo in float.
    Se il valore è None, NaN, stringa vuota o non numerico, restituisce 0.0.
    """
    if val is None:
        return 0.0
    try:
        if isinstance(val, (float, np.floating)) and (np.isnan(val) or pd.isna(val)):
            return 0.0
        if isinstance(val, str):
            val_clean = val.strip().lower()
            if val_clean in ["nan", "none", "", "null"]:
                return 0.0
        return float(val)
    except (ValueError, TypeError):
        return 0.0

# --------------------------------------------------------------------------- #
# CORE API: Caricamento Output Modello e Calcolo
# --------------------------------------------------------------------------- #

def load_model_predictions(result_root: str | Path) -> Optional[dict[str, float]]:
    """
    Carica il file global_offsets.csv generato dal modello, mappando i nomi dei
    video (es. 'ID_0_cam_top_000_150') nelle viste standard ('TOP', 'FPV', 'TPV').
    """
    csv_path = Path(result_root) / "global_offsets.csv"
    
    if not csv_path.is_file():
        return None
        
    try:
        df = pd.read_csv(csv_path)
        # Pulizia spazi bianchi dai nomi delle colonne
        df.columns = df.columns.str.strip()
        
        # Validazione colonne specifiche basate sulla struttura reale
        if 'video' not in df.columns or 'global_offset_frames' not in df.columns:
            print(f"  [!] Struttura colonne CSV non attesa in {csv_path}. Colonne trovate: {list(df.columns)}", file=sys.stderr)
            return None
            
        preds_pulite = {}
        
        for _, row in df.iterrows():
            video_name = str(row['video']).lower().strip()
            offset_val = float(row['global_offset_frames'])
            
            offset_val = sanitize_float_value(row['global_offset_frames'])
            
            # Mappatura fuzzy basata sulle stringhe del CSV reale
            if "top" in video_name:
                preds_pulite["TOP"] = offset_val
            elif "fpv" in video_name:
                preds_pulite["FPV"] = offset_val
            elif "tpv" in video_name:
                preds_pulite["TPV"] = offset_val
                
        return preds_pulite if preds_pulite else None

    except Exception as e:
        print(f"  [!] Errore nel parsing di {csv_path}: {e}", file=sys.stderr)
        return None


def compute_metrics(raw_root: str | Path, result_root: str | Path, id_name: str, fps: float, max_auc_tau: float = 2000.0) -> dict[str, Any]:
    """
    Esegue il core logico del calcolo confrontando il Ground Truth (in secondi)
    convertito in frame con le predizioni del modello (in frame).
    """
    # 1. Recupero Ground Truth originale
    gt_dataset = get_all_synchronization_data(raw_root, [id_name])
    if id_name not in gt_dataset:
        return {"success": False, "msg": f"Impossibile calcolare il GT per {id_name}. Verifica i video in {raw_root}."}
        
    # 2. Caricamento Predizioni grezze dal modello
    preds_frame_raw = load_model_predictions(result_root)
    if preds_frame_raw is None:
        return {"success": False, "msg": f"File 'global_offsets.csv' non trovato o malformato in {result_root}."}
        
    # === SANITIZZAZIONE ESTRATTIVA (SENZA CAMBIARE I SEGNI ORIGINALI) ===
    # Forziamo a 0.0 qualsiasi valore mancante o NaN per evitare la propagazione nei calcoli
    preds_pulite = {}
    for view in ["TOP", "FPV", "TPV"]:
        raw_pred = preds_frame_raw.get(view, 0.0)
        preds_pulite[view] = sanitize_float_value(raw_pred)
        
    gt_sec_raw = gt_dataset[id_name].get("global_offsets_secondi", {})
    gt_pulito = {}
    for view in ["TOP", "FPV", "TPV"]:
        raw_gt = gt_sec_raw.get(view, 0.0)
        gt_pulito[view] = sanitize_float_value(raw_gt)

    # Riassegniamo alle variabili usate dalla tua formula originale
    gt_sec = gt_pulito
    preds_frame = preds_pulite

    id_errors_ms = {}
    all_errors_ms = []
    
    # Valutiamo le viste non-pivot (TOP e FPV) rispetto alla vista perno TPV
    for view in ["TOP", "FPV"]:
        # Rimosso il controllo rigido "if view not in..." poiché ora la presenza a 0.0 è garantita
            
        # FORMULA MATEMATICA ORIGINALE DI CONVERSIONE E CONFRONTO (Segni invariati)
        gt_frame_val = gt_sec[view] * fps
        pred_frame_val = preds_frame[view]
        
        # Errore assoluto in frame
        err_frame = abs(pred_frame_val - gt_frame_val)
        
        # Conversione finale in Millisecondi
        err_ms = (err_frame / fps) * 1000
        
        id_errors_ms[view] = err_ms
        all_errors_ms.append(err_ms)
        
    if not all_errors_ms:
        return {"success": False, "msg": "Nessuna corrispondenza trovata tra le viste del GT e le predizioni del modello."}
        
    # === AGGREGAZIONE STATISTICA ===
    errors = np.array(all_errors_ms)
    mean_error = np.mean(errors)
    median_error = np.median(errors)
    
    # Accuracy @ K ms
    a_100 = np.mean(errors <= 100.0) * 100
    a_500 = np.mean(errors <= 500.0) * 100
    
    # AUC (Area Under Curve) via metodo dei trapezi (0-2000 ms)
    thresholds = np.linspace(0, max_auc_tau, int(max_auc_tau) + 1)
    accuracies = [np.mean(errors <= t) for t in thresholds]
    auc = np.trapz(accuracies, thresholds) / max_auc_tau
    
    return {
        "success": True,
        "id_name": id_name,
        "fps": fps,
        "metrics": {
            "mean_error_ms": mean_error,
            "median_error_ms": median_error,
            "A@100ms": a_100,
            "A@500ms": a_500,
            "AUC": auc
        },
        "details": {
            "views": id_errors_ms,
            "gt_seconds": gt_sec,
            "pred_frames": preds_frame
        }
    }


# --------------------------------------------------------------------------- #
# CLI Mode (Interfaccia da Terminale)
# --------------------------------------------------------------------------- #

def main():
    # Recupero dinamico dalle variabili d'ambiente correnti
    env_raw_root = os.environ.get("RAW_ROOT")
    env_result_root = os.environ.get("RESULT_ROOT")
    env_group = os.environ.get("GROUP")
    env_fps = os.environ.get("FPS")
    
    default_fps = float(env_fps) if env_fps else 20.0

    parser = argparse.ArgumentParser(
        description="Calcolo metriche scientifiche di sincronizzazione per il dataset PRIN.")
    
    parser.add_argument("--raw_root", type=Path, default=env_raw_root,
                        help=f"Path dataset video originale. Default da env: {env_raw_root}")
    parser.add_argument("--result_root", type=Path, default=env_result_root,
                        help=f"Path cartella output del modello (RESULT_ROOT). Default da env: {env_result_root}")
    parser.add_argument("--id", type=str, default=env_group,
                        help=f"ID dell'esperimento (GROUP). Default da env: {env_group}")
    parser.add_argument("--fps", type=float, default=default_fps,
                        help=f"Frame rate del test. Default da env: {default_fps}")
    
    args = parser.parse_args()

    if not args.raw_root:
        parser.error("Manca il percorso raw_root. Esporta RAW_ROOT o usa --raw_root")
    if not args.result_root:
        parser.error("Manca il percorso result_root. Esporta RESULT_ROOT o usa --result_root")
    if not args.id:
        parser.error("Manca l'ID dell'esperimento. Esporta GROUP o usa --id")

    print(f"[*] Estrazione Metriche per l'esperimento: {args.id}")
    print(f"[*] Cartella Output Modello: {args.result_root}")
    print(f"[*] Configurazione temporale: {args.fps} FPS")

    res = compute_metrics(args.raw_root, args.result_root, args.id, args.fps)

    if not res["success"]:
        print(f"[!] Errore: {res['msg']}", file=sys.stderr)
        sys.exit(1)

    metrics = res["metrics"]
    dt = res["details"]

    print("\n=========================================================================")
    print(f"   REPORT DI VALUTAZIONE SCIENTIFICA: {res['id_name']} (@ {res['fps']} FPS)")
    print("=========================================================================")
    
    print(" [A] CONFRONTO DIRETTO DEI FRAME:")
    for view in ["TOP", "FPV"]:
        if view in dt["gt_seconds"] and view in dt["pred_frames"]:
            gt_s = dt["gt_seconds"][view]
            gt_f = gt_s * args.fps
            pred_f = dt["pred_frames"][view]
            err_ms = dt["views"][view]
            print(f"   {view:4s} | GT: {gt_s:+.2f}s ({gt_f:+.1f} f) | Pred: {pred_f:+.1f} f | Errore: {err_ms:.2f} ms")

    print("\n [B] METRICHE COMPLESSIVE DEL PAPER (VisualSync):")
    print(f"   Errore Medio (Mean Error):     {metrics['mean_error_ms']:.2f} ms")
    print(f"   Errore Mediano (Median Error):  {metrics['median_error_ms']:.2f} ms")
    print(f"   Accuratezza @ 100ms (A@100ms): {metrics['A@100ms']:.1f}%")
    print(f"   Accuratezza @ 500ms (A@500ms): {metrics['A@500ms']:.1f}%")
    print(f"   Area Sotto la Curva (AUC):     {metrics['AUC']:.4f}")
    print("=========================================================================")


if __name__ == "__main__":
    main()