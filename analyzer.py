"""
STL file analyzer - dimensions, volume, surface area, mass estimates
"""

import warnings
import numpy as np
from stl import mesh
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# Suppress mesh warnings
warnings.filterwarnings('ignore', message='.*mesh is not closed.*')


@dataclass
class AnalysisResult:
    """Analysis results for an STL file"""
    filename: str
    length: float
    width: float
    height: float
    volume: float
    surface_area: float
    triangle_count: int
    is_watertight: bool
    
    def get_mass(self, density: float = 1.24) -> float:
        """
        Calculate the mass of the object in grams based on its volume and material density.
        
        Args:
            density: Material density in g/cm³. Defaults to 1.24 (PLA).
            
        Returns:
            Calculated mass in grams.
        """
        # Convert mm³ to cm³ (1 cm³ = 1000 mm³)
        volume_cm3 = self.volume / 1000
        return volume_cm3 * density
    
    def to_imperial(self) -> dict:
        """
        Convert all metric measurements (mm, mm², mm³) to imperial units (in, in², in³).
        
        Returns:
            Dictionary containing imperial measurements.
        """
        # Standard conversion constants
        MM_TO_IN = 0.0393701
        MM3_TO_IN3 = 0.0000610237
        MM2_TO_IN2 = 0.00155
        
        return {
            'filename': str(self.filename),
            'length': float(self.length * MM_TO_IN),
            'width': float(self.width * MM_TO_IN),
            'height': float(self.height * MM_TO_IN),
            'volume': float(self.volume * MM3_TO_IN3),
            'surface_area': float(self.surface_area * MM2_TO_IN2),
            'triangle_count': int(self.triangle_count),
            'is_watertight': bool(self.is_watertight)
        }
    
    def to_dict(self, imperial: bool = False) -> dict:
        """Convert to dictionary for export"""
        if imperial:
            return self.to_imperial()
        return {
            'filename': str(self.filename),
            'length': float(self.length),
            'width': float(self.width),
            'height': float(self.height),
            'volume': float(self.volume),
            'surface_area': float(self.surface_area),
            'triangle_count': int(self.triangle_count),
            'is_watertight': bool(self.is_watertight)
        }


