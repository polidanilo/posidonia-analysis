import trimesh
import os

# Cambia il nome del file se il tuo si chiama diversamente
file_obj = "OBJ//Posidonia_Porto_Cesareo_2.obj"

if not os.path.exists(file_obj):
    print(f"❌ Errore: Il file {file_obj} non si trova nella cartella corrente.")
else:
    print(f"⏳ Caricamento del modello 3D '{file_obj}' in corso...")
    print("(Se il file è grande, potrebbe volerci qualche secondo...)")
    
    # Carica la mesh
    mesh = trimesh.load(file_obj)
    
    # Calcola il Bounding Box (la scatola che contiene tutto il 3D)
    dimensioni = mesh.extents
    
    print("\n" + "="*50)
    print("🎯 TEST DIMENSIONI COMPLETATO")
    print("="*50)
    print(f"Larghezza (X): {dimensioni[0]:.2f}")
    print(f"Profondità (Y): {dimensioni[1]:.2f}")
    print(f"Altezza (Z): {dimensioni[2]:.2f}")
    print("="*50)
    
    # Un piccolo trucco logico per aiutarti a capire
    if dimensioni[0] < 500:
        print("🟢 IPOTESI: Il modello sembra essere già scalato in METRI! Vittoria!")
    else:
        print("🟡 IPOTESI: Il modello è probabilmente in MILLIMETRI o in coordinate arbitrarie.")