#!/usr/bin/env python3
"""
estimate_metrics.py

Modulo per il calcolo delle metriche di allineamento temporale.
Implementa una logica di controllo sul database CSV: se l'ID manca, invoca 
automaticamente l'estrattore per generare e salvare i dati mancanti.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional, Any

import numpy as np
import pandas as pd

# Importiamo i componenti necessari per il Fallback dinamico
try:
    from ground_truth_extractor import get_all_synchronization_data, save_single_id_to_csv
except ImportError:
    print("[!] Errore: Assicurati che 'ground_truth_extractor.py' sia nel PYTHONPATH.", file=sys.stderr)
    sys.exit(1)


def sanitize_float_value(val: Any) -> float:
    if val is None: return 0.0
    try:
        if isinstance(val, (float, np.floating)) and (np.isnan(val) or pd.isna(val)): return 0.0
        if isinstance(val, str) and val.strip().lower() in ["nan", "none", "", "null"]: return 0.0
        return float(val)
    except (ValueError, TypeError): return 0.0


def load_model_predictions(result_root: str | Path) -> Optional[dict[str, float]]:
    csv_path = Path(result_root) / "global_offsets.csv"
    if not csv_path.is_file(): return None
    try:
        df = pd.read_csv(csv_path)
        df.columns = df.columns.str.strip()
        preds = {}
        for _, row in df.iterrows():
            v_name = str(row['video']).lower().strip()
            val = sanitize_float_value(row['global_offset_frames'])
            if "top" in v_name: preds["TOP"] = val
            elif "fpv" in v_name: preds["FPV"] = val
            elif "tpv" in v_name: preds["TPV"] = val
        return preds if preds else None
    except Exception: return None


def load_gt_or_compute_fallback(raw_root: str | Path, result_root: str | Path, id_name: str) -> Optional[dict[str, float]]:
    """
    LOGICA REQUISITO FONDAMENTALE: Controlla se l'id esiste nel CSV.
    Se non esiste, richiama il ground_truth_extractor per calcolarlo, salvarlo e restituirlo.
    """
    csv_path = Path(result_root) / "ground_truth_metadata.csv"
    
    # Tentativo di lettura da cache CSV
    if csv_path.is_file():
        try:
            df = pd.read_csv(csv_path)
            row = df[df['id'] == id_name]
            if not row.empty:
                return {
                    "TOP": float(row.iloc[0]['top_offset']),
                    "TPV": float(row.iloc[0]['tpv_offset']),
                    "FPV": float(row.iloc[0]['fpv_offset'])
                }
        except Exception as e:
            print(f"  [!] Errore lettura CSV cache ({e}). Procedo al ricalcolo forzato.")

    # FALLBACK ATTIVO: L'ID non esiste o il file manca. Estraiamo al volo.
    print(f"  [!] Cache Miss per '{id_name}' nel CSV. Attivazione dinamica dell'estrattore visivo...")
    try:
        # Calcolo dei dati di sincronizzazione completi
        computed_data = get_all_synchronization_data(raw_root, id_name)
        # Salvataggio immediato sul CSV centralizzato per sanare la situazione futura
        save_single_id_to_csv(id_name, computed_data, csv_path)
        
        # Estraiamo i global offsets appena calcolati per restituirli alla pipeline delle metriche
        glob_offsets = computed_data["global_offsets_secondi"]
        return {
            "TOP": glob_offsets.get("TOP", 0.0),
            "TPV": 0.0,
            "FPV": glob_offsets.get("FPV", 0.0)
        }
    except Exception as e:
        print(f"  [!] Errore critico nel Fallback di estrazione del Ground Truth: {e}", file=sys.stderr)
        return None


def print_metrics_report(res: dict[str, Any]):
    """
    FUNZIONE CENTRALIZZATA DI PRINT DEL REPORT SCIENTIFICO
    Esportabile in run_full_validation.py ed exec_visualsync.py.
    """
    metrics = res["metrics"]
    dt = res["details"]
    
    print("\n=========================================================================")
    print(f"   REPORT DI VALUTAZIONE SCIENTIFICA (LOGICA UNIFICATA): {res['id_name']} (@ {res['fps']} FPS)")
    print("=========================================================================")
    print(" [A] CONFRONTO DIRETTO DEI FRAME:")
    for view in ["TOP", "FPV"]:
        gt_s = dt["gt_seconds"][view]
        gt_f = gt_s * res["fps"]
        pred_f = dt["pred_frames"][view]
        err_ms = dt["views"][view]
        print(f"   {view:4s} | GT: {gt_s:+.2f}s ({gt_f:+.1f} f) | Pred: {pred_f:+.1f} f | Errore: {err_ms:.2f} ms")

    print("\n [B] METRICHE COMPLESSIVE DEL PAPER (VisualSync):")
    print(f"   Errore Medio (Mean Error):     {metrics['mean_error_ms']:.2f} ms")
    print(f"   Errore Mediano (Median Error):  {metrics['median_error_ms']:.2f} ms")
    print(f"   Accuratezza @ 100ms (A@100ms): {metrics['A@100ms']:.1f}%")
    print(f"   Accuratezza @ 500ms (A@500ms): {metrics['A@500ms']:.1f}%")
    print(f"   Area Sotto la Curva (AUC):     {metrics['AUC']:.4f}")
    print("=========================================================================\n")


def compute_metrics(raw_root: str | Path, result_root: str | Path, id_name: str, fps: float, max_auc_tau: float = 2000.0) -> dict[str, Any]:
    # Risoluzione del GT con logica di fallback integrata
    gt_sec = load_gt_or_compute_fallback(raw_root, result_root, id_name)
    if gt_sec is None:
        return {"success": False, "msg": f"Impossibile ricavare il Ground Truth per l'ID: {id_name}."}
        
    preds_frame_raw = load_model_predictions(result_root)
    if preds_frame_raw is None:
        return {"success": False, "msg": f"File 'global_offsets.csv' assente o malformato in {result_root}."}
        
    preds_frame = {v: sanitize_float_value(preds_frame_raw.get(v, 0.0)) for v in ["TOP", "FPV", "TPV"]}
    id_errors_ms = {}
    all_errors_ms = []
    
    for view in ["TOP", "FPV"]:
        gt_frame_val = gt_sec[view] * fps
        pred_frame_val = preds_frame[view]
        err_frame = abs(pred_frame_val - gt_frame_val)
        err_ms = (err_frame / fps) * 1000
        id_errors_ms[view] = err_ms
        all_errors_ms.append(err_ms)
        
    errors = np.array(all_errors_ms)
    mean_error = np.mean(errors)
    median_error = np.median(errors)
    a_100 = np.mean(errors <= 100.0) * 100
    a_500 = np.mean(errors <= 500.0) * 100
    
    thresholds = np.linspace(0, max_auc_tau, int(max_auc_tau) + 1)
    accuracies = [np.mean(errors <= t) for t in thresholds]
    auc = np.trapz(accuracies, thresholds) / max_auc_tau
    
    return {
        "success": True, "id_name": id_name, "fps": fps,
        "metrics": {"mean_error_ms": mean_error, "median_error_ms": median_error, "A@100ms": a_100, "A@500ms": a_500, "AUC": auc},
        "details": {"views": id_errors_ms, "gt_seconds": gt_sec, "pred_frames": preds_frame}
    }


def main():
    parser = argparse.ArgumentParser(description="Calcolo metriche scientifiche con auto-guarigione cache.")
    parser.add_argument("--raw_root", type=Path, default=os.environ.get("RAW_ROOT"))
    parser.add_argument("--result_root", type=Path, default=os.environ.get("RESULT_ROOT"))
    parser.add_argument("--id", type=str, default=os.environ.get("GROUP"))
    parser.add_argument("--fps", type=float, default=float(os.environ.get("FPS") or 20.0))
    args = parser.parse_args()

    if not args.raw_root or not args.result_root or not args.id:
        print("[!] Parametri insufficienti nelle variabili d'ambiente o nei flag.", file=sys.stderr)
        sys.exit(1)

    res = compute_metrics(args.raw_root, args.result_root, args.id, args.fps)
    if not res["success"]:
        print(f"[!] Errore: {res['msg']}", file=sys.stderr)
        sys.exit(1)

    # Chiamata alla funzione di stampa centralizzata
    print_metrics_report(res)


if __name__ == "__main__":
    main()