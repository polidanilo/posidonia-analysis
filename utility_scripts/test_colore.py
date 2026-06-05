import matplotlib.pyplot as plt
import numpy as np

nome_file = 'test_manuale.jpg'

print(f"Lettura dell'immagine '{nome_file}' in corso...")

try:
    img = plt.imread(nome_file)
    
    if img.max() <= 1.0:
        img = (img * 255).astype(np.uint8)
        
    if img.shape[2] == 4:
        img = img[:, :, :3]
        
    R = img[:, :, 0]
    G = img[:, :, 1]
    B = img[:, :, 2]
    
    # 1. SFONDO NERO 
    maschera_sfondo = (R <= 20) & (G <= 20) & (B <= 20)
    
    # 2. POSIDONIA ROSSA
    maschera_posidonia = (R > 200) & (G < 50) & (B < 50)
    
    # 3. SABBIA
    maschera_valida = ~maschera_sfondo
    maschera_sabbia = maschera_valida & ~maschera_posidonia
    
    pixel_validi = np.sum(maschera_valida)
    pixel_posidonia = np.sum(maschera_posidonia)
    pixel_sabbia = np.sum(maschera_sabbia)
    
    if pixel_validi == 0:
        print("Errore: L'immagine sembra essere vuota/tutta nera.")
        exit()
        
    perc_posidonia = (pixel_posidonia / pixel_validi) * 100
    perc_sabbia = (pixel_sabbia / pixel_validi) * 100
    
    print("\n" + "="*60)
    print(" RISULTATI GROUND TRUTH (ANNOTAZIONE MANUALE 2D)")
    print("="*60)
    print(f"Area valida analizzata: {pixel_validi:,} pixel")
    print(f"Posidonia (Rossa): {perc_posidonia:.1f}%")
    print(f"Sabbia nuda: {perc_sabbia:.1f}%")
    print("="*60)
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    axes[0].imshow(img)
    axes[0].set_title("Ortofoto Originale (Annotata)")
    
    axes[1].imshow(maschera_posidonia, cmap='Reds')
    axes[1].set_title(f"Maschera Posidonia ({perc_posidonia:.1f}%)")
    
    axes[2].imshow(maschera_sabbia, cmap='Oranges')
    axes[2].set_title(f"Maschera Sabbia ({perc_sabbia:.1f}%)")
    
    for ax in axes:
        ax.axis('off')
    plt.tight_layout()
    plt.show()

except FileNotFoundError:
    print(f"Errore di sistema: Non trovo '{nome_file}'.")