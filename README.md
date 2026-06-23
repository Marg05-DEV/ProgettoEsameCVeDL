Al giorno 13/06 abbiamo eseguito i seguenti passaggi riportati sul README del repository di visualsync. Il giorno 16/06 abbiamo dovuto replicare i comandi avendo cambaito server (Questo cambiamento era dovuto al fatto che nel vecchio server la versione di CUDA non era sufficient -> avevamoa vuto un errore al passo 7) perciò aggiorniamo i passi elencati precedentemente con alcune informazioni aggiuntive: 
- **Passo 1**: Clonazione della repository da github al server. Fatti alcuni comandi per creare la nostra repo sia con il progetto che con la cartella della relazione;
- **Passo 2**: Setup dell'enviroment seguendo il punto 2 sul readme. Aggiunto il comando che mancava per il download dei pesi (ricordando che il file download_weights.sh aveva alcuni errori sull'ultima riga: 2 wget e mancava `-O \preprocess` prima di `\pretrained...`).
**RICORDA:** Nel passo 2 è riportato anche il config del venv. Nelle prossime esecuzioni ricordarsi di eseguire sul venv altrimenti i pip install fatti nel venv non vengono trovati
- **Passo Aggiuntivo**: Trasferire il dataset zippato sul server remoto per poi poterlo utilizzare con il passo 3
- **Passo 3**: Stabilite le variabili globali per l'esecuzione del modello. Riportiamo l'esempio delle variabili globali utilizzate (noi ci dovremmo trovare dentro la cartella visualsync). Abbiamo creato il file dentro `scripts/custom_scripts` che include tutti i seguenti comandi:

    ```bash
    export RAW_ROOT="/app/Progetto/dataset/PRIN_DATASET/Video ed Excel"

    export GROUP="ID_0"
    export START_SEC=15
    export END_SEC=30
    export FPS=10

    export DATA_ROOT="data/prin_${GROUP}_${START_SEC}_${END_SEC}"
    export TRACK_ROOT="tracks/prin_${GROUP}_${START_SEC}_${END_SEC}"
    export RESULT_ROOT="results/prin_${GROUP}_${START_SEC}_${END_SEC}"
    
    export MASK_PREFIX="deva_improved"
    ```

    Note
    - START_SEC and END_SEC define the action-focused crop window.
    - The output frame folders are named rgb_aligned.
    - By default, TOP and FPV are horizontally flipped during extraction because this improved matching behavior in our tests.
    - If a camera does not need flipping, remove it from --flip_views.

Riprendiamo la preparazione e l'esecuzione del modello dal punto 4 dove andiamo a preparare, dentro visualsync la cartella e la successiva struttura che accoglierà i dati croppati che il modello vuole ed inoltre raccoglierà i risultati del modello. 

**NB. (secondo tentativo)** In realtà eravamo arrivati al punto 6 dove avevamo interrotto in quanto non avevamo eseguito il download dei pesi che non era riportato inizialmente del README. Per dare continuità all'esecuzione abbiamo eliminato la cartella data che viene generata nel punto 4 e ricorsivamente anche le cartelle e i dati all'interno generati dai punti 5 e 6. Ripartiamo dal passo 4

**NB. (terzo tentativo)** Nel secondo tentativo abbiamo avuto bisogno di tmux al passo 6 in quanto eseguire i comandi sul terminale comportava il rischio che se si bloccava il server si bloccava anche l'esecuzione. Siamo dovuti passare ad un terzo tentativo perchè al passo 7 abbiamo avuto un errore per una versione troppo vecchia di CUDA. Perciò abbiamo ricevuto un container su un nuovo server con CUDA aggiornato e abbiamo dovuto riniziare l'esecuzione. Per questo terzo tentativo facciamo tutta l'esecuzione su tmux. Perciò riporto i comandi utili per l'esecuzione su tmux:
- Per creare la sessione usato il comando:
  ```bash
  tmux new -s <nome_sessione>
  ```

  Poi si può uscire dal terminale di tmux senza fermare la sessione facendo la combinazione di tasti `Ctrl + B` e poi `D`
  ATTENZIONE: Non fare mai `exit` quando si è su tmux con una sessione attiva che sta elaborando.
- Per riprendere la sessione fare il comando:
  ```bash
  tmux attach -t <nome_sessione>
  ```

Il nome dato alla sessione dove eseguiamo è `visualsyncID0`. In questa sessione sono stati fatti i comandi dal passo 3

Appena viene avviata la sessione controllare se il venv è attivo (cioè se c'è `(vissync)` all'inizio del prompt). Se non è attivo, per prima cosa fare il coamndo:
```bash
source vissync/bin/activate
```

Infatti molti (probabilmente tutti) dei pip install indicati successivamente sono stati fatti perchè non avevamo il venv attivo e non si trovavano i pacchetti installati effettivamente nel venv. Guardare il file `requirements.txt` per i pacchetti installati

Poi eseguire lo script per impostare le variabili globali che velocizza il processo descritto sopra:

```bash
source scripts/custom_scripts/set_globals_variables.sh ID_<gruppo> <start_sec> <end_sec> <fps>
```
I valori di default sono: `GROUP = ID_0`, `START_SEC = 15`, `END_SEC = 30`, `FPS = 10`

**ATTENZIONE:** Usare `source` e non `bash` altrimenti le variabili vengono settate in una 'sub-shell' e muoiono con lo script

A questo punto possiamo passare al passo 4


--- 
---
### Passo 4: Prepare the cropped PRIN dataset
Riporto il testo del README riguardo il passo 4:

---

This step reads the original PRIN folder structure:

```text
$RAW_ROOT/
└── ID_0/
    ├── TOP/
    ├── TPV/
    ├── FPV/
    ├── TOP_synchronized.mp4 
    ├── TPV_synchronized.mp4
    └── FPV_synchronized.mp4
```

