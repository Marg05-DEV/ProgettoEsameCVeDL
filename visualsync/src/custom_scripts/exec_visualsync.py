import subprocess
import os
import sys
import time
import re
import shutil
from codecarbon import EmissionsTracker
import pandas as pd

# Importazione integrata dei componenti scientifici di estimate_metrics
try:
    from estimate_metrics import compute_metrics, print_metrics_report
except ImportError:
    print("[!] Errore: Assicurati che 'estimate_metrics.py' e 'ground_truth_extractor.py' siano nel PYTHONPATH.", file=sys.stderr)
    sys.exit(1)

# Costanti
BASE_PATH = "/app/Progetto/visualsync"
LOG_PREFIX = ">>> [PIPELINE]"

def load_vars_from_bash(group_id, start_sec, end_sec, fps):
    cmd = (
        f"source scripts/custom_scripts/set_globals_variables.sh ID_{group_id} {start_sec} {end_sec} {fps} > /dev/null && "
        "export -p"
    )
    
    output = subprocess.check_output(cmd, shell=True, executable='/bin/bash', text=True)
    
    new_env = os.environ.copy()
    for line in output.splitlines():
        if "declare -x" in line:
            var_def = line.replace("declare -x ", "")
            if "=" in var_def:
                key, val = var_def.split("=", 1)
                # Rimuoviamo eventuali virgolette aggiunte da export -p
                new_env[key] = val.strip("'\"")
    return new_env

