"""
Report Generator - Esportazione e visualizzazione dati strutturati
"""

import numpy as np
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Genera report e output dell'analisi."""
    
    def __init__(self, output_dir: str = "."):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def export_json(
        self,
        metrics: dict,
        segmentation_info: dict,
        calibration_info: dict,
        warnings: List[str],
        source_file: str = "unknown",
        output_filename: str = "report_posidonia.json"
    ) -> str:
        """Esporta report completo in JSON."""

        if calibration_info is None:
            calibration_info = {}

        logger.info(f"Esportazione JSON: {output_filename}")
        
        output_path = self.output_dir / output_filename
        
        report = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "version": "2.0",
                "source_file": str(source_file),
                "tool": "bio_analysis.reporter"
            },
            "calibration": calibration_info,
            "segmentation": segmentation_info,
            "metrics": metrics,
            "validation": {
                "warnings": warnings,
                "n_warnings": len(warnings),
                "passed": len(warnings) == 0
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"  Salvato: {output_path}")
        return str(output_path)
    
    def export_excel(
        self,
        metrics: dict,
        segmentation_info: dict,
        calibration_info: dict,
        output_filename: str = "report_posidonia.xlsx"
    ) -> str:
        """
        Esporta l'Excel con 2 fogli essenziali: Summary (Ecologia) e Validazione Biologica.
        """
        try:
            import pandas as pd
        except ImportError:
            logger.warning("Libreria pandas mancante - Esportazione Excel saltata")
            return ""
        
        logger.info(f"Esportazione Excel: {output_filename}")
        output_path = self.output_dir / output_filename
        
        if calibration_info is None:
            calibration_info = {}
            
        # --- FOGLIO 1: SUMMARY ECOLOGICO ---
        summary_data = {
            "Parametro": list(metrics.keys()),
            "Valore": list(metrics.values())
        }
        df_summary = pd.DataFrame(summary_data)
        
        # --- FOGLIO 2: VALIDAZIONE FISICA/BIOLOGICA ---
        try:
            calib_dict = calibration_info.get('plane_model') or {}
            max_dist = calib_dict.get('max_distance_post_scaling', 0.70)
        except Exception:
            max_dist = 0.70

        validation_data = {
            "Check Scientifico": [
                "Calibrazione RANSAC (Atteso: ~0.70m)",
                "Ratio Volume/Area",
                "Copertura Posidonia %",
                "K-Means Silhouette Score"
            ],
            "Valore Rilevato": [
                f"{max_dist:.4f} m",
                f"{metrics.get('volume_area_ratio', 0):.3f} m",
                f"{metrics.get('coverage_posidonia_pct', 0):.1f} %",
                f"{segmentation_info.get('silhouette_score', 0):.4f}"
            ]
        }
        df_validation = pd.DataFrame(validation_data)
        
        # Salvataggio
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df_summary.to_excel(writer, sheet_name='Summary Ecologico', index=False)
            df_validation.to_excel(writer, sheet_name='Validazione Biologica', index=False)
        
        logger.info(f"  Salvato: {output_path}")
        return str(output_path)
    
    def export_png(
        self,
        metrics: dict,
        warnings: List[str],
        luminanza_grid: np.ndarray,
        altezze_grid: np.ndarray,
        mask_posidonia: np.ndarray,
        celle_valide: np.ndarray,
        output_filename: str = "visualization_posidonia.png"
    ) -> str:
        """
        Esporta dashboard visiva a 4 pannelli.
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib mancante - Esportazione PNG saltata")
            return ""
        
        logger.info(f"Esportazione PNG: {output_filename}")
        output_path = self.output_dir / output_filename
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle("Report Analisi Posidonia Oceanica", fontsize=20, fontweight='bold')
        
        # Pannello 1: Mappa Luminanza
        ax = axes[0, 0]
        if luminanza_grid is not None:
            im = ax.imshow(luminanza_grid, cmap='gray', origin='lower')
            ax.set_title("Mappa Luminanza", fontsize=14)
            ax.axis('off')
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            
        # Pannello 2: Mappa Altezze
        ax = axes[0, 1]
        if altezze_grid is not None:
            alt_disp = np.ma.masked_where(altezze_grid == 0, altezze_grid)
            im = ax.imshow(alt_disp, cmap='viridis', origin='lower')
            ax.set_title("Topografia (Altezze dal fondale)", fontsize=14)
            ax.axis('off')
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            
        # Pannello 3: Segmentazione
        ax = axes[1, 0]
        if luminanza_grid is not None and mask_posidonia is not None:
            rgb_out = np.zeros((*luminanza_grid.shape, 3))
            
            # Spalmiamo i dati 1D sulla griglia 2D
            pos_mask_2d = np.zeros_like(celle_valide, dtype=bool)
            pos_mask_2d[celle_valide] = mask_posidonia
            
            sab_mask_2d = np.zeros_like(celle_valide, dtype=bool)
            sab_mask_2d[celle_valide] = ~mask_posidonia
            
            # Coloriamo la mappa
            rgb_out[pos_mask_2d] = [0.2, 0.8, 0.2]  # Verde Posidonia
            rgb_out[sab_mask_2d] = [0.9, 0.7, 0.1]  # Oro Sabbia
            
            ax.imshow(rgb_out, origin='lower')
            ax.set_title("Segmentazione Algoritmica", fontsize=14)
            ax.axis('off')
            
        # Pannello 4: Report Testuale
        ax = axes[1, 1]
        ax.axis('off')
        
        testo = (
            f"RISULTATI ECOLOGICI\n"
            f"{'-'*40}\n"
            f"Area totale: {metrics.get('area_total_m2', 0):.2f} m2\n"
            f"Area Posidonia: {metrics.get('area_posidonia_m2', 0):.2f} m2\n"
            f"Area sabbia: {metrics.get('area_sabbia_m2', 0):.2f} m2\n"
            f"Volume chioma: {metrics.get('volume_posidonia_m3', 0):.2f} m3\n"
            f"Copertura Posidonia: {metrics.get('coverage_posidonia_pct', 0):.1f}%\n"
            f"CO2 assorbita: {metrics.get('co2_assorbita_kg_anno', 0):.2f} kg/anno\n"
            f"O2 prodotto: {metrics.get('o2_prodotto_L_anno', 0):.0f} L/anno\n"
        )
        
        if warnings:
            testo += f"\nNOTE BIOLOGICHE:\n"
            for w in warnings:
                testo += f" - {w}\n"
                
        ax.text(0.1, 0.8, testo, fontsize=14, va='top', ha='left', family='monospace', 
                bbox=dict(facecolor='#f0f0f0', edgecolor='black', boxstyle='round,pad=1'))
                
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"  Salvato: {output_path}")
        return str(output_path)
    
    def export_plotly_3d(
        self,
        vertices_scaled: Optional[np.ndarray] = None,
        mask_posidonia: Optional[np.ndarray] = None,
        celle_valide: Optional[np.ndarray] = None,
        luminanza_grid: Optional[np.ndarray] = None,
        altezze_grid: Optional[np.ndarray] = None,
        metrics: Optional[dict] = None,
        output_filename: str = "visualization_3d_interactive.html"
    ) -> str:
        """
        Esporta visualizzazione 3D interattiva per visualizzazione nel browser.
        """
        try:
            import numpy as np
            import plotly.graph_objects as go
            import plotly.express as px
        except ImportError:
            logger.warning("plotly non installato - 3D visualization saltata")
            return ""
        
        logger.info(f"Esportazione Plotly 3D interattiva: {output_filename}")
        
        output_path = self.output_dir / output_filename
        
        if vertices_scaled is not None and len(vertices_scaled) > 0:
            n_points = len(vertices_scaled)
            if n_points > 50000:
                idx = np.random.choice(n_points, 50000, replace=False)
                verts = vertices_scaled[idx]
                logger.info(f"  -> Campionamento: {n_points:,} -> 50,000 punti")
            else:
                verts = vertices_scaled
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter3d(
                x=verts[:, 0],
                y=verts[:, 1],
                z=verts[:, 2],
                mode='markers',
                marker=dict(size=2, color='lightgray', opacity=0.3),
                name='Nuvola di punti',
                hovertemplate='X: %{x:.2f}<br>Y: %{y:.2f}<br>Z: %{z:.2f}<extra></extra>'
            ))
        else:
            fig = go.Figure()
        
        if mask_posidonia is not None and celle_valide is not None and luminanza_grid is not None:
            n_celle_grid = luminanza_grid.shape
            x_grid = np.arange(n_celle_grid[0])
            z_grid = np.arange(n_celle_grid[1])
            xx, zz = np.meshgrid(x_grid, z_grid, indexing='ij')
            
            altezze = np.zeros_like(luminanza_grid)
            if altezze_grid is not None:
                altezze = altezze_grid
            
            if np.shape(celle_valide) != np.shape(mask_posidonia):
                if np.ndim(mask_posidonia) == 1:
                    pos_mask = np.zeros_like(celle_valide, dtype=bool)
                    pos_mask[celle_valide] = mask_posidonia
                elif np.ndim(celle_valide) == 1:
                    pos_mask = np.zeros_like(mask_posidonia, dtype=bool)
                    pos_mask[mask_posidonia] = celle_valide
                else:
                    pos_mask = mask_posidonia
            else:
                pos_mask = celle_valide & mask_posidonia

            pos_x = xx[pos_mask]
            pos_z = zz[pos_mask]
            pos_alt = altezze[pos_mask]
            
            fig.add_trace(go.Scatter3d(
                x=pos_x,
                y=pos_alt,
                z=pos_z,
                mode='markers',
                marker=dict(size=5, color='darkgreen', opacity=0.8, symbol='square'),
                name=f"Posidonia ({len(pos_x)} celle)",
                hovertemplate='X: %{x:.0f}<br>Altezza: %{y:.3f}m<br>Z: %{z:.0f}<extra></extra>'
            ))
            
            sabbia_mask = celle_valide & ~pos_mask
            sab_x = xx[sabbia_mask]
            sab_z = zz[sabbia_mask]
            sab_alt = altezze[sabbia_mask]
            
            fig.add_trace(go.Scatter3d(
                x=sab_x,
                y=sab_alt,
                z=sab_z,
                mode='markers',
                marker=dict(size=5, color='gold', opacity=0.7, symbol='diamond'),
                name=f"Sabbia ({len(sab_x)} celle)",
                hovertemplate='X: %{x:.0f}<br>Altezza: %{y:.3f}m<br>Z: %{z:.0f}<extra></extra>'
            ))
        
        fig.update_layout(
            title={
                'text': "Posidonia 3D Interactive Visualization<br><sub>Verde=Posidonia | Giallo=Sabbia</sub>",
                'x': 0.5,
                'xanchor': 'center'
            },
            scene=dict(
                xaxis_title='X',
                yaxis_title='Altezza (m)',
                zaxis_title='Z',
                camera=dict(eye=dict(x=1.5, y=1.5, z=1.3)),
                aspectmode='data'
            ),
            width=1200,
            height=800,
            hovermode='closest',
            showlegend=True,
            legend=dict(x=0.02, y=0.98)
        )
        
        fig.write_html(str(output_path))
        logger.info(f"  Salvato HTML: {output_path}")
        
        return str(output_path)