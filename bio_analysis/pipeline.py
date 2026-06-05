"""
Pipeline Orchestrator - Coordina loader → calibrator → segmenter → geometry → metrics → reporter
"""

import numpy as np
import logging
from pathlib import Path
from typing import Optional, Tuple

from .loader import PointCloudLoader
from .calibrator import PlaneCalibrator
from .segmenter import PosidoniaSegmenter
from .geometry import GeometryAnalyzer
from .metrics import EcologicalMetrics
from .reporter import ReportGenerator

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """
    Pipeline orchestrator per analisi completa di Posidonia oceanica.
    Supporta workflow singolo (single OBJ) e tiled (multiple PLY/LAS merged).
    """
    
    def __init__(self, output_dir: str = ".", cell_size: float = None, config: dict = None):
        self.output_dir = Path(output_dir)
        self.config = config or {}
        
        # Lettura parametri dal config.json
        tech_params = self.config.get("parametri_tecnici", {})
        bio_params = self.config.get("parametri_biologici", {})
        
        # Imposta le grandezze dinamiche
        self.cell_size = cell_size if cell_size is not None else tech_params.get("dimensione_cella_griglia_m", 0.10)
        self.max_height = bio_params.get("altezza_max_posidonia_m", 0.70)
        
        self.loader = PointCloudLoader()
        # Passiamo la nuova altezza al calibratore!
        self.calibrator = PlaneCalibrator(known_height_m=self.max_height)
        self.segmenter = PosidoniaSegmenter(cell_size=self.cell_size)
        self.geometry = GeometryAnalyzer(cell_size=self.cell_size)
        # Passiamo il config completo alle metriche
        self.metrics_analyzer = EcologicalMetrics(config=self.config)
        self.reporter = ReportGenerator(output_dir=str(self.output_dir))
        
        self.results = None
        
    def run_single_file(
        self,
        input_path: str,
        output_prefix: str = "report_posidonia"
    ) -> dict:
        """
        Esegue pipeline su un singolo file.
        
        Args:
            input_path: Path al file (PLY, OBJ, o LAS)
            output_prefix: Prefisso per file output
        
        Returns:
            Dictionary con risultati completi
        """
        logger.info("\n" + "="*70)
        logger.info("🚀 INIZIO ANALISI SINGLE-FILE")
        logger.info("="*70)
        
        try:
            # Step 1: Load
            logger.info(f"\n[1/6] Loading file: {input_path}")
            vertices, colors = self.loader.load(input_path)
            logger.info(f"   ✅ Caricati {len(vertices):,} vertici")
            
            # Step 2: Calibrate
            logger.info(f"\n[2/6] RANSAC Calibration")
            scale, distances, plane_info = self.calibrator.detect_and_calibrate(vertices)
            vertices_scaled = self.calibrator.apply_scale(vertices)
            logger.info(f"   ✅ Scale factor: {scale:.4f}")
            
            # Step 3: Segment
            logger.info(f"\n[3/6] K-Means Segmentation")
            mask_pos, mask_sab, seg_info = self.segmenter.segment(vertices_scaled, colors)
            logger.info(f"   ✅ Segmentazione completata")
            
            # Step 4: Geometry
            logger.info(f"\n[4/6] Area & Volume Computation")
            lum_grid, alt_grid, celle_val = self.segmenter.get_grids()
            area_pos, area_sab = self.geometry.compute_areas(mask_pos, mask_sab, celle_val)
            volume = self.geometry.compute_volume(alt_grid, mask_pos, celle_val)
            logger.info(f"   ✅ Area & Volume calcolati")
            
            # Step 5: Metrics
            logger.info(f"\n[5/6] Ecological Metrics & Validation")
            metrics, warnings = self.metrics_analyzer.compute(
                area_pos, area_sab, volume,
                seg_info['silhouette_score'],
                plane_info['max_distance_post_scaling'],
                known_height=self.max_height
            )
            logger.info(f"   ✅ Metriche completate")
            
            # Step 6: Report
            logger.info(f"\n[6/6] Report Generation")
            json_path = self.reporter.export_json(
                metrics, seg_info, self.calibrator.get_calibration_report(),
                warnings, input_path, f"{output_prefix}.json"
            )
            
            xlsx_path = self.reporter.export_excel(
                metrics, seg_info, self.calibrator.get_calibration_report(),
                warnings, lum_grid, alt_grid, celle_val, mask_pos,
                f"{output_prefix}.xlsx"
            )
            
            png_path = self.reporter.export_png(
                metrics, seg_info, warnings,
                lum_grid, alt_grid, mask_pos, celle_val,
                f"{output_prefix}.png"
            )
            
            html_3d_path = self.reporter.export_plotly_3d(
                vertices_scaled=vertices_scaled,
                mask_posidonia=mask_pos,
                celle_valide=celle_val,
                luminanza_grid=lum_grid,
                altezze_grid=alt_grid,
                metrics=metrics,
                output_filename=f"{output_prefix}_3d_interactive.html"
            )
            logger.info(f"   ✅ Report generati (inclusa visualizzazione 3D interattiva)")
            
            # Compila risultati
            self.results = {
                "status": "success",
                "input_file": str(input_path),
                "output_files": {
                    "json": json_path,
                    "excel": xlsx_path,
                    "png": png_path,
                    "html_3d": html_3d_path
                },
                "metrics": metrics,
                "validation": {
                    "warnings": warnings,
                    "passed": len(warnings) == 0
                },
                "processing_steps": {
                    "loading": len(vertices),
                    "calibration": float(scale),
                    "segmentation": seg_info,
                    "geometry": {"area_posidonia": area_pos, "volume": volume}
                }
            }
            
            logger.info("\n" + "="*70)
            logger.info("✅ ANALISI COMPLETATA CON SUCCESSO")
            logger.info("="*70)
            
            return self.results
            
        except Exception as e:
            logger.error(f"❌ Errore pipeline: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
    
    def run_tiled_ply(
        self,
        ply_folder: str,
        output_prefix: str = "report_posidonia_tiled"
    ) -> dict:
        """
        Esegue pipeline su cartella PLY (merge automatico).
        
        Args:
            ply_folder: Cartella con file .ply da fondere
            output_prefix: Prefisso per file output
        
        Returns:
            Dictionary con risultati completi
        """
        logger.info("\n" + "="*70)
        logger.info("🚀 INIZIO ANALISI TILED-PLY (MERGE AUTOMATICO)")
        logger.info("="*70)
        
        try:
            # Step 1: Load & Merge
            logger.info(f"\n[1/6] Loading & Merging PLY tiles from: {ply_folder}")
            vertices, colors = self.loader.load_tiled_ply(ply_folder)
            logger.info(f"   ✅ Caricati e fusi {len(vertices):,} vertici")
            
            # Step 2-6: Stessi step di single file
            logger.info(f"\n[2/6] RANSAC Calibration")
            scale, distances, plane_info = self.calibrator.detect_and_calibrate(vertices)
            vertices_scaled = self.calibrator.apply_scale(vertices)
            logger.info(f"   ✅ Scale factor: {scale:.4f}")
            
            logger.info(f"\n[3/6] K-Means Segmentation")
            mask_pos, mask_sab, seg_info = self.segmenter.segment(vertices_scaled, colors)
            logger.info(f"   ✅ Segmentazione completata")
            
            logger.info(f"\n[4/6] Area & Volume Computation")
            lum_grid, alt_grid, celle_val = self.segmenter.get_grids()
            area_pos, area_sab = self.geometry.compute_areas(mask_pos, mask_sab, celle_val)
            volume = self.geometry.compute_volume(alt_grid, mask_pos, celle_val)
            logger.info(f"   ✅ Area & Volume calcolati")
            
            logger.info(f"\n[5/6] Ecological Metrics & Validation")
            metrics, warnings = self.metrics_analyzer.compute(
                area_pos, area_sab, volume,
                seg_info['silhouette_score'],
                plane_info['max_distance_post_scaling'],
                known_height=self.max_height
            )
            logger.info(f"   ✅ Metriche completate")
            
            logger.info(f"\n[6/6] Report Generation")
            json_path = self.reporter.export_json(
                metrics, seg_info, self.calibrator.get_calibration_report(),
                warnings, ply_folder, f"{output_prefix}.json"
            )
            
            xlsx_path = self.reporter.export_excel(
                metrics, seg_info, self.calibrator.get_calibration_report(),
                warnings, lum_grid, alt_grid, celle_val, mask_pos,
                f"{output_prefix}.xlsx"
            )
            
            png_path = self.reporter.export_png(
                metrics, seg_info, warnings,
                lum_grid, alt_grid, mask_pos, celle_val,
                f"{output_prefix}.png"
            )
            
            html_3d_path = self.reporter.export_plotly_3d(
                vertices_scaled=vertices_scaled,
                mask_posidonia=mask_pos,
                celle_valide=celle_val,
                luminanza_grid=lum_grid,
                altezze_grid=alt_grid,
                metrics=metrics,
                output_filename=f"{output_prefix}_3d_interactive.html"
            )
            logger.info(f"   ✅ Report generati (inclusa visualizzazione 3D interattiva)")
            
            self.results = {
                "status": "success",
                "input_folder": str(ply_folder),
                "output_files": {
                    "json": json_path,
                    "excel": xlsx_path,
                    "png": png_path,
                    "html_3d": html_3d_path
                },
                "metrics": metrics,
                "validation": {
                    "warnings": warnings,
                    "passed": len(warnings) == 0
                }
            }
            
            logger.info("\n" + "="*70)
            logger.info("✅ ANALISI TILED COMPLETATA CON SUCCESSO")
            logger.info("="*70)
            
            return self.results
            
        except Exception as e:
            logger.error(f"❌ Errore pipeline: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
    
    def get_results(self) -> dict:
        """Ritorna risultati completi dell'ultima esecuzione."""
        return self.results or {}
