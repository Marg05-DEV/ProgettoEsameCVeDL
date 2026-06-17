#!/bin/bash

# Argomenti opzionali con valori di default
GROUP="${1:-ID_0}"
START_SEC="${2:-15}"
END_SEC="${3:-30}"
FPS="${4:-10}"

# Variabili derivate (fisse)
export RAW_ROOT="/app/Progetto/dataset/PRIN_DATASET/Video ed Excel"
export GROUP
export START_SEC
export END_SEC
export FPS
export DATA_ROOT="data/prin_${GROUP}_${START_SEC}_${END_SEC}"
export TRACK_ROOT="tracks/prin_${GROUP}_${START_SEC}_${END_SEC}"
export RESULT_ROOT="results/prin_${GROUP}_${START_SEC}_${END_SEC}"
export MASK_PREFIX="deva_improved"
export PYTHONPATH="/app/Progetto/visualsync/mast3r:/app/Progetto/visualsync/mast3r/dust3r:$PYTHONPATH"

# Riepilogo
echo "==============================="
echo " Variabili settate:"
echo "==============================="
echo "  RAW_ROOT    = $RAW_ROOT"
echo "  GROUP       = $GROUP"
echo "  START_SEC   = $START_SEC"
echo "  END_SEC     = $END_SEC"
echo "  FPS         = $FPS"
echo "  DATA_ROOT   = $DATA_ROOT"
echo "  TRACK_ROOT  = $TRACK_ROOT"
echo "  RESULT_ROOT = $RESULT_ROOT"
echo "  MASK_PREFIX = $MASK_PREFIX"
echo "==============================="