and creates:

```text
$DATA_ROOT/
├── ID_0_cam_top_000_150/rgb_aligned/
├── ID_0_cam_tpv_000_150/rgb_aligned/
└── ID_0_fpv_000_150/rgb_aligned/
```

Run:

```bash
python src/prepare_prin_timecrop.py --raw_root "$RAW_ROOT" --out_root "$DATA_ROOT" --group "$GROUP" --start_sec "$START_SEC" --end_sec "$END_SEC" --fps "$FPS" --flip_views TOP,FPV --overwrite
```

The script checks both `.mp4` and `.MP4`.

Check the output:

```bash
find "$DATA_ROOT" -maxdepth 2 -type d | sort
find "$DATA_ROOT" -path "*/rgb_aligned/*.jpg" | wc -l
```

---

Questo punto va a prendere uno dei video del dataset che indichiamo e lo prepara seguendo le condizioni imposta dal modello (Il modello non accetta in input un video ma vuole una sequenza di imamgine per ogni punto di vista). Inoltre possiamo limitare il video a uno specifico intevallo di tempo definito attraverso le VARIABILI GLOBALI del passo 3. Un altra impostazione riguarda gli fps.

~~Abbiamo dovuto installare la libreria cv2 con il comando~~
~~```pip install opencv-python```~~ (non necessario con il venv attivo)

### Passo 5: Create GPT/SAM2 tag files

Riporto il testo del README riguardo il passo 5:

---

For the simplified pipeline, we ask the segmentation stage to focus on dynamic action regions:

```json
{
  "dynamic": [
    "hand",
    "arm"
  ]
}
```

Run:

```bash
python src/create_tags.py --data_root "$DATA_ROOT" --dynamic hand,arm --overwrite
```

This creates:

```text
$DATA_ROOT/ID_0_cam_top_000_150/gpt_video/tags.json
$DATA_ROOT/ID_0_cam_tpv_000_150/gpt_video/tags.json
$DATA_ROOT/ID_0_fpv_000_150/gpt_video/tags.json
```

Check:

```bash
find "$DATA_ROOT" -path "*/gpt_video/tags.json" -type f -print -exec cat {} \;
```
---

L'output del check del comando è:
```bash
data/prin_ID_0_15_30/ID_0_cam_top_000_150/gpt_video/tags.json
{
  "dynamic": [
    "hand",
    "arm"
  ]
}
data/prin_ID_0_15_30/ID_0_fpv_000_150/gpt_video/tags.json
{
  "dynamic": [
    "hand",
    "arm"
  ]
}
data/prin_ID_0_15_30/ID_0_cam_tpv_000_150/gpt_video/tags.json
{
  "dynamic": [
    "hand",
    "arm"
  ]
}
```

### Passo 6: Run SAM2 / GroundingDINO segmentation

Riporto il testo del README riguardo il passo 6:

---
Run the VisualSync segmentation step:

```bash
python preprocess/run_dino_sam2.py --workdir "$DATA_ROOT"
```

The terminal output should show which tags are being used. For this pipeline, it should use the `gpt_video/tags.json` files created in the previous step.

Check masks:

```bash
find "$DATA_ROOT" -path "*/$MASK_PREFIX/Annotations" -type d | sort
```

Expected folders:

```text
$DATA_ROOT/ID_0_cam_top_000_150/deva_improved/Annotations
$DATA_ROOT/ID_0_cam_tpv_000_150/deva_improved/Annotations
$DATA_ROOT/ID_0_fpv_000_150/deva_improved/Annotations
```
---


~~Abbiamo installato i seguenti moduli (torch, supervision, torchvision, hydra-core, iopath)~~ (già nel venv se attivo)

 - **TENTATIVO 2 (prima volta che si arrivava al passo 6)**:
 L'esecuzione per la segmentazione del gruppo ID_0 è durata circa 16 ore e 46 minuti
 - **TENTATIVO 3**: La segmentazione del gruppo ID_0 è durata 44 minuti e 22 secondi

Il comando per vedere se l'esecuzione è andata a buon fine riporta proprio quello che ci si aspettava (in entrambi i tentativi)
```bash
data/prin_ID_0_15_30/ID_0_cam_top_000_150/deva_improved/Annotations
data/prin_ID_0_15_30/ID_0_cam_tpv_000_150/deva_improved/Annotations
data/prin_ID_0_15_30/ID_0_fpv_000_150/deva_improved/Annotations
```

### Passo 7: Run VGGT camera estimation

Riporto il testo del README riguardo il passo 7:

---

Run:

```bash
python preprocess/vggt_to_colmap.py --workdir "$DATA_ROOT" --vis_path vggt_output --save_colmap
```

Check:

```bash
find "$DATA_ROOT" -path "*/vggt/*.npz" -type f | sort
```

Expected:

```text
camera_parameters.npz
```

Do not use `--vggt_choice full` unless `camera_parameters_full.npz` exists

--- 
Come abbiamo detto nei passi precedenti, abbiamo dovuto cambiare server per avere una versione di CUDA maggiore in quanto l'esecuzione del passo 7 non andava a buon fine (nel secondo tentativo).