def run_command(command, env=None, description=""):
    print(f"\n{LOG_PREFIX} Esecuzione: {description}")
    try:
        subprocess.run(command, shell=True, env=env, check=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n{LOG_PREFIX} ERRORE in {description}: {e}")
        return False

def run_pipeline(group_id, start_sec, end_sec, fps, start_from_step=None):
    group_name = f"ID_{group_id}"
    env = load_vars_from_bash(group_id, start_sec, end_sec, fps)

    if start_from_step is None or start_from_step <= 4:
        purge_previous_outputs(env, group_id, start_sec, end_sec, fps)

    total_frames = (end_sec - start_sec) * fps
    suffix = f"000_{total_frames:03d}"
    top_name = f"{group_name}_cam_top_{suffix}"
    tpv_name = f"{group_name}_cam_tpv_{suffix}"
    fpv_name = f"{group_name}_fpv_{suffix}"
    print(f"{LOG_PREFIX} Nomi cartelle calcolati -> TOP: {top_name} | TPV: {tpv_name} | FPV: {fpv_name}")
 
    # Struttura originale intatta al 100%, incluso ogni comando commentato
    pipeline_steps = [
        ("Passo 4: Preparazione del dataset", ["python src/prepare_prin_timecrop.py --raw_root \"$RAW_ROOT\" --out_root \"$DATA_ROOT\" --group \"$GROUP\" --start_sec \"$START_SEC\" --end_sec \"$END_SEC\" --fps \"$FPS\" --flip_views TOP,FPV --overwrite"]),
        ("Passo 5: Creazione dei file tag GPT/SAM2", ["python src/create_tags.py --data_root \"$DATA_ROOT\" --dynamic hand,arm --overwrite"]),
        ("Passo 6: Sementazione con SAM2/DINO", ["python preprocess/run_dino_sam2.py --workdir \"$DATA_ROOT\""]),
        ("Passo 7: Camera estimation con VGGT", ["python preprocess/vggt_to_colmap.py --workdir \"$DATA_ROOT\" --vis_path vggt_output --save_colmap"]),
        ("Passo 8: Run CoTracker", [
            "rm -rf \"$TRACK_ROOT\"",
            "mkdir -p \"$TRACK_ROOT\"",
            "python src/run_cotracker_all.py --dataset_root \"$DATA_ROOT\" --track_root \"$TRACK_ROOT\" --gpu 0 --mask_prefix \"$MASK_PREFIX\" --only static --static_interval 3 --static_grid_step 5 --max_query_per_batch 200 --skip_exist",
            "python src/run_cotracker_all.py --dataset_root \"$DATA_ROOT\" --track_root \"$TRACK_ROOT\" --gpu 0 --mask_prefix \"$MASK_PREFIX\" --only fpv --dynamic_interval 8 --dynamic_grid_step 10 --max_query_per_batch 60 --skip_exist"
        ]),
        ("Passo 9: Run MASt3R Image Matching", [
            "rm -rf \"$RESULT_ROOT\"",
            "mkdir -p \"$RESULT_ROOT/$GROUP\"",
            f"CUDA_VISIBLE_DEVICES=0 python src/img_match_v4.py --dataset_root \"$DATA_ROOT\" --video1_name \"{top_name}\" --video2_name \"{tpv_name}\" --save_root \"$RESULT_ROOT/$GROUP\" --mask_prefix \"$MASK_PREFIX\" --interval 2 --batch_size 16 --filter_mask --enable_blurry",
            f"CUDA_VISIBLE_DEVICES=0 python src/img_match_v4.py --dataset_root \"$DATA_ROOT\" --video1_name \"{tpv_name}\" --video2_name \"{fpv_name}\" --save_root \"$RESULT_ROOT/$GROUP\" --mask_prefix \"$MASK_PREFIX\" --interval 3 --batch_size 16 --filter_mask --enable_blurry",
            #f"CUDA_VISIBLE_DEVICES=0 python src/img_match_v4.py --dataset_root \"$DATA_ROOT\" --video1_name \"{top_name}\" --video2_name \"{fpv_name}\" --save_root \"$RESULT_ROOT/$GROUP\" --mask_prefix \"$MASK_PREFIX\" --interval 3 --batch_size 16 --filter_mask --enable_blurry"
        ]),
        ("Passo 10: Filter Track Correspondences", [
            f"CUDA_VISIBLE_DEVICES=0 python src/filter_corr_v2.py --dataset_root \"$DATA_ROOT\" --result_root \"$RESULT_ROOT\" --track_root \"$TRACK_ROOT\" --result_name1 \"{top_name}\" --result_name2 \"{tpv_name}\" --group_prefix \"$GROUP\" --mask_prefix \"$MASK_PREFIX\" --min_matches 3 --pixel_tol 10 --min_neighbors 1 --max_batch_size 4096",
            f"CUDA_VISIBLE_DEVICES=0 python src/filter_corr_v2.py --dataset_root \"$DATA_ROOT\" --result_root \"$RESULT_ROOT\" --track_root \"$TRACK_ROOT\" --result_name1 \"{tpv_name}\" --result_name2 \"{fpv_name}\" --group_prefix \"$GROUP\" --mask_prefix \"$MASK_PREFIX\" --min_matches 3 --pixel_tol 10 --min_neighbors 1 --max_batch_size 4096",
            #f"CUDA_VISIBLE_DEVICES=0 python src/filter_corr_v2.py --dataset_root \"$DATA_ROOT\" --result_root \"$RESULT_ROOT\" --track_root \"$TRACK_ROOT\" --result_name1 \"{top_name}\" --result_name2 \"{fpv_name}\" --group_prefix \"$GROUP\" --mask_prefix \"$MASK_PREFIX\" --min_matches 3 --pixel_tol 10 --min_neighbors 1 --max_batch_size 4096"
        ]),
        ("Passo 11: VisualSync Offset Estimation", [
            f"CUDA_VISIBLE_DEVICES=0 python src/shaowei_sync_v6.py --dataset_root \"$DATA_ROOT\" --result_root \"$RESULT_ROOT\" --video1_name \"{top_name}\" --video2_name \"{tpv_name}\" --offset_range 30 --moving_threshold 0.5 --pixel_threshold 4 --max_batch_size 4096 --max_N 30000 --use_v2 --use_vggt --disable_gt",
            f"CUDA_VISIBLE_DEVICES=0 python src/shaowei_sync_v6.py --dataset_root \"$DATA_ROOT\" --result_root \"$RESULT_ROOT\" --video1_name \"{tpv_name}\" --video2_name \"{fpv_name}\" --offset_range 30 --moving_threshold 0.5 --pixel_threshold 4 --max_batch_size 4096 --max_N 30000 --use_v2 --use_vggt --disable_gt"
            #f"CUDA_VISIBLE_DEVICES=0 python src/shaowei_sync_v6.py --dataset_root \"$DATA_ROOT\" --result_root \"$RESULT_ROOT\" --video1_name \"{top_name}\" --video2_name \"{fpv_name}\" --offset_range 25 --moving_threshold 0.5 --pixel_threshold 4 --max_batch_size 4096 --max_N 30000 --use_v2 --use_vggt --disable_gt"
        ]),
        ("Passo 12: Collect offset & create merged video", [
            f"python src/collect_sync_results.py --dataset_root \"$DATA_ROOT\" --result_root \"$RESULT_ROOT\" --group_name \"$GROUP\" --fps \"$FPS\" --max_seconds $((END_SEC-START_SEC)) --panel_height 480 --ignore_pair \"{top_name}__{fpv_name}\"",
            f"python src/collect_sync_results.py --dataset_root \"$DATA_ROOT\" --result_root \"$RESULT_ROOT\" --group_name \"$GROUP\" --fps \"$FPS\" --max_seconds $((END_SEC-START_SEC)) --panel_height 480 --offset_sign -1 --out_video_dir \"$RESULT_ROOT/merged_videos_flip\" --ignore_pair \"{top_name}__{fpv_name}\""
        ])
    ]

    for step_name, commands in pipeline_steps:
        match = re.search(r'Passo (\d+)', step_name)
        current_step_num = int(match.group(1)) if match else 0

        if start_from_step is not None and current_step_num < start_from_step:
            print(f">>> [PIPELINE] Passo {current_step_num} saltato (richiesta partenza dal passo {start_from_step}).")
            continue

        print("step_name", step_name)
        print("current_step_num", current_step_num)

        
        if current_step_num == 12:
            raw_root = env.get("RAW_ROOT")
            result_root = env.get("RESULT_ROOT")
            id_name = f"ID_{group_id}"
            
            print(f"\n{LOG_PREFIX} --- AVVIO COMPARAZIONE METRICHE PASSO 12 (NORMAL VS FLIPPED) ---")
            
            # 1. Esecuzione del primo comando della lista (Configurazione standard)
            cmd_normal = commands[0]
            if not run_command(cmd_normal, env=env, description=f"{step_name} [Normal] -> {cmd_normal[:50]}..."):
                return False
            res_normal = compute_metrics(raw_root, result_root, id_name, fps, save_to_csv=False)
            auc_normal = res_normal["metrics"]["AUC"] if res_normal["success"] else float('inf')
            
            # 2. Esecuzione del secondo comando della lista (Configurazione invertita)
            cmd_flipped = commands[1]
            if not run_command(cmd_flipped, env=env, description=f"{step_name} [Flipped] -> {cmd_flipped[:50]}..."):
                return False
            res_flipped = compute_metrics(raw_root, result_root, id_name, fps, save_to_csv=False)
            auc_flipped = res_flipped["metrics"]["AUC"] if res_flipped["success"] else float('inf')
            
            # Valutazione della configurazione migliore tramite AUC
            if auc_normal >= auc_flipped:
                print(f"\n[+] Scelta Ottimale: NORMAL ({auc_normal:.2f} >= {auc_flipped:.2f})")
                run_command(cmd_normal, env=env, description="Ripristino configurazione Normal")
                os.environ["VS_LAST_OFFSET_MODE"] = "normal"
            else:
                print(f"\n[+] Scelta Ottimale: FLIPPED ({auc_flipped:.2f} > {auc_normal:.2f})")
                os.environ["VS_LAST_OFFSET_MODE"] = "flipped"
        else:
            # Esecuzione standard lineare per tutti gli altri passaggi della pipeline
            for cmd in commands:
                if not run_command(cmd, env=env, description=f"{step_name} -> {cmd[:50]}..."):
                    return False
                    
    return True


def purge_previous_outputs(env, group_id, start_sec, end_sec, fps):
    """
    Elimina preventivamente solo i dati intermedi (DATA, TRACK, VGGT).
    Mantiene intatta RESULT_ROOT per non compromettere la cronologia o i test correnti.
    """
    print(f"\n{LOG_PREFIX} [-] Avvio pulizia preventiva dei dati intermedi per ID_{group_id}...")
    
    group_name = f"ID_{group_id}"
    total_frames = (end_sec - start_sec) * fps
    suffix = f"000_{total_frames:03d}"
    
    # Escludiamo RESULT_ROOT da questa lista
    folders_to_delete = [
        os.path.join(env.get("DATA_ROOT", "")),
        os.path.join(env.get("TRACK_ROOT", "")),
        os.path.join("vggt_output/vggt_poses/", f"{group_name}")
    ]

    print(folders_to_delete)
    
    for folder in folders_to_delete:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
                print(f"    -> Rimossa cartella intermedia obsoleta: {folder}")
            except Exception as e:
                print(f"    [!] Impossibile rimuovere {folder}: {e}")



def print_execution_summary(id_str, status, elapsed_time, energy_kwh, emissions):
    """
    Funzione centralizzata per stampare i dati computazionali ed ecologici di esecuzione.
    """
    if status == "FALLITO":
        print(f"\n[-] {id_str} FALLITO durante l'esecuzione.")
    else:
        print(f"\n[+] {id_str} COMPLETATO CON SUCCESSO:")
        print(f"    -> Tempo di esecuzione: {elapsed_time:.2f} s")
        print(f"    -> Energia Consumata:   {energy_kwh:.4f} kWh")
        print(f"    -> Emissioni Stimate:   {emissions:.6f} kg CO2")


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


if __name__ == "__main__":
    print("="*50)
    print("      VISUALSYNC EXPERIMENTAL PIPELINE MANAGER      ")
    print("="*50)
    print("Seleziona la modalità di esecuzione:")
    print("1) Modalità Standard (Input manuale dei parametri temporali)")
    print("2) Modalità Batch da CSV (Configurazione da custom_out/run_setting.csv)")
    print("3) Modalità Solo Report Interattiva (Visualizzazione metriche e consumi storici)")
    
    scelta = input("\nInserisci il numero della modalità (1/2/3): ").strip()
    
    if scelta not in ["1", "2", "3"]:
        print("Errore: Selezione non valida.")
        sys.exit(1)
        
    test_dir = None
    if scelta in ["2", "3"]:
        test_dir_input = input("Inserisci il nome della cartella del test dentro custom_out (Premi Invio per root): ").strip()
        if test_dir_input:
            test_dir = test_dir_input
        else:
            test_dir = None 
            
    # Caricamento preventivo del CSV passando la variabile test_dir appena calcolata
    df_settings = load_run_settings(test_dir) if scelta in ["2", "3"] else None

    # ========================================================================
    # BLOCCO DI SINOPSIS / INPUT (GESTIONE DELLE VARIABILI DI ESECUZIONE)
    # ========================================================================
    if scelta in ["1", "2"]:
        # Inizializzazione dizionario per mappare i parametri per ogni ID nel range
        execution_batch = {}
        
        if scelta == "1":
            try:
                start_id = int(input("ID di partenza: "))
                end_id = int(input("ID di arrivo: "))
                start_sec = int(input("Start sec: "))
                end_sec = int(input("End sec: "))
                fps = int(input("FPS: "))
                
                start_step_input = input("Inserisci il numero del passo da cui ripartire (premi invio per iniziare dall'inizio): ")
                start_step = int(start_step_input) if start_step_input.strip() else None
                
                # Popoliamo il dizionario con i medesimi parametri per tutto il range scelto manualmente
                for i in range(start_id, end_id + 1):
                    execution_batch[i] = {
                        "start_sec": start_sec,
                        "end_sec": end_sec,
                        "fps": fps,
                        "start_step": start_step
                    }
            except ValueError:
                print("Errore: Input non validi.")
                sys.exit(1)
                
        elif scelta == "2":
            try:
                start_id = int(input("ID di partenza (da CSV): "))
                end_id = int(input("ID di arrivo (da CSV): "))
                # Vincolo del Mentor: Niente richiesta step, si parte da 0 (None o 0 in base alla logica di run_pipeline)
                start_step = 11
            except ValueError:
                print("Errore: Input ID non validi.")
                sys.exit(1)
                
            for i in range(start_id, end_id + 1):
                if i == start_id:
                    print("")
                else:
                    start_step = 11

                # Gestione flessibile sia per formati interi che stringa ("ID_X" o X) nel CSV
                str_key = f"ID_{i}"
                if str_key in df_settings.index:
                    row = df_settings.loc[str_key]
                elif i in df_settings.index:
                    row = df_settings.loc[i]
                else:
                    print(f"[!] Warning: ID {i} (o ID_{i}) non trovato nel file CSV. Verrà saltato.")
                    continue
                
                if isinstance(row, pd.DataFrame):
                    row = row.iloc[0]
                    
                execution_batch[i] = {
                    "start_sec": int(row["start_sec"]),
                    "end_sec": int(row["end_sec"]),
                    "fps": int(row["fps"]),
                    "start_step": start_step
                }
                print(execution_batch)

        # ========================================================================
        # CICLO UNICO DI ESECUZIONE (Fase 1 e Fase 3 della Pipeline)
        # ========================================================================
        results = []
        for i, params in execution_batch.items():
            print(f"\n{'='*40}\nAVVIO PIPELINE + EMISSIONI PER ID_{i}\n{'='*40}")
            
            # Isolamento atomico dei consumi energetici
            tracker = EmissionsTracker(
                project_name=f"ID_{i}_Execution",
                save_to_file=False,
                log_level="error"
            )
            
            tracker.start()
            t0 = time.time()
            
            os.environ["VS_LAST_OFFSET_MODE"] = "undefined"
            success = run_pipeline(i, params["start_sec"], params["end_sec"], params["fps"], params["start_step"])
            
            elapsed_time = time.time() - t0
            emissions = tracker.stop()
            energy_kwh = tracker._total_energy.kWh if hasattr(tracker, '_total_energy') else 0.0
            
            if success:
                status_str = f"{elapsed_time:.2f} s"
                print_execution_summary(f"ID_{i}", status_str, elapsed_time, energy_kwh, emissions)

                pipeline_vars = load_vars_from_bash(i, params["start_sec"], params["end_sec"], params["fps"])
                raw_root = pipeline_vars.get("RAW_ROOT")
                standard_result_root = pipeline_vars.get("RESULT_ROOT")  # Es: /app/Progetto/visualsync/result/ID_8
                
                # Memorizziamo i riferimenti della cartella result globale per usarli fuori dal ciclo
                result_parent_dir = os.path.dirname(standard_result_root) # Es: /app/Progetto/visualsync/result
                workspace_dir = os.path.dirname(result_parent_dir)         # Es: /app/Progetto/visualsync

                # DURANTE IL CICLO: Leggiamo i dati direttamente dalla cartella standard "result"
                # Perché non è ancora stata rinominata!
                if params["start_step"] is None or params["start_step"] <= 12:
                    energy_dict = {
                        "duration_seconds": elapsed_time,
                        "energy_kwh": energy_kwh,
                        "emissions_kg": emissions
                    }
                    
                    res_definitivo = compute_metrics(
                        raw_root=raw_root, 
                        result_root=standard_result_root,  # Legge da result/ID_8
                        id_name=f"ID_{i}", 
                        fps=float(params["fps"]),
                        offset_mode_override=os.environ.get("VS_LAST_OFFSET_MODE", "normal"),
                        energy_data=energy_dict,
                        save_to_csv=True,
                        test_dir=test_dir # Salva correttamente il CSV delle metriche in custom_out/test_dir/
                    )
                    
                    if res_definitivo and "metrics" in res_definitivo:
                        print_metrics_report(res_definitivo)
                    else:
                        print(f"[!] Errore nel calcolo delle metriche per ID_{i}")
            else:
                status_str = "FALLITO"
                print_execution_summary(f"ID_{i}", status_str, elapsed_time, energy_kwh, emissions)
                
            results.append((f"ID_{i}", status_str, energy_kwh, emissions))
            
        # ========================================================================
        # FINE DEL CICLO FOR: ORA EFFETTUIAMO L'ARCHIVIAZIONE DELLA CARTELLA RESULT
        # ========================================================================
        if test_dir and 'result_parent_dir' in locals() and os.path.exists(result_parent_dir):
            new_result_parent_name = f"results_{test_dir}"  # Es: results_test_1
            new_result_parent_path = os.path.join(workspace_dir, new_result_parent_name)
            
            if not os.path.exists(new_result_parent_path):
                try:
                    os.rename(result_parent_dir, new_result_parent_path)
                    print(f"\n[+] Archiviazione Finale: Rinominalo con successo '{result_parent_dir}' in '{new_result_parent_path}'")
                except Exception as e:
                    print(f"\n[!] Errore durante la rinomina finale della cartella result: {e}")
            else:
                print(f"\n[!] Avviso: La cartella di destinazione '{new_result_parent_path}' esiste già. Archiviazione saltata per evitare sovrascritture.")

        # Stampa della tabella riassuntiva finale dei consumi
        print_final_table(results)

    # ------------------------------------------------------------------------
    # MODALITÀ 3: SOLO REPORT INTERATTIVO (WHILE LOOP CON LOOKUP AUTOMATICO)
    # ------------------------------------------------------------------------
    elif scelta == "3":
        print("\n" + "="*50 + "\nMODALITÀ SOLO REPORT INTERATTIVA\n" + "="*50)
        
        while True:
            id_input = input("\nInserisci l'ID numerico da ispezionare (es. 2, oppure 'q' per uscire): ").strip()
            if id_input.lower() in ['q', 'exit', 'esci']:
                print("Uscita dalla modalità report.")
                break
                
            try:
                i = int(id_input)
            except ValueError:
                print("Errore: Inserisci un numero intero valido.")
                continue
                
            # Verifica della corrispondenza delle chiavi nel DataFrame (gestisce sia "ID_2" che 2)
            str_key = f"ID_{i}"
            row = None
            if str_key in df_settings.index:
                row = df_settings.loc[str_key]
            elif i in df_settings.index:
                row = df_settings.loc[i]
                
            if row is None:
                print(f"[-] Errore: L'ID_{i} non è presente in 'run_setting.csv'. Impossibile recuperare i metadati temporali.")
                continue
                
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
                
            # Recupero automatico dei parametri dal CSV senza interazione dell'utente
            fps_val = float(row["fps"])
            start_sec_val = int(row["start_sec"])
            end_sec_val = int(row["end_sec"])
            
            print(f"\n[Dati Configurazione CSV] ID_{i} -> FPS: {fps_val}, Start: {start_sec_val}s, End: {end_sec_val}s")
            
            try:
                # Eseguiamo il lookup di load_vars_from_bash per trovare i path corretti di output del modello
                pipeline_vars = load_vars_from_bash(i, start_sec_val, end_sec_val, int(fps_val))
                raw_root = pipeline_vars.get("RAW_ROOT")
                standard_result_root = pipeline_vars.get("RESULT_ROOT")
                
                # Se l'utente ha caricato un test specifico, cerchiamo gli offset in results_<test_dir>
                if test_dir:
                    result_parent_dir = os.path.dirname(standard_result_root) # /app/Progetto/visualsync/result
                    group_folder_name = os.path.basename(standard_result_root) # ID_1
                    workspace_dir = os.path.dirname(result_parent_dir)         # /app/Progetto/visualsync
                    
                    actual_result_root = os.path.join(workspace_dir, f"results_{test_dir}", group_folder_name)
                else:
                    actual_result_root = standard_result_root
                
                print(f"[Lookup] Estrazione dati di allineamento da: {actual_result_root}")

                res_definitivo = compute_metrics(
                    raw_root=raw_root, 
                    result_root=actual_result_root, 
                    id_name=f"ID_{i}", 
                    fps=fps_val,
                    offset_mode_override="normal",
                    energy_data=None, 
                    save_to_csv=False,
                    test_dir=test_dir
                )
                
                # Stampa del report delle metriche fisiche/geometriche del modello
                print_metrics_report(res_definitivo)
                
                # Recupero dei dati computazionali storici direttamente da metrics_report.csv se presente
                if test_dir:
                    metrics_csv_path = os.path.join("custom_out", test_dir, "metrics_report.csv")
                else:
                    metrics_csv_path = os.path.join("custom_out", "metrics_report.csv")
                if os.path.exists(metrics_csv_path):
                    try:
                        df_metrics_history = pd.read_csv(metrics_csv_path)
                        
                        # Uniformiamo i nomi delle colonne in minuscolo per evitare problemi di Case Sensitivity
                        df_metrics_history.columns = [c.lower() for c in df_metrics_history.columns]
                        
                        # Definiamo le possibili stringhe identificative memorizzate (es: "ID_2" o "2")
                        target_id_str = f"ID_{i}"
                        target_id_int = i
                        
                        # Troviamo la colonna usata come chiave primaria (solitamente 'id' o 'experiment')
                        id_col = None
                        for col in ['id', 'experiment', 'id_name']:
                            if col in df_metrics_history.columns:
                                id_col = col
                                break
                        
                        if id_col is not None:
                            # Filtriamo il DataFrame per trovare la riga corrispondente al nostro ID
                            # Gestiamo sia il caso in cui nel CSV sia salvato come stringa "ID_X" sia come intero X
                            row_match = df_metrics_history[
                                (df_metrics_history[id_col].astype(str) == target_id_str) | 
                                (df_metrics_history[id_col].astype(str) == str(target_id_int))
                            ]
                            
                            if not row_match.empty:
                                # Se ci sono più righe (es. test ripetuti), prendiamo l'ultima esecuzione (.iloc[-1])
                                target_row = row_match.iloc[-1]
                                
                                h_time = target_row['duration_seconds'] if "duration_seconds" in target_row else 0.0
                                h_energy = target_row['energy_kwh'] if "energy_kwh" in target_row else 0.0
                                h_co2 = target_row['emissions_kg'] if "emissions_kg" in target_row else 0.0
                                
                                status_format = f"{h_time:.2f} s"
                                
                                # Inviamo alla funzione delegata solo i dati estratti per il rispettivo ID
                                print_final_table([(f"ID_{i}", status_format, h_energy, h_co2)])
                            else:
                                print(f" [!] Nota: ID_{i} non trovato all'interno del file {metrics_csv_path}.")
                        else:
                            print(f" [!] Errore: Colonna ID non identificata nel CSV. Colonne presenti: {list(df_metrics_history.columns)}")
                            
                    except Exception as ex_csv:
                        print(f" [!] Nota: Errore nel parsing dei consumi storici da metrics_report.csv ({ex_csv})")
                else:
                    print(f" [!] Avviso: File {metrics_csv_path} non trovato. Dati di consumo storici non disponibili.")
                    
            except Exception as e:
                print(f"[-] Errore critico durante il recupero dei dati per ID_{i}: {e}")
                
            # Chiediamo esplicitamente se continuare, per mantenere pulito il terminale
            continua = input("\nVuoi esaminare un altro ID? (s/n): ").strip().lower()
            if continua not in ['s', 'si', 'y', 'yes', '']:
                print("Uscita dalla modalità report.")
                break