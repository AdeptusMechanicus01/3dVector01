"""
Vectorizer module for converting raster images to vector contours
"""

import cv2
import numpy as np
from scipy import ndimage
from skimage.measure import find_contours, approximate_polygon
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
from PIL import Image
import io


@dataclass
class Contour:
    """Represents a vector contour with points and metadata"""
    points: List[Tuple[float, float]]  # List of (x, y) points
    is_closed: bool = True
    is_external: bool = True
    color: Tuple[int, int, int] = (255, 255, 255)
    
    def to_svg_path(self) -> str:
        """Convert contour to SVG path string"""
        if len(self.points) < 2:
            return ""
        
        parts = []
        if self.is_closed:
            parts.append(f"M {self.points[0][0]:.2f} {self.points[0][1]:.2f}")
            for x, y in self.points[1:]:
                parts.append(f"L {x:.2f} {y:.2f}")
            parts.append("Z")
        else:
            parts.append(f"M {self.points[0][0]:.2f} {self.points[0][1]:.2f}")
            for x, y in self.points[1:]:
                parts.append(f"L {x:.2f} {y:.2f}")
        
        return " ".join(parts)
    
    def to_numpy(self) -> np.ndarray:
        """Convert to numpy array of shape (N, 2)"""
        return np.array(self.points, dtype=np.float32)
    
    def simplify(self, epsilon: float = 1.0) -> 'Contour':
        """Simplify contour using Ramer-Douglas-Peucker algorithm"""
        if len(self.points) < 3:
            return self
        
        # Convert to numpy and simplify
        pts = self.to_numpy()
        simplified = approximate_polygon(pts, tolerance=epsilon)
        
        return Contour(
            points=[(float(p[0]), float(p[1])) for p in simplified],
            is_closed=self.is_closed,
            is_external=self.is_external,
            color=self.color
        )
    
    def translate(self, dx: float, dy: float) -> 'Contour':
        """Translate contour by dx, dy"""
        return Contour(
            points=[(x + dx, y + dy) for x, y in self.points],
            is_closed=self.is_closed,
            is_external=self.is_external,
            color=self.color
        )
    
    def scale(self, sx: float, sy: float) -> 'Contour':
        """Scale contour"""
        return Contour(
            points=[(x * sx, y * sy) for x, y in self.points],
            is_closed=self.is_closed,
            is_external=self.is_external,
            color=self.color
        )


@dataclass
class ROI:
    """Region of Interest for cropping"""
    x: float
    y: float
    width: float
    height: float
    
    def to_slice(self) -> Tuple[slice, slice]:
        """Convert to numpy slice objects"""
        return (slice(int(self.y), int(self.y + self.height)), 
                slice(int(self.x), int(self.x + self.width)))
    
    def contains(self, x: float, y: float) -> bool:
        """Check if point is inside ROI"""
        return (self.x <= x <= self.x + self.width and 
                self.y <= y <= self.y + self.height)


