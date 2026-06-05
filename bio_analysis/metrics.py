"""
Metriche ecologiche - Controlli sulla validità dei parametri biologici riscontrati
"""

import numpy as np
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)


class EcologicalMetrics:
    """
    Calcola metriche ecologiche e controlla validità dei parametri.
    """
    
    CO2_CONVERSION_FACTOR = 3.6663
    
    COVERAGE_MIN_PCT = 10
    COVERAGE_MAX_PCT = 95
    KMEANS_SILHOUETTE_THRESHOLD = 0.3
    
    def __init__(self, config: dict = None):
        self.metrics = {}
        self.warnings = []
        
        config = config or {}
        bio_params = config.get("parametri_biologici", {})
        
        self.CARBON_SINK_TC_PER_M2 = bio_params.get("co2_sequestrata_tc_m2", 0.0002)
        self.O2_PRODUCTION_L_PER_M2 = bio_params.get("o2_prodotto_l_m2_anno", 3650)
        self.VOLUME_AREA_RATIO_MIN = bio_params.get("ratio_volume_area_min_sano", 0.2)
        self.VOLUME_AREA_RATIO_MAX = 0.8
        
    def compute(
        self,
        area_posidonia_m2: float,
        area_sabbia_m2: float,
        volume_posidonia_m3: float,
        silhouette_score: float,
        max_dist_post_scaling: float,
        known_height: float = 0.70
    ) -> Tuple[dict, List[str]]:
        """
        Calcola tutte le metriche ecologiche.
        """
        logger.info("\nVALIDAZIONE BIOLOGICA")
        logger.info("-" * 70)
        
        self.warnings = []
        area_total = area_posidonia_m2 + area_sabbia_m2
        
        # === Metriche Ecologiche - sull'area della Posidonia viva
        co2_absorbed_kg_year = area_posidonia_m2 * self.CARBON_SINK_TC_PER_M2 * self.CO2_CONVERSION_FACTOR * 1000
        o2_produced_L_year = area_posidonia_m2 * self.O2_PRODUCTION_L_PER_M2
        coverage_pct = (area_posidonia_m2 / area_total * 100) if area_total > 0 else 0
        
        # === Validazione Biologica ===
        
        # Check 1: Calibration
        calibration_ok = abs(max_dist_post_scaling - known_height) < known_height * 0.05
        logger.info(f"Calibrazione RANSAC: {max_dist_post_scaling:.4f}m (Target: {known_height}m)")
        if not calibration_ok:
            self.warnings.append(f"Calibrazione fuori range: {max_dist_post_scaling:.4f}m (tolleranza: {known_height*0.05:.4f}m)")
        else:
            logger.info("  Calibrazione OK")
        
        # Check 2: Volume/Area Ratio
        ratio_vol_area = 0
        if area_posidonia_m2 > 0:
            ratio_vol_area = volume_posidonia_m3 / area_posidonia_m2
            logger.info(f"Volume/Area Ratio: {ratio_vol_area:.3f}m")
            
            if ratio_vol_area < self.VOLUME_AREA_RATIO_MIN:
                self.warnings.append(f"Ratio < {self.VOLUME_AREA_RATIO_MIN}m: Possibile diradamento o fondale ondulato")
            elif ratio_vol_area > self.VOLUME_AREA_RATIO_MAX:
                self.warnings.append(f"Ratio > {self.VOLUME_AREA_RATIO_MAX}m: Possibile rumore nelle altezze")
        else:
            self.warnings.append("Area Posidonia = 0, impossibile validare ratio")
        
        # Check 3: Coverage
        logger.info(f"Copertura Posidonia: {coverage_pct:.1f}%")
        if coverage_pct < self.COVERAGE_MIN_PCT:
            self.warnings.append(f"Copertura < {self.COVERAGE_MIN_PCT}%: Area fortemente degradata")
        elif coverage_pct > self.COVERAGE_MAX_PCT:
            self.warnings.append(f"Copertura > {self.COVERAGE_MAX_PCT}%: Copertura vicina al limite massimo")
        
        # Check 4: K-Means clustering quality
        logger.info(f"K-Means Silhouette Score: {silhouette_score:.4f}")
        if silhouette_score < 0.2:
            self.warnings.append("Clustering molto debole (silhouette < 0.2)")
        elif silhouette_score < self.KMEANS_SILHOUETTE_THRESHOLD:
            self.warnings.append(f"Clustering debole (silhouette < {self.KMEANS_SILHOUETTE_THRESHOLD})")
        
        # === Salva metriche ===
        self.metrics = {
            "area_total_m2": round(area_total, 2),
            "area_posidonia_m2": round(area_posidonia_m2, 2),
            "area_sabbia_m2": round(area_sabbia_m2, 2),
            "coverage_posidonia_pct": round(coverage_pct, 1),
            "volume_posidonia_m3": round(volume_posidonia_m3, 2),
            "volume_area_ratio": round(ratio_vol_area, 3),
            "co2_assorbita_kg_anno": round(co2_absorbed_kg_year, 2),
            "o2_prodotto_L_anno": round(o2_produced_L_year, 0),  
        }
        
        if self.warnings:
            logger.info(f"\nWARNINGS DETECTED ({len(self.warnings)}):")
            for w in self.warnings:
                logger.info(f"  {w}")
        else:
            logger.info("\nNessun warning - Dati rientrano nei range attesi.")
        
        return self.metrics, self.warnings
    
    def get_validation_report(self) -> dict:
        """Ritorna report completo di validazione."""
        return {
            "metrics": self.metrics,
            "warnings": self.warnings,
            "n_warnings": len(self.warnings),
            "passed": len(self.warnings) == 0
        }