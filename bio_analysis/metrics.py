"""
Ecological Metrics & Biological Validation
"""

import numpy as np
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)


class EcologicalMetrics:
    """
    Calcola metriche ecologiche (CO2, O2) e validazione biologica.
    """
    
    # Coefficienti standard letteratura Posidonia oceanica
    CARBON_SINK_TC_PER_M2 = 0.0002  # tC/m²/anno
    CO2_CONVERSION_FACTOR = 3.6663  # moltiplica tC per avere kg CO2
    O2_PRODUCTION_L_PER_M2 = 3650  # L O2/m²/anno
    
    # Range biologicamente realistico
    VOLUME_AREA_RATIO_MIN = 0.2
    VOLUME_AREA_RATIO_MAX = 0.8
    COVERAGE_MIN_PCT = 10
    COVERAGE_MAX_PCT = 95
    KMEANS_SILHOUETTE_THRESHOLD = 0.3
    
    def __init__(self):
        self.metrics = {}
        self.warnings = []
        
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
        Calcola tutte le metriche e validazione biologica.
        
        Args:
            area_posidonia_m2: Area Posidonia in m²
            area_sabbia_m2: Area Sabbia in m²
            volume_posidonia_m3: Volume Posidonia in m³
            silhouette_score: K-Means silhouette score
            max_dist_post_scaling: Distanza massima post-scaling (calibration check)
            known_height: Altezza nota (default 0.70m)
        
        Returns:
            (metrics_dict, warnings_list)
        """
        logger.info("\n✅ VALIDAZIONE BIOLOGICA")
        logger.info("-" * 70)
        
        self.warnings = []
        area_total = area_posidonia_m2 + area_sabbia_m2
        
        # === Metriche Ecologiche ===
        co2_loss_kg_year = area_sabbia_m2 * self.CARBON_SINK_TC_PER_M2 * self.CO2_CONVERSION_FACTOR * 1000
        o2_loss_L_year = area_sabbia_m2 * self.O2_PRODUCTION_L_PER_M2
        coverage_pct = (area_posidonia_m2 / area_total * 100) if area_total > 0 else 0
        
        # === Validazione Biologica ===
        
        # Check 1: Calibration
        calibration_ok = abs(max_dist_post_scaling - known_height) < known_height * 0.05
        logger.info(f"Calibrazione RANSAC: {max_dist_post_scaling:.4f}m ≈ {known_height}m")
        if not calibration_ok:
            self.warnings.append(f"⚠️ Calibrazione fuori range: {max_dist_post_scaling:.4f}m (tolleranza ±{known_height*0.05:.4f}m)")
        else:
            logger.info("   ✅ Calibrazione OK")
        
        # Check 2: Volume/Area Ratio
        ratio_vol_area = 0
        if area_posidonia_m2 > 0:
            ratio_vol_area = volume_posidonia_m3 / area_posidonia_m2
            logger.info(f"Volume/Area Ratio: {ratio_vol_area:.3f}m (atteso: {self.VOLUME_AREA_RATIO_MIN}-{self.VOLUME_AREA_RATIO_MAX}m)")
            
            if ratio_vol_area < self.VOLUME_AREA_RATIO_MIN:
                self.warnings.append(f"⚠️ Ratio < {self.VOLUME_AREA_RATIO_MIN}m: Posidonia sottostimata o fondale ondulato")
            elif ratio_vol_area > self.VOLUME_AREA_RATIO_MAX:
                self.warnings.append(f"⚠️ Ratio > {self.VOLUME_AREA_RATIO_MAX}m: Possibile rumore negli altezze")
            else:
                logger.info("   ✅ Biologicamente realistico")
        else:
            self.warnings.append("❌ Area Posidonia = 0, impossibile validare ratio")
        
        # Check 3: Coverage
        logger.info(f"Copertura Posidonia: {coverage_pct:.1f}%")
        if coverage_pct < self.COVERAGE_MIN_PCT:
            self.warnings.append(f"⚠️ Copertura < {self.COVERAGE_MIN_PCT}%: Area molto degradata")
        elif coverage_pct > self.COVERAGE_MAX_PCT:
            self.warnings.append(f"⚠️ Copertura > {self.COVERAGE_MAX_PCT}%: Danneggiamento minimo (verificare dati)")
        else:
            logger.info("   ✅ Ragionevole")
        
        # Check 4: K-Means clustering quality
        logger.info(f"K-Means Silhouette Score: {silhouette_score:.4f}")
        if silhouette_score < 0.2:
            self.warnings.append(f"❌ Clustering molto debole (silhouette < 0.2)")
        elif silhouette_score < self.KMEANS_SILHOUETTE_THRESHOLD:
            self.warnings.append(f"⚠️ Clustering debole (silhouette < {self.KMEANS_SILHOUETTE_THRESHOLD})")
        else:
            logger.info("   ✅ Clustering robusto")
        
        # === Salva metriche ===
        self.metrics = {
            "area_total_m2": round(area_total, 2),
            "area_posidonia_m2": round(area_posidonia_m2, 2),
            "area_sand_cicatrice_m2": round(area_sabbia_m2, 2),
            "coverage_posidonia_pct": round(coverage_pct, 1),
            "volume_posidonia_m3": round(volume_posidonia_m3, 2),
            "volume_area_ratio": round(ratio_vol_area, 3),
            "co2_loss_kg_year": round(co2_loss_kg_year, 2),
            "o2_loss_L_year": round(o2_loss_L_year, 0),
        }
        
        # === Summary ===
        if self.warnings:
            logger.info(f"\n🔴 WARNINGS DETECTED ({len(self.warnings)}):")
            for w in self.warnings:
                logger.info(f"   {w}")
        else:
            logger.info("\n✅ Nessun warning - Dati validati correttamente!")
        
        return self.metrics, self.warnings
    
    def get_validation_report(self) -> dict:
        """Ritorna report completo di validazione."""
        return {
            "metrics": self.metrics,
            "warnings": self.warnings,
            "n_warnings": len(self.warnings),
            "passed": len(self.warnings) == 0
        }
