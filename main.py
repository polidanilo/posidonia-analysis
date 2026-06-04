from bio_analysis.pipeline import AnalysisPipeline
import os

if __name__ == "__main__":
    print("🌊 Avvio Poseidonia Analyzer v2.0...")
    
    # Creiamo le cartelle di output se per caso non esistono ancora
    os.makedirs("data/output", exist_ok=True)
    
    # 1. "Accendiamo" la pipeline (inizializziamo la classe)
    # Impostiamo la cartella ordinata come destinazione per i report
    analyzer = AnalysisPipeline(output_dir="data/output")
    
    # 2. Premiamo il pulsante di avvio dicendogli di leggere la cartella PLY
    # Ora il software sa che deve andare a pescare i dati nel nuovo percorso
    risultati = analyzer.run_tiled_ply('data/input/PLY/')
    
    # 3. Un piccolo check finale per vedere se tutto è andato liscio
    if risultati.get('status') == 'success':
        print(f"\n🎉 TUTTO FINITO! I tuoi report Excel, JSON e PNG ti aspettano ordinati nella cartella 'data/output'.")
    else:
        print(f"\n❌ Ops, qualcosa è andato storto. Leggi il log qui sopra per i dettagli.")