class Vectorizer:
    """
    Main vectorizer class for converting raster images to vector contours
    """
    
    def __init__(self):
        self._image: Optional[np.ndarray] = None
        self._original_image: Optional[np.ndarray] = None
        self._roi: Optional[ROI] = None
        self._contours: List[Contour] = []
        self._parameters: Dict[str, Any] = {
            'blur_radius': 3,
            'canny_threshold1': 50,
            'canny_threshold2': 150,
            'edge_sensitivity': 0.5,
            'simplification_epsilon': 1.0,
            'corner_threshold_deg': 30,
            'remove_background': True,
            'background_color': (0, 0, 0),
            'detect_internal_edges': True
        }
    
    def load_image(self, path: str) -> bool:
        """Load image from file path"""
        try:
            # Try with OpenCV first
            if isinstance(path, str) and Path(path).exists():
                self._original_image = cv2.imread(path, cv2.IMREAD_UNCHANGED)
            elif isinstance(path, bytes):
                # Handle raw bytes
                self._original_image = cv2.imdecode(np.frombuffer(path, np.uint8), cv2.IMREAD_UNCHANGED)
            else:
                return False
            
            if self._original_image is None:
                return False
            
            # Convert BGR to RGB if needed
            if len(self._original_image.shape) == 3 and self._original_image.shape[2] == 3:
                self._original_image = cv2.cvtColor(self._original_image, cv2.COLOR_BGR2RGB)
            
            self._image = self._original_image.copy()
            self._contours = []
            self._roi = None
            return True
            
        except Exception as e:
            print(f"Error loading image: {e}")
            return False
    
    def load_image_from_pil(self, pil_image: Image.Image) -> bool:
        """Load image from PIL Image"""
        try:
            self._original_image = np.array(pil_image)
            if len(self._original_image.shape) == 3 and self._original_image.shape[2] == 4:
                # RGBA to RGB
                self._original_image = cv2.cvtColor(self._original_image, cv2.COLOR_RGBA2RGB)
            elif len(self._original_image.shape) == 3 and self._original_image.shape[2] == 3:
                # Ensure RGB
                pass
            
            self._image = self._original_image.copy()
            self._contours = []
            self._roi = None
            return True
        except Exception as e:
            print(f"Error loading PIL image: {e}")
            return False
    
    def get_image(self) -> Optional[np.ndarray]:
        """Get current image (with ROI applied if set)"""
        if self._image is None:
            return None
        
        img = self._image.copy()
        
        if self._roi:
            sy, sx = self._roi.to_slice()
            img = img[sy, sx]
        
        return img
    
    def get_original_image(self) -> Optional[np.ndarray]:
        """Get original image without any modifications"""
        return self._original_image
    
    def set_roi(self, roi: ROI) -> None:
        """Set region of interest for cropping"""
        self._roi = roi
    
    def clear_roi(self) -> None:
        """Clear region of interest"""
        self._roi = None
    
    def get_roi(self) -> Optional[ROI]:
        """Get current ROI"""
        return self._roi
    
    def set_parameter(self, name: str, value: Any) -> None:
        """Set vectorization parameter"""
        if name in self._parameters:
            self._parameters[name] = value
    
    def get_parameter(self, name: str) -> Any:
        """Get vectorization parameter"""
        return self._parameters.get(name)
    
    def _preprocess_image(self, img: np.ndarray) -> np.ndarray:
        """Preprocess image for edge detection"""
        # Convert to grayscale
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        else:
            gray = img.copy()
        
        # Apply Gaussian blur
        blur = self._parameters['blur_radius']
        if blur > 0:
            gray = cv2.GaussianBlur(gray, (0, 0), sigmaX=blur)
        
        return gray
    
    def _detect_edges(self, gray: np.ndarray) -> np.ndarray:
        """Detect edges using Canny"""
        thresh1 = self._parameters['canny_threshold1']
        thresh2 = self._parameters['canny_threshold2']
        edges = cv2.Canny(gray, thresh1, thresh2, apertureSize=3)
        return edges
    
    def _find_contours(self, edges: np.ndarray) -> List[np.ndarray]:
        """Find contours from edge image"""
        # Use OpenCV's findContours
        contours, hierarchy = cv2.findContours(
            edges, 
            cv2.RETR_TREE, 
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        # Convert to list of numpy arrays
        return [c.squeeze() for c in contours]
    
    def _filter_contours(self, contours: List[np.ndarray]) -> List[Contour]:
        """Filter and process contours"""
        results = []
        
        # Get image dimensions for filtering
        img = self.get_image()
        if img is None:
            return results
        
        img_height, img_width = img.shape[:2]
        min_area = 10  # Minimum area for a contour
        
        for i, contour in enumerate(contours):
            if len(contour) < 3:
                continue
            
            # Calculate area
            area = cv2.contourArea(contour)
            if area < min_area:
                continue
            
            # Check if contour is too large (likely background)
            bounding_rect = cv2.boundingRect(contour)
            x, y, w, h = bounding_rect
            
            # If contour covers most of the image, it's likely the background
            if self._parameters['remove_background']:
                area_ratio = (w * h) / (img_width * img_height)
                if area_ratio > 0.95:
                    # This is the background, skip it
                    # But we want the external silhouette
                    # For now, skip very large contours
                    continue
            
            # Create Contour object
            points = [(float(p[0]), float(p[1])) for p in contour]
            
            # Determine if it's external or internal
            # Hierarchy: [Next, Previous, First_Child, Parent]
            # For RETR_TREE: positive hierarchy[3] means it's a hole
            # We'll use a simpler approach: check if contour is convex
            is_external = True
            if self._parameters['detect_internal_edges']:
                # Check if this contour is inside another
                # For now, mark all as external
                pass
            
            results.append(Contour(
                points=points,
                is_closed=True,
                is_external=is_external,
                color=(255, 255, 255)
            ))
        
        return results
    
    def vectorize(self) -> List[Contour]:
        """
        Main vectorization method
        Converts current image to vector contours
        """
        img = self.get_image()
        if img is None:
            return []
        
        # Preprocess
        gray = self._preprocess_image(img)
        
        # Detect edges
        edges = self._detect_edges(gray)
        
        # Find contours
        contours = self._find_contours(edges)
        
        # Filter and create Contour objects
        self._contours = self._filter_contours(contours)
        
        # Simplify contours
        epsilon = self._parameters['simplification_epsilon']
        if epsilon > 0:
            self._contours = [c.simplify(epsilon) for c in self._contours]
        
        return self._contours
    
    def get_contours(self) -> List[Contour]:
        """Get current contours"""
        return self._contours
    
    def clear_contours(self) -> None:
        """Clear all contours"""
        self._contours = []
    
    def get_silhouette(self) -> Optional[Contour]:
        """Get the main external silhouette (largest contour)"""
        if not self._contours:
            return None
        
        # Find largest contour by area
        max_area = -1
        max_contour = None
        
        for contour in self._contours:
            if not contour.is_external:
                continue
            
            # Calculate area using shoelace formula
            pts = contour.to_numpy()
            area = cv2.contourArea(pts)
            
            if area > max_area:
                max_area = area
                max_contour = contour
        
        return max_contour
    
    def get_internal_contours(self) -> List[Contour]:
        """Get all internal contours (holes, details)"""
        return [c for c in self._contours if not c.is_external]
    
    def to_svg(self, width: int = 1024, height: int = 1024) -> str:
        """Convert contours to SVG string"""
        parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
        
        for contour in self._contours:
            path = contour.to_svg_path()
            if path:
                color_hex = f"#{contour.color[0]:02x}{contour.color[1]:02x}{contour.color[2]:02x}"
                parts.append(f'<path d="{path}" fill="none" stroke="{color_hex}" stroke-width="1"/>')
        
        parts.append('</svg>')
        return '\n'.join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Export contours to dictionary for JSON serialization"""
        return {
            'contours': [
                {
                    'points': c.points,
                    'is_closed': c.is_closed,
                    'is_external': c.is_external,
                    'color': c.color
                }
                for c in self._contours
            ],
            'parameters': self._parameters.copy()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Vectorizer':
        """Create vectorizer from dictionary"""
        vec = cls()
        vec._contours = [
            Contour(
                points=c['points'],
                is_closed=c.get('is_closed', True),
                is_external=c.get('is_external', True),
                color=tuple(c.get('color', (255, 255, 255)))
            )
            for c in data.get('contours', [])
        ]
        if 'parameters' in data:
            vec._parameters.update(data['parameters'])
        return vec


def create_vectorizer_from_file(path: str) -> Optional[Vectorizer]:
    """Convenience function to create and load vectorizer from file"""
    vec = Vectorizer()
    if vec.load_image(path):
        return vec
    return None
