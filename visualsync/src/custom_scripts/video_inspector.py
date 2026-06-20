#!/usr/bin/env python3
"""
video_inspector.py

Strumento scientifico interattivo in CLI per la verifica visiva della sincronizzazione.
Funziona in un ciclo continuo: ad ogni iterazione accetta nuovi offset, 
sovrascrive il file PNG ad alta risoluzione e stampa un riepilogo dei frame estratti.
"""

import argparse
import os
import sys
from pathlib import Path
import cv2
import numpy as np

VIEWS = ["TOP", "TPV", "FPV"]

def extract_and_save_canvas(id_dir, time_ref, offsets_sec, output_name, width_per_view):
    """Estrae i frame dai video a 30 FPS applicando gli offset e salva il PNG."""
    frames_extracted = []
    summary_data = {}

    for view in VIEWS:
        view_dir = id_dir / view
        candidates = [f for f in view_dir.glob("*") if f.suffix.lower() in [".mp4", ".mov", ".avi"]]
        
        if not candidates:
            print(f"[!] Nessun video trovato per la vista {view} in {view_dir}", file=sys.stderr)
            return None
            
        video_path = max(candidates, key=lambda f: f.stat().st_size)
        
        cap = cv2.VideoCapture(str(video_path))
        orig_fps = cap.get(cv2.CAP_PROP_FPS)
        if not orig_fps or orig_fps <= 0:
            orig_fps = 30.0 # Dataset reale del PRIN a 30 FPS
            
        # CALCOLO MATEMATICO DEL FRAME SUL VIDEO ORIGINALE (30 FPS)
        target_seconds = time_ref - offsets_sec[view]
        target_frame = int(target_seconds * orig_fps)
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            height, width = frame.shape[:2]
            new_height = int(height * (width_per_view / width))
            frame_res = cv2.resize(frame, (width_per_view, new_height))
            
            # Testo informativo sovrimpresso nel PNG
            info_text = f"{view} | Time: {time_ref}s (File: {target_seconds:.2f}s, Frame: {target_frame})"
            cv2.putText(frame_res, info_text, (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)
            frames_extracted.append(frame_res)
            
            summary_data[view] = {
                "success": True,
                "file_seconds": target_seconds,
                "frame_idx": target_frame
            }
        else:
            blank_frame = np.zeros((int(width_per_view * 0.75), width_per_view, 3), dtype=np.uint8)
            cv2.putText(blank_frame, f"{view} | FRAME NON TROVATO", (20, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)
            frames_extracted.append(blank_frame)
            summary_data[view] = {"success": False}

    # Unione orizzontale e salvataggio (sovrascrittura del file precedente)
    output_canvas = np.hstack(frames_extracted)
    cv2.imwrite(str(output_name), output_canvas)
    
    return summary_data


def main():
    env_raw_root = os.environ.get("RAW_ROOT")
    env_group = os.environ.get("GROUP")

    parser = argparse.ArgumentParser(description="Ispettore interattivo per allineamento video.")
    parser.add_argument("--root", type=Path, default=env_raw_root, help="Cartella dei video originali.")
    parser.add_argument("--id", type=str, default=env_group, help="ID dell'esperimento (es. ID_0).")
    parser.add_argument("--output_name", type=str, default="sync_interactive_check.png", help="File PNG generato.")
    parser.add_argument("--width", type=int, default=800, help="Larghezza di ogni riquadro video.")
    args = parser.parse_args()

    if not args.root or not args.id:
        parser.error("Specifica --root e --id o imposta le variabili d'ambiente RAW_ROOT e GROUP.")

    id_dir = args.root / args.id
    if not id_dir.is_dir():
        print(f"[!] Cartella non trovata: {id_dir}", file=sys.stderr)
        sys.exit(1)

    print("\n=========================================================================")
    print(f" INTERFACCIA DI VERIFICA INTERATTIVA: {args.id}")
    print("=========================================================================")
    print(f"[*] I video originali verranno analizzati a 30 FPS.")
    print(f"[*] L'immagine ad alta risoluzione verrà salvata in: {args.output_name}")
    print("    (Consiglio: lascia l'immagine aperta nel tuo visualizzatore per vederla aggiornarsi)")
    print("=========================================================================\n")

    # Stato iniziale degli offset (in secondi)
    offsets_sec = {"TOP": 0.0, "TPV": 0.0, "FPV": 0.0}
    time_ref = 5.0 # Secondo master di default iniziale
    
    # Primo rendering iniziale
    extract_and_save_canvas(id_dir, time_ref, offsets_sec, args.output_name, args.width)

    while True:
        print("\n--- IMPOSTAZIONI CORRENTI ---")
        print(f" Secondo di riferimento globale (Master): {time_ref}s")
        print(f" Offset attuali (in secondi): TOP = {offsets_sec['TOP']:.2f}s | TPV = {offsets_sec['TPV']:.2f}s | FPV = {offsets_sec['FPV']:.2f}s")
        print("-----------------------------")
        print("Cosa vuoi fare? [t = Cambia tempo master | o = Modifica offset | q = Esci]")
        scelta = input("Scegli un'opzione: ").strip().lower()

        if scelta == 'q':
            print("[*] Chiusura dell'ispettore interattivo.")
            break

        elif scelta == 't':
            try:
                nuovo_tempo = float(input("Inserisci il nuovo secondo master di riferimento (es. 10.5): "))
                time_ref = nuovo_tempo
            except ValueError:
                print("[!] Valore non valido. Riprova.")
                continue

        elif scelta == 'o':
            print("\nScegli l'unità di misura per l'inserimento:")
            print(" [1] Inserisci in SECONDI (es. 10.83 o -3.91)")
            print(" [2] Inserisci in FRAME basandoti sul modello a 10 FPS (es. 11.0 o -24.0)")
            print(" [3] Inserisci in FRAME basandoti sul modello a 15 FPS")
            tipo_input = input("Scegli (1, 2 o 3): ").strip()

            try:
                top_in = float(input(" Nuova misura per TOP: "))
                tpv_in = float(input(" Nuova misura per TPV: "))
                fpv_in = float(input(" Nuova misura per FPV: "))
                
                if tipo_input == '1':
                    offsets_sec["TOP"] = top_in
                    offsets_sec["TPV"] = tpv_in
                    offsets_sec["FPV"] = fpv_in
                elif tipo_input == '2':
                    # Conversione da frame del modello (10 FPS) a secondi
                    offsets_sec["TOP"] = top_in / 10.0
                    offsets_sec["TPV"] = tpv_in / 10.0
                    offsets_sec["FPV"] = fpv_in / 10.0
                elif tipo_input == '3':
                    # Conversione da frame del modello (15 FPS) a secondi
                    offsets_sec["TOP"] = top_in / 15.0
                    offsets_sec["TPV"] = tpv_in / 15.0
                    offsets_sec["FPV"] = fpv_in / 15.0
                else:
                    print("[!] Opzione non valida. Offset non modificati.")
                    continue
            except ValueError:
                print("[!] Input numerico errato. Operazione annullata.")
                continue
        else:
            print("[!] Opzione sconosciuta.")
            continue

        # Generazione della nuova immagine e calcolo dei dati di riepilogo
        print("\n[*] Elaborazione flussi video in corso...")
        summary = extract_and_save_canvas(id_dir, time_ref, offsets_sec, args.output_name, args.width)
        
        if summary:
            # Stampa del riepilogo a terminale (Sostituisce le informazioni a schermo della vecchia finestra)
            print("\n=========================================================================")
            print(f" RIEPILOGO COORDINATE TEMPORALI GENERATE (Video Originali a 30 FPS)")
            print("=========================================================================")
            for view in VIEWS:
                if summary[view]["success"]:
                    sec_file = summary[view]["file_seconds"]
                    idx_frame = summary[view]["frame_idx"]
                    print(f"  Vista {view:4s} -> Estratto secondo: {sec_file:6.2f}s | Indice Frame Originale: {idx_frame:5d}")
                else:
                    print(f"  Vista {view:4s} -> [ERRORE] Fuori dai limiti temporali del file")
            print("=========================================================================")
            print("[+] Immagine PNG aggiornata e salvata correttamente!")


if __name__ == "__main__":
    main()