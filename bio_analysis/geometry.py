"""
Geometry Analyzer - Calcolo area e volume
"""

import numpy as np
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class GeometryAnalyzer:
    """
    Calcola area e volume della nuvola di punti.
    Area: proiezione 2D + Delaunay (scipy non usato, griglia cells).
    Volume: grid-based voxel approach.
    """
    
    def __init__(self, cell_size: float = 0.10):
        self.cell_size = cell_size
        
    def compute_areas(
        self,
        mask_posidonia: np.ndarray,
        mask_sabbia: np.ndarray,
        celle_valide: np.ndarray
    ) -> Tuple[float, float]:
        """
        Calcola aree proiettate (XY) delle maschere.
        
        Args:
            mask_posidonia: Boolean array celle con posidonia
            mask_sabbia: Boolean array celle con sabbia
            celle_valide: Boolean array celle valide
        
        Returns:
            (area_posidonia_m2, area_sabbia_m2)
        """
        area_cella = self.cell_size ** 2
        
        n_celle_pos = np.sum(mask_posidonia)
        n_celle_sab = np.sum(mask_sabbia)
        
        area_pos_m2 = n_celle_pos * area_cella
        area_sab_m2 = n_celle_sab * area_cella
        
        logger.info(f"  -> Area Posidonia: {area_pos_m2:.2f} m² ({n_celle_pos} celle)")
        logger.info(f"  -> Area Sabbia: {area_sab_m2:.2f} m² ({n_celle_sab} celle)")
        
        return area_pos_m2, area_sab_m2
    
    def compute_volume(
        self,
        altezze_grid: np.ndarray,
        mask_posidonia: np.ndarray,
        celle_valide: np.ndarray
    ) -> float:
        """
        Calcola volume della Posidonia usando grid-based approach.
        Volume = sum(altezza_cella × area_cella) per celle Posidonia.
        
        Args:
            altezze_grid: Array altezze per cella
            mask_posidonia: Boolean array celle con posidonia
            celle_valide: Boolean array celle valide
        
        Returns:
            volume_m3
        """
        area_cella = self.cell_size ** 2
        
        altezze_valide = altezze_grid[celle_valide]
        altezze_posidonia = altezze_valide[mask_posidonia]
        
        # Filtra altezze non realistiche (0 < h < 1.5m per Posidonia)
        altezze_pulite = altezze_posidonia[
            (altezze_posidonia > 0) & (altezze_posidonia < 1.5)
        ]
        
        if len(altezze_pulite) == 0:
            logger.warning("⚠️ Nessun altezza valida per volume")
            return 0.0
        
        volume_m3 = np.sum(altezze_pulite) * area_cella
        
        logger.info(f"  -> Volume Posidonia: {volume_m3:.2f} m³")
        logger.info(f"  -> Altezza media: {np.mean(altezze_pulite):.3f} m")
        
        return volume_m3
    
    def get_geometry_report(self) -> dict:
        """Ritorna report di geometria."""
        return {
            "cell_size_m": float(self.cell_size),
            "cell_area_m2": float(self.cell_size ** 2)
        }
