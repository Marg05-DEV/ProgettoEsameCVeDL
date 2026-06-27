import subprocess
import os
import sys
import time
import re
from codecarbon import EmissionsTracker



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

    total_frames = (end_sec - start_sec) * fps
    suffix = f"000_{total_frames:03d}"
    top_name = f"{group_name}_cam_top_{suffix}"
    tpv_name = f"{group_name}_cam_tpv_{suffix}"
    fpv_name = f"{group_name}_fpv_{suffix}"
    print(f"{LOG_PREFIX} Nomi cartelle calcolati -> TOP: {top_name} | TPV: {tpv_name} | FPV: {fpv_name}")
 
    # Struttura: Lista di tuple (Nome Passo, Lista Comandi)
    pipeline_steps = [
        ("Passo 4: Preparazione del dataset", ["python src/prepare_prin_timecrop.py --raw_root \"$RAW_ROOT\" --out_root \"$DATA_ROOT\" --group \"$GROUP\" --start_sec \"$START_SEC\" --end_sec \"$END_SEC\" --fps \"$FPS\" --flip_views TOP,FPV --overwrite"]),
        ("Passo 5: Creazione dei file tag GPT/SAM2", ["python src/create_tags.py --data_root \"$DATA_ROOT\" --dynamic hand,arm --overwrite"]),
        ("Passo 6: Sementazione con SAM2/DINO", ["python preprocess/run_dino_sam2.py --workdir \"$DATA_ROOT\""]),
        ("Passo 7: Camera estimation con VGGT", ["python preprocess/vggt_to_colmap.py --workdir \"$DATA_ROOT\" --vis_path vggt_output --save_colmap"]),
        ("Passo 8: Run CoTracker", [
            "rm -rf \"$TRACK_ROOT\"",
            "mkdir -p \"$TRACK_ROOT\"",
            "python src/run_cotracker_all.py --dataset_root \"$DATA_ROOT\" --track_root \"$TRACK_ROOT\" --gpu 0 --mask_prefix \"$MASK_PREFIX\" --only static --static_interval 3 --static_grid_step 5 --max_query_per_batch 200 --skip_exist",
            "python src/run_cotracker_all.py --dataset_root \"$DATA_ROOT\" --track_root \"$TRACK_ROOT\" --gpu 0 --mask_prefix \"$MASK_PREFIX\" --only fpv --dynamic_interval 8 --dynamic_grid_step 10 --max_query_per_batch 120 --skip_exist"
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
            f"CUDA_VISIBLE_DEVICES=0 python src/shaowei_sync_v6.py --dataset_root \"$DATA_ROOT\" --result_root \"$RESULT_ROOT\" --video1_name \"{top_name}\" --video2_name \"{tpv_name}\" --offset_range 25 --moving_threshold 0.5 --pixel_threshold 4 --max_batch_size 4096 --max_N 30000 --use_v2 --use_vggt --disable_gt",
            f"CUDA_VISIBLE_DEVICES=0 python src/shaowei_sync_v6.py --dataset_root \"$DATA_ROOT\" --result_root \"$RESULT_ROOT\" --video1_name \"{tpv_name}\" --video2_name \"{fpv_name}\" --offset_range 25 --moving_threshold 0.5 --pixel_threshold 4 --max_batch_size 4096 --max_N 30000 --use_v2 --use_vggt --disable_gt"
            #f"CUDA_VISIBLE_DEVICES=0 python src/shaowei_sync_v6.py --dataset_root \"$DATA_ROOT\" --result_root \"$RESULT_ROOT\" --video1_name \"{top_name}\" --video2_name \"{fpv_name}\" --offset_range 25 --moving_threshold 0.5 --pixel_threshold 4 --max_batch_size 4096 --max_N 30000 --use_v2 --use_vggt --disable_gt"
        ]),
        ("Passo 12: Collect offset & create merged video", [
            f"python src/collect_sync_results.py --dataset_root \"$DATA_ROOT\" --result_root \"$RESULT_ROOT\" --group_name \"$GROUP\" --fps \"$FPS\" --max_seconds $((END_SEC-START_SEC)) --panel_height 480 --ignore_pair \"{top_name}__{fpv_name}\""
            #f"python src/collect_sync_results.py --dataset_root \"$DATA_ROOT\" --result_root \"$RESULT_ROOT\" --group_name \"$GROUP\" --fps \"$FPS\" --max_seconds $((END_SEC-START_SEC)) --panel_height 480 --offset_sign -1 --out_video_dir \"$RESULT_ROOT/merged_videos_flip\" --ignore_pair \"{top_name}__{fpv_name}\""
        ])
    ]

    for step_name, commands in pipeline_steps:
        for cmd in commands:
            match = re.search(r'Passo (\d+)', step_name)
            print("step_name", step_name)
            current_step_num = int(match.group(1)) if match else 0
            print("current_step_num", current_step_num)
            if start_from_step is not None and current_step_num < start_from_step:
                print(f">>> [PIPELINE] Passo {current_step_num} saltato (richiesta partenza dal passo {start_from_step}).")
                continue

            if not run_command(cmd, env=env, description=f"{step_name} -> {cmd[:50]}..."):
                return False
    return True

