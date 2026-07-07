#!/usr/bin/env python3
"""
run_full_validation_v3.py

Orchestratore Accademico Principale per la Pipeline di Validazione di VisualSync.
Implementa:
  - CLI semplificata e fortemente tipizzata.
  - Caching del Ground Truth (GT) su file CSV per evitare calcoli ridondanti.
  - Generazione adattiva dei report metrici e dei canvas visivi.
  
Sviluppato da: CVeDL Progetto Helper / Mentor Scientifico
"""

from __future__ import annotations

import os
import sys
import argparse
import subprocess
from pathlib import Path
import pandas as pd

# Moduli interni del laboratorio
import ground_truth_extractor as gte
import estimate_metrics as em


def load_vars_from_bash(group_id: str, start: int, end: int, fps: float) -> dict[str, str]:
    """
    Esegue il sourcing dinamico dello script Bash e ne cattura l'ambiente esportato.
    Accetta il formato 'ID_X' inserito direttamente dall'utente.
    """
    cmd = (
        f"source scripts/custom_scripts/set_globals_variables.sh {group_id} {start} {end} {fps} > /dev/null && "
        "export -p"
    )
    
    try:
        output = subprocess.check_output(cmd, shell=True, executable='/bin/bash', text=True)
    except subprocess.CalledProcessError as e:
        print(f"[!] Errore critico nel sourcing delle variabili globali: {e}", file=sys.stderr)
        sys.exit(1)
        
    new_env = os.environ.copy()
    for line in output.splitlines():
        if "declare -x" in line:
            var_def = line.replace("declare -x ", "")
            if "=" in var_def:
                key, val = var_def.split("=", 1)
                new_env[key] = val.strip("'\"")
    return new_env


