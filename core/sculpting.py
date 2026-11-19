"""
Sculpting tools for 3D mesh manipulation
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
from copy import deepcopy
import trimesh


class SculptTool(Enum):
    """Types of sculpting tools"""
    INFLATE = "inflate"
    GRAB = "grab"
    SMOOTH = "smooth"
    CREASE = "crease"
    FLATTEN = "flatten"


@dataclass
class BrushSettings:
    """Settings for sculpting brush"""
    radius: float = 0.1  # Brush radius in world units
    strength: float = 0.5  # Brush strength (0-1)
    hardness: float = 0.5  # Brush hardness (0-1, 1 = hard edge)
    tool: SculptTool = SculptTool.INFLATE
    use_x_mirror: bool = False  # Mirror across X axis
    use_symmetry: bool = False  # Use radial symmetry
    symmetry_count: int = 6  # Number of symmetry axes


@dataclass
class SculptAction:
    """Represents a sculpting action for undo/redo"""
    vertices_before: np.ndarray
    vertices_after: np.ndarray
    description: str = ""


class SculptingTools:
    """
    Main class for sculpting operations on 3D meshes
    """
    
    def __init__(self):
        self.brush = BrushSettings()
        self._mesh: Optional[trimesh.Trimesh] = None
        self._history: List[SculptAction] = []
        self._history_index: int = -1
        self._max_history: int = 50
        self._selected_vertices: List[int] = []
        self._last_hit: Optional[Tuple[int, float]] = None  # (vertex_index, distance)
    
    def set_mesh(self, mesh: trimesh.Trimesh) -> None:
        """Set the mesh to sculpt on"""
        self._mesh = mesh
        self._history = []
        self._history_index = -1
        self._selected_vertices = []
    
    def get_mesh(self) -> Optional[trimesh.Trimesh]:
        """Get the current mesh"""
        return self._mesh
    
    def set_brush_settings(self, settings: BrushSettings) -> None:
        """Set brush settings"""
        self.brush = settings
    
    def get_brush_settings(self) -> BrushSettings:
        """Get current brush settings"""
        return self.brush
    
    def _find_vertices_in_radius(self, position: np.ndarray) -> List[int]:
        """Find vertices within brush radius"""
        if self._mesh is None:
            return []
        
        # Calculate distances from position to all vertices
        distances = np.linalg.norm(self._mesh.vertices - position, axis=1)
        
        # Find vertices within radius
        mask = distances <= self.brush.radius
        indices = np.where(mask)[0].tolist()
        
        return indices
    
    def _calculate_brush_weights(self, position: np.ndarray, vertex_indices: List[int]) -> np.ndarray:
        """Calculate brush weights for each vertex"""
        if self._mesh is None or len(vertex_indices) == 0:
            return np.array([])
        
        vertices = self._mesh.vertices[vertex_indices]
        distances = np.linalg.norm(vertices - position, axis=1)
        
        # Normalize distances to [0, 1]
        normalized = distances / self.brush.radius
        
        # Apply hardness: higher hardness = sharper falloff
        # Using smoothstep function for smooth falloff
        weights = 1.0 - np.clip(normalized, 0, 1)
        weights = weights ** (1.0 / max(self.brush.hardness, 0.01))
        
        # Apply strength
        weights *= self.brush.strength
        
        return weights
    
    def _apply_x_mirror(self, vertex_indices: List[int]) -> List[int]:
        """Apply X-axis mirroring to vertex selection"""
        if not self.brush.use_x_mirror or self._mesh is None:
            return vertex_indices
        
        mirrored_indices = []
        for idx in vertex_indices:
            # Find mirrored vertex
            vertex = self._mesh.vertices[idx]
            mirrored_pos = np.array([-vertex[0], vertex[1], vertex[2]])
            
            # Find closest vertex to mirrored position
            distances = np.linalg.norm(self._mesh.vertices - mirrored_pos, axis=1)
            mirrored_idx = np.argmin(distances)
            
            if mirrored_idx not in vertex_indices and mirrored_idx not in mirrored_indices:
                mirrored_indices.append(mirrored_idx)
        
        return vertex_indices + mirrored_indices
    
    def _apply_symmetry(self, vertex_indices: List[int]) -> List[int]:
        """Apply radial symmetry to vertex selection"""
        if not self.brush.use_symmetry or self.brush.symmetry_count < 2:
            return vertex_indices
        
        if self._mesh is None:
            return vertex_indices
        
        all_indices = vertex_indices.copy()
        center = np.mean(self._mesh.vertices[vertex_indices], axis=0)
        
        for symmetry_idx in range(1, self.brush.symmetry_count):
            angle = (2 * np.pi * symmetry_idx) / self.brush.symmetry_count
            
            # Rotation matrix around Y axis
            rotation = np.array([
                [np.cos(angle), 0, np.sin(angle)],
                [0, 1, 0],
                [-np.sin(angle), 0, np.cos(angle)]
            ])
            
            for idx in vertex_indices:
                vertex = self._mesh.vertices[idx]
                # Translate to origin, rotate, translate back
                relative = vertex - center
                rotated = rotation @ relative
                rotated_pos = rotated + center
                
                # Find closest vertex to rotated position
                distances = np.linalg.norm(self._mesh.vertices - rotated_pos, axis=1)
                closest_idx = np.argmin(distances)
                
                if closest_idx not in all_indices:
                    all_indices.append(closest_idx)
        
        return all_indices
    
    def _get_affected_vertices(self, position: np.ndarray) -> List[int]:
        """Get all vertices affected by brush at position"""
        indices = self._find_vertices_in_radius(position)
        indices = self._apply_x_mirror(indices)
        indices = self._apply_symmetry(indices)
        return indices
    
    def _save_state(self, description: str = "") -> None:
        """Save current state for undo"""
        if self._mesh is None:
            return
        
        # Trim history if too long
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
            self._history_index = len(self._history) - 1
        
        # Save action
        action = SculptAction(
            vertices_before=self._mesh.vertices.copy(),
            vertices_after=self._mesh.vertices.copy(),
            description=description
        )
        
        self._history = self._history[:self._history_index + 1]
        self._history.append(action)
        self._history_index = len(self._history) - 1
    
    def inflate(self, position: np.ndarray, direction: float = 1.0) -> bool:
        """
        Inflate tool: Move vertices along their normals
        
        Args:
            position: World position of brush center
            direction: 1.0 for inflate, -1.0 for deflate
            
        Returns:
            True if operation succeeded
        """
        if self._mesh is None:
            return False
        
        # Find affected vertices
        vertex_indices = self._get_affected_vertices(position)
        if len(vertex_indices) == 0:
            return False
        
        # Save state for undo
        self._save_state(f"Inflate at {position}")
        
        # Calculate weights
        weights = self._calculate_brush_weights(position, vertex_indices)
        
        # Get normals for affected vertices
        normals = self._mesh.vertex_normals[vertex_indices]
        
        # Apply inflation
        for i, idx in enumerate(vertex_indices):
            offset = normals[i] * weights[i] * direction
            self._mesh.vertices[idx] += offset
        
        # Update normals
        self._mesh.vertex_normals = self._mesh.vertex_normals  # Recalculate
        
        return True
    
    def grab(self, position: np.ndarray, drag_vector: np.ndarray) -> bool:
        """
        Grab tool: Move vertices in the direction of drag
        
        Args:
            position: World position of brush center
            drag_vector: Vector indicating drag direction and distance
            
        Returns:
            True if operation succeeded
        """
        if self._mesh is None:
            return False
        
        # Find affected vertices
        vertex_indices = self._get_affected_vertices(position)
        if len(vertex_indices) == 0:
            return False
        
        # Save state for undo
        self._save_state(f"Grab at {position}")
        
        # Calculate weights
        weights = self._calculate_brush_weights(position, vertex_indices)
        
        # Apply grab
        for i, idx in enumerate(vertex_indices):
            offset = drag_vector * weights[i]
            self._mesh.vertices[idx] += offset
        
        # Update normals
        self._mesh.vertex_normals = self._mesh.vertex_normals  # Recalculate
        
        return True
    
    def smooth(self, position: np.ndarray) -> bool:
        """
        Smooth tool: Smooth vertices by averaging with neighbors
        
        Args:
            position: World position of brush center
            
        Returns:
            True if operation succeeded
        """
        if self._mesh is None:
            return False
        
        # Find affected vertices
        vertex_indices = self._get_affected_vertices(position)
        if len(vertex_indices) == 0:
            return False
        
        # Save state for undo
        self._save_state(f"Smooth at {position}")
        
        # Calculate weights
        weights = self._calculate_brush_weights(position, vertex_indices)
        
        # Build adjacency list
        adjacency = {}
        for face in self._mesh.faces:
            for i in range(3):
                v0 = face[i]
                v1 = face[(i + 1) % 3]
                if v0 not in adjacency:
                    adjacency[v0] = []
                if v1 not in adjacency[v0]:
                    adjacency[v0].append(v1)
                if v1 not in adjacency:
                    adjacency[v1] = []
                if v0 not in adjacency[v1]:
                    adjacency[v1].append(v0)
        
        # Apply smoothing
        for i, idx in enumerate(vertex_indices):
            if idx not in adjacency:
                continue
            
            # Get neighbors
            neighbors = adjacency[idx]
            if len(neighbors) == 0:
                continue
            
            # Calculate weighted average
            neighbor_positions = self._mesh.vertices[neighbors]
            average = np.mean(neighbor_positions, axis=0)
            
            # Blend with current position
            blend_factor = weights[i] * 0.5  # Smoothing strength
            new_pos = self._mesh.vertices[idx] * (1 - blend_factor) + average * blend_factor
            
            self._mesh.vertices[idx] = new_pos
        
        # Update normals
        self._mesh.vertex_normals = self._mesh.vertex_normals  # Recalculate
        
        return True
    
    def crease(self, position: np.ndarray, direction: float = 1.0) -> bool:
        """
        Crease tool: Sharpen edges by moving vertices towards center
        
        Args:
            position: World position of brush center
            direction: 1.0 for crease in, -1.0 for crease out
            
        Returns:
            True if operation succeeded
        """
        if self._mesh is None:
            return False
        
        # Find affected vertices
        vertex_indices = self._get_affected_vertices(position)
        if len(vertex_indices) == 0:
            return False
        
        # Save state for undo
        self._save_state(f"Crease at {position}")
        
        # Calculate weights
        weights = self._calculate_brush_weights(position, vertex_indices)
        
        # Calculate center of affected vertices
        center = np.mean(self._mesh.vertices[vertex_indices], axis=0)
        
        # Apply crease
        for i, idx in enumerate(vertex_indices):
            direction_to_center = center - self._mesh.vertices[idx]
            if np.linalg.norm(direction_to_center) > 0:
                direction_to_center = direction_to_center / np.linalg.norm(direction_to_center)
            
            offset = direction_to_center * weights[i] * direction * 0.5
            self._mesh.vertices[idx] += offset
        
        # Update normals
        self._mesh.vertex_normals = self._mesh.vertex_normals  # Recalculate
        
        return True
    
    def flatten(self, position: np.ndarray, flatten_normal: np.ndarray = None) -> bool:
        """
        Flatten tool: Flatten vertices onto a plane
        
        Args:
            position: World position of brush center
            flatten_normal: Normal of the flattening plane (default: view normal)
            
        Returns:
            True if operation succeeded
        """
        if self._mesh is None:
            return False
        
        # Find affected vertices
        vertex_indices = self._get_affected_vertices(position)
        if len(vertex_indices) == 0:
            return False
        
        # Save state for undo
        self._save_state(f"Flatten at {position}")
        
        # Default flatten normal (towards viewer / Z axis)
        if flatten_normal is None:
            flatten_normal = np.array([0, 0, 1])
        flatten_normal = flatten_normal / np.linalg.norm(flatten_normal)
        
        # Calculate weights
        weights = self._calculate_brush_weights(position, vertex_indices)
        
        # Project vertices onto plane
        for i, idx in enumerate(vertex_indices):
            vertex = self._mesh.vertices[idx]
            # Distance from vertex to plane (plane passes through position)
            distance = np.dot(vertex - position, flatten_normal)
            # Move vertex towards plane
            offset = flatten_normal * distance * weights[i]
            self._mesh.vertices[idx] -= offset
        
        # Update normals
        self._mesh.vertex_normals = self._mesh.vertex_normals  # Recalculate
        
        return True
    
    def undo(self) -> bool:
        """Undo last sculpting action"""
        if self._history_index > 0:
            self._history_index -= 1
            action = self._history[self._history_index]
            if self._mesh is not None:
                self._mesh.vertices = action.vertices_before.copy()
                self._mesh.vertex_normals = self._mesh.vertex_normals  # Recalculate
            return True
        return False
    
    def redo(self) -> bool:
        """Redo last undone action"""
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            action = self._history[self._history_index]
            if self._mesh is not None:
                self._mesh.vertices = action.vertices_after.copy()
                self._mesh.vertex_normals = self._mesh.vertex_normals  # Recalculate
            return True
        return False
    
    def clear_history(self) -> None:
        """Clear undo/redo history"""
        self._history = []
        self._history_index = -1
    
    def ray_cast(self, ray_origin: np.ndarray, ray_direction: np.ndarray) -> Optional[Tuple[int, float]]:
        """
        Cast a ray to find the closest vertex
        
        Args:
            ray_origin: Origin of ray in world space
            ray_direction: Direction of ray (normalized)
            
        Returns:
            Tuple of (vertex_index, distance) or None if no intersection
        """
        if self._mesh is None:
            return None
        
        # Simple ray-vertex intersection (not true ray-triangle)
        # For sculpting, we just want the closest vertex to the ray
        vertices = self._mesh.vertices
        
        # Vector from origin to each vertex
        vertex_vectors = vertices - ray_origin
        
        # Project onto ray direction
        projections = np.dot(vertex_vectors, ray_direction)
        
        # Find vertex with largest positive projection (in front of ray)
        valid_mask = projections > 0
        if not np.any(valid_mask):
            return None
        
        # Get distances
        distances = np.linalg.norm(vertex_vectors[valid_mask], axis=1)
        
        # Find closest
        closest_idx = np.argmin(distances)
        actual_idx = np.where(valid_mask)[0][closest_idx]
        
        self._last_hit = (actual_idx, distances[closest_idx])
        return self._last_hit
    
    def get_last_hit(self) -> Optional[Tuple[int, float]]:
        """Get the last ray cast hit"""
        return self._last_hit
    
    def select_vertices(self, position: np.ndarray, radius: float = None) -> List[int]:
        """
        Select vertices within a radius
        
        Args:
            position: World position
            radius: Selection radius (default: brush radius)
            
        Returns:
            List of selected vertex indices
        """
        if self._mesh is None:
            return []
        
        if radius is None:
            radius = self.brush.radius
        
        # Save previous brush radius
        old_radius = self.brush.radius
        self.brush.radius = radius
        
        # Get vertices
        indices = self._find_vertices_in_radius(position)
        indices = self._apply_x_mirror(indices)
        indices = self._apply_symmetry(indices)
        
        # Restore brush radius
        self.brush.radius = old_radius
        
        self._selected_vertices = indices
        return indices
    
    def get_selected_vertices(self) -> List[int]:
        """Get currently selected vertices"""
        return self._selected_vertices
    
    def clear_selection(self) -> None:
        """Clear vertex selection"""
        self._selected_vertices = []
    
    def apply_tool(self, tool: SculptTool, position: np.ndarray, 
                   direction: float = 1.0, drag_vector: np.ndarray = None) -> bool:
        """
        Apply a sculpting tool
        
        Args:
            tool: Sculpting tool to use
            position: World position of brush
            direction: For tools that use direction (inflate/crease)
            drag_vector: For grab tool
            
        Returns:
            True if operation succeeded
        """
        self.brush.tool = tool
        
        if tool == SculptTool.INFLATE:
            return self.inflate(position, direction)
        elif tool == SculptTool.GRAB:
            if drag_vector is None:
                return False
            return self.grab(position, drag_vector)
        elif tool == SculptTool.SMOOTH:
            return self.smooth(position)
        elif tool == SculptTool.CREASE:
            return self.crease(position, direction)
        elif tool == SculptTool.FLATTEN:
            return self.flatten(position)
        
        return False
    
    def bake_vertex_colors(self, mesh: trimesh.Trimesh, slide_images: List[Any]) -> Optional[np.ndarray]:
        """
        Bake colors from reference slides to vertex colors
        
        Args:
            mesh: The 3D mesh
            slide_images: List of reference slide images with positions
            
        Returns:
            Vertex colors array or None
        """
        # This is a placeholder implementation
        # In a full implementation, this would:
        # 1. Project each vertex onto each slide
        # 2. Sample the color from the slide image
        # 3. Blend colors from multiple slides
        
        # For now, just return white colors
        if mesh is None:
            return None
        
        return np.ones((len(mesh.vertices), 3), dtype=np.float32) * 0.8