if __name__ == "__main__":
    try:
        start_id = int(input("ID di partenza: "))
        end_id = int(input("ID di arrivo: "))
        start_sec, end_sec, fps = int(input("Start sec: ")), int(input("End sec: ")), int(input("FPS: "))

        start_step_input = input("Inserisci il numero del passo da cui ripartire (premi invio per iniziare dall'inizio): ")
        start_step = int(start_step_input) if start_step_input.strip() else None
    except ValueError:
        print("Errore: Input non validi.")
        sys.exit(1)

    results = []
    for i in range(start_id, end_id + 1):
        print(f"\n{'='*40}\nAVVIO PIPELINE + EMISSIONI PER ID_{i}\n{'='*40}")
        
        # Configurazione CodeCarbon puramente a schermo (senza CSV)
        tracker = EmissionsTracker(
            project_name=f"ID_{i}_Execution",
            save_to_file=False,
            log_level="error"
        )
        
        tracker.start()
        t0 = time.time()
        
        # Esecuzione della pipeline con i passi e i commenti originali intatti
        success = run_pipeline(i, start_sec, end_sec, fps, start_step)
        
        elapsed_time = time.time() - t0
        emissions = tracker.stop()
        
        # Recupero dell'energia consumata in tempo reale dalla RAM
        energy_kwh = tracker._total_energy.kWh if hasattr(tracker, '_total_energy') else 0.0
        
        if success:
            status_str = f"{elapsed_time:.2f} s"
            print(f"\n[+] ID_{i} COMPLETATO CON SUCCESSO:")
            print(f"    -> Tempo di esecuzione: {status_str}")
            print(f"    -> Energia Consumata:   {energy_kwh:.4f} kWh")
            print(f"    -> Emissioni Stimate:   {emissions:.6f} kg CO2")
        else:
            status_str = "FALLITO"
            print(f"\n[-] ID_{i} FALLITO durante l'esecuzione.")
            
        results.append((f"ID_{i}", status_str, energy_kwh, emissions))

    # Riepilogo strutturato finale stampato a schermo
    print("\n" + "="*55 + "\nRIEPILOGO FINALE (TEMPI ED ENERGIA A SCHERMO)\n" + "="*55)
    print(f"{'ESPERIMENTO':<15} | {'TEMPO':<12} | {'ENERGIA (kWh)':<15} | {'EMISSIONI (kg CO2)'}")
    print("-"*55)
    for g, t, eng, ems in results:
        if t == "FALLITO":
            print(f"{g:<15} | {t:<12} | {'-':<15} | -")
        else:
            print(f"{g:<15} | {t:<12} | {eng:<15.4f} | {ems:.6f}")
    print("="*55 + "\n")