def parse_arguments():
    """Definisce l'interfaccia CLI semplificata richiesta per l'attività di laboratorio."""
    parser = argparse.ArgumentParser(
        description="VisualSync Validation Core - Versione Sperimentale V3",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Argomenti posizionali o opzionali semplificati e fortemente tipizzati
    parser.add_argument("--id", type=str, default="", help="Identificativo del gruppo nel formato ID_<X> (es. ID_1).")
    parser.add_argument("--workdir", type=str, default=None, help="Directory opzionale dell'esperimento corrente per i log metrici.")
    
    return parser.parse_args()


def load_run_settings(test_dir=None):
    """
    Carica il CSV di configurazione da custom_out o da una sua sottocartella.
    """
    # Se test_dir è specificato, punta alla sottocartella, altrimenti alla radice di custom_out
    base_dir = os.path.join("custom_out", test_dir) if test_dir else "custom_out"
    csv_path = os.path.join(base_dir, "run_setting.csv")

    if not os.path.exists(csv_path):
        print(f"Errore critico: Il file '{csv_path}' non esiste.")
        sys.exit(1)
    try:
        df = pd.read_csv(csv_path)
        # Uniformiamo l'indice indipendentemente dal case (id o ID)
        df.columns = [c.lower() for c in df.columns]
        if 'id' in df.columns:
            df.set_index('id', inplace=True)
        else:
            print("Errore: Il CSV run_setting.csv deve contenere una colonna 'id' o 'ID'.")
            sys.exit(1)
        return df
    except Exception as e:
        print(f"Errore nel parsing del CSV di configurazione: {e}")
        sys.exit(1)


def print_final_table(results):
    """
    Stampa la tabella riepilogativa finale per la sessione di esecuzione corrente.
    """
    print("\n" + "="*55 + "\nRIEPILOGO FINALE (TEMPI ED ENERGIA A SCHERMO)\n" + "="*55)
    print(f"{'ESPERIMENTO':<15} | {'TEMPO':<12} | {'ENERGIA (kWh)':<15} | {'EMISSIONI (kg CO2)'}")
    print("-"*55)
    for g, t, eng, ems in results:
        if t == "FALLITO":
            print(f"{g:<15} | {t:<12} | {'-':<15} | -")
        else:
            print(f"{g:<15} | {t:<12} | {eng:<15.4f} | {ems:.6f}")
    print("="*55 + "\n")
    
def main():
    # 1. Parsing degli input semplificati
    args = parse_arguments()

    run_settings_df = load_run_settings(args.workdir)

    if str(args.id):
        if args.id not in run_settings_df.index:
            print(f"[!] Errore Critico: L'identificativo '{args.id}' non è presente nel file di configurazione.", file=sys.stderr)
            print(f"    ID disponibili nel file: {list(run_settings_df.index)}", file=sys.stderr)
            sys.exit(1)
        ids = [args.id]
    else:
        ids = list(run_settings_df.index)
    
    print(ids)
    
    for group in ids:

        # 3. Estrazione dei parametri specifici della riga tramite locazione indicizzata (.loc)
        # Usiamo .loc[target_id] per estrarre la serie. Se ci fossero duplicati (errore del laboratorio), 
        # prendiamo la prima istanza (.iloc[0] se serie di serie, ma qui assumiamo ID univoco).
        row_data = run_settings_df.loc[group]

        try:
            # Estrazione dinamica basandoci sui nomi colonna attesi (convertiti in minuscolo dalla tua funzione)
            start = int(row_data['start_sec'])
            end = int(row_data['end_sec'])
            fps = float(row_data['fps'])
        except KeyError as e:
            print(f"[!] Errore: Colonna obbligatoria {e} mancante nel tracciato record di run_setting.csv.", file=sys.stderr)
            sys.exit(1)
        except ValueError as e:
            print(f"[!] Errore: Valore non valido nella colonna {e} nel tracciato record di run_setting.csv.", file=sys.stderr)
            sys.exit(1)

        # 2. Sourcing dell'ambiente tramite i parametri aggiornati
        print(f"[*] Configurazione dell'ambiente sperimentale per {group}...")
        injected_env = load_vars_from_bash(group, start, end, fps)
        os.environ.update(injected_env)
        
        raw_root = os.environ.get("RAW_ROOT")
        result_root = os.environ.get("RESULT_ROOT")
        fps_env = os.environ.get("FPS")
        
        if not all([raw_root, result_root, fps_env]):
            print("[!] Errore: Variabili d'ambiente essenziali mancanti dopo il sourcing.", file=sys.stderr)
            sys.exit(1)
            
        fps_esperimento = float(fps_env)
        id_dir = Path(raw_root) / group

        # Definizioni dei percorsi fissi secondo le specifiche di progetto
        # current_visualsync_root = Path(os.getcwd())
        output_png = Path("sync_interactive_check.png")
        gt_csv_path = Path("custom_out") / "ground_truths.csv"
        
        print("\n" + "="*80)
        print(f" INIZIO SESSIONE DI VALIDAZIONE: {group}")
        print(f"  - Range Temporale: {start}s -> {end}s | Frequenza Campionamento: {fps_esperimento} FPS")
        print(f"  - Directory Risultati Modello: {result_root}")
        print(f"  - Directory di Lavoro Sperimentale (workdir): {args.workdir}")
        print("="*80)

        # =========================================================================
        # FASE 1: GESTIONE CACHING GROUND TRUTH
        # =========================================================================
        gt_offsets_sec = em.load_gt_or_compute_fallback(raw_root, group)
        
        print("\n>>> CONFIGURAZIONE GROUND TRUTH CORRENTE (Riferimento TPV = 0.0):")
        for view in ["TOP", "TPV", "FPV"]:
            print(f"    Vista {view:4s} -> {gt_offsets_sec.get(view, 0.0):+.2f} secondi")

        # =========================================================================
        # FASE 2: GENERAZIONE CANVAS VISIVO (PERCORSO FISSO NELLA ROOT VISUALSYNC)
        # =========================================================================
        print(f"\n[*] Fase 2: Verifica geometrico-temporale sub-frame (Canvas)...")
        time_ref_checkpoint = (start + end) / 2.0
        
        try:
            import video_inspector as vi
            vi.extract_and_save_canvas(
                id_dir=id_dir,
                time_ref=time_ref_checkpoint,
                offsets_sec=gt_offsets_sec,
                output_name=str(output_png),
                width_per_view=800
            )
            print(f"[+] Canvas ispettivo salvato in posizione fissa: {output_png}")
        except Exception as e:
            print(f"[!] Impossibile generare l'ispezione visiva: {e}", file=sys.stderr)

        # =========================================================================
        # FASE 3: COMPUTAZIONE METRICHE ED EMISSIONE REPORT SCIENTIFICO
        # =========================================================================
        print("\n[*] Fase 3: Esecuzione motore metrico computazionale...")
        
        # Passiamo la stringa esplicita se definita, altrimenti None (gestione dell'opzionalità della workdir)
        test_dir_param = str(args.workdir) if args.workdir is not None else None
        
        res_dict = em.compute_metrics(
            raw_root=raw_root,
            result_root=result_root,
            id_name=group,
            fps=fps_esperimento,
            save_to_csv=True,
            test_dir=test_dir_param
        )
        
        if not res_dict.get("success", False):
            print(f"\n[!] Errore irreversibile nel calcolo delle metriche: {res_dict.get('msg')}", file=sys.stderr)
            sys.exit(1)

        # Invocazione della funzione di stampa dedicata passando l'output strutturato di compute_metrics
        em.print_metrics_report(res_dict)


        base_dir = os.path.join("custom_out", args.workdir) if args.workdir is not None else "custom_out"
        csv_path = os.path.join(base_dir, "metrics_report.csv")

        if not os.path.exists(csv_path):
            print(f"Errore critico: Il file '{csv_path}' non esiste.")
            sys.exit(1)
        try:
            metrics_df = pd.read_csv(csv_path)
            # Uniformiamo l'indice indipendentemente dal case (id o ID)
            metrics_df.columns = [c.lower() for c in metrics_df.columns]
            if 'id' in metrics_df.columns:
                metrics_df.set_index('id', inplace=True)
            else:
                print("Errore: Il CSV metrics_report.csv deve contenere una colonna 'id' o 'ID'.")
                sys.exit(1)
        except Exception as e:
            print(f"Errore nel parsing del CSV di configurazione: {e}")
            sys.exit(1)

        target_row = metrics_df.loc[group]

        try:        
            h_time = target_row['duration_seconds'] if "duration_seconds" in target_row else 0.0
            h_energy = target_row['energy_kwh'] if "energy_kwh" in target_row else 0.0
            h_co2 = target_row['emissions_kg'] if "emissions_kg" in target_row else 0.0
            
            status_format = f"{h_time:.2f} s"
            
            # Inviamo alla funzione delegata solo i dati estratti per il rispettivo ID
            print_final_table([(group, status_format, h_energy, h_co2)])
        except KeyError:
            print(f" [!] Nota: ID_{group} non trovato all'interno del file {csv_path}.")

        print(f"[+] Analisi conclusa per il target {group}.\n")


if __name__ == "__main__":
    main()