Nel terzo tentativo abbiamo avuto un ulteriore errore sempre dovuto all'incompatibilità della versione di CUDA con la libreria torch:
```
/app/Progetto/visualsync/vissync/lib/python3.10/site-packages/torch/cuda/__init__.py:187: UserWarning: CUDA initialization: The NVIDIA driver on your system is too old (found version 12020). Please update your GPU driver by downloading and installing a new version from the URL: http://www.nvidia.com/Download/index.aspx Alternatively, go to: https://pytorch.org to install a PyTorch version that has been compiled with your version of the CUDA driver. (Triggered internally at /pytorch/c10/cuda/CUDAFunctions.cpp:119.)
  return torch._C._cuda_getDeviceCount() > 0
Using device: cpu
Working on sports: {'ID_0'}
Processing sport: ID_0
Found 152 images in ID_0 dataset.
Found 152 images in ID_0 dataset.
VGGT refs for ID_0: total=152, static_anchors=2, dynamic=150
Using max_images_per_chunk=32
Running VGGT in 5 chunks
[VGGT chunk 1/5] images=32
Preprocessed chunk shape: torch.Size([32, 3, 518, 518])
Traceback (most recent call last):
  File "/app/Progetto/visualsync/preprocess/vggt_to_colmap.py", line 1070, in <module>
    main()
  File "/app/Progetto/visualsync/preprocess/vggt_to_colmap.py", line 1005, in main
    predictions, references, all_ratios = process_sport_with_vggt(BASE, sport, device, model, args.sampling_mode, args.max_images_per_chunk)
  File "/app/Progetto/visualsync/preprocess/vggt_to_colmap.py", line 951, in process_sport_with_vggt
    pred, refs, ratios = _run_vggt_once(base, chunk_refs, device, model)
  File "/app/Progetto/visualsync/preprocess/vggt_to_colmap.py", line 819, in _run_vggt_once
    dtype = torch.bfloat16 if torch.cuda.get_device_capability()[0] >= 8 else torch.float16
  File "/app/Progetto/visualsync/vissync/lib/python3.10/site-packages/torch/cuda/__init__.py", line 682, in get_device_capability
    prop = get_device_properties(device)
  File "/app/Progetto/visualsync/vissync/lib/python3.10/site-packages/torch/cuda/__init__.py", line 699, in get_device_properties
    _lazy_init()  # will define _get_device_properties
  File "/app/Progetto/visualsync/vissync/lib/python3.10/site-packages/torch/cuda/__init__.py", line 491, in _lazy_init
    torch._C._cuda_init()
RuntimeError: The NVIDIA driver on your system is too old (found version 12020). Please update your GPU driver by downloading and installing a new version from the URL: http://www.nvidia.com/Download/index.aspx Alternatively, go to: https://pytorch.org to install a PyTorch version that has been compiled with your version of the CUDA driver.
```

Per risolvere abbiamo fatto i seguenti comandi per ridurre la versione di torch ( quella di prima necessitava di CUDA13):
```bash
pip uninstall torch torchvision torchaudio -y

pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

Poi potrebbe servire reinstallare le dipendenze di SAM2
```bash
cd /app/Progetto/visualsync/Grounded-SAM-2
pip install --no-build-isolation -e .
```
```bash
cd grounding_dino
pip install --no-build-isolation .
```

Facendo il comando riportato dal README per fare il check, viene stampato:
```bash
data/prin_ID_0_15_30/ID_0_cam_top_000_150/vggt/camera_parameters.npz
data/prin_ID_0_15_30/ID_0_cam_tpv_000_150/vggt/camera_parameters.npz
data/prin_ID_0_15_30/ID_0_fpv_000_150/vggt/camera_parameters.npz
```
### Passo 8: Run CoTracker

Riporto il testo del README riguardo il passo 8:

---

Use the SAM2 masks directly:

```bash
--mask_prefix "$MASK_PREFIX"
```

Run TOP and TPV with denser settings:

```bash
rm -rf "$TRACK_ROOT"
mkdir -p "$TRACK_ROOT"

