"""
Posidonia Segmenter - K-Means clustering per segmentazione sand/posidonia
"""

import numpy as np
from scipy.stats import binned_statistic_2d
import scipy.ndimage as ndimage
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class PosidoniaSegmenter:
    """
    Segmenta la nuvola di punti in Posidonia (scura) e Sabbia (chiara).
    Usa K-Means clustering per soglia obiettiva (rimuove p-hacking).
    """
    
    def __init__(self, cell_size: float = 0.10):
        """
        Args:
            cell_size: Dimensione cella griglia (metri)
        """
        self.cell_size = cell_size
        self.luminanza_grid = None
        self.altezze_grid = None
        self.celle_valide = None
        self.kmeans = None
        self.threshold_luminanza = None
        self.silhouette = None
        
    def segment(self, vertices_scaled: np.ndarray, colors: np.ndarray) -> Tuple[np.ndarray, np.ndarray, dict]:
        """
        Segmenta la nuvola in grid e usa K-Means per soglia di luminanza.
        
        Args:
            vertices_scaled: Array (N, 3) in metri reali
            colors: Array (N, 4) con colori RGBA
        
        Returns:
            (mask_posidonia, mask_sabbia, segmentation_info)
        """
        logger.info("🧠 K-Means Clustering per soglia di luminanza (rimuove p-hacking)...")
        
        # Step 1: Calcola griglia spaziale
        x = vertices_scaled[:, 0]
        y = vertices_scaled[:, 1]
        z = vertices_scaled[:, 2]
        
        larghezza = x.max() - x.min()
        profondita = z.max() - z.min()
        x_bins = int(np.ceil(larghezza / self.cell_size))
        z_bins = int(np.ceil(profondita / self.cell_size))
        
        logger.info(f"  -> Griglia: {x_bins} x {z_bins} celle ({self.cell_size}m)")
        
        # Step 2: Calcola griglia altezze (min_y e max_y per cella)
        min_y, x_edge, z_edge, _ = binned_statistic_2d(
            x, z, y, statistic='min', bins=[x_bins, z_bins]
        )
        max_y, _, _, _ = binned_statistic_2d(
            x, z, y, statistic='max', bins=[x_edge, z_edge]
        )
        self.altezze_grid = max_y - min_y
        
        # Step 3: Calcola griglia luminanza (R+G+B)/3
        luminanza = (
            colors[:, 0].astype(float) + 
            colors[:, 1].astype(float) + 
            colors[:, 2].astype(float)
        ) / 3.0
        
        luminanza_media, _, _, _ = binned_statistic_2d(
            x, z, luminanza, statistic='mean', bins=[x_edge, z_edge]
        )
        self.luminanza_grid = luminanza_media
        
        # Step 4: K-Means 2D (Luminanza + Altezza) per massima precisione
        logger.info("🧠 K-Means 2D (Luminanza + Altezza) - Upgrade per massima precisione...")
        
        self.celle_valide = ~np.isnan(luminanza_media)
        
        # Estraiamo luminanza e altezza per le celle valide
        lum_validi = luminanza_media[self.celle_valide]
        alt_validi = self.altezze_grid[self.celle_valide]
        
        if len(lum_validi) < 2:
            raise ValueError("Troppo poche celle valide per clustering")
        
        # Creiamo matrice features con due colonne: (Luminanza, Altezza)
        features = np.column_stack((lum_validi, alt_validi))
        
        # Normalizziamo i dati (FONDAMENTALE: Luminanza 0-255, Altezza 0-1.5m)
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        # Addestriamo K-Means 2D
        self.kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
        labels = self.kmeans.fit_predict(features_scaled)
        
        # Identifichiamo quale cluster è Posidonia (altezza MAGGIORE)
        centro_0_altezza = np.mean(alt_validi[labels == 0])
        centro_1_altezza = np.mean(alt_validi[labels == 1])
        
        if centro_0_altezza > centro_1_altezza:
            posidonia_label = 0
            sabbia_label = 1
        else:
            posidonia_label = 1
            sabbia_label = 0
        
        # Calcoliamo Silhouette Score (campione se dati troppi)
        if len(features_scaled) > 10000:
            idx = np.random.choice(len(features_scaled), 10000, replace=False)
            self.silhouette = silhouette_score(features_scaled[idx], labels[idx])
        else:
            self.silhouette = silhouette_score(features_scaled, labels)
        
        # Info clustering
        centro_0_lum = np.mean(lum_validi[labels == 0])
        centro_1_lum = np.mean(lum_validi[labels == 1])
        
        logger.info(f"  -> Cluster 0: Lum={centro_0_lum:.1f}, Alt={centro_0_altezza:.3f}m {'(POSIDONIA)' if posidonia_label == 0 else '(SABBIA)'}")
        logger.info(f"  -> Cluster 1: Lum={centro_1_lum:.1f}, Alt={centro_1_altezza:.3f}m {'(POSIDONIA)' if posidonia_label == 1 else '(SABBIA)'}")
        logger.info(f"  -> Silhouette Score: {self.silhouette:.4f} {'✅ OK' if self.silhouette > 0.3 else '⚠️ DEBOLE'}")
        logger.info("  -> Innovazione: La Posidonia è identificata come il cluster con ALTEZZA maggiore")
        logger.info("  -> Questo risolve falsi positivi da ombre sulla sabbia e foglie illuminated")
        
        if self.silhouette < 0.3:
            logger.warning("⚠️ Clustering quality bassa - possibile sovrapposizione sand/posidonia")
        
        # Step 5: Crea maschera da K-Means 2D
        maschera_posidonia_grezza = np.zeros_like(luminanza_media, dtype=bool)
        maschera_posidonia_grezza[self.celle_valide] = (labels == posidonia_label)
        maschera_posidonia_grezza = np.nan_to_num(maschera_posidonia_grezza, nan=False)
        
        # Salva la soglia per compatibilità backward
        self.threshold_luminanza = (np.mean(lum_validi[labels == 0]) + np.mean(lum_validi[labels == 1])) / 2.0
        
        # Step 6: Morphological filtering (opening/closing)
        kernel = np.ones((3, 3), dtype=bool)
        maschera_pulita = ndimage.binary_opening(maschera_posidonia_grezza, structure=kernel)
        maschera_pulita = ndimage.binary_closing(maschera_pulita, structure=kernel)
        
        # Step 7: Fix reshape bug - mantieni shape della griglia
        maschera_posidonia_full = np.zeros_like(luminanza_media, dtype=bool)
        maschera_posidonia_full[self.celle_valide] = maschera_pulita[self.celle_valide]
        
        maschera_posidonia_final = maschera_posidonia_full[self.celle_valide]
        maschera_sabbia_final = ~maschera_posidonia_final
        
        segmentation_info = {
            "method": "K-Means 2D (Luminanza + Altezza)",
            "cluster_0": {"luminanza_media": float(centro_0_lum), "altezza_media": float(centro_0_altezza), "classe": "POSIDONIA" if posidonia_label == 0 else "SABBIA"},
            "cluster_1": {"luminanza_media": float(centro_1_lum), "altezza_media": float(centro_1_altezza), "classe": "POSIDONIA" if posidonia_label == 1 else "SABBIA"},
            "threshold_luminanza": float(self.threshold_luminanza),
            "silhouette_score": float(self.silhouette),
            "n_celle_valide": int(np.sum(self.celle_valide)),
            "n_celle_posidonia": int(np.sum(maschera_posidonia_final)),
            "n_celle_sabbia": int(np.sum(maschera_sabbia_final))
        }
        
        return maschera_posidonia_final, maschera_sabbia_final, segmentation_info
    
    def get_grids(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Ritorna le griglie: (luminanza, altezze, celle_valide)"""
        return self.luminanza_grid, self.altezze_grid, self.celle_valide
