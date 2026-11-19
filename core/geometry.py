"""
Geometry module for 3D mesh generation using SDF and Marching Cubes
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from scipy import ndimage
from skimage.measure import marching_cubes
import trimesh


@dataclass
class Mesh:
    """Represents a 3D mesh"""
    vertices: np.ndarray  # (N, 3) array of vertex positions
    faces: np.ndarray  # (M, 3) array of face indices
    vertex_colors: Optional[np.ndarray] = None  # (N, 3) or (N, 4) array of colors
    normals: Optional[np.ndarray] = None  # (N, 3) array of vertex normals
    
    def to_trimesh(self) -> trimesh.Trimesh:
        """Convert to trimesh object"""
        return trimesh.Trimesh(
            vertices=self.vertices,
            faces=self.faces,
            vertex_colors=self.vertex_colors
        )
    
    def to_pyvista(self):
        """Convert to PyVista mesh (lazy import)"""
        try:
            import pyvista as pv
            return pv.PolyData(self.vertices, self.faces)
        except ImportError:
            raise ImportError("PyVista is required for visualization")
    
    def save_to_glb(self, path: str, scale: float = 1.0) -> bool:
        """Save mesh to GLB format"""
        try:
            mesh = self.to_trimesh()
            # Apply scale
            mesh.vertices *= scale
            mesh.export(path, file_type='glb')
            return True
        except Exception as e:
            print(f"Error saving GLB: {e}")
            return False
    
    def get_bounds(self) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        """Get bounding box of the mesh"""
        if len(self.vertices) == 0:
            return ((0, 0, 0), (0, 0, 0))
        
        min_coords = self.vertices.min(axis=0)
        max_coords = self.vertices.max(axis=0)
        
        return (tuple(min_coords), tuple(max_coords))
    
    def center(self) -> np.ndarray:
        """Get center of the mesh"""
        if len(self.vertices) == 0:
            return np.array([0, 0, 0])
        return self.vertices.mean(axis=0)
    
    def translate(self, vector: np.ndarray) -> 'Mesh':
        """Translate mesh by vector"""
        return Mesh(
            vertices=self.vertices + vector,
            faces=self.faces,
            vertex_colors=self.vertex_colors,
            normals=self.normals
        )
    
    def scale(self, factor: float) -> 'Mesh':
        """Scale mesh uniformly"""
        return Mesh(
            vertices=self.vertices * factor,
            faces=self.faces,
            vertex_colors=self.vertex_colors,
            normals=self.normals
        )


class SDFGenerator:
    """
    Signed Distance Field generator for creating 3D shapes from 2D contours
    """
    
    def __init__(self, grid_size: int = 128, voxel_size: float = 0.01):
        self.grid_size = grid_size
        self.voxel_size = voxel_size
    
    def create_capsule_sdf(self, start: np.ndarray, end: np.ndarray, radius: float) -> np.ndarray:
        """
        Create SDF for a capsule (cylinder with hemispherical caps)
        
        Args:
            start: Start point of capsule axis
            end: End point of capsule axis
            radius: Radius of capsule
            
        Returns:
            3D numpy array with SDF values
        """
        # Create grid
        axis = end - start
        length = np.linalg.norm(axis)
        
        # Create bounding box
        center = (start + end) / 2
        half_length = length / 2 + radius
        
        # Create grid coordinates
        x = np.linspace(-half_length, half_length, self.grid_size)
        y = np.linspace(-radius * 2, radius * 2, self.grid_size)
        z = np.linspace(-radius * 2, radius * 2, self.grid_size)
        xx, yy, zz = np.meshgrid(x, y, z, indexing='ij')
        
        # Transform to capsule local coordinates
        if length > 0:
            axis_dir = axis / length
        else:
            axis_dir = np.array([0, 1, 0])
        
        # Create orthogonal basis
        # Find vector orthogonal to axis
        if np.abs(axis_dir[0]) < 0.5:
            v1 = np.array([1, 0, 0])
        else:
            v1 = np.array([0, 1, 0])
        v1 = v1 - np.dot(v1, axis_dir) * axis_dir
        v1 = v1 / np.linalg.norm(v1)
        v2 = np.cross(axis_dir, v1)
        
        # Transform grid points to local coordinates
        local_pts = np.stack([xx.ravel(), yy.ravel(), zz.ravel()], axis=1) - center
        local_coords = np.array([
            np.dot(local_pts, v1),
            np.dot(local_pts, axis_dir),
            np.dot(local_pts, v2)
        ]).T
        
        # Calculate SDF
        r_xy = np.sqrt(local_coords[:, 0]**2 + local_coords[:, 2]**2)
        
        # Distance along axis (clamped)
        t = np.clip(local_coords[:, 1], -half_length, half_length)
        
        # SDF for capsule
        sdf = np.sqrt(r_xy**2 + (np.abs(t) - half_length + radius)**2) - radius
        
        # Reshape back to 3D
        sdf = sdf.reshape((self.grid_size, self.grid_size, self.grid_size))
        
        return sdf
    
    def create_sphere_sdf(self, center: np.ndarray, radius: float) -> np.ndarray:
        """Create SDF for a sphere"""
        x = np.linspace(-radius * 2, radius * 2, self.grid_size)
        y = np.linspace(-radius * 2, radius * 2, self.grid_size)
        z = np.linspace(-radius * 2, radius * 2, self.grid_size)
        xx, yy, zz = np.meshgrid(x, y, z, indexing='ij')
        
        distance = np.sqrt((xx - center[0])**2 + (yy - center[1])**2 + (zz - center[2])**2)
        sdf = distance - radius
        
        return sdf
    
    def create_box_sdf(self, center: np.ndarray, size: np.ndarray) -> np.ndarray:
        """Create SDF for a box"""
        half_size = size / 2
        
        x = np.linspace(-half_size[0] * 2, half_size[0] * 2, self.grid_size)
        y = np.linspace(-half_size[1] * 2, half_size[1] * 2, self.grid_size)
        z = np.linspace(-half_size[2] * 2, half_size[2] * 2, self.grid_size)
        xx, yy, zz = np.meshgrid(x, y, z, indexing='ij')
        
        # Calculate distance to box
        dx = np.abs(xx - center[0]) - half_size[0]
        dy = np.abs(yy - center[1]) - half_size[1]
        dz = np.abs(zz - center[2]) - half_size[2]
        
        # SDF for box
        sdf_outside = np.sqrt(
            np.maximum(dx, 0)**2 + 
            np.maximum(dy, 0)**2 + 
            np.maximum(dz, 0)**2
        )
        sdf_inside = np.sqrt(
            np.maximum(-dx, 0)**2 + 
            np.maximum(-dy, 0)**2 + 
            np.maximum(-dz, 0)**2
        )
        sdf = sdf_outside - sdf_inside
        
        return sdf
    
    def union_sdf(self, sdf1: np.ndarray, sdf2: np.ndarray) -> np.ndarray:
        """Union of two SDFs (minimum)"""
        return np.minimum(sdf1, sdf2)
    
    def intersection_sdf(self, sdf1: np.ndarray, sdf2: np.ndarray) -> np.ndarray:
        """Intersection of two SDFs (maximum)"""
        return np.maximum(sdf1, sdf2)
    
    def subtract_sdf(self, sdf1: np.ndarray, sdf2: np.ndarray) -> np.ndarray:
        """Subtraction of two SDFs"""
        return np.maximum(sdf1, -sdf2)


class MeshGenerator:
    """
    Mesh generator using Marching Cubes algorithm
    """
    
    def __init__(self, sdf_generator: Optional[SDFGenerator] = None):
        self.sdf_gen = sdf_generator or SDFGenerator()
    
    def generate_from_sdf(self, sdf: np.ndarray, level: float = 0.0) -> Optional[Mesh]:
        """
        Generate mesh from SDF using Marching Cubes
        
        Args:
            sdf: 3D numpy array with SDF values
            level: Iso-surface level (typically 0 for surface)
            
        Returns:
            Mesh object or None if mesh generation fails
        """
        try:
            # Use scikit-image's marching cubes
            # Note: marching_cubes expects the array in (z, y, x) order by default
            # but we'll use it in standard order
            verts, faces, normals, values = marching_cubes(
                sdf, 
                level=level,
                spacing=(1, 1, 1)
            )
            
            # Adjust vertex order for proper normals
            # Marching cubes might produce inverted normals
            
            return Mesh(
                vertices=verts,
                faces=faces,
                normals=normals,
                vertex_colors=None
            )
        except Exception as e:
            print(f"Error in marching cubes: {e}")
            return None
    
    def generate_capsule_mesh(self, start: np.ndarray, end: np.ndarray, radius: float, 
                                resolution: int = 64) -> Optional[Mesh]:
        """Generate a capsule mesh directly (more efficient than SDF)"""
        try:
            # Create capsule using trimesh
            length = float(np.linalg.norm(end - start))
            
            # Create capsule
            capsule = trimesh.creation.capsule(
                height=length,
                radius=radius,
                count=(resolution, resolution)
            )
            
            # Rotate and position
            direction = end - start
            direction_norm = np.linalg.norm(direction)
            
            if direction_norm > 0:
                direction = direction / direction_norm
                # Create rotation matrix
                # Default capsule is along Z axis
                z_axis = np.array([0.0, 0.0, 1.0])
                if not np.allclose(direction, z_axis):
                    # Find rotation axis
                    rotation_axis = np.cross(z_axis, direction)
                    rotation_angle = np.arccos(np.clip(float(np.dot(z_axis, direction)), -1.0, 1.0))
                    
                    if np.linalg.norm(rotation_axis) > 0:
                        rotation_axis = rotation_axis / np.linalg.norm(rotation_axis)
                        # Create rotation matrix using Rodrigues' formula
                        K = np.array([
                            [0.0, -rotation_axis[2], rotation_axis[1]],
                            [rotation_axis[2], 0.0, -rotation_axis[0]],
                            [-rotation_axis[1], rotation_axis[0], 0.0]
                        ])
                        R = np.eye(3) + np.sin(rotation_angle) * K + \
                            (1.0 - np.cos(rotation_angle)) * np.dot(K, K)
                    else:
                        R = np.eye(3)
                else:
                    R = np.eye(3)
                
                # Apply rotation and translation
                capsule.vertices = (R @ capsule.vertices.T).T
                capsule.vertices += start
            else:
                capsule.vertices += start
            
            return Mesh(
                vertices=capsule.vertices,
                faces=capsule.faces,
                normals=capsule.vertex_normals,
                vertex_colors=None
            )
        except Exception as e:
            print(f"Error generating capsule: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def generate_skeleton_mesh(self, joints: Dict[str, Any], bones: List[Dict[str, Any]],
                                capsule_radii: Dict[str, float] = None) -> Optional[Mesh]:
        """
        Generate mesh from skeleton by creating capsules for each bone
        
        Args:
            joints: Dictionary of joint IDs to Joint objects or dicts with 'worldPosition'
            bones: List of bone data with 'from', 'to', 'region'
            capsule_radii: Dictionary of region names to radius values
            
        Returns:
            Combined mesh of all capsules
        """
        if capsule_radii is None:
            capsule_radii = {
                'torso': 0.15,
                'arms': 0.06,
                'legs': 0.09,
                'head': 0.08,
                'neck': 0.05
            }
        
        meshes = []
        
        for bone in bones:
            from_id = bone.get('from', '')
            to_id = bone.get('to', '')
            region = bone.get('region', 'other')
            
            if from_id not in joints or to_id not in joints:
                continue
            
            from_joint = joints[from_id]
            to_joint = joints[to_id]
            
            # Extract positions - handle both Joint objects and dicts
            from_pos = self._get_joint_position(from_joint)
            to_pos = self._get_joint_position(to_joint)
            
            # Get radius for this region
            radius = capsule_radii.get(region, 0.05)
            
            # Generate capsule for this bone
            capsule_mesh = self.generate_capsule_mesh(from_pos, to_pos, radius)
            if capsule_mesh:
                meshes.append(capsule_mesh)
        
        # Combine all meshes
        if len(meshes) == 0:
            return None
        
        return self.combine_meshes(meshes)
    
    def _get_joint_position(self, joint: Any) -> np.ndarray:
        """
        Extract position from joint (handles both Joint objects and dicts)
        
        Args:
            joint: Joint object or dict with position data
            
        Returns:
            Position as numpy array [x, y, z]
        """
        # Check if it's a Joint object (has world_position attribute)
        if hasattr(joint, 'world_position'):
            wp = joint.world_position
            return np.array([float(wp[0]), float(wp[1]), float(wp[2])])
        # Check if it's a dict with worldPosition
        elif isinstance(joint, dict) and 'worldPosition' in joint:
            wp = joint['worldPosition']
            if isinstance(wp, dict):
                return np.array([wp.get('x', 0), wp.get('y', 0), wp.get('z', 0)])
            elif isinstance(wp, (list, tuple)) and len(wp) >= 3:
                return np.array([float(wp[0]), float(wp[1]), float(wp[2])])
        # Check if it's a dict with x, y, z directly
        elif isinstance(joint, dict):
            return np.array([joint.get('x', 0), joint.get('y', 0), joint.get('z', 0)])
        # Fallback
        else:
            return np.array([0.0, 0.0, 0.0])
    
    def combine_meshes(self, meshes: List[Mesh]) -> Optional[Mesh]:
        """Combine multiple meshes into one"""
        if len(meshes) == 0:
            return None
        
        try:
            # Use trimesh for combining
            trimesh_meshes = [m.to_trimesh() for m in meshes]
            combined = trimesh.util.concatenate(trimesh_meshes)
            
            return Mesh(
                vertices=combined.vertices,
                faces=combined.faces,
                vertex_colors=combined.visual.vertex_colors if hasattr(combined.visual, 'vertex_colors') else None,
                normals=combined.vertex_normals
            )
        except Exception as e:
            print(f"Error combining meshes: {e}")
            return None
    
    def generate_from_contours(self, contours: List[Any], height: float = 1.8) -> Optional[Mesh]:
        """
        Generate 3D mesh from 2D contours by extruding and connecting
        
        Args:
            contours: List of contour objects with points
            height: Total height for extrusion
            
        Returns:
            3D mesh
        """
        if len(contours) == 0:
            return None
        
        try:
            # For now, create a simple extrusion
            # In a full implementation, this would create a proper SDF
            # and use marching cubes
            
            # Sort contours by Y position (assuming they're at different heights)
            sorted_contours = sorted(contours, key=lambda c: np.mean([p[1] for p in c.points]))
            
            # Create 3D points
            vertices_3d = []
            for i, contour in enumerate(sorted_contours):
                z = (i / len(sorted_contours)) * height
                for x, y in contour.points:
                    vertices_3d.append([x, z, y])  # Note: using Z for height
            
            # Create simple mesh (this is a placeholder)
            # In a real implementation, we'd create proper connectivity
            vertices = np.array(vertices_3d)
            
            # Create a simple box for now
            # This is just a placeholder - actual implementation would be more complex
            box = trimesh.creation.box(extents=[1, height, 1])
            
            return Mesh(
                vertices=box.vertices,
                faces=box.faces,
                normals=box.vertex_normals
            )
        except Exception as e:
            print(f"Error generating mesh from contours: {e}")
            return None
    
    def smooth_mesh(self, mesh: Mesh, iterations: int = 1) -> Optional[Mesh]:
        """
        Smooth a mesh using Laplacian smoothing
        
        Args:
            mesh: Input mesh
            iterations: Number of smoothing iterations
            
        Returns:
            Smoothed mesh
        """
        try:
            tm = mesh.to_trimesh()
            smoothed = tm.smoothed(iterations=iterations)
            
            return Mesh(
                vertices=smoothed.vertices,
                faces=smoothed.faces,
                vertex_colors=mesh.vertex_colors,
                normals=smoothed.vertex_normals
            )
        except Exception as e:
            print(f"Error smoothing mesh: {e}")
            return None
    
    def decimate_mesh(self, mesh: Mesh, target_faces: int = 1000) -> Optional[Mesh]:
        """
        Decimate a mesh to reduce polygon count
        
        Args:
            mesh: Input mesh
            target_faces: Target number of faces
            
        Returns:
            Decimated mesh
        """
        try:
            tm = mesh.to_trimesh()
            decimated = tm.simplify_quadric_decimation(target_faces)
            
            return Mesh(
                vertices=decimated.vertices,
                faces=decimated.faces,
                vertex_colors=mesh.vertex_colors,
                normals=decimated.vertex_normals
            )
        except Exception as e:
            print(f"Error decimating mesh: {e}")
            return None


class ReferenceSlide:
    """
    Represents a reference slide (2D image) positioned in 3D space
    """
    
    def __init__(self, image: np.ndarray, position: np.ndarray = np.array([0, 0, 0]),
                 rotation: np.ndarray = np.array([0, 0, 0]),
                 scale: np.ndarray = np.array([1, 1, 1]),
                 opacity: float = 1.0, x_ray_mode: bool = False):
        self.image = image
        self.position = position
        self.rotation = rotation  # Euler angles in radians
        self.scale = scale
        self.opacity = opacity
        self.x_ray_mode = x_ray_mode
        
        # Calculate transformation matrix
        self._update_transform()
    
    def _update_transform(self) -> None:
        """Update transformation matrix"""
        # Create rotation matrix from Euler angles
        rx, ry, rz = self.rotation
        
        # Rotation matrices
        Rx = np.array([
            [1, 0, 0],
            [0, np.cos(rx), -np.sin(rx)],
            [0, np.sin(rx), np.cos(rx)]
        ])
        
        Ry = np.array([
            [np.cos(ry), 0, np.sin(ry)],
            [0, 1, 0],
            [-np.sin(ry), 0, np.cos(ry)]
        ])
        
        Rz = np.array([
            [np.cos(rz), -np.sin(rz), 0],
            [np.sin(rz), np.cos(rz), 0],
            [0, 0, 1]
        ])
        
        R = Rz @ Ry @ Rx
        
        # Scale matrix
        S = np.diag(self.scale)
        
        # Translation
        T = np.eye(4)
        T[:3, 3] = self.position
        
        # Combined transformation
        self.transform = T @ S @ R
    
    def set_position(self, position: np.ndarray) -> None:
        """Set position and update transform"""
        self.position = position
        self._update_transform()
    
    def set_rotation(self, rotation: np.ndarray) -> None:
        """Set rotation and update transform"""
        self.rotation = rotation
        self._update_transform()
    
    def set_scale(self, scale: np.ndarray) -> None:
        """Set scale and update transform"""
        self.scale = scale
        self._update_transform()
    
    def get_vertices(self) -> np.ndarray:
        """Get vertices of the slide quad in world space"""
        # Image dimensions
        h, w = self.image.shape[:2]
        
        # Corners in local space
        corners = np.array([
            [0, 0, 0, 1],
            [w, 0, 0, 1],
            [w, h, 0, 1],
            [0, h, 0, 1]
        ]).T
        
        # Transform to world space
        world_corners = self.transform @ corners
        
        return world_corners[:3].T
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'position': self.position.tolist(),
            'rotation': self.rotation.tolist(),
            'scale': self.scale.tolist(),
            'opacity': self.opacity,
            'x_ray_mode': self.x_ray_mode
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], image: np.ndarray = None) -> 'ReferenceSlide':
        """Create from dictionary"""
        slide = cls(
            image=image or np.zeros((100, 100, 3), dtype=np.uint8),
            position=np.array(data.get('position', [0, 0, 0])),
            rotation=np.array(data.get('rotation', [0, 0, 0])),
            scale=np.array(data.get('scale', [1, 1, 1])),
            opacity=data.get('opacity', 1.0),
            x_ray_mode=data.get('x_ray_mode', False)
        )
        return slide