python src/run_cotracker_all.py --dataset_root "$DATA_ROOT" --track_root "$TRACK_ROOT" --gpu 0 --mask_prefix "$MASK_PREFIX" --only static --static_interval 3 --static_grid_step 5 --skip_exist
```

Run FPV more conservatively because it is much slower:

```bash
python src/run_cotracker_all.py --dataset_root "$DATA_ROOT" --track_root "$TRACK_ROOT" --gpu 0 --mask_prefix "$MASK_PREFIX" --only fpv --dynamic_interval 8 --dynamic_grid_step 10 --skip_exist
```

If FPV becomes too sparse, rerun only FPV with a denser setting:

```bash
python src/run_cotracker_all.py --dataset_root "$DATA_ROOT" --track_root "$TRACK_ROOT" --gpu 0 --mask_prefix "$MASK_PREFIX" --only fpv --dynamic_interval 5 --dynamic_grid_step 8
```

Check:

```bash
find "$TRACK_ROOT" -name "tracks.pkl" | sort
```

Expected:

```text
$TRACK_ROOT/ID_0_cam_top_000_150/tracks.pkl
$TRACK_ROOT/ID_0_cam_tpv_000_150/tracks.pkl
$TRACK_ROOT/ID_0_fpv_000_150/tracks.pkl
```
---

Inizialmente non erano state installate le dipendenze per coTracker. Questo comportava un errore quando lanciavamo lo script `src/run_cotracker_all.py`. Per risolverlo abbiamo dovuto installare le dipendenze con i seguenti comandi:

```bash
cd /app/Progetto/visualsync/co-tracker
pip install -e .
```



Inoltre è occorso un ulteriore errore dovuto ad una stringa hard-coded che indicava un path non effettivamente esistente nel nostro file system. Infatti a riga `700` dello script in `src/run_cotracker_v5.py` (che viene lanciato dall'interno di `src/run_cotracker_all.py`) avevamo la seguente riga:
```python
torch.hub.load("/home/vrai/anilegin/visualsync/co-tracker", "cotracker3_offline", source="local")
```

Ed è stata sostituita con la seguente che invece utilizza un path relativo. Perciò, il comando del passo 8, va lanciato da visualsync:
```python
torch.hub.load("co-tracker", "cotracker3_offline", source="local")
```

Dopo aver fatto i due comandi, dal comando di check viene stampato ciò che ci aspettavamo

### Passo 9: Run MASt3R image matching

Riporto il testo del README riguardo il passo 9:

---
Create result root:

```bash
rm -rf "$RESULT_ROOT"
mkdir -p "$RESULT_ROOT/$GROUP"
```

#### 9.1 TOP–TPV

```bash
CUDA_VISIBLE_DEVICES=0 python src/img_match_v4.py --dataset_root "$DATA_ROOT" --video1_name "${GROUP}_cam_top_000_150" --video2_name "${GROUP}_cam_tpv_000_150" --save_root "$RESULT_ROOT/$GROUP" --mask_prefix "$MASK_PREFIX" --interval 2 --batch_size 16 --filter_mask --enable_blurry
```

#### 9.2 TPV–FPV

```bash
CUDA_VISIBLE_DEVICES=0 python src/img_match_v4.py --dataset_root "$DATA_ROOT" --video1_name "${GROUP}_cam_tpv_000_150" --video2_name "${GROUP}_fpv_000_150" --save_root "$RESULT_ROOT/$GROUP" --mask_prefix "$MASK_PREFIX" --interval 3 --batch_size 16 --filter_mask --enable_blurry
```

#### 9.3 Optional TOP–FPV diagnostic

```bash
CUDA_VISIBLE_DEVICES=0 python src/img_match_v4.py --dataset_root "$DATA_ROOT" --video1_name "${GROUP}_cam_top_000_150" --video2_name "${GROUP}_fpv_000_150" --save_root "$RESULT_ROOT/$GROUP" --mask_prefix "$MASK_PREFIX" --interval 3 --batch_size 16 --filter_mask --enable_blurry
```

---

Come nel passo precedente, abbiamo avuto un errore dovuto alla mancanza delle dipendenze di mast3r. Per risolverlo eseguiamo i seguenti comandi che installano le dipendenze. 

**Non** abbiamo potuto fare i seguenti comandi perchè mast3r non è installabile con pip 
```bash
pip install -e .
Obtaining file:///app/Progetto/visualsync/mast3r
ERROR: file:///app/Progetto/visualsync/mast3r does not appear to be a Python project: neither 'setup.py' nor 'pyproject.toml' found.
```

Perciò quello che abbiamo fatto è aggiungere mast3r e dust3r al PYTHONPATH. Però, prima di aggiungerlo dobbiamo installare le dipendenze di mast3r e dust3r con i comandi:

```bash
pip install -r requirements.txt
pip install -r dust3r/requirements.txt
```
Però, prima di eseguire i comandi precedenti, ci siamo accorti che il submodule di dust3r non era stato correttamente inizializzato (infatti era vuoto). Per correggere abbiamo fatto il comando:

```bash
git submodule update --init --recursive
```

Inoltre, prima di eseguire i comandi per l'installazione delle dipendenze di mast3r e dust3r, abbiamo controllato che non venisse modificata la versioen di torch con cui avevamo avuto problemi con la compatibilità con CUDA

Solo dopo abbiamo aggiunto mast3r e dust3r al PYTHONPATH con il comando:

```bash
export PYTHONPATH="/app/Progetto/visualsync/mast3r:/app/Progetto/visualsync/mast3r/dust3r:$PYTHONPATH"
```
Questo è stato poi aggiunto allo script per il set delel variabili globali, cioè `scripts/custom_scripts/set_globals_variables.sh`.

Riportiamo i tempi di esecuzione per ogni coppia di telecamere:
- 9.1 TOP-TPV:
  ```bash
  100%|██████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 352/352 [10:43<00:00,  1.83s/it]
  done!
  ```
- 9.2 TPV-FPV:
  ```bash
  100%|██████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 157/157 [06:36<00:00,  2.52s/it]
  done!
  ```
- 9.3 TOP-FPV:
  ```bash
  100%|██████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 157/157 [06:32<00:00,  2.50s/it]
  done!
  ```

### Passo 10: Filter track correspondences

Riporto il testo del README riguardo il passo 10:

---

Use relaxed thresholds for action-specific masks:

```text
min_matches = 3
pixel_tol = 10
min_neighbors = 1
```

#### 10.1 TOP–TPV

```bash
CUDA_VISIBLE_DEVICES=0 python src/filter_corr_v2.py --dataset_root "$DATA_ROOT" --result_root "$RESULT_ROOT" --track_root "$TRACK_ROOT" --result_name1 "${GROUP}_cam_top_000_150" --result_name2 "${GROUP}_cam_tpv_000_150" --group_prefix "$GROUP" --mask_prefix "$MASK_PREFIX" --min_matches 3 --pixel_tol 10 --min_neighbors 1 --max_batch_size 4096
```

#### 10.2 TPV–FPV

```bash
CUDA_VISIBLE_DEVICES=0 python src/filter_corr_v2.py --dataset_root "$DATA_ROOT" --result_root "$RESULT_ROOT" --track_root "$TRACK_ROOT" --result_name1 "${GROUP}_cam_tpv_000_150" --result_name2 "${GROUP}_fpv_000_150" --group_prefix "$GROUP" --mask_prefix "$MASK_PREFIX" --min_matches 3 --pixel_tol 10 --min_neighbors 1 --max_batch_size 4096
```

#### 10.3 Optional TOP–FPV

```bash
CUDA_VISIBLE_DEVICES=0 python src/filter_corr_v2.py --dataset_root "$DATA_ROOT" --result_root "$RESULT_ROOT" --track_root "$TRACK_ROOT" --result_name1 "${GROUP}_cam_top_000_150" --result_name2 "${GROUP}_fpv_000_150" --group_prefix "$GROUP" --mask_prefix "$MASK_PREFIX" --min_matches 3 --pixel_tol 10 --min_neighbors 1 --max_batch_size 4096
```

Check outputs:

```bash
find "$RESULT_ROOT/$GROUP" -name "tracks_match_v2.npz" -exec ls -lh {} \;
```
---

Il risultato dal comando di checking è:
```bash
-rw-r--r-- 1 root root 19M Jun 17 10:11 results/prin_ID_0_15_30/ID_0/ID_0_cam_top_000_150__ID_0_cam_tpv_000_150/tracks_match_v2.npz
-rw-r--r-- 1 root root 93M Jun 17 10:19 results/prin_ID_0_15_30/ID_0/ID_0_cam_top_000_150__ID_0_fpv_000_150/tracks_match_v2.npz
-rw-r--r-- 1 root root 89M Jun 17 10:15 results/prin_ID_0_15_30/ID_0/ID_0_cam_tpv_000_150__ID_0_fpv_000_150/tracks_match_v2.npz
```

### Passo 11: Run VisualSync offset estimation

Riporto il testo del README riguardo il passo 11:

---
Use a constrained search range for cropped action windows:

```text
offset_range = 25
```

Large ranges can create false minima, especially with FPV.

#### 11.1 TOP–TPV

```bash
CUDA_VISIBLE_DEVICES=0 python src/shaowei_sync_v6.py \
  --dataset_root "$DATA_ROOT" \
  --result_root "$RESULT_ROOT" \
  --video1_name "${GROUP}_cam_top_000_150" \
  --video2_name "${GROUP}_cam_tpv_000_150" \
  --offset_range 25 \
  --moving_threshold 0.5 \
  --pixel_threshold 4 \
  --max_batch_size 4096 \
  --max_N 30000 \
  --use_v2 \
  --use_vggt \
  --disable_gt