class CADAnalyzer:
    """STL file analyzer"""
    
    # Material densities (g/cm³)
    MATERIALS = {
        'PLA': 1.24,
        'ABS': 1.04,
        'PETG': 1.27,
        'Nylon': 1.15,
        'TPU': 1.21,
        'Resin': 1.10,
        'Aluminum': 2.70,
        'Steel': 7.85,
        'Titanium': 4.50,
        'Copper': 8.96,
    }
    
    @staticmethod
    def analyze_stl(filepath: str) -> Optional[AnalysisResult]:
        """
        Perform comprehensive geometric analysis of an STL file.
        
        Calculates:
        - Bounding box dimensions (sorted L > W > H)
        - Mesh volume (using mass properties)
        - Total surface area of all triangles
        - Triangle count and basic validity (watertightness)
        """
        try:
            # Load mesh using numpy-stl
            stl_mesh = mesh.Mesh.from_file(filepath)
            filename = Path(filepath).stem
            
            # 1. Calculate Bounding Box
            # Find min/max across all vectors to determine spatial extent
            min_coords = stl_mesh.vectors.min(axis=(0, 1))
            max_coords = stl_mesh.vectors.max(axis=(0, 1))
            dimensions = max_coords - min_coords
            
            # Sort dimensions so L is always the longest, H the shortest
            # This is standard for manufacturing/shipping estimates
            sorted_dims = sorted(dimensions, reverse=True)
            length, width, height = sorted_dims
            
            # 2. Calculate Volume
            # stl-numpy provides mass properties based on signed volume of tetrahedra
            volume, cog, inertia = stl_mesh.get_mass_properties()
            volume = abs(volume) # Use absolute value in case of inverted normals
            
            # 3. Calculate Surface Area
            # Sum of areas of all triangles in the mesh
            # Area = 0.5 * |(v1-v0) x (v2-v0)|
            v0 = stl_mesh.vectors[:, 0, :]
            v1 = stl_mesh.vectors[:, 1, :]
            v2 = stl_mesh.vectors[:, 2, :]
            
            edge1 = v1 - v0
            edge2 = v2 - v0
            crosses = np.cross(edge1, edge2)
            areas = 0.5 * np.linalg.norm(crosses, axis=1)
            surface_area = np.sum(areas)
            
            triangle_count = len(stl_mesh.vectors)
            
            # Simple heuristic for watertightness: non-zero volume and area
            # Note: A truly watertight check requires manifoldness analysis
            is_watertight = volume > 0 and surface_area > 0
            
            return AnalysisResult(
                filename=filename,
                length=float(length),
                width=float(width),
                height=float(height),
                volume=float(volume),
                surface_area=float(surface_area),
                triangle_count=triangle_count,
                is_watertight=is_watertight
            )
            
        except Exception as e:
            print(f"Error analyzing {filepath}: {e}")
            return None
    
    @staticmethod
    def analyze_multiple(filepaths: list) -> list:
        """Analyze multiple files"""
        results = []
        for filepath in filepaths:
            result = CADAnalyzer.analyze_stl(filepath)
            if result:
                results.append(result)
        return results
    
    @staticmethod
    def format_dimension(value: float, imperial: bool = False) -> str:
        """Format a dimension value with units"""
        if imperial:
            return f'{value * 0.0393701:.2f}"'
        return f'{value:.1f} mm'
    
    @staticmethod
    def format_volume(value: float, imperial: bool = False) -> str:
        """Format a volume value with units"""
        if imperial:
            return f'{value * 0.0000610237:.3f} in³'
        return f'{value:.1f} mm³'
    
    @staticmethod
    def format_area(value: float, imperial: bool = False) -> str:
        """Format a surface area value with units"""
        if imperial:
            return f'{value * 0.00155:.2f} in²'
        return f'{value:.1f} mm²'


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Professional STL File Geometric Analyzer")
    parser.add_argument("file", help="Path to the STL file to analyze")
    parser.add_argument("--imperial", action="store_true", help="Display results in imperial units")
    
    args = parser.parse_args()
    
    result = CADAnalyzer.analyze_stl(args.file)
    
    if result:
        imp = args.imperial
        unit = "in" if imp else "mm"
        
        print(f"\n{'='*60}")
        print(f"  CAD ANALYSIS: {result.filename.upper()}")
        print(f"{'='*60}")
        
        # Dimensions
        l, w, h = (result.length, result.width, result.height)
        if imp:
            l, w, h = (l * 0.0393701, w * 0.0393701, h * 0.0393701)
            
        print(f"  Dimensions:    {l:.2f} x {w:.2f} x {h:.2f} {unit}")
        
        # Volume/Area
        vol = result.volume * (0.0000610237 if imp else 1.0)
        area = result.surface_area * (0.00155 if imp else 1.0)
        vol_u = "in³" if imp else "mm³"
        area_u = "in²" if imp else "mm²"
        
        print(f"  Volume:        {vol:,.2f} {vol_u}")
        print(f"  Surface Area:  {area:,.2f} {area_u}")
        print(f"  Triangles:     {result.triangle_count:,}")
        print(f"  Watertight:    {'YES' if result.is_watertight else 'NO'}")
        
        print(f"\n  MASS ESTIMATES (Solid):")
        for material, density in CADAnalyzer.MATERIALS.items():
            mass = result.get_mass(density)
            print(f"    - {material:<10}: {mass:>8.2f} g")
        print(f"{'='*60}\n")
    else:
        print(f"Error: Could not analyze '{args.file}'. Ensure it is a valid STL file.")

