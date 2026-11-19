"""
Export module for GLB and other formats
"""

import json
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
import trimesh
from datetime import datetime


class GLBExporter:
    """
    Exporter for GLB format (GL Transmission Format)
    Compatible with Unity and other 3D engines
    """
    
    def __init__(self):
        self.metadata: Dict[str, Any] = {
            'format': 'GLB',
            'version': '2.0',
            'generator': '3D Vector Pipeline',
            'timestamp': datetime.now().isoformat()
        }
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set export metadata"""
        self.metadata[key] = value
    
    def export_mesh(self, mesh: trimesh.Trimesh, path: str, 
                    scale: float = 1.0, 
                    translate: Tuple[float, float, float] = (0, 0, 0),
                    rotate: Tuple[float, float, float] = (0, 0, 0),
                    include_normals: bool = True,
                    include_colors: bool = True) -> bool:
        """
        Export a mesh to GLB format
        
        Args:
            mesh: Trimesh object to export
            path: Output file path
            scale: Scale factor (1.0 = original size)
            translate: Translation vector (x, y, z)
            rotate: Rotation in degrees (x, y, z)
            include_normals: Include vertex normals
            include_colors: Include vertex colors
            
        Returns:
            True if export succeeded
        """
        try:
            # Create a copy to avoid modifying original
            export_mesh = mesh.copy()
            
            # Apply transformations
            if scale != 1.0:
                export_mesh.vertices *= scale
            
            if translate != (0, 0, 0):
                export_mesh.vertices += np.array(translate)
            
            if any(rotate):
                # Convert degrees to radians
                rx, ry, rz = np.radians(rotate)
                
                # Create rotation matrix
                # Rotation around X
                Rx = np.array([
                    [1, 0, 0],
                    [0, np.cos(rx), -np.sin(rx)],
                    [0, np.sin(rx), np.cos(rx)]
                ])
                
                # Rotation around Y
                Ry = np.array([
                    [np.cos(ry), 0, np.sin(ry)],
                    [0, 1, 0],
                    [-np.sin(ry), 0, np.cos(ry)]
                ])
                
                # Rotation around Z
                Rz = np.array([
                    [np.cos(rz), -np.sin(rz), 0],
                    [np.sin(rz), np.cos(rz), 0],
                    [0, 0, 1]
                ])
                
                R = Rz @ Ry @ Rx
                export_mesh.vertices = (R @ export_mesh.vertices.T).T
            
            # Ensure we have normals if requested
            if include_normals and not hasattr(export_mesh, 'vertex_normals'):
                export_mesh.vertex_normals = export_mesh.vertex_normals
            
            # Ensure we have colors if requested
            if include_colors and not hasattr(export_mesh, 'visual'):
                # Create default colors
                colors = np.ones((len(export_mesh.vertices), 4), dtype=np.float32) * 0.8
                colors[:, 3] = 1.0  # Alpha
                export_mesh.visual = trimesh.visual.ColorVisuals(
                    vertex_colors=colors
                )
            
            # Export to GLB
            export_mesh.export(path, file_type='glb')
            
            return True
            
        except Exception as e:
            print(f"Error exporting GLB: {e}")
            return False
    
    def export_scene(self, meshes: List[trimesh.Trimesh], path: str,
                     scale: float = 1.0,
                     center_at_origin: bool = True) -> bool:
        """
        Export multiple meshes as a GLB scene
        
        Args:
            meshes: List of meshes to export
            path: Output file path
            scale: Scale factor
            center_at_origin: Center all meshes at origin
            
        Returns:
            True if export succeeded
        """
        try:
            if len(meshes) == 0:
                return False
            
            # Create scene
            scene = trimesh.Scene()
            
            for i, mesh in enumerate(meshes):
                # Create a copy
                export_mesh = mesh.copy()
                
                # Apply scale
                if scale != 1.0:
                    export_mesh.vertices *= scale
                
                # Add to scene
                node = trimesh.scene.transforms.TransformNode(
                    geometry=export_mesh,
                    name=f"Mesh_{i}"
                )
                scene.add_geometry(node)
            
            # Center at origin if requested
            if center_at_origin:
                # Calculate bounding box of all meshes
                all_vertices = []
                for mesh in meshes:
                    all_vertices.append(mesh.vertices)
                all_vertices = np.concatenate(all_vertices, axis=0)
                center = np.mean(all_vertices, axis=0)
                
                # Translate all meshes
                for node in scene.geometry.values():
                    if hasattr(node, 'vertices'):
                        node.vertices -= center
            
            # Export
            scene.export(path, file_type='glb')
            
            return True
            
        except Exception as e:
            print(f"Error exporting GLB scene: {e}")
            return False
    
    def export_with_unity_settings(self, mesh: trimesh.Trimesh, path: str,
                                    height_cm: float = 180.0,
                                    floor_y: float = 0.0) -> bool:
        """
        Export mesh with Unity-compatible settings
        
        Args:
            mesh: Mesh to export
            path: Output file path
            height_cm: Character height in centimeters
            floor_y: Y position of floor
            
        Returns:
            True if export succeeded
        """
        try:
            # Convert height to meters
            height_m = height_cm / 100.0
            
            # Calculate scale factor
            # Assuming mesh height is currently in arbitrary units
            # We want to scale it so the final height is height_m
            mesh_bounds = mesh.bounds
            current_height = mesh_bounds[1][1] - mesh_bounds[0][1]
            
            if current_height > 0:
                scale = height_m / current_height
            else:
                scale = 1.0
            
            # Calculate translation to put floor at Y=0
            # Find lowest point
            min_y = mesh_bounds[0][1]
            translate_y = -min_y * scale + floor_y
            
            # Export with transformations
            return self.export_mesh(
                mesh=mesh,
                path=path,
                scale=scale,
                translate=(0, translate_y, 0),
                include_normals=True,
                include_colors=True
            )
            
        except Exception as e:
            print(f"Error exporting with Unity settings: {e}")
            return False
    
    def create_unity_material(self, color: Tuple[float, float, float, float] = (0.8, 0.8, 0.8, 1.0),
                              metallic: float = 0.0, roughness: float = 0.5) -> Dict[str, Any]:
        """
        Create a Unity-compatible material definition
        
        Args:
            color: Base color (RGBA)
            metallic: Metallic value (0-1)
            roughness: Roughness value (0-1)
            
        Returns:
            Material definition dictionary
        """
        return {
            'name': 'DefaultMaterial',
            'shader': 'Standard',
            'properties': {
                '_Color': list(color),
                '_Metallic': metallic,
                '_Smoothness': 1.0 - roughness,
                '_Glossiness': 1.0 - roughness
            }
        }
    
    def export_with_materials(self, meshes: List[trimesh.Trimesh], 
                               materials: List[Dict[str, Any]], path: str) -> bool:
        """
        Export meshes with custom materials
        
        Note: GLB format has limited material support.
        This method exports the mesh and creates a separate JSON file
        with material definitions for Unity.
        
        Args:
            meshes: List of meshes
            materials: List of material definitions
            path: Output file path (GLB)
            
        Returns:
            True if export succeeded
        """
        # Export the mesh
        if not self.export_scene(meshes, path):
            return False
        
        # Create material JSON
        material_path = path.replace('.glb', '_materials.json')
        
        try:
            material_data = {
                'format': 'UnityMaterials',
                'version': '1.0',
                'materials': materials,
                'mesh_path': Path(path).name
            }
            
            with open(material_path, 'w', encoding='utf-8') as f:
                json.dump(material_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Error exporting materials: {e}")
            return False


class OBJExporter:
    """
    Exporter for OBJ format
    """
    
    @staticmethod
    def export_mesh(mesh: trimesh.Trimesh, path: str, 
                    include_normals: bool = True,
                    include_colors: bool = True) -> bool:
        """
        Export mesh to OBJ format
        
        Args:
            mesh: Mesh to export
            path: Output file path
            include_normals: Include vertex normals
            include_colors: Include vertex colors
            
        Returns:
            True if export succeeded
        """
        try:
            export_options = {
                'vn': include_normals,
                'vc': include_colors
            }
            
            mesh.export(path, file_type='obj', **export_options)
            return True
            
        except Exception as e:
            print(f"Error exporting OBJ: {e}")
            return False


class STLExporter:
    """
    Exporter for STL format
    """
    
    @staticmethod
    def export_mesh(mesh: trimesh.Trimesh, path: str, 
                    ascii: bool = False) -> bool:
        """
        Export mesh to STL format
        
        Args:
            mesh: Mesh to export
            path: Output file path
            ascii: Use ASCII format (default: binary)
            
        Returns:
            True if export succeeded
        """
        try:
            mesh.export(path, file_type='stl', ascii=ascii)
            return True
            
        except Exception as e:
            print(f"Error exporting STL: {e}")
            return False


class ExportManager:
    """
    Manager class for all export operations
    """
    
    def __init__(self):
        self.glb_exporter = GLBExporter()
        self.obj_exporter = OBJExporter()
        self.stl_exporter = STLExporter()
    
    def export_to_glb(self, mesh: trimesh.Trimesh, path: str, 
                      **kwargs) -> bool:
        """Export to GLB format"""
        return self.glb_exporter.export_mesh(mesh, path, **kwargs)
    
    def export_to_obj(self, mesh: trimesh.Trimesh, path: str, 
                      **kwargs) -> bool:
        """Export to OBJ format"""
        return self.obj_exporter.export_mesh(mesh, path, **kwargs)
    
    def export_to_stl(self, mesh: trimesh.Trimesh, path: str, 
                      **kwargs) -> bool:
        """Export to STL format"""
        return self.stl_exporter.export_mesh(mesh, path, **kwargs)
    
    def export_for_unity(self, mesh: trimesh.Trimesh, path: str,
                         height_cm: float = 180.0, floor_y: float = 0.0) -> bool:
        """
        Export mesh optimized for Unity
        
        Args:
            mesh: Mesh to export
            path: Output file path
            height_cm: Character height in centimeters
            floor_y: Y position of floor (should be 0 for Unity)
            
        Returns:
            True if export succeeded
        """
        return self.glb_exporter.export_with_unity_settings(
            mesh, path, height_cm, floor_y
        )
    
    def export_scene(self, meshes: List[trimesh.Trimesh], path: str,
                     format: str = 'glb', **kwargs) -> bool:
        """
        Export multiple meshes as a scene
        
        Args:
            meshes: List of meshes
            path: Output file path
            format: Export format ('glb', 'obj', 'stl')
            **kwargs: Additional arguments for specific exporter
            
        Returns:
            True if export succeeded
        """
        if format == 'glb':
            return self.glb_exporter.export_scene(meshes, path, **kwargs)
        elif format == 'obj':
            # OBJ doesn't support scenes directly, export first mesh
            if len(meshes) > 0:
                return self.obj_exporter.export_mesh(meshes[0], path, **kwargs)
            return False
        elif format == 'stl':
            # STL doesn't support scenes, export first mesh
            if len(meshes) > 0:
                return self.stl_exporter.export_mesh(meshes[0], path, **kwargs)
            return False
        
        return False


# Convenience functions

def export_to_glb(mesh: trimesh.Trimesh, path: str, **kwargs) -> bool:
    """Convenience function to export to GLB"""
    exporter = GLBExporter()
    return exporter.export_mesh(mesh, path, **kwargs)


def export_for_unity(mesh: trimesh.Trimesh, path: str, height_cm: float = 180.0) -> bool:
    """Convenience function to export for Unity"""
    exporter = GLBExporter()
    return exporter.export_with_unity_settings(mesh, path, height_cm)