```

#### 11.2 TPV–FPV

```bash
CUDA_VISIBLE_DEVICES=0 python src/shaowei_sync_v6.py \
  --dataset_root "$DATA_ROOT" \
  --result_root "$RESULT_ROOT" \
  --video1_name "${GROUP}_cam_tpv_000_150" \
  --video2_name "${GROUP}_fpv_000_150" \
  --offset_range 25 \
  --moving_threshold 0.5 \
  --pixel_threshold 4 \
  --max_batch_size 4096 \
  --max_N 30000 \
  --use_v2 \
  --use_vggt \
  --disable_gt
```

#### 11.3 Optional TOP–FPV

```bash
CUDA_VISIBLE_DEVICES=0 python src/shaowei_sync_v6.py \
  --dataset_root "$DATA_ROOT" \
  --result_root "$RESULT_ROOT" \
  --video1_name "${GROUP}_cam_top_000_150" \
  --video2_name "${GROUP}_fpv_000_150" \
  --offset_range 25 \
  --moving_threshold 0.5 \
  --pixel_threshold 4 \
  --max_batch_size 4096 \
  --max_N 30000 \
  --use_v2 \
  --use_vggt \
  --disable_gt
```

### Passo 12: Collect offsets and create merged video

Riporto il testo del README riguardo il passo 12:

---

Use the collector script to summarize pairwise candidates, estimate global offsets, and create a merged video:

```bash
python src/collect_sync_results.py \
  --dataset_root "$DATA_ROOT" \
  --result_root "$RESULT_ROOT" \
  --group_name "$GROUP" \
  --fps "$FPS" \
  --max_seconds $((END_SEC-START_SEC)) \
  --panel_height 480 \
  --ignore_pair "${GROUP}_cam_top_000_150__${GROUP}_fpv_000_150"
```

This creates:

```text
$RESULT_ROOT/pairwise_offsets.csv
$RESULT_ROOT/global_offsets.csv
$RESULT_ROOT/merged_videos/
```

Check:

```bash
cat "$RESULT_ROOT/pairwise_offsets.csv"
cat "$RESULT_ROOT/global_offsets.csv"
ls -lh "$RESULT_ROOT/merged_videos"
```

If the merged video appears sign-reversed, regenerate with:

```bash
python src/collect_sync_results.py \
  --dataset_root "$DATA_ROOT" \
  --result_root "$RESULT_ROOT" \
  --group_name "$GROUP" \
  --fps "$FPS" \
  --max_seconds $((END_SEC-START_SEC)) \
  --panel_height 480 \
  --offset_sign -1 \
  --out_video_dir "$RESULT_ROOT/merged_videos_flip" \
  --ignore_pair "${GROUP}_cam_top_000_150__${GROUP}_fpv_000_150"
