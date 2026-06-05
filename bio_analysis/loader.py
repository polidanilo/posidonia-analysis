"""
Point Cloud Loader - Supporta LAS, PLY, OBJ con auto-detection
"""

import numpy as np
import trimesh
import glob
import os
from pathlib import Path
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class PointCloudLoader:
    """Carica file mesh 3D (LAS, PLY, OBJ) e estrae vertici e colori."""
    
    def __init__(self):
        self.vertices = None
        self.colors = None
        self.source_file = None
        
    def load(self, path: str) -> Tuple[np.ndarray, np.ndarray]:
        """
        Carica un singolo file PLY/OBJ/LAS.
        """
        path = str(path)
        
        if not os.path.exists(path):
            raise FileNotFoundError(f"File non trovato: {path}")
        
        ext = Path(path).suffix.lower()
        
        if ext in ['.ply', '.obj']:
            return self._load_trimesh(path)
        elif ext == '.las':
            return self._load_las(path)
        else:
            raise ValueError(f"Formato non supportato: {ext}")
    
    def load_tiled_ply(self, folder: str) -> Tuple[np.ndarray, np.ndarray]:
        """
        Carica e fonde i frammenti PLY da una cartella.
        """
        ply_files = sorted(glob.glob(os.path.join(folder, '*.ply')))
        
        if not ply_files:
            raise FileNotFoundError(f"Nessun file .ply trovato in {folder}")
        
        logger.info(f"Trovati {len(ply_files)} tile PLY. Inizio merge...")
        
        all_vertices = []
        all_colors = []
        
        for i, file_path in enumerate(ply_files):
            name = os.path.basename(file_path)
            logger.info(f" [{i+1}/{len(ply_files)}] Caricamento {name}...")
            
            try:
                vertices, colors = self._load_trimesh(file_path)
                all_vertices.append(vertices)
                all_colors.append(colors)
            except Exception as e:
                logger.warning(f"Errore caricamento {name}: {e}")
                continue
        
        if not all_vertices:
            raise RuntimeError("Nessun file PLY caricato con successo")
        
        self.vertices = np.vstack(all_vertices)
        self.colors = np.vstack(all_colors)
        self.source_file = folder
        
        logger.info(f"Merge completato: {len(self.vertices):,} vertici totali")
        
        return self.vertices, self.colors
    
    def _load_trimesh(self, path: str) -> Tuple[np.ndarray, np.ndarray]:
        """Carica PLY/OBJ con trimesh."""
        mesh = trimesh.load(path, process=False)
        vertices = np.array(mesh.vertices, dtype=np.float32)
        
        if hasattr(mesh.visual, 'vertex_colors') and len(mesh.visual.vertex_colors) > 0:
            colors = np.array(mesh.visual.vertex_colors, dtype=np.uint8)
        else:
            colors = np.ones((len(vertices), 4), dtype=np.uint8) * 128
        
        self.vertices = vertices
        self.colors = colors
        
        return vertices, colors
    
    def _load_las(self, path: str) -> Tuple[np.ndarray, np.ndarray]:
        """Carica LAS con laspy."""
        try:
            import laspy
        except ImportError:
            raise ImportError("laspy non installato. Installa con: pip install laspy")
        
        las = laspy.read(path)
        vertices = np.vstack([las.x, las.y, las.z]).T.astype(np.float32)
        
        if hasattr(las, 'red') and hasattr(las, 'green') and hasattr(las, 'blue'):
            colors = np.vstack([las.red, las.green, las.blue, np.ones(len(las))*255]).T.astype(np.uint8)
        else:
            colors = np.ones((len(vertices), 4), dtype=np.uint8) * 128
        
        self.vertices = vertices
        self.colors = colors
        
        return vertices, colors
    
    def get_stats(self) -> dict:
        """Ritorna statistiche della nuvola di punti caricata."""
        if self.vertices is None:
            return {}
        
        return {
            "n_points": len(self.vertices),
            "has_colors": self.colors is not None,
            "bounds_x": (self.vertices[:, 0].min(), self.vertices[:, 0].max()),
            "bounds_y": (self.vertices[:, 1].min(), self.vertices[:, 1].max()),
            "bounds_z": (self.vertices[:, 2].min(), self.vertices[:, 2].max()),
            "source": self.source_file,
        }