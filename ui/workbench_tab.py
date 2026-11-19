"""
3D Workbench tab for generating and sculpting 3D meshes
"""

import os
import numpy as np
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
    QComboBox, QSlider, QSplitter, QFileDialog, QMessageBox,
    QScrollArea, QFrame, QGraphicsView, QGraphicsScene
)
from PySide6.QtCore import Qt, Signal, QSize, QPoint, QRectF, QTimer, QEvent
from PySide6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QBrush, QMouseEvent, QWheelEvent

try:
    import pyvista as pv
    from pyvistaqt import BackgroundThread
    PV_AVAILABLE = True
except ImportError:
    PV_AVAILABLE = False

from core.skeleton import Skeleton
from core.geometry import Mesh, MeshGenerator, SDFGenerator, ReferenceSlide
from core.sculpting import SculptingTools, BrushSettings, SculptTool
from core.export import GLBExporter, ExportManager
from ui.styles import Colors


class Viewport3D(QWidget):
    """3D viewport widget using PyVista"""
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        
        self._plotter: Optional[pv.Plotter] = None
        self._mesh: Optional[pv.PolyData] = None
        self._reference_slides: List[ReferenceSlide] = []
        self._show_grid: bool = True
        self._show_axis: bool = True
        self._camera_position: Optional[Tuple[float, float, float]] = None
        self._camera_focal_point: Optional[Tuple[float, float, float]] = None
        self._camera_view_up: Optional[Tuple[float, float, float]] = None
        
        # Mouse interaction
        self._last_mouse_pos: Optional[QPoint] = None
        self._is_dragging: bool = False
        self._is_rotating: bool = False
        
        # Initialize
        self._init_viewport()
    
    def _init_viewport(self) -> None:
        """Initialize the 3D viewport"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        if not PV_AVAILABLE:
            # Create a fallback label
            self.lbl_fallback = QLabel("PyVista not available. Install with: pip install pyvista pyvistaqt")
            self.lbl_fallback.setStyleSheet("color: #f87171; font: 14px 'System';")
            layout.addWidget(self.lbl_fallback)
            self.setLayout(layout)
            self.setMinimumSize(400, 400)
            return
        
        try:
            # Create PyVista plotter
            self._plotter = pv.Plotter()
            
            # Configure plotter
            self._plotter.set_background(Colors.VIEWPORT_BG)
            
            # Add grid
            if self._show_grid:
                self._add_grid()
            
            # Add axis
            if self._show_axis:
                self._add_axis()
            
            # Set up camera
            self._plotter.camera_position = 'xy'
            self._plotter.camera.zoom(1.5)
            
            # Store in widget
            self._plotter.show(auto_close=False)
            
            # Add to layout
            layout.addWidget(self._plotter.ren_win)
            self.setLayout(layout)
            
            # Set minimum size
            self.setMinimumSize(400, 400)
        except Exception as e:
            # Fallback if PyVista fails
            self.lbl_fallback = QLabel(f"PyVista error: {str(e)}")
            self.lbl_fallback.setStyleSheet("color: #f87171; font: 14px 'System';")
            layout.addWidget(self.lbl_fallback)
            self.setLayout(layout)
            self.setMinimumSize(400, 400)
    
    def _add_grid(self) -> None:
        """Add grid to viewport"""
        if self._plotter is None:
            return
        
        # Create grid
        grid = pv.Plane(center=(0, 0, 0), direction=(0, 0, 1), i_size=10, j_size=10)
        grid_lines = grid.lines('x').lines('y')
        self._plotter.add_mesh(
            grid_lines,
            color=Colors.GRID_COLOR,
            line_width=1,
            opacity=0.5
        )
    
    def _add_axis(self) -> None:
        """Add coordinate axis to viewport"""
        if self._plotter is None:
            return
        
        # Add axis
        self._plotter.show_axes(
            xlabel='X', ylabel='Y', zlabel='Z',
            x_color=Colors.AXIS_X, y_color=Colors.AXIS_Y, z_color=Colors.AXIS_Z,
            xtitle='X', ytitle='Y', ztitle='Z'
        )
    
    def set_mesh(self, mesh: Optional[Mesh]) -> None:
        """Set the mesh to display"""
        if not PV_AVAILABLE:
            return
        
        if self._plotter is None:
            self._init_viewport()
            if self._plotter is None:
                return
        
        # Remove old mesh
        if self._mesh is not None:
            self._plotter.remove_actor(self._mesh)
        
        if mesh is not None:
            # Convert to PyVista
            self._mesh = mesh.to_pyvista()
            
            # Add to plotter
            self._plotter.add_mesh(
                self._mesh,
                color='white',
                show_edges=True,
                edge_color=Colors.BORDER_LIGHT,
                opacity=1.0
            )
        else:
            self._mesh = None
        
        # Reset camera
        self._plotter.reset_camera()
        self._plotter.camera.zoom(1.5)
        
        # Render
        self._plotter.render()
    
    def add_reference_slide(self, slide: ReferenceSlide) -> None:
        """Add a reference slide to the viewport"""
        if not PV_AVAILABLE or self._plotter is None:
            return
        
        self._reference_slides.append(slide)
        self._update_reference_slides()
    
    def remove_reference_slide(self, index: int) -> None:
        """Remove a reference slide"""
        if 0 <= index < len(self._reference_slides):
            self._reference_slides.pop(index)
            self._update_reference_slides()
    
    def clear_reference_slides(self) -> None:
        """Clear all reference slides"""
        self._reference_slides = []
        self._update_reference_slides()
    
    def _update_reference_slides(self) -> None:
        """Update reference slide display"""
        if not PV_AVAILABLE or self._plotter is None:
            return
        
        # Remove all slide actors
        for actor_name in [f"slide_{i}" for i in range(len(self._reference_slides) + 10)]:
            try:
                self._plotter.remove_actor(actor_name)
            except:
                pass
        
        # Add slides
        for i, slide in enumerate(self._reference_slides):
            # For now, create a simple plane with the image
            # In a full implementation, this would be a proper image plane
            if slide.image is not None and len(slide.image.shape) >= 2:
                h, w = slide.image.shape[:2]
                plane = pv.Plane(center=slide.position, direction=(0, 0, 1), i_size=w/100, j_size=h/100)
                self._plotter.add_mesh(plane, name=f"slide_{i}", color='white', opacity=slide.opacity)
        
        self._plotter.render()
    
    def set_show_grid(self, show: bool) -> None:
        """Show or hide grid"""
        self._show_grid = show
        # Note: Grid is added at initialization, would need to recreate viewport to toggle
    
    def set_show_axis(self, show: bool) -> None:
        """Show or hide axis"""
        self._show_axis = show
        # Note: Axis is added at initialization, would need to recreate viewport to toggle
    
    def reset_camera(self) -> None:
        """Reset camera to default position"""
        if self._plotter is not None:
            self._plotter.reset_camera()
            self._plotter.camera_position = 'xy'
            self._plotter.camera.zoom(1.5)
            self._plotter.render()
    
    def get_camera_position(self) -> Optional[Tuple[float, float, float]]:
        """Get current camera position"""
        if self._plotter is not None:
            return self._plotter.camera.position
        return None
    
    def set_camera_position(self, position: Tuple[float, float, float]) -> None:
        """Set camera position"""
        if self._plotter is not None:
            self._plotter.camera.position = position
            self._plotter.render()
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press"""
        if not PV_AVAILABLE or self._plotter is None:
            return
        
        self._last_mouse_pos = event.position().toPoint()
        self._is_dragging = True
        
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_rotating = True
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move"""
        if not PV_AVAILABLE or self._plotter is None or not self._is_dragging:
            return
        
        current_pos = event.position().toPoint()
        delta = current_pos - self._last_mouse_pos
        
        if self._is_rotating:
            # Rotate camera
            self._plotter.camera.azimuth = delta.x() * 0.5
            self._plotter.camera.elevation = delta.y() * 0.5
            self._plotter.render()
        
        self._last_mouse_pos = current_pos
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release"""
        self._is_dragging = False
        self._is_rotating = False
        self._last_mouse_pos = None
        
        super().mouseReleaseEvent(event)
    
    def wheelEvent(self, event: QWheelEvent) -> None:
        """Handle wheel event"""
        if not PV_AVAILABLE or self._plotter is None:
            return
        
        # Zoom
        zoom_factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        self._plotter.camera.zoom(zoom_factor)
        self._plotter.render()
        
        super().wheelEvent(event)