```

---
---

## ESPERIMENTI

### 4a esecuzione:
**Obiettivo:**: Dopo l'esecuzione del terzo tentativo che è andato a buon fine. Ne eseguiamo un quarto per testare uno script che andiamo a creare che ci permette di eseguire tutti i 12 passi con un solo comando

Ricordarsi sempre di avviare il venv prima dell'esecuzione dello script.
```bash
source vissync/bin/activate
```

Il comando per lanciare, dalla cartella visualsync, lo script è:

```bash
python src/custom_scripts/exec_visualsync.py
```
Lo script è stato lanciato con le seguenti impostazioni
```text
GROUP = ID_0
START_SEC = 30
END_SEC = 45
FPS = 10
```

**Note:** Abbiamo notato che il passo 6 (sempre esoso in termini di tempo) abbia fatto l'esecuzione in meno di un minuto. Dovuto al fatto che avevamo già fatto un esecuzione sull'ID_0? Abbiamo aggiunto una funzionalità per far partire l'esecuzione da un determinato passo (utile in caso di errore intermendio)

```text
==============================
RIEPILOGO TEMPI
==============================
ID_0            | 3833.15 s = circa 63 minuti 
# Però l'esecuzione è stata fatta ripartire dal passo 8. Il tempo di esecuzione si riferisce a partire da quel punto.
```


### 5a esecuzione:
**Obiettivo:** testare, con le stesse impostazioni, un gruppo diverso da ID_0 (esecuzioni)

**Risultati:** 
Abbiamo lanciato lo script con le seguenti impostazioni
```text
GROUP = ID_1
START_SEC = 30
END_SEC = 45
FPS = 10
```

```
==============================
RIEPILOGO TEMPI
==============================
ID_1            | 4422.97 s = circa 73 minuti
```

### 6a esecuzione:
**Obiettivo:** testare con impostazioni più impegnative per il modello (maggiore minutaggio e maggiori fps). Nel paper veniva detto che DEVA e ... avevano difficoltà con frame rate bassi. Con questa esecuzione valutiamo le differenze 
```text
GROUP = ID_2
START_SEC = 15
END_SEC = 45
FPS = 20
```
Questo comporta l'avere 30 secondi di video campionizzati a 20 frame al secondo, cioè avere 600 frame analizzati rispetto ai 150 delle esecuzioni precedente

Al passo 8, l'esecuzione si è interrotta per un OutOfMemory. Abbiamo visto che nello script che viene eseguito nel passo 8 (precisamente `run_cotracker_v5.py` che però viene richiamato da `run_cotracker_all.py`) viene messa a disposizione la variabile `max_query_per_batch`. Per utilizzarlo abbiamo:
- Modificato `run_cotracker_all.py` che si occupa di propagare il comando. Quindi abbiamo messo a disposizione la variabile modificando due blocchi in questo modo:
  ```python
  parser.add_argument("--gpu", default="0")
  parser.add_argument("--mask_prefix", default="deva_improved")
  parser.add_argument("--skip_exist", action="store_true")

  parser.add_argument("--max_query_per_batch",type=int, default=1000)
  ```
    ```python
  cmd = [
          "python", "src/run_cotracker_v5.py",
          "--video_dir", str(rgb_dir),
          "--mask_dir", str(mask_dir),
          "--save_dir", str(out_dir),
          "--interval", str(interval),
          "--grid_step", str(grid_step),

          "--max_query_per_batch", str(args.max_query_per_batch),
        ]
  ```

- Cambiato il comando che lanciamo dallo script per lanciare il processo (`custom_scripts/exec_visualsync.py`):
  ```python
  ("Passo 8: Run CoTracker", [
      "rm -rf \"$TRACK_ROOT\"",
      
      "mkdir -p \"$TRACK_ROOT\"",

      "python src/run_cotracker_all.py --dataset_root \"$DATA_ROOT\" --track_root \"$TRACK_ROOT\" --gpu 0 --mask_prefix \"$MASK_PREFIX\" --only static --static_interval 3 --static_grid_step 5 --max_query_per_batch 200 --skip_exist",

      "python src/run_cotracker_all.py --dataset_root \"$DATA_ROOT\" --track_root \"$TRACK_ROOT\" --gpu 0 --mask_prefix \"$MASK_PREFIX\" --only fpv --dynamic_interval 8 --dynamic_grid_step 10 --max_query_per_batch 120 --skip_exist"
  ]),
  ```

Abbiamo fatto diversi tentativi per fare in modo che non avvenisse l'OOM ma continua ad occorrere
- Da 300 di batch size siamo passati a 200, poi 150 e anche 120 per poi stabilizzarci a 200 per le cam statiche e 120 per quelle dinamiche;
- Abbiamo aumentato i valori di `dynamic_interval` (da 8 a 12) e `dynamic_grid_step` (da 10 a 15)
- Nello script del set delle variabili globali è stata aggiunta la voce per evitare la fragmentazione della memoria
  ```bash
  export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
  ```
Dei miglioramenti ci sono stati. infatti il comando per le cam statiche va a buon fine (prima era lui ad avere OOM). L'errore adesso occorre a causa del comando per la cam dinamica.
Alla fine è stato fatto un tentativo di 15 secondi a 15 fps che è andato a buon fine.

### 7a esecuzione:
Nuovo tentativo con queste impostazioni:
```text
GROUP = ID_3
START_SEC = 30
END_SEC = 40
FPS = 20
```
Abbiamo divuto stoppare l'esecuzione al punto 10. Questo perchè abbiamo capito che lanciare i 2 comandi del passo 12 (uno per il calcolo degli offset globali normali e uno per quelli a segno invertito), il secondo sovrascriveva i csv del primo (i video rimanevano in due cartelle separate). I csv ci servono per calcolare le metriche andando a confrontare i dati del csv con quelli del ground truth (usati scripts descritti successivamente). Perciò il tempo di esecuzione è sballato (abbiamo solo quello dal passo 10 al passo 12). Però possiamo riportare le metriche:

```bash
=========================================================================
    REPORT DI VALUTAZIONE SCIENTIFICA REALE: ID_3 (@ 20.0 FPS)
=========================================================================
 [A] CONFRONTO DIRETTO DELLE VISTE (Rispetto al pivot TPV = 0.0):
     Vista TOP  | GT: -1.30s (-26.0 f) | Pred: -21.0 f | Errore: 250.00 ms
     Vista FPV  | GT: +0.69s (+13.7 f) | Pred: -25.0 f | Errore: 1936.77 ms

 [B] METRICHE COMPLESSIVE DEL PAPER (VisualSync):
     Errore Medio (Mean Error):      1093.38 ms
     Errore Mediano (Median Error):   1093.38 ms
     Accuratezza @ 100ms (A@100ms):   0.0%
     Accuratezza @ 500ms (A@500ms):   50.0%
     Area Sotto la Curva (AUC):       0.4535
