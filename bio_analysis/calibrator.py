"""
Plane Calibrator - RANSAC plane detection + scale calibration
"""

import numpy as np
from sklearn.linear_model import RANSACRegressor
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class PlaneCalibrator:
    """
    Rileva il piano del fondale con RANSAC (robusto a outlier).
    Calibra la scala usando il vincolo biologico: h_max = 0.70m.
    """
    
    def __init__(self, known_height_m: float = 0.70):
        """
        Args:
            known_height_m: Altezza massima nota della Posidonia (default: 0.70m)
        """
        self.known_height = known_height_m
        self.scale_factor = None
        self.plane_model = None
        self.distances_to_plane = None
        
    def detect_and_calibrate(self, vertices: np.ndarray):
        from sklearn.linear_model import RANSACRegressor
        import numpy as np
        import logging
        logger = logging.getLogger(__name__)
        
        # 1. Prepariamo i dati: cerchiamo di prevedere l'altezza (Y) basandoci su X e Z
        X_data = vertices[:, [0, 2]]  
        y_data = vertices[:, 1]       
        
        # 2. Addestriamo il modello RANSAC
        ransac = RANSACRegressor(random_state=42)
        ransac.fit(X_data, y_data)
        
        # 3. IL FIX: Estraiamo i coefficienti dal modello interno (estimator_)
        coef = ransac.estimator_.coef_
        intercept = ransac.estimator_.intercept_
        
        # L'equazione del piano è Y = aX + cZ + d
        # Portiamo tutto da una parte: aX - 1Y + cZ + d = 0
        a, b, c, d_plane = coef[0], -1.0, coef[1], intercept
        
        # 4. Calcoliamo la distanza perpendicolare di tutti i punti dal piano del fondale
        denom = np.sqrt(a**2 + b**2 + c**2)
        distances = np.abs(a * vertices[:, 0] + b * vertices[:, 1] + c * vertices[:, 2] + d_plane) / denom
        
        # 5. Troviamo il fattore di scala (usando il 98° percentile)
        max_dist_arbitrary = np.percentile(distances, 98)
        scale = self.known_height / max_dist_arbitrary
        self.scale_factor = scale  # <--- AGGIUNGI QUESTA RIGA!
        
        plane_info = {
            'equation': [a, b, c, d_plane],
            'max_distance_pre_scaling': max_dist_arbitrary,
            'max_distance_post_scaling': max_dist_arbitrary * scale
        }
        
        return scale, distances, plane_info

    def apply_scale(self, vertices: np.ndarray) -> np.ndarray:
        """
        Applica il fattore scala ai vertici.
        
        Args:
            vertices: Array (N, 3)
        
        Returns:
            vertices_scaled: Array (N, 3) in metri reali
        """
        if self.scale_factor is None:
            raise ValueError("Calibration non ancora effettuata. Chiama detect_and_calibrate() prima.")
        
        return vertices * self.scale_factor
    
    def get_calibration_report(self) -> dict:
        """Ritorna report della calibrazione."""
        return {
            "scale_factor": float(self.scale_factor) if self.scale_factor else None,
            "plane_model": self.plane_model,
            "calibration_ok": (
                self.scale_factor is not None and 
                abs(self.plane_model["max_distance_post_scaling"] - self.known_height) < self.known_height * 0.05
            ) if self.plane_model else False
        }
