import trimesh
import os

file_obj = "OBJ//Posidonia_Porto_Cesareo_2.obj"

if not os.path.exists(file_obj):
    print(f"Errore: Il file {file_obj} non si trova nella cartella corrente.")
else:
    print(f"Caricamento del modello 3D '{file_obj}' in corso...")
    
    mesh = trimesh.load(file_obj)
    
    dimensioni = mesh.extents
    
    print("\n" + "="*50)
    print("TEST DIMENSIONI COMPLETATO")
    print("="*50)
    print(f"Larghezza (X): {dimensioni[0]:.2f}")
    print(f"Profondità (Y): {dimensioni[1]:.2f}")
    print(f"Altezza (Z): {dimensioni[2]:.2f}")
    print("="*50)
    
    if dimensioni[0] < 500:
        print("IPOTESI: Il modello sembrerebbe essere scalato in coordinate metriche.")
    else:
        print("IPOTESI: Il modello sembrerebbe in millimetri o in coordinate arbitrarie.")