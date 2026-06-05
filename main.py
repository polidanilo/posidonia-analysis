from bio_analysis.pipeline import AnalysisPipeline
import os
import json
import tkinter as tk
from tkinter import filedialog

def seleziona_file_graficamente():
    """Apre la finestra di sistema per selezionare un file"""
    root = tk.Tk()
    root.withdraw() 
    root.attributes('-topmost', True)
    file_path = filedialog.askopenfilename(
        title="Seleziona il rilievo 3D da analizzare",
        filetypes=[("File 3D", "*.obj *.las *.ply"), ("Tutti i file", "*.*")]
    )
    return file_path

if __name__ == "__main__":
    print("=========================================")
    print("  POSIDONIA ANALYSIS ")
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
    
    # 2. SELEZIONE MODALITA' DI ANALISI
    print("\nSeleziona la modalità di analisi:")
    print("  [1] Intera cartella dei frammenti PLY (data/input/PLY/)")
    print("  [2] Singolo rilievo 3D (.obj, .las, .ply) dal PC")
    
    scelta = input("\nDigita 1 o 2 e premi Invio: ").strip()
    
    if scelta == "1":
        print("\nAvvio analisi automatica della cartella PLY...")
        risultati = analyzer.run_tiled_ply('data/input/PLY/')
        
    elif scelta == "2":
        print("\nSeleziona il file dalla finestra di dialogo appena aperta...")
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
        print(f"\nAnalisi completata. I report sono disponibili nella cartella 'data/output'.")
    else:
        print(f"\nErrore durante l'elaborazione. Leggere il log per i dettagli.")