=========================================================================
```

### 8a esecuzione:
Nell'ottava esecuzione abbiamo testato anche il fatto che lo script per l'esecuzioen è in grado di iterare più gruppi di video nella stessa esecuzione. Di fatti abbiamo applicato il modello su `ID_4` e `ID_5` con le stesse seguenti impostazioni:
```
START_SEC = 30
END_SEC = 40
FPS = 25
```
Lo script per l'esecuzione stampa entrambi i tempi di esecuzione in una tabella:
```
==============================
RIEPILOGO TEMPI
==============================
ID_4            | 6436.43 s
ID_5            | 8051.52 s
```

Commentiamo separatamente la valutazione dei due gruppi:
- `ID_4`: Prima di riportare la valutazione c'è da dire che solo per questo id, il gt calcolato dallo script non è corretto (di fatti con tale offset le viste non sono sincronizzate) e quindi le metriche non sono veritiere. Come verrà descritto successivamente nella sezioen del rispettivo script, sono stati fatti aggiornamenti che hanno visto un miglioramento ma comunque un errore persiste. Lascio comunque le valutazioni con la possibilità di sostituirle a problema risolto:
  ```
  =========================================================================
      REPORT DI VALUTAZIONE SCIENTIFICA REALE: ID_4 (@ 25.0 FPS)
  =========================================================================
  [A] CONFRONTO DIRETTO DELLE VISTE (Rispetto al pivot TPV = 0.0):
      Vista TOP  | GT: +5.73s (+143.3 f) | Pred: -24.0 f | Errore: 6693.33 ms
      Vista FPV  | GT: +8.02s (+200.5 f) | Pred: +17.0 f | Errore: 7341.73 ms

  [B] METRICHE COMPLESSIVE DEL PAPER (VisualSync):
      Errore Medio (Mean Error):      7017.53 ms
      Errore Mediano (Median Error):   7017.53 ms
      Accuratezza @ 100ms (A@100ms):   0.0%
      Accuratezza @ 500ms (A@500ms):   0.0%
      Area Sotto la Curva (AUC):       0.0000
  =========================================================================
  ```

- `ID_5`: Qui l'errore nel calcolo del gt sembra non esserci. Perciò le metriche di valutazioen sono corrette
  ```
  =========================================================================
      REPORT DI VALUTAZIONE SCIENTIFICA REALE: ID_5 (@ 25.0 FPS)
  =========================================================================
  [A] CONFRONTO DIRETTO DELLE VISTE (Rispetto al pivot TPV = 0.0):
      Vista TOP  | GT: -0.87s (-21.7 f) | Pred: +13.0 f | Errore: 1386.67 ms
      Vista FPV  | GT: +1.42s (+35.5 f) | Pred: +0.0 f | Errore: 1419.67 ms

  [B] METRICHE COMPLESSIVE DEL PAPER (VisualSync):
      Errore Medio (Mean Error):      1403.17 ms
      Errore Mediano (Median Error):   1403.17 ms
      Accuratezza @ 100ms (A@100ms):   0.0%
      Accuratezza @ 500ms (A@500ms):   0.0%
      Area Sotto la Curva (AUC):       0.2985
  =========================================================================
  ```

### 9a esecuzione:
Abbiamo tentato l'esecuzione a 30 fps con le seguenti impostazioni:
```
GROUP = ID_6
START_SEC = 30
END_SEC = 40
FPS = 30
```
Abbiamo avuto un problema di OOM. Quindi abbiamo ridotto l'intervallo a 9 secondi (30-39) ma il risultato è stato un ulteriore OOM
Riducendo nuovamente l'intervallo a 30-38 = 8s il problema non è occorso e l'esecuzione si è conclusa con successo:

```
==============================
RIEPILOGO TEMPI
==============================
ID_6            | 8842.28 s
```

Abbiamo fatto anche la valutazione delle metriche:
```
=========================================================================
    REPORT DI VALUTAZIONE SCIENTIFICA REALE: ID_6 (@ 30.0 FPS)
=========================================================================
 [A] CONFRONTO DIRETTO DELLE VISTE (Rispetto al pivot TPV = 0.0):
     Vista TOP  | GT: -0.90s (-27.0 f) | Pred: +25.0 f | Errore: 1733.33 ms
     Vista FPV  | GT: +0.59s (+17.6 f) | Pred: -25.0 f | Errore: 1418.90 ms

 [B] METRICHE COMPLESSIVE DEL PAPER (VisualSync):
     Errore Medio (Mean Error):      1576.12 ms
     Errore Mediano (Median Error):   1576.12 ms
     Accuratezza @ 100ms (A@100ms):   0.0%
     Accuratezza @ 500ms (A@500ms):   0.0%
     Area Sotto la Curva (AUC):       0.2120
