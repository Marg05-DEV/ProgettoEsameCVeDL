#!/usr/bin/env python3
"""
run_full_validation.py

Script di orchestrazione totale. 
1. Calcola il GT con il nuovo Template Matching ROI.
2. Genera l'immagine di ispezione visiva al secondo 20.0 (punto di controllo).
3. Stampa il report scientifico delle metriche.
"""

import os
import sys
from pathlib import Path

# Importiamo i moduli costruiti insieme
import ground_truth_extractor as gte
import estimate_metrics as em


def main():
    # 1. Controllo ed estrazione delle variabili d'ambiente globali del tuo tmux
    raw_root = os.environ.get("RAW_ROOT")
    result_root = os.environ.get("RESULT_ROOT")
    group_id = os.environ.get("GROUP")
    fps_env = os.environ.get("FPS")

    if not all([raw_root, result_root, group_id, fps_env]):
        print("[!] Errore: Variabili d'ambiente mancanti nel tmux.", file=sys.stderr)
        print("    Assicurati che RAW_ROOT, RESULT_ROOT, GROUP e FPS siano esportate.", file=sys.stderr)
        sys.exit(1)

    fps_esperimento = float(fps_env)
    print("ciao", group_id)
    id_dir = Path(raw_root) / group_id
    
    # IMPOSTAZIONE STRATEGICA: Salviamo nella cartella corrente con il nome fisso richiesto
    output_png = Path("sync_interactive_check.png")
    output_csv = Path("custom_out/ground_truths.csv")

    print("\n" + "="*75)
    print(f" PIPELINE DI VALIDAZIONE AUTOMATICA: {group_id} (@ {fps_esperimento} FPS)")
    print("="*75)

    # 2. FASE 1: Calcolo automatico del Ground Truth con l'algoritmo ROI + Soglia 0.6
    print("[*] Fase 1: Calcolo del Ground Truth via Anchor Template Matching (ROI)...")
    sync_data = gte.get_all_synchronization_data(raw_root, group_id)
    gte.save_single_id_to_csv(group_id, sync_data, output_csv)
    
    # Estraiamo gli offset globali in secondi calcolati (TPV è il perno a 0.0)
    gt_offsets_sec = sync_data["global_offsets_secondi"]
    
    print("\n>>> GROUND TRUTH RILEVATO (Rispetto al pivot TPV):")
    for view in ["TOP", "TPV", "FPV"]:
        print(f"    {view:4s} -> {gt_offsets_sec[view]:+.2f} secondi")

    # 3. FASE 2: Generazione istantanea del frame di ispezione visiva (Video Inspector)
    print("\n[*] Fase 2: Generazione immagine ad alta risoluzione (Video Inspector)...")
    print(f"    Punto di controllo visivo impostato al secondo: 20.0s")
    
    try:
        import video_inspector as vi
        # Usiamo una larghezza generosa (800px per vista) per l'ispezione a occhio nudo
        vi.extract_and_save_canvas(
            id_dir=id_dir,
            time_ref=20.0,
            offsets_sec=gt_offsets_sec,
            output_name=str(output_png),
            width_per_view=800
        )
        print(f"[+] Immagine di controllo aggiornata in: {output_png.resolve()}")
    except Exception as e:
        print(f"[!] Errore durante il rendering dell'immagine dell'inspector: {e}", file=sys.stderr)

    # 4. FASE 3: Calcolo ed emissione delle metriche scientifiche del modello
    print("\n[*] Fase 3: Calcolo delle metriche di allineamento del modello...")
    
    # Eseguiamo il core logico importato da estimate_metrics
    # Passiamo prima la directory principale, ma se fallisce facciamo il tentativo nella sottocartella
    res_dict = em.compute_metrics(raw_root, result_root, group_id, fps_esperimento)
    
    if not res_dict.get("success", False):
        # Fallback di sicurezza se il CSV si trova nella sottocartella prin_ID_X_FPS_30
        sub_result_dir = Path(result_root) / f"prin_{group_id}_{int(fps_esperimento)}_30"
        res_dict = em.compute_metrics(raw_root, sub_result_dir, group_id, fps_esperimento)

    # Controlliamo se il calcolo è andato a buon fine
    if not res_dict.get("success", False):
        print(f"[!] Errore nel calcolo delle metriche: {res_dict.get('msg', 'Errore sconosciuto')}", file=sys.stderr)
        sys.exit(1)

    # Estrazione dei dati dal dizionario di output di compute_metrics
    metrics = res_dict["metrics"]
    details = res_dict["details"]
    
    # Stampa del Report Scientifico Elegante
    print("\n=========================================================================")
    print(f"    REPORT DI VALUTAZIONE SCIENTIFICA REALE: {group_id} (@ {fps_esperimento} FPS)")
    print("=========================================================================")
    print(" [A] CONFRONTO DIRETTO DELLE VISTE (Rispetto al pivot TPV = 0.0):")
    
    for view in ["TOP", "FPV"]:
        gt_sec = details["gt_seconds"].get(view, 0.0)
        gt_fr = gt_sec * fps_esperimento
        pred_fr = details["pred_frames"].get(view, 0.0)
        err_ms = details["views"].get(view, 0.0)
        
        print(f"     Vista {view:4s} | GT: {gt_sec:+.2f}s ({gt_fr:+.1f} f) | Pred: {pred_fr:+.1f} f | Errore: {err_ms:.2f} ms")
        
    print("\n [B] METRICHE COMPLESSIVE DEL PAPER (VisualSync):")
    print(f"     Errore Medio (Mean Error):      {metrics['mean_error_ms']:.2f} ms")
    print(f"     Errore Mediano (Median Error):   {metrics['median_error_ms']:.2f} ms")
    print(f"     Accuratezza @ 100ms (A@100ms):   {metrics['A@100ms']:.1f}%")
    print(f"     Accuratezza @ 500ms (A@500ms):   {metrics['A@500ms']:.1f}%")
    print(f"     Area Sotto la Curva (AUC):       {metrics['AUC']:.4f}")
    print("=========================================================================")
    print("[+] Validazione completata con successo!\n")


if __name__ == "__main__":
    main()