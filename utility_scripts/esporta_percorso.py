import numpy as np
import trimesh

file_obj = 'OBJ/Posidonia_Porto_Cesareo_2.obj'
file_images = 'images.txt'

print("⏳ Calcolo del fattore di scala dal modello 3D...")
mesh = trimesh.load(file_obj)
vertici = mesh.vertices

# 1. Ritroviamo il nostro fattore di scala (0.70m di Posidonia)
y_fondale = np.percentile(vertici[:, 1], 2)
y_chioma = np.percentile(vertici[:, 1], 98)
altezza_arbitraria = y_chioma - y_fondale
fattore_di_scala = 0.70 / altezza_arbitraria

print(f"✅ Fattore di scala: 1 unità = {fattore_di_scala:.4f} metri")

# 2. Leggiamo le telecamere
coordinate = []
with open(file_images, "r") as f:
    for riga in f:
        if riga.startswith("#"): continue
        parti = riga.strip().split()
        if len(parti) >= 10 and (parti[-1].lower().endswith(".jpg") or parti[-1].lower().endswith(".png")):
            # COLMAP salva le coordinate. Le estraiamo e le SCALIAMO subito in metri reali!
            tx, ty, tz = float(parti[5]), float(parti[6]), float(parti[7])
            coordinate.append([tx * fattore_di_scala, ty * fattore_di_scala, tz * fattore_di_scala])

percorso = np.array(coordinate)

# 3. Salviamo in CSV per CloudCompare
np.savetxt("traiettoria_modugno.csv", percorso, delimiter=",", header="X,Y,Z", comments="")
print(f"🎯 Fatto! Salvate {len(percorso)} posizioni in 'traiettoria_modugno.csv'")