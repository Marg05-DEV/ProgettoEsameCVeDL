import subprocess
import os
import sys
import time
import re

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

    # Struttura: Lista di tuple (Nome Passo, Lista Comandi)
    pipeline_steps = [
        ("Passo 4: Preparazione del dataset", ["python src/prepare_prin_timecrop.py --raw_root \"$RAW_ROOT\" --out_root \"$DATA_ROOT\" --group \"$GROUP\" --start_sec \"$START_SEC\" --end_sec \"$END_SEC\" --fps \"$FPS\" --flip_views TOP,FPV --overwrite"]),
        ("Passo 5: Creazione dei file tag GPT/SAM2", ["python src/create_tags.py --data_root \"$DATA_ROOT\" --dynamic hand,arm --overwrite"]),
        ("Passo 6: Sementazione con SAM2/DINO", ["python preprocess/run_dino_sam2.py --workdir \"$DATA_ROOT\""]),
        ("Passo 7: Camera estimation con VGGT", ["python preprocess/vggt_to_colmap.py --workdir \"$DATA_ROOT\" --vis_path vggt_output --save_colmap"]),
        ("Passo 8: Run CoTracker", [
            "rm -rf \"$TRACK_ROOT\"",
            "mkdir -p \"$TRACK_ROOT\"",
            "python src/run_cotracker_all.py --dataset_root \"$DATA_ROOT\" --track_root \"$TRACK_ROOT\" --gpu 0 --mask_prefix \"$MASK_PREFIX\" --only static --static_interval 3 --static_grid_step 5 --skip_exist",
            "python src/run_cotracker_all.py --dataset_root \"$DATA_ROOT\" --track_root \"$TRACK_ROOT\" --gpu 0 --mask_prefix \"$MASK_PREFIX\" --only fpv --dynamic_interval 8 --dynamic_grid_step 10 --skip_exist"
        ]),
        ("Passo 9: Run MASt3R Image Matching", [
            "rm -rf \"$RESULT_ROOT\"",
            "mkdir -p \"$RESULT_ROOT/$GROUP\"",
            "CUDA_VISIBLE_DEVICES=0 python src/img_match_v4.py --dataset_root \"$DATA_ROOT\" --video1_name \"${GROUP}_cam_top_000_150\" --video2_name \"${GROUP}_cam_tpv_000_150\" --save_root \"$RESULT_ROOT/$GROUP\" --mask_prefix \"$MASK_PREFIX\" --interval 2 --batch_size 16 --filter_mask --enable_blurry",
            "CUDA_VISIBLE_DEVICES=0 python src/img_match_v4.py --dataset_root \"$DATA_ROOT\" --video1_name \"${GROUP}_cam_tpv_000_150\" --video2_name \"${GROUP}_fpv_000_150\" --save_root \"$RESULT_ROOT/$GROUP\" --mask_prefix \"$MASK_PREFIX\" --interval 3 --batch_size 16 --filter_mask --enable_blurry",
            "CUDA_VISIBLE_DEVICES=0 python src/img_match_v4.py --dataset_root \"$DATA_ROOT\" --video1_name \"${GROUP}_cam_top_000_150\" --video2_name \"${GROUP}_fpv_000_150\" --save_root \"$RESULT_ROOT/$GROUP\" --mask_prefix \"$MASK_PREFIX\" --interval 3 --batch_size 16 --filter_mask --enable_blurry"
        ]),
        ("Passo 10: Filter Track Correspondences", [
            "CUDA_VISIBLE_DEVICES=0 python src/filter_corr_v2.py --dataset_root \"$DATA_ROOT\" --result_root \"$RESULT_ROOT\" --track_root \"$TRACK_ROOT\" --result_name1 \"${GROUP}_cam_top_000_150\" --result_name2 \"${GROUP}_cam_tpv_000_150\" --group_prefix \"$GROUP\" --mask_prefix \"$MASK_PREFIX\" --min_matches 3 --pixel_tol 10 --min_neighbors 1 --max_batch_size 4096",
            "CUDA_VISIBLE_DEVICES=0 python src/filter_corr_v2.py --dataset_root \"$DATA_ROOT\" --result_root \"$RESULT_ROOT\" --track_root \"$TRACK_ROOT\" --result_name1 \"${GROUP}_cam_tpv_000_150\" --result_name2 \"${GROUP}_fpv_000_150\" --group_prefix \"$GROUP\" --mask_prefix \"$MASK_PREFIX\" --min_matches 3 --pixel_tol 10 --min_neighbors 1 --max_batch_size 4096",
            "CUDA_VISIBLE_DEVICES=0 python src/filter_corr_v2.py --dataset_root \"$DATA_ROOT\" --result_root \"$RESULT_ROOT\" --track_root \"$TRACK_ROOT\" --result_name1 \"${GROUP}_cam_top_000_150\" --result_name2 \"${GROUP}_fpv_000_150\" --group_prefix \"$GROUP\" --mask_prefix \"$MASK_PREFIX\" --min_matches 3 --pixel_tol 10 --min_neighbors 1 --max_batch_size 4096"
        ]),
        ("Passo 11: VisualSync Offset Estimation", [
            "CUDA_VISIBLE_DEVICES=0 python src/shaowei_sync_v6.py --dataset_root \"$DATA_ROOT\" --result_root \"$RESULT_ROOT\" --video1_name \"${GROUP}_cam_top_000_150\" --video2_name \"${GROUP}_cam_tpv_000_150\" --offset_range 25 --moving_threshold 0.5 --pixel_threshold 4 --max_batch_size 4096 --max_N 30000 --use_v2 --use_vggt --disable_gt",
            "CUDA_VISIBLE_DEVICES=0 python src/shaowei_sync_v6.py --dataset_root \"$DATA_ROOT\" --result_root \"$RESULT_ROOT\" --video1_name \"${GROUP}_cam_tpv_000_150\" --video2_name \"${GROUP}_fpv_000_150\" --offset_range 25 --moving_threshold 0.5 --pixel_threshold 4 --max_batch_size 4096 --max_N 30000 --use_v2 --use_vggt --disable_gt",
            "CUDA_VISIBLE_DEVICES=0 python src/shaowei_sync_v6.py --dataset_root \"$DATA_ROOT\" --result_root \"$RESULT_ROOT\" --video1_name \"${GROUP}_cam_top_000_150\" --video2_name \"${GROUP}_fpv_000_150\" --offset_range 25 --moving_threshold 0.5 --pixel_threshold 4 --max_batch_size 4096 --max_N 30000 --use_v2 --use_vggt --disable_gt"
        ]),
        ("Passo 12: Collect offset & create merged video", [
            "python src/collect_sync_results.py --dataset_root \"$DATA_ROOT\" --result_root \"$RESULT_ROOT\" --group_name \"$GROUP\" --fps \"$FPS\" --max_seconds $((END_SEC-START_SEC)) --panel_height 480 --ignore_pair \"${GROUP}_cam_top_000_150__${GROUP}_fpv_000_150\"",
            "python src/collect_sync_results.py --dataset_root \"$DATA_ROOT\" --result_root \"$RESULT_ROOT\" --group_name \"$GROUP\" --fps \"$FPS\" --max_seconds $((END_SEC-START_SEC)) --panel_height 480 --offset_sign -1 --out_video_dir \"$RESULT_ROOT/merged_videos_flip\" --ignore_pair \"${GROUP}_cam_top_000_150__${GROUP}_fpv_000_150\""  
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
        print(f"\n{'='*20}\nAVVIO PIPELINE PER ID_{i}\n{'='*20}")
        t0 = time.time()
        success = run_pipeline(i, start_sec, end_sec, fps, start_step)
        results.append((f"ID_{i}", time.time() - t0 if success else "FALLITO"))

    print("\n" + "="*30 + "\nRIEPILOGO TEMPI\n" + "="*30)
    for g, t in results: print(f"{g:<15} | {t if isinstance(t, str) else f'{t:.2f} s'}")