import matplotlib.pyplot as plt
import numpy as np

nome_file = 'test_manuale.jpg'

print(f"🔍 Lettura dell'immagine '{nome_file}' in corso...")

try:
    # Carica l'immagine
    img = plt.imread(nome_file)
    
    # Normalizzazione a 0-255
    if img.max() <= 1.0:
        img = (img * 255).astype(np.uint8)
        
    # Rimozione canale Alpha (se presente)
    if img.shape[2] == 4:
        img = img[:, :, :3]
        
    R = img[:, :, 0]
    G = img[:, :, 1]
    B = img[:, :, 2]
    
    # 1. SFONDO NERO (#0B0B0B = RGB 11, 11, 11 o più scuro)
    # Impostiamo la soglia a 20 per catturare anche le zone leggermente più scure come hai detto
    maschera_sfondo = (R <= 20) & (G <= 20) & (B <= 20)
    
    # 2. POSIDONIA ROSSA (#FE0000 = RGB 254, 0, 0)
    # Rileviamo il rosso acceso (Molto R, poco G, poco B)
    maschera_posidonia = (R > 200) & (G < 50) & (B < 50)
    
    # 3. SABBIA/CICATRICE (Il resto)
    # Tutto ciò che è parte del fondale ma non è stato colorato di rosso
    maschera_valida = ~maschera_sfondo
    maschera_sabbia = maschera_valida & ~maschera_posidonia
    
    # Conteggio Pixel
    pixel_validi = np.sum(maschera_valida)
    pixel_posidonia = np.sum(maschera_posidonia)
    pixel_sabbia = np.sum(maschera_sabbia)
    
    if pixel_validi == 0:
        print("❌ Errore: L'immagine sembra essere tutta nera.")
        exit()
        
    # Percentuali finali (Ground Truth)
    perc_posidonia = (pixel_posidonia / pixel_validi) * 100
    perc_sabbia = (pixel_sabbia / pixel_validi) * 100
    
    print("\n" + "="*60)
    print("📊 RISULTATI GROUND TRUTH (ANNOTAZIONE MANUALE 2D)")
    print("="*60)
    print(f"Area valida analizzata: {pixel_validi:,} pixel")
    print(f"🌿 Posidonia (Rossa) : {perc_posidonia:.1f}%")
    print(f"⚠️ Sabbia / Cicatrice: {perc_sabbia:.1f}%")
    print("="*60)
    
    # Mostra a schermo il check visivo per assicurarti che abbia "letto" bene i tuoi colori
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    axes[0].imshow(img)
    axes[0].set_title("La tua Annotazione")
    
    axes[1].imshow(maschera_posidonia, cmap='Reds')
    axes[1].set_title(f"Maschera Posidonia ({perc_posidonia:.1f}%)")
    
    axes[2].imshow(maschera_sabbia, cmap='Oranges')
    axes[2].set_title(f"Maschera Sabbia ({perc_sabbia:.1f}%)")
    
    for ax in axes:
        ax.axis('off')
    plt.tight_layout()
    plt.show()

except FileNotFoundError:
    print(f"❌ Errore: Non trovo '{nome_file}'.")