"""
Report Generator - Excel, JSON, PNG exports + Plotly 3D interactive visualization
"""

import numpy as np
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Genera report in Excel, JSON e PNG."""
    
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
        """
        Esporta report completo in JSON.
        
        Args:
            metrics: Dictionary con metriche (area, volume, CO2, O2)
            segmentation_info: Dictionary con info K-Means
            calibration_info: Dictionary con info RANSAC
            warnings: Lista di warning
            source_file: Path del file originale
            output_filename: Nome file output
        
        Returns:
            Path del file generato
        """

        if calibration_info is None:
            calibration_info = {}

        logger.info(f"📄 Esportazione JSON: {output_filename}")
        
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
        
        logger.info(f"   ✅ Salvato: {output_path}")
        
        return str(output_path)
    
    def export_excel(
        self,
        metrics: dict,
        segmentation_info: dict,
        calibration_info: dict,
        warnings: List[str],
        luminanza_grid: Optional[np.ndarray] = None,
        altezze_grid: Optional[np.ndarray] = None,
        celle_valide: Optional[np.ndarray] = None,
        mask_posidonia: Optional[np.ndarray] = None,
        output_filename: str = "report_posidonia.xlsx"
    ) -> str:
        """
        Esporta report in Excel (4 sheets: summary, grid_data, validation, cicatrice).
        
        Args:
            metrics: Dictionary con metriche
            segmentation_info: Dictionary con info clustering
            calibration_info: Dictionary con info plane
            warnings: Lista di warning
            luminanza_grid: Griglia luminanza
            altezze_grid: Griglia altezze
            celle_valide: Boolean mask celle valide
            mask_posidonia: Boolean mask Posidonia
            output_filename: Nome file output
        
        Returns:
            Path del file generato
        """

        if calibration_info is None:
            calibration_info = {}

        try:
            import pandas as pd
        except ImportError:
            logger.warning("pandas non installato - Excel export skipped")
            return ""
        
        logger.info(f"📊 Esportazione Excel: {output_filename}")
        
        output_path = self.output_dir / output_filename
        
        # Sheet 1: Summary
        summary_data = {
            "Parametro": list(metrics.keys()),
            "Valore": list(metrics.values())
        }
        df_summary = pd.DataFrame(summary_data)
        
        # Sheet 2: Grid Data
        grid_data_list = []
        if luminanza_grid is not None and celle_valide is not None:
            lum_flat = luminanza_grid[celle_valide]
            alt_flat = altezze_grid[celle_valide] if altezze_grid is not None else np.zeros_like(lum_flat)
            pos_flat = mask_posidonia if mask_posidonia is not None else np.zeros_like(lum_flat, dtype=bool)
            
            for i, (lum, alt, pos) in enumerate(zip(lum_flat, alt_flat, pos_flat)):
                grid_data_list.append({
                    "cella_idx": i,
                    "luminanza_media": round(float(lum), 2) if not np.isnan(lum) else None,
                    "altezza_m": round(float(alt), 3) if not np.isnan(alt) else None,
                    "posidonia": bool(pos)
                })
        
        df_grid = pd.DataFrame(grid_data_list) if grid_data_list else pd.DataFrame()
        
# Sheet 3: Validation (Safe Extract)
        try:
            calib_dict = calibration_info.get('plane_model') or {}
            max_dist = calib_dict.get('max_distance_post_scaling', 0.70)
        except Exception:
            max_dist = 0.70

        validation_data = {
            "Check": [
                "K-Means Silhouette",
                "Volume/Area Ratio",
                "Coverage %",
                "Calibration RANSAC"
            ],
            "Valore": [
                f"{segmentation_info.get('silhouette_score', 0):.4f}",
                f"{metrics.get('volume_area_ratio', 0):.3f}m",
                f"{metrics.get('coverage_posidonia_pct', 0):.1f}%",
                f"{max_dist:.4f}m"
            ]
        }
        df_validation = pd.DataFrame(validation_data)
        
        # Sheet 4: Cicatrice (Sand)
        cicatrice_data = {
            "Metriche Danno": [
                "Area Cicatrice (sand)",
                "CO2 Loss (kg/year)",
                "O2 Loss (L/year)",
                "Copertura residua"
            ],
            "Valore": [
                f"{metrics.get('area_sand_cicatrice_m2', 0):.2f} m²",
                f"{metrics.get('co2_loss_kg_year', 0):.0f} kg",
                f"{metrics.get('o2_loss_L_year', 0):.0f} L",
                f"{metrics.get('coverage_posidonia_pct', 0):.1f}%"
            ]
        }
        df_cicatrice = pd.DataFrame(cicatrice_data)
        
        # Scrivi Excel
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df_summary.to_excel(writer, sheet_name='Summary', index=False)
            if not df_grid.empty:
                df_grid.to_excel(writer, sheet_name='Grid Data', index=False)
            df_validation.to_excel(writer, sheet_name='Validation', index=False)
            df_cicatrice.to_excel(writer, sheet_name='Cicatrice', index=False)
        
        logger.info(f"   ✅ Salvato: {output_path}")
        
        return str(output_path)
    
    def export_png(
        self,
        metrics: dict,
        segmentation_info: dict,
        warnings: List[str],
        luminanza_grid: Optional[np.ndarray] = None,
        altezze_grid: Optional[np.ndarray] = None,
        mask_posidonia: Optional[np.ndarray] = None,
        celle_valide: Optional[np.ndarray] = None,
        output_filename: str = "visualization_posidonia.png"
    ) -> str:
        """
        Esporta 5-panel visualization PNG (histogram, maps, metrics, report).
        
        Args:
            metrics: Dictionary con metriche
            segmentation_info: Dictionary con info clustering
            warnings: Lista di warning
            luminanza_grid: Griglia luminanza
            altezze_grid: Griglia altezze
            mask_posidonia: Boolean mask Posidonia
            celle_valide: Boolean mask celle valide
            output_filename: Nome file output
        
        Returns:
            Path del file generato
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
        except ImportError:
            logger.warning("matplotlib non installato - PNG export skipped")
            return ""
        
        logger.info(f"🎨 Esportazione PNG (5-panel): {output_filename}")
        
        output_path = self.output_dir / output_filename
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle("Posidonia 3D Analysis Report", fontsize=16, weight='bold')
        
        # Panel 1: Luminanza Histogram
        ax = axes[0, 0]
        if luminanza_grid is not None and celle_valide is not None:
            lum_values = luminanza_grid[celle_valide]
            lum_valid = lum_values[~np.isnan(lum_values)]
            ax.hist(lum_valid, bins=50, color='steelblue', edgecolor='black', alpha=0.7)
            threshold = segmentation_info.get('threshold', 0)
            ax.axvline(threshold, color='red', linestyle='--', linewidth=2, label=f'Threshold: {threshold:.1f}')
            ax.legend()
        ax.set_xlabel('Luminanza media (R+G+B)/3')
        ax.set_ylabel('Numero celle')
        ax.set_title('1. Istogramma Luminanza')
        ax.grid(True, alpha=0.3)
        
        # Panel 2: Luminanza Map
        ax = axes[0, 1]
        if luminanza_grid is not None:
            im = ax.imshow(luminanza_grid, cmap='gray', origin='lower')
            ax.set_title('2. Mappa Luminanza')
            ax.set_xlabel('X (celle)')
            ax.set_ylabel('Z (celle)')
            plt.colorbar(im, ax=ax, label='Luminanza')
        
        # Panel 3: Altezze Map
        ax = axes[0, 2]
        if altezze_grid is not None:
            im = ax.imshow(altezze_grid, cmap='viridis', origin='lower')
            ax.set_title('3. Mappa Altezze (max-min Y)')
            ax.set_xlabel('X (celle)')
            ax.set_ylabel('Z (celle)')
            plt.colorbar(im, ax=ax, label='Altezza (m)')
        
        # Panel 4: Segmentazione Map
        ax = axes[1, 0]
        if luminanza_grid is not None and mask_posidonia is not None:
            maschera_display = np.full_like(luminanza_grid, np.nan)
            maschera_display[celle_valide] = mask_posidonia.astype(float)
            im = ax.imshow(maschera_display, cmap='RdYlGn', origin='lower', vmin=0, vmax=1)
            ax.set_title('4. Segmentazione (Verde=Posidonia, Rosso=Sabbia)')
            ax.set_xlabel('X (celle)')
            ax.set_ylabel('Z (celle)')
            plt.colorbar(im, ax=ax, label='Posidonia' )
        
        # Panel 5: Metrics Report
        ax = axes[1, 1]
        ax.axis('off')
        report_text = f"""
        METRICHE ECOLOGICHE
        ─────────────────────────
        Area Totale: {metrics.get('area_total_m2', 0):.2f} m²
        Area Posidonia: {metrics.get('area_posidonia_m2', 0):.2f} m²
        Area Cicatrice: {metrics.get('area_sand_cicatrice_m2', 0):.2f} m²
        Copertura: {metrics.get('coverage_posidonia_pct', 0):.1f}%
        
        Volume: {metrics.get('volume_posidonia_m3', 0):.2f} m³
        Ratio: {metrics.get('volume_area_ratio', 0):.3f} m
        
        CO2 Loss: {metrics.get('co2_loss_kg_year', 0):.0f} kg/year
        O2 Loss: {metrics.get('o2_loss_L_year', 0):.0f} L/year
        
        Silhouette Score: {segmentation_info.get('silhouette_score', 0):.4f}
        """
        ax.text(0.1, 0.5, report_text, fontsize=11, family='monospace', verticalalignment='center')
        
        # Panel 6: Warnings
        ax = axes[1, 2]
        ax.axis('off')
        warnings_text = f"VALIDAZIONE\n{'─' * 30}\n"
        if warnings:
            warnings_text += f"{len(warnings)} Warning(s):\n\n"
            for w in warnings[:6]:  # Mostra max 6 warning
                warnings_text += f"• {w}\n"
        else:
            warnings_text += "✅ Nessun Warning"
        ax.text(0.1, 0.5, warnings_text, fontsize=10, family='monospace', verticalalignment='center')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"   ✅ Salvato: {output_path}")
        
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
        Esporta visualizzazione 3D interattiva con Plotly (HTML).
        
        Permette:
        - Rotazione/zoom della nuvola di punti 3D
        - Colori differenti per Posidonia (verde) vs Sabbia (giallo)
        - Ombra delle celle sulla base
        - Report metrico integrato nell'HTML
        
        Args:
            vertices_scaled: Array (N, 3) dei vertici (punti spaziali)
            mask_posidonia: Boolean array celle con Posidonia
            celle_valide: Boolean array celle valide della griglia
            luminanza_grid: Griglia luminanza (per visualizzazione alternativa)
            altezze_grid: Griglia altezze
            metrics: Dictionary con metriche ecologiche
            output_filename: Nome file HTML output
        
        Returns:
            Path del file generato
        """
        try:
            import plotly.graph_objects as go
            import plotly.express as px
        except ImportError:
            logger.warning("plotly non installato - 3D visualization skipped")
            logger.warning("Installa con: pip install plotly")
            return ""
        
        logger.info(f"🎨 Esportazione Plotly 3D interattiva: {output_filename}")
        
        output_path = self.output_dir / output_filename
        
        # Se vertices_scaled fornito, visualizza direttamente i punti 3D
        if vertices_scaled is not None and len(vertices_scaled) > 0:
            # Campionamento per performance (max 50k punti)
            n_points = len(vertices_scaled)
            if n_points > 50000:
                idx = np.random.choice(n_points, 50000, replace=False)
                verts = vertices_scaled[idx]
                logger.info(f"  -> Campionamento: {n_points:,} → 50,000 punti per performance")
            else:
                verts = vertices_scaled
            
            # Crea figura 3D
            fig = go.Figure()
            
            # Aggiungi nuvola di punti (grigio neutro)
            fig.add_trace(go.Scatter3d(
                x=verts[:, 0],
                y=verts[:, 1],
                z=verts[:, 2],
                mode='markers',
                marker=dict(
                    size=2,
                    color='lightgray',
                    opacity=0.3
                ),
                name='Nuvola di punti (campionata)',
                hovertemplate='X: %{x:.2f}<br>Y: %{y:.2f}<br>Z: %{z:.2f}<extra></extra>'
            ))
            
        else:
            fig = go.Figure()
        
        # Se griglia disponibile, aggiungi celle colorate
        if mask_posidonia is not None and celle_valide is not None and luminanza_grid is not None:
            # Ricostruisci coordinate delle celle
            n_celle_grid = luminanza_grid.shape
            x_grid = np.arange(n_celle_grid[0])
            z_grid = np.arange(n_celle_grid[1])
            xx, zz = np.meshgrid(x_grid, z_grid, indexing='ij')
            
            # Altezze (se disponibili)
            altezze = np.zeros_like(luminanza_grid)
            if altezze_grid is not None:
                altezze = altezze_grid
            
            # Posidonia (verde)
            pos_mask = celle_valide & mask_posidonia
            pos_x = xx[pos_mask]
            pos_z = zz[pos_mask]
            pos_alt = altezze[pos_mask]
            
            fig.add_trace(go.Scatter3d(
                x=pos_x,
                y=pos_alt,
                z=pos_z,
                mode='markers',
                marker=dict(
                    size=5,
                    color='darkgreen',
                    opacity=0.8,
                    symbol='square'
                ),
                name=f"Posidonia ({len(pos_x)} celle)",
                hovertemplate='Cella X: %{x:.0f}<br>Altezza: %{y:.3f}m<br>Cella Z: %{z:.0f}<extra></extra>'
            ))
            
            # Sabbia (giallo/rosso)
            sabbia_mask = celle_valide & ~mask_posidonia
            sab_x = xx[sabbia_mask]
            sab_z = zz[sabbia_mask]
            sab_alt = altezze[sabbia_mask]
            
            fig.add_trace(go.Scatter3d(
                x=sab_x,
                y=sab_alt,
                z=sab_z,
                mode='markers',
                marker=dict(
                    size=5,
                    color='gold',
                    opacity=0.7,
                    symbol='diamond'
                ),
                name=f"Sabbia/Cicatrice ({len(sab_x)} celle)",
                hovertemplate='Cella X: %{x:.0f}<br>Altezza: %{y:.3f}m<br>Cella Z: %{z:.0f}<extra></extra>'
            ))
        
        # Layout
        fig.update_layout(
            title={
                'text': "Posidonia 3D Interactive Visualization<br><sub>Ruota, zoom, hover per dettagli | Verde=Posidonia | Giallo=Sabbia</sub>",
                'x': 0.5,
                'xanchor': 'center'
            },
            scene=dict(
                xaxis_title='X (celle)',
                yaxis_title='Altezza (m)',
                zaxis_title='Z (celle)',
                camera=dict(
                    eye=dict(x=1.5, y=1.5, z=1.3)
                ),
                aspectmode='data'
            ),
            width=1200,
            height=800,
            hovermode='closest',
            showlegend=True,
            legend=dict(x=0.02, y=0.98)
        )
        
        # Salva HTML
        fig.write_html(str(output_path))
        
        logger.info(f"   ✅ Salvato: {output_path}")
        logger.info("   -> Apri il file HTML nel browser per interazione 3D")
        
        return str(output_path)
