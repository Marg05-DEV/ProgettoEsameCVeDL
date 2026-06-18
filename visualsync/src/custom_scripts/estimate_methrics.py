import numpy as np
import pandas as pd
import os

# ==========================================
# CONFIGURAZIONE — modifica solo questa sezione
# ==========================================
FPS = 10
GROUP_IDS = [0, 1, 2, 3, 4]  # ID da testare
START_SEC = 15


# ==========================================
# FUNZIONI
# ==========================================
def compute_auc(errors_ms, threshold_ms):
    if len(errors_ms) == 0:
        return 0.0
    return np.mean(np.array(errors_ms) < threshold_ms) * 100

def get_result_root(group_id):
    return f"results/prin_ID_{group_id}_{START_SEC}_{END_SEC}"

def get_cam_names(group_id):
    g = f"ID_{group_id}"
    return {
        "top": f"{g}_cam_top_000_150",
        "tpv": f"{g}_cam_tpv_000_150",
        "fpv": f"{g}_fpv_000_150",
    }

def get_gt_pairwise(group_id):
    cams = get_cam_names(group_id)
    return {
        f"{cams['top']}__{cams['tpv']}": 0.0,
        f"{cams['top']}__{cams['fpv']}": 0.0,
        f"{cams['tpv']}__{cams['fpv']}": 0.0,
    }

def get_gt_global(group_id):
    cams = get_cam_names(group_id)
    return {
        cams['top']: 0.0,
        cams['tpv']: 0.0,
        cams['fpv']: 0.0,
    }

# ==========================================
# ELABORAZIONE PER OGNI ID
# ==========================================

if __name__ = "__main__":
    main()

def main():
    all_pairwise_errors_ms = []
    all_global_errors_ms   = []

    for gid in GROUP_IDS:
        result_root = get_result_root(gid)
        pairwise_csv = os.path.join(result_root, "pairwise_offsets.csv")
        global_csv   = os.path.join(result_root, "global_offsets.csv")

        # Controlla se i file esistono
        if not os.path.exists(pairwise_csv) or not os.path.exists(global_csv):
            print(f"\n[ATTENZIONE] ID_{gid}: file CSV non trovati, salto.")
            continue

        pairwise_df = pd.read_csv(pairwise_csv)
        global_df   = pd.read_csv(global_csv)

        gt_pairwise = get_gt_pairwise(gid)
        gt_global   = get_gt_global(gid)

        print(f"\n{'='*60}")
        print(f" ID_{gid}")
        print(f"{'='*60}")

        # --- PAIRWISE ---
        print("  PAIRWISE:")
        pairwise_errors_ms = []
        for _, row in pairwise_df.iterrows():
            pair    = f"{row['video1']}__{row['video2']}"
            pred_ms = (row['pred_offset'] / FPS) * 1000
            gt_ms   = gt_pairwise.get(pair, None)
            if gt_ms is not None:
                error_ms = abs(pred_ms - gt_ms)
                pairwise_errors_ms.append(error_ms)
                print(f"    {pair}")
                print(f"      Predetto: {pred_ms:.1f} ms | GT: {gt_ms:.1f} ms | Errore: {error_ms:.1f} ms")

        auc_100 = compute_auc(pairwise_errors_ms, 100)
        auc_500 = compute_auc(pairwise_errors_ms, 500)
        print(f"  AUC @100ms: {auc_100:.1f}%")
        print(f"  AUC @500ms: {auc_500:.1f}%")
        all_pairwise_errors_ms.extend(pairwise_errors_ms)

        # --- GLOBAL ---
        print("  GLOBAL:")
        global_errors_ms = []
        for _, row in global_df.iterrows():
            cam     = row['video']
            pred_ms = (row['global_offset_frames'] / FPS) * 1000
            gt_ms   = gt_global.get(cam, None)
            if gt_ms is not None:
                error_ms = abs(pred_ms - gt_ms)
                global_errors_ms.append(error_ms)
                print(f"    {cam}")
                print(f"      Predetto: {pred_ms:.1f} ms | GT: {gt_ms:.1f} ms | Errore: {error_ms:.1f} ms")

        mean_error   = np.mean(global_errors_ms) if global_errors_ms else 0.0
        median_error = np.median(global_errors_ms) if global_errors_ms else 0.0
        print(f"  Errore Medio:   {mean_error:.1f} ms")
        print(f"  Errore Mediano: {median_error:.1f} ms")
        all_global_errors_ms.extend(global_errors_ms)

    # ==========================================
    # RIEPILOGO AGGREGATO SU TUTTI GLI ID
    # ==========================================
    print(f"\n{'='*60}")
    print(f" RIEPILOGO AGGREGATO (ID {GROUP_IDS[0]} → ID {GROUP_IDS[-1]})")
    print(f"{'='*60}")
    print(f"  AUC @100ms:     {compute_auc(all_pairwise_errors_ms, 100):.1f}%")
    print(f"  AUC @500ms:     {compute_auc(all_pairwise_errors_ms, 500):.1f}%")
    print(f"  Errore Medio:   {np.mean(all_global_errors_ms):.1f} ms")
    print(f"  Errore Mediano: {np.median(all_global_errors_ms):.1f} ms")