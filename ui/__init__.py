"""
UI module for 3D Vector Pipeline
Contains all user interface components
"""

# Optional imports - may fail without Qt
try:
    from .main_window import MainWindow
    from .vectorizer_tab import VectorizerTab
    from .skeleton_tab import SkeletonTab
    from .workbench_tab import WorkbenchTab
except ImportError:
    MainWindow = None
    VectorizerTab = None
    SkeletonTab = None
    WorkbenchTab = None

from .styles import StyleSheet

__all__ = ['MainWindow', 'VectorizerTab', 'SkeletonTab', 'WorkbenchTab', 'StyleSheet']