=========================================================================
```


## SCRIPTS

Questa sezione serve per spiegare l'utilità ed il funzionamento degli script aggiunti al modello. Perlopiù si tratta di script di utilità. Prima di tutto è importante dire che è stata creata una sessione tmux per il testing e l'esecuzione di questi script cos' che siano indipendenti dall'esecuzione degli esperimenti sul modello descritti nella sezione precedente. I comandi per tmux sono:
- Per creare la sessione:
  ```bash
  tmux new -s script_tests
  ```
- Per riprendere la sessione:
  ```bash
  tmux attach -t script_tests
  ```

Inoltre controllare che il venv sia attivo altrimenti lanciare il comando:
```bash
source vissync/bin/activate
```

**NB.** Tutti gli esempi di comandi mostrati successivamente sono pensati per essere lanciati a partire dalla cartella `app/Progetto/visualsync`. Fare il comando `cd <path>` per andare nella cartella desiderata

--- 
### `set_global_variables.sh`
Questo script in bash serve per il set delle variabili globali
Va eseguito con il comando:
```bash
source scripts/custom_scripts/set_globals_variables.sh ID_<gruppo> <start_sec> <end_sec> <fps>
```
Alcuni degli script che presenteremo successivamente necessiteranno di questo comando prima o lo includono al loro interno (verrà specificato nei rispettivi comandi)

---
### `exec_visualsync.py`
Questo script in python si occupa di eseguire tutti i comandi della pipline del modello. Inizia croppando il dataset e preparandolo all'uso fino a calcolare gli offset globali e generare il video sincronizzato. 
Viene lanciato con il comando:
```bash
python src/custom_scripts/exec_visualsync.py
```

Appena eseguito comparirà a schermo un prompt che chiederà l'inserimento dei dati di input per proseguire con l'esecuzione:
- inserimento dell'id d'inizio e di fine (infatti lo script itera il range di id così da eseguire la pipeline su ogni gruppo di video senza richiedere le impostazioni di avvio)
  ```text
  ID id partenza: _
  ID di arrivo: _
  ```
- inserimento dei dati con cui settare le variabili globali utili per l'esecuzione del modello:
  ```text
  Start sec: _
  End sec: _
  FPS: _
  ```
- inserimento del passo da cui proseguire con l'esecuzione
  ```text
  Inserisci il numero del passo da cui ripartire (premi invio per iniziare dall'inizio): _
  ```
  infatti lo script implementa anche la possibilità di ripartire con l'esecuzione da un passo dove ci si era bloccati (ad esempio per un errore). Bisogna stare attenti a riinserire i dati uguali a quelli dell'esecuzione su cui ci si era bloccati.

---
### `ground_truth_extractor.py`
Questo script serve per elaborare le durate dei video del dataset per recuperare i valori di offset pairwise e globali che possono fungere da ground_truth del modello e quindi possono aiutare a valutare l'errore e quindi la bontà della risposta del modello. 

`v2`: Inizialmente la prima versione sfruttava le sole durate dei video originali e quelli sincronizzati e faceva la differenza ma il risultato non era corretto. Perciò nella versione attuale viene preso il primissimo frame del video sincronizzato e si confronta con i frame del rispettivo video orignale per vedere a che minutaggio compare così da calcolare gli offset.

`v3`: Nella terza versione si è cercato di risolvere il problema che ha afflitto il calcolo del gt per l'`ID_4` (come descritto nella rispettiva esecuzione). Si è pensato che la staticità dei video nei primi secondi poteva far risultare uguali tanti frame e quindi indurre l'errore nel calcolo del gt. Quindi si è preso come frame da confrontare quello di un istante di tempo più avanti (dove c'è più probabilità che ci sia movimento). Inoltre si è tolta la tolleranza dell'errore medio visto che si confrontano gli stessi video tagliati, l'errore tra lo stesso frame dovrebbe essere 0. L'errore per l'ID_4 sembra essersi ridotto ma persiste ugualmente. Si prevedono altre migliorie per eliminare l'errore

Questo script mette a disposizione delle funzioni che poi verranno utilizzate dal prossimo script che servirà per il calcolo delle metriche. Inoltre è comunque possibile eseguirlo per stampare sul terminale i dati (durate, offsets, ...) di alcuni gruppi di video. Si può eseguire con il comando come nel seguente esempio:
```bash
python src/custom_scripts/ground_truth_extractor.py --root "$RAW_ROOT" --ids ID_0 ID_1
```
Per eseguire questo comando con l'iniettamento della variabile globale bisogerà prima eseguire `set_global_variables.sh` (si può tralasciare anche qualsiasi parametro. L'importante e unico utilizzato qui è RAW_ROOT)

---
### `estimate_metrics.py`

Questo script serve per il calcolo delle metriche di valutazione su un gruppo di video. Quello che fa è confrontare i valori di gt ricavati dal modulo `ground_truth_extractor.py`
e quelli in output del modello e calcolare errore medio, mediano e AUC.
Da la possiblità di lanciare l'esecuzione sia direttamente da terminale passando l'id di cui fare la stima e gli fps con il comando:
```bash
python src/custom_scripts/estimate_metrics.py
```
Ovviamente bisogna anche qui impostare le variabili globali prima dell'esecuzione perchè il modulo necessita dei path dove andare a prendere i dati

---
### `video_inspector.py`

Questo script serve per ispezionare i video originali del dataset e confrontare i frame dei tre video (TPV, TOP e FPV). Lo script è stato utilizzato per vedere se il ground truth estratto dallo script `ground_truth_extractor.py` era corretto. Infatti, accertata l'errore della prima versione dello script per il calcolo del gt, questo è stato riscritto utilizzando una tecnica diversa. Per lanciare lo script per l'ispezione dei video si lancia il comando:

```bash
python src/custom_scripts/video_inspector.py
```
Ovviamente, anche questo script deve essere preceduto da un setting delle variabile globali.

---
### `run_full_validation.py`
Questo script unisce  `ground_truth_extractor.py`, `video_inspector.py` e `estimate_metrics.py` sempre previo setting delle variabili globali. Infatti serve per calcolare il gt di un ID per poi passare i valori al video inspector per essere sicuri che il gt sia corretto (è stato utile per valutare l'errore dell'ID_4) e poi passarli al calcolo delle metriche dove sono utili per calcolare l'errore.
Possiamo lanciarlo con il comando:
```bash
python src/custom_scripts/run_full_validation.py
```



## Cose da implementare

- ~~Possibile script python per definire le variabili globali tutte con un comando unico (praticamente eseguire il passo 3 con un solo comando)~~

- Capire perchè, durante il crop del dataset, la vista FPV viene fatto il source non a 30 fps ma a 29,97