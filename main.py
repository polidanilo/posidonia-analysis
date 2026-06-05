from bio_analysis.pipeline import AnalysisPipeline
import os
import json
import glob
import tkinter as tk
from tkinter import filedialog

def seleziona_file_graficamente():
    """Apre la finestra per selezionare un SINGOLO file"""
    root = tk.Tk()
    root.withdraw() 
    root.attributes('-topmost', True)
    file_path = filedialog.askopenfilename(
        title="Seleziona IL SINGOLO RILIEVO 3D da analizzare",
        filetypes=[("File 3D", "*.obj *.las *.ply"), ("Tutti i file", "*.*")]
    )
    return file_path

def seleziona_cartella_graficamente():
    """Apre la finestra per selezionare una CARTELLA"""
    root = tk.Tk()
    root.withdraw() 
    root.attributes('-topmost', True)
    folder_path = filedialog.askdirectory(
        title="Seleziona la CARTELLA contenente i frammenti del rilievo"
    )
    return folder_path

if __name__ == "__main__":
    print("=========================================")
    print("  Posidonia Analysis ")
    print("=========================================\n")
    
    os.makedirs("data/output", exist_ok=True)
    
    # 1. Caricamento Configurazione
    config = {}
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        print("Pannello di controllo (config.json) caricato.")
    except FileNotFoundError:
        print("File 'config.json' non trovato. Utilizzo i parametri di default.")
    
    analyzer = AnalysisPipeline(output_dir="data/output", config=config)
    
    # 2. MENU INTERATTIVO E AUTO-DETECT
    print("\nSeleziona la modalità di analisi:")
    print("  [1] Seleziona una CARTELLA (Unisce tutti i frammenti all'interno in automatico)")
    print("  [2] Seleziona un SINGOLO FILE (.obj, .las, .ply)")
    
    scelta = input("\nDigita 1 o 2 e premi Invio: ").strip()
    
    if scelta == "1":
        print("\nSeleziona la cartella dalla finestra appena aperta...")
        mia_cartella = seleziona_cartella_graficamente()
        
        if not mia_cartella:
            print("Nessuna cartella selezionata. Operazione annullata.")
            exit()
            
        # Logica Intelligente: Conta quanti file ci sono
        ply_files = glob.glob(os.path.join(mia_cartella, '*.ply'))
        n_file = len(ply_files)
        
        if n_file == 0:
            print(f"Errore: Nessun file .ply trovato nella cartella selezionata.")
            exit()
        elif n_file == 1:
            print(f"\nAuto-detect: Trovato un solo file PLY. Avvio analisi singola...")
            risultati = analyzer.run_single_file(input_path=ply_files[0], output_prefix="report_tiled_singolo")
        else:
            print(f"\nAuto-detect: Trovati {n_file} frammenti. Avvio fusione automatica e analisi...")
            risultati = analyzer.run_tiled_ply(ply_folder=mia_cartella)
            
    elif scelta == "2":
        print("\nSeleziona il file dalla finestra appena aperta...")
        mio_file = seleziona_file_graficamente()
        
        if not mio_file:
            print("Nessun file selezionato. Operazione annullata.")
            exit()
            
        print(f"\nAvvio analisi del file: {os.path.basename(mio_file)}")
        risultati = analyzer.run_single_file(input_path=mio_file, output_prefix="report_singolo")
        
    else:
        print("Scelta non valida. Riavvia il programma e digita 1 o 2.")
        exit()
    
    # 3. Chiusura
    if risultati.get('status') == 'success':
        print(f"\nAnalisi completata! I report sono disponibili nella cartella 'data/output'.")
    else:
        print(f"\nErrore durante l'elaborazione. Leggere il log per i dettagli.")