class WorkbenchTab(QWidget):
    """Tab for 3D mesh generation and sculpting"""
    
    # Signals
    mesh_ready = Signal(int, int)  # vertex_count, face_count
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        
        self.mesh_generator = MeshGenerator()
        self.sculpting_tools = SculptingTools()
        self.exporter = ExportManager()
        self._mesh: Optional[Mesh] = None
        self._skeleton: Optional[Skeleton] = None
        self._reference_slides: List[ReferenceSlide] = []
        self._brush_settings = BrushSettings()
        self._current_tool: SculptTool = SculptTool.INFLATE
        self._is_sculpting: bool = False
        self._last_mouse_pos: Optional[QPoint] = None
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self) -> None:
        """Setup the user interface"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        
        # Create splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(8)
        splitter.setStyleSheet("QSplitter::handle { background-color: #1e2833; }")
        
        # Left panel - 3D Viewport
        left_panel = QFrame()
        left_panel.setStyleSheet("background-color: #10151c; border: 1px solid #1e2833; border-radius: 6px;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(6)
        
        # 3D Viewport
        self.viewport = Viewport3D()
        left_layout.addWidget(QLabel("3D Viewport"))
        left_layout.addWidget(self.viewport)
        
        # Viewport controls
        viewport_controls = QHBoxLayout()
        self.btn_reset_camera = QPushButton("Reset Camera")
        self.btn_reset_camera.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        self.btn_show_grid = QPushButton("Toggle Grid")
        self.btn_show_grid.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        self.btn_show_axis = QPushButton("Toggle Axis")
        self.btn_show_axis.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        viewport_controls.addWidget(self.btn_reset_camera)
        viewport_controls.addWidget(self.btn_show_grid)
        viewport_controls.addWidget(self.btn_show_axis)
        left_layout.addLayout(viewport_controls)
        
        splitter.addWidget(left_panel)
        
        # Right panel - Controls
        right_panel = QFrame()
        right_panel.setStyleSheet("background-color: #10151c; border: 1px solid #1e2833; border-radius: 6px;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(6)
        
        # Generation
        gen_group = QGroupBox("Mesh Generation")
        gen_group.setStyleSheet("QGroupBox { border: 1px solid #1e2833; border-radius: 6px; padding: 8px; }")
        gen_layout = QVBoxLayout()
        
        self.btn_generate_mesh = QPushButton("Generate Mesh from Skeleton")
        self.btn_generate_mesh.setStyleSheet("""
            QPushButton {
                background-color: rgba(34, 211, 238, 0.12);
                color: #22d3ee;
                border: 1px solid rgba(34, 211, 238, 0.55);
                border-radius: 6px;
                padding: 8px 16px;
            }
        """)
        gen_layout.addWidget(self.btn_generate_mesh)
        
        self.btn_generate_from_contours = QPushButton("Generate Mesh from Contours")
        self.btn_generate_from_contours.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        gen_layout.addWidget(self.btn_generate_from_contours)
        
        gen_group.setLayout(gen_layout)
        right_layout.addWidget(gen_group)
        
        # Sculpting tools
        sculpt_group = QGroupBox("Sculpting Tools")
        sculpt_group.setStyleSheet("QGroupBox { border: 1px solid #1e2833; border-radius: 6px; padding: 8px; }")
        sculpt_layout = QVBoxLayout()
        
        # Tool selection
        tool_layout = QHBoxLayout()
        tool_layout.addWidget(QLabel("Tool:"))
        self.combo_tool = QComboBox()
        for tool in SculptTool:
            self.combo_tool.addItem(tool.value.title())
        self.combo_tool.setCurrentIndex(0)
        self.combo_tool.setStyleSheet("QComboBox { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 4px 8px; }")
        tool_layout.addWidget(self.combo_tool)
        sculpt_layout.addLayout(tool_layout)
        
        # Brush settings
        brush_group = QGroupBox("Brush Settings")
        brush_group.setStyleSheet("QGroupBox { border: 1px solid #26313f; border-radius: 4px; padding: 6px; }")
        brush_layout = QVBoxLayout()
        
        # Radius
        radius_layout = QHBoxLayout()
        radius_layout.addWidget(QLabel("Radius:"))
        self.dspin_radius = QDoubleSpinBox()
        self.dspin_radius.setRange(0.01, 5.0)
        self.dspin_radius.setValue(0.5)
        self.dspin_radius.setSingleStep(0.05)
        self.dspin_radius.setStyleSheet("QDoubleSpinBox { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 4px 8px; }")
        radius_layout.addWidget(self.dspin_radius)
        brush_layout.addLayout(radius_layout)
        
        # Strength
        strength_layout = QHBoxLayout()
        strength_layout.addWidget(QLabel("Strength:"))
        self.dspin_strength = QDoubleSpinBox()
        self.dspin_strength.setRange(0.01, 1.0)
        self.dspin_strength.setValue(0.5)
        self.dspin_strength.setSingleStep(0.05)
        self.dspin_strength.setStyleSheet("QDoubleSpinBox { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 4px 8px; }")
        strength_layout.addWidget(self.dspin_strength)
        brush_layout.addLayout(strength_layout)
        
        # Hardness
        hardness_layout = QHBoxLayout()
        hardness_layout.addWidget(QLabel("Hardness:"))
        self.dspin_hardness = QDoubleSpinBox()
        self.dspin_hardness.setRange(0.01, 1.0)
        self.dspin_hardness.setValue(0.5)
        self.dspin_hardness.setSingleStep(0.05)
        self.dspin_hardness.setStyleSheet("QDoubleSpinBox { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 4px 8px; }")
        hardness_layout.addWidget(self.dspin_hardness)
        brush_layout.addLayout(hardness_layout)
        
        # X-Mirror
        mirror_layout = QHBoxLayout()
        self.chk_x_mirror = QCheckBox("X-Mirror")
        self.chk_x_mirror.setChecked(False)
        self.chk_x_mirror.setStyleSheet("QCheckBox { color: #d7e0ea; spacing: 8px; }")
        mirror_layout.addWidget(self.chk_x_mirror)
        brush_layout.addLayout(mirror_layout)
        
        brush_group.setLayout(brush_layout)
        sculpt_layout.addWidget(brush_group)
        
        # Sculpt buttons
        sculpt_btn_layout = QHBoxLayout()
        self.btn_inflate = QPushButton("Inflate")
        self.btn_inflate.setStyleSheet("""
            QPushButton {
                background-color: rgba(34, 211, 238, 0.12);
                color: #22d3ee;
                border: 1px solid rgba(34, 211, 238, 0.55);
                border-radius: 4px;
                padding: 6px 12px;
            }
        """)
        self.btn_deflate = QPushButton("Deflate")
        self.btn_deflate.setStyleSheet("""
            QPushButton {
                background-color: rgba(248, 113, 113, 0.12);
                color: #f87171;
                border: 1px solid rgba(248, 113, 113, 0.55);
                border-radius: 4px;
                padding: 6px 12px;
            }
        """)
        self.btn_smooth = QPushButton("Smooth")
        self.btn_smooth.setStyleSheet("""
            QPushButton {
                background-color: rgba(52, 211, 153, 0.12);
                color: #34d399;
                border: 1px solid rgba(52, 211, 153, 0.55);
                border-radius: 4px;
                padding: 6px 12px;
            }
        """)
        self.btn_grab = QPushButton("Grab")
        self.btn_grab.setStyleSheet("""
            QPushButton {
                background-color: rgba(251, 191, 36, 0.12);
                color: #fbbf24;
                border: 1px solid rgba(251, 191, 36, 0.55);
                border-radius: 4px;
                padding: 6px 12px;
            }
        """)
        sculpt_btn_layout.addWidget(self.btn_inflate)
        sculpt_btn_layout.addWidget(self.btn_deflate)
        sculpt_btn_layout.addWidget(self.btn_smooth)
        sculpt_btn_layout.addWidget(self.btn_grab)
        sculpt_layout.addLayout(sculpt_btn_layout)
        
        sculpt_group.setLayout(sculpt_layout)
        right_layout.addWidget(sculpt_group)
        
        # Export
        export_group = QGroupBox("Export")
        export_group.setStyleSheet("QGroupBox { border: 1px solid #1e2833; border-radius: 6px; padding: 8px; }")
        export_layout = QVBoxLayout()
        
        # Scale settings
        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("Scale (m):"))
        self.dspin_scale = QDoubleSpinBox()
        self.dspin_scale.setRange(0.01, 10.0)
        self.dspin_scale.setValue(1.0)
        self.dspin_scale.setSingleStep(0.01)
        self.dspin_scale.setStyleSheet("QDoubleSpinBox { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 4px 8px; }")
        scale_layout.addWidget(self.dspin_scale)
        export_layout.addLayout(scale_layout)
        
        # Height
        height_layout = QHBoxLayout()
        height_layout.addWidget(QLabel("Height (cm):"))
        self.spin_height = QSpinBox()
        self.spin_height.setRange(50, 300)
        self.spin_height.setValue(180)
        self.spin_height.setStyleSheet("QSpinBox { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 4px 8px; }")
        height_layout.addWidget(self.spin_height)
        export_layout.addLayout(height_layout)
        
        # Export buttons
        export_btn_layout = QHBoxLayout()
        self.btn_export_glb = QPushButton("Export GLB")
        self.btn_export_glb.setStyleSheet("""
            QPushButton {
                background-color: rgba(34, 211, 238, 0.12);
                color: #22d3ee;
                border: 1px solid rgba(34, 211, 238, 0.55);
                border-radius: 6px;
                padding: 8px 16px;
            }
        """)
        self.btn_export_obj = QPushButton("Export OBJ")
        self.btn_export_obj.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        self.btn_export_stl = QPushButton("Export STL")
        self.btn_export_stl.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        export_btn_layout.addWidget(self.btn_export_glb)
        export_btn_layout.addWidget(self.btn_export_obj)
        export_btn_layout.addWidget(self.btn_export_stl)
        export_layout.addLayout(export_btn_layout)
        
        export_group.setLayout(export_layout)
        right_layout.addWidget(export_group)
        
        # Stats
        self.lbl_stats = QLabel("No mesh")
        self.lbl_stats.setStyleSheet("color: #7c8b9d; font: 11px 'Consolas';")
        right_layout.addWidget(self.lbl_stats)
        
        # Action buttons
        action_layout = QHBoxLayout()
        self.btn_clear = QPushButton("Clear All")
        self.btn_clear.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        self.btn_smooth_mesh = QPushButton("Smooth Mesh")
        self.btn_smooth_mesh.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        self.btn_decimate = QPushButton("Decimate")
        self.btn_decimate.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        action_layout.addWidget(self.btn_clear)
        action_layout.addWidget(self.btn_smooth_mesh)
        action_layout.addWidget(self.btn_decimate)
        right_layout.addLayout(action_layout)
        
        # Undo/Redo
        undo_layout = QHBoxLayout()
        self.btn_undo = QPushButton("Undo")
        self.btn_undo.setShortcut("Ctrl+Z")
        self.btn_undo.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        self.btn_redo = QPushButton("Redo")
        self.btn_redo.setShortcut("Ctrl+Y")
        self.btn_redo.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        undo_layout.addWidget(self.btn_undo)
        undo_layout.addWidget(self.btn_redo)
        right_layout.addLayout(undo_layout)
        
        # Add stretch
        right_layout.addStretch()
        
        splitter.addWidget(right_panel)
        splitter.setSizes([500, 300])
        
        main_layout.addWidget(splitter)
    
    def _connect_signals(self) -> None:
        """Connect signals"""
        # Viewport controls
        self.btn_reset_camera.clicked.connect(self.reset_camera)
        self.btn_show_grid.clicked.connect(self.toggle_grid)
        self.btn_show_axis.clicked.connect(self.toggle_axis)
        
        # Generation
        self.btn_generate_mesh.clicked.connect(self.on_generate_mesh)
        self.btn_generate_from_contours.clicked.connect(self.on_generate_from_contours)
        
        # Tool selection
        self.combo_tool.currentIndexChanged.connect(self.on_tool_changed)
        
        # Brush settings
        self.dspin_radius.valueChanged.connect(self.on_brush_changed)
        self.dspin_strength.valueChanged.connect(self.on_brush_changed)
        self.dspin_hardness.valueChanged.connect(self.on_brush_changed)
        self.chk_x_mirror.stateChanged.connect(self.on_brush_changed)
        
        # Sculpt buttons
        self.btn_inflate.clicked.connect(lambda: self.set_tool(SculptTool.INFLATE))
        self.btn_deflate.clicked.connect(lambda: self.set_tool(SculptTool.INFLATE))
        self.btn_smooth.clicked.connect(lambda: self.set_tool(SculptTool.SMOOTH))
        self.btn_grab.clicked.connect(lambda: self.set_tool(SculptTool.GRAB))
        
        # Export
        self.btn_export_glb.clicked.connect(self.on_export_glb)
        self.btn_export_obj.clicked.connect(self.on_export_obj)
        self.btn_export_stl.clicked.connect(self.on_export_stl)
        
        # Actions
        self.btn_clear.clicked.connect(self.clear_all)
        self.btn_smooth_mesh.clicked.connect(self.on_smooth_mesh)
        self.btn_decimate.clicked.connect(self.on_decimate)
        
        # Undo/Redo
        self.btn_undo.clicked.connect(self.undo)
        self.btn_redo.clicked.connect(self.redo)
    
    def set_skeleton(self, skeleton: Skeleton) -> None:
        """Set the skeleton for mesh generation"""
        self._skeleton = skeleton
        self._update_stats()
    
    def set_reference_slides(self, slides: List[ReferenceSlide]) -> None:
        """Set reference slides"""
        self._reference_slides = slides
        for slide in slides:
            self.viewport.add_reference_slide(slide)
    
    def clear_reference_slides(self) -> None:
        """Clear reference slides"""
        self._reference_slides = []
        self.viewport.clear_reference_slides()
    
    def set_show_grid(self, show: bool) -> None:
        """Show or hide grid"""
        self.viewport.set_show_grid(show)
    
    def set_show_axis(self, show: bool) -> None:
        """Show or hide axis"""
        self.viewport.set_show_axis(show)
    
    def reset_camera(self) -> None:
        """Reset camera"""
        self.viewport.reset_camera()
    
    def toggle_grid(self) -> None:
        """Toggle grid visibility"""
        self.set_show_grid(not self.viewport._show_grid)
    
    def toggle_axis(self) -> None:
        """Toggle axis visibility"""
        self.set_show_axis(not self.viewport._show_axis)
    
    def on_generate_mesh(self) -> None:
        """Generate mesh from skeleton"""
        if self._skeleton is None:
            QMessageBox.warning(self, "No Skeleton", "Please set a skeleton first.")
            return
        
        try:
            # Convert skeleton to mesh
            # For now, create a simple capsule-based mesh
            # In a full implementation, this would use SDF and marching cubes
            
            # Create a simple test mesh
            import trimesh
            mesh = trimesh.creation.icosphere(radius=0.5, subdivisions=3)
            
            # Scale based on skeleton height
            height = self._skeleton.calculate_height()
            if height > 0:
                scale = height / 2
                mesh.vertices *= scale
            
            # Convert to our Mesh class
            self._mesh = Mesh(
                vertices=mesh.vertices,
                faces=mesh.faces,
                vertex_colors=None,
                normals=mesh.vertex_normals
            )
            
            # Update viewport
            self.viewport.set_mesh(self._mesh)
            
            # Update sculpting tools
            self.sculpting_tools.set_mesh(mesh)
            
            # Update stats
            self._update_stats()
            
            # Emit signal
            self.mesh_ready.emit(len(self._mesh.vertices), len(self._mesh.faces))
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate mesh: {str(e)}")
    
    def on_generate_from_contours(self) -> None:
        """Generate mesh from contours"""
        # For now, just show a message
        QMessageBox.information(self, "Not Implemented", "Mesh generation from contours is not yet implemented.")
    
    def on_tool_changed(self, index: int) -> None:
        """Handle tool selection change"""
        tools = list(SculptTool)
        if index < len(tools):
            self._current_tool = tools[index]
    
    def on_brush_changed(self) -> None:
        """Handle brush settings change"""
        self._brush_settings.radius = self.dspin_radius.value()
        self._brush_settings.strength = self.dspin_strength.value()
        self._brush_settings.hardness = self.dspin_hardness.value()
        self._brush_settings.use_x_mirror = self.chk_x_mirror.isChecked()
        
        self.sculpting_tools.set_brush_settings(self._brush_settings)
    
    def set_tool(self, tool: SculptTool) -> None:
        """Set the current sculpting tool"""
        self._current_tool = tool
        index = list(SculptTool).index(tool)
        self.combo_tool.setCurrentIndex(index)
    
    def get_current_mesh(self) -> Optional[Mesh]:
        """Get the current mesh"""
        return self._mesh
    
    def export_to_glb(self, path: str = "") -> bool:
        """Export mesh to GLB"""
        if self._mesh is None:
            return False
        
        if not path:
            options = QFileDialog.Options()
            path, _ = QFileDialog.getSaveFileName(
                self, "Export to GLB", "",
                "GLB Files (*.glb);;All Files (*)",
                options=options
            )
            if not path:
                return False
        
        try:
            # Convert to trimesh
            tm = self._mesh.to_trimesh()
            
            # Apply scale
            scale = self.dspin_scale.value()
            tm.vertices *= scale
            
            # Export
            tm.export(path, file_type='glb')
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export GLB: {str(e)}")
            return False
    
    def export_to_obj(self, path: str = "") -> bool:
        """Export mesh to OBJ"""
        if self._mesh is None:
            return False
        
        if not path:
            options = QFileDialog.Options()
            path, _ = QFileDialog.getSaveFileName(
                self, "Export to OBJ", "",
                "OBJ Files (*.obj);;All Files (*)",
                options=options
            )
            if not path:
                return False
        
        try:
            tm = self._mesh.to_trimesh()
            tm.export(path, file_type='obj')
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export OBJ: {str(e)}")
            return False
    
    def export_to_stl(self, path: str = "") -> bool:
        """Export mesh to STL"""
        if self._mesh is None:
            return False
        
        if not path:
            options = QFileDialog.Options()
            path, _ = QFileDialog.getSaveFileName(
                self, "Export to STL", "",
                "STL Files (*.stl);;All Files (*)",
                options=options
            )
            if not path:
                return False
        
        try:
            tm = self._mesh.to_trimesh()
            tm.export(path, file_type='stl')
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export STL: {str(e)}")
            return False
    
    def on_export_glb(self) -> None:
        """Handle export GLB button"""
        self.export_to_glb()
    
    def on_export_obj(self) -> None:
        """Handle export OBJ button"""
        self.export_to_obj()
    
    def on_export_stl(self) -> None:
        """Handle export STL button"""
        self.export_to_stl()
    
    def on_smooth_mesh(self) -> None:
        """Handle smooth mesh button"""
        if self._mesh is None:
            return
        
        try:
            tm = self._mesh.to_trimesh()
            smoothed = tm.smoothed(iterations=1)
            
            self._mesh = Mesh(
                vertices=smoothed.vertices,
                faces=smoothed.faces,
                vertex_colors=self._mesh.vertex_colors,
                normals=smoothed.vertex_normals
            )
            
            self.viewport.set_mesh(self._mesh)
            self.sculpting_tools.set_mesh(smoothed)
            self._update_stats()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to smooth mesh: {str(e)}")
    
    def on_decimate(self) -> None:
        """Handle decimate button"""
        if self._mesh is None:
            return
        
        try:
            tm = self._mesh.to_trimesh()
            # Decimate to 50% of faces
            target_faces = len(tm.faces) // 2
            decimated = tm.simplify_quadric_decimation(target_faces)
            
            self._mesh = Mesh(
                vertices=decimated.vertices,
                faces=decimated.faces,
                vertex_colors=self._mesh.vertex_colors,
                normals=decimated.vertex_normals
            )
            
            self.viewport.set_mesh(self._mesh)
            self.sculpting_tools.set_mesh(decimated)
            self._update_stats()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to decimate mesh: {str(e)}")
    
    def _update_stats(self) -> None:
        """Update statistics display"""
        if self._mesh:
            self.lbl_stats.setText(f"Vertices: {len(self._mesh.vertices)} | Faces: {len(self._mesh.faces)}")
        else:
            self.lbl_stats.setText("No mesh")
    
    def undo(self) -> None:
        """Undo last sculpting action"""
        if self.sculpting_tools.undo():
            # Update mesh
            tm = self.sculpting_tools.get_mesh()
            if tm:
                self._mesh = Mesh(
                    vertices=tm.vertices,
                    faces=tm.faces,
                    vertex_colors=self._mesh.vertex_colors if self._mesh else None,
                    normals=tm.vertex_normals
                )
                self.viewport.set_mesh(self._mesh)
                self._update_stats()
    
    def redo(self) -> None:
        """Redo last undone action"""
        if self.sculpting_tools.redo():
            # Update mesh
            tm = self.sculpting_tools.get_mesh()
            if tm:
                self._mesh = Mesh(
                    vertices=tm.vertices,
                    faces=tm.faces,
                    vertex_colors=self._mesh.vertex_colors if self._mesh else None,
                    normals=tm.vertex_normals
                )
                self.viewport.set_mesh(self._mesh)
                self._update_stats()
    
    def clear_all(self) -> None:
        """Clear all data"""
        self._mesh = None
        self._skeleton = None
        self._reference_slides = []
        self.viewport.set_mesh(None)
        self.viewport.clear_reference_slides()
        self.sculpting_tools.set_mesh(None)
        self._update_stats()
    
    def keyPressEvent(self, event) -> None:
        """Handle key press events"""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Z:
                self.undo()
                event.accept()
                return
            elif event.key() == Qt.Key.Key_Y:
                self.redo()
                event.accept()
                return
        
        super().keyPressEvent(event)


if __name__ == "__main__":
    # For testing
    from PySide6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    tab = WorkbenchTab()
    tab.show()
    sys.exit(app.exec())
