"""
Core module for 3D Vector Pipeline
Contains vectorization, skeleton, geometry, and sculpting functionality
"""

# Optional imports - may fail in some environments
try:
    from .vectorizer import Vectorizer
except ImportError:
    Vectorizer = None

from .skeleton import Skeleton, Joint, Bone
from .geometry import SDFGenerator, MeshGenerator
from .sculpting import SculptingTools
from .export import GLBExporter

__all__ = ['Vectorizer', 'Skeleton', 'Joint', 'Bone', 'SDFGenerator', 'MeshGenerator', 'SculptingTools', 'GLBExporter']
