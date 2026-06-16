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
    └── FPV/
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
 - **TENTATIVO 3**:

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
---
--- 
## Cose da implementare

- Possibile script python per definire le variabili globali tutte con un comando unico (praticamente eseguire il passo 3 con un solo comando)