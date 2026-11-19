"""
Skeleton Builder tab for creating and editing character skeletons
"""

import os
import json
import math
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
    QComboBox, QSlider, QSplitter, QFileDialog, QMessageBox,
    QScrollArea, QFrame, QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsTextItem, QGraphicsPathItem
)
from PySide6.QtCore import Qt, Signal, QSize, QPoint, QRectF, QPointF, QTimer, QLineF
from PySide6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QBrush, QPainterPath, QTransform

from core.skeleton import Skeleton, Joint, JointRole, BodyContour, create_skeleton_from_json_file
from core.vectorizer import Contour
from ui.styles import Colors, Fonts


class JointItem(QGraphicsEllipseItem):
    """Graphics item for a joint"""
    
    def __init__(self, joint: Joint, radius: float = 8):
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        
        self.joint = joint
        self.radius = radius
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        
        # Set colors based on joint type
        self._update_brush()
        self.setPen(QPen(QColor(255, 255, 255, 180), 1))
    
    def _update_brush(self) -> None:
        """Update brush based on joint properties"""
        if self.joint.role == JointRole.ROOT:
            color = Colors.ACCENT_ORANGE
        elif self.joint.role == JointRole.HEAD or self.joint.role == JointRole.HEADTOP:
            color = Colors.ACCENT_GREEN
        elif self.joint.is_left():
            color = Colors.ACCENT_BLUE
        elif self.joint.is_right():
            color = Colors.ACCENT_RED
        else:
            color = Colors.ACCENT_CYAN
        
        brush = QBrush(color)
        self.setBrush(brush)
    
    def hoverEnterEvent(self, event) -> None:
        """Handle hover enter"""
        self.setScale(1.25)
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event) -> None:
        """Handle hover leave"""
        self.setScale(1.0)
        super().hoverLeaveEvent(event)
    
    def mousePressEvent(self, event) -> None:
        """Handle mouse press"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.setZValue(10)  # Bring to front
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event) -> None:
        """Handle mouse release"""
        self.setZValue(0)
        super().mouseReleaseEvent(event)


class BoneItem(QGraphicsLineItem):
    """Graphics item for a bone"""
    
    def __init__(self, from_joint: JointItem, to_joint: JointItem):
        super().__init__()
        
        self.from_joint = from_joint
        self.to_joint = to_joint
        
        self.setPen(QPen(QColor(100, 100, 100, 200), 2))
        self.setZValue(-1)
        
        self._update_line()
    
    def _update_line(self) -> None:
        """Update line position"""
        line = QLineF(
            self.from_joint.pos(),
            self.to_joint.pos()
        )
        self.setLine(line)


class ContourItem(QGraphicsPathItem):
    """Graphics item for a body contour"""
    
    def __init__(self, contour: BodyContour):
        super().__init__()
        
        self.contour = contour
        self.setPen(QPen(Colors.ACCENT_GREEN, 2))
        self.setBrush(QBrush(QColor(52, 211, 153, 40)))
        
        self._update_path()
    
    def _update_path(self) -> None:
        """Update path from contour points"""
        if not self.contour.points:
            return
        
        path = QPainterPath()
        path.moveTo(QPointF(self.contour.points[0].x, self.contour.points[0].y))
        for point in self.contour.points[1:]:
            path.lineTo(QPointF(point.x, point.y))
        
        if len(self.contour.points) >= 3:
            path.closeSubpath()
        
        self.setPath(path)


class SkeletonView(QGraphicsView):
    """Graphics view for displaying and editing skeleton"""
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        # Settings
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        
        # Colors
        self.setStyleSheet("background-color: #0a0e13;")
        self.scene.setBackgroundBrush(QBrush(QColor(10, 14, 19)))
        
        # Grid
        self._show_grid = True
        self._grid_size = 20
        
        # Items
        self.joint_items: Dict[str, JointItem] = {}
        self.bone_items: List[BoneItem] = []
        self.contour_items: List[ContourItem] = []
        self.reference_contour_items: List[QGraphicsPathItem] = []
        
        # Selection
        self._selected_joint: Optional[JointItem] = None
        self._hovered_joint: Optional[JointItem] = None
        
        # Pan and zoom
        self._zoom = 1.0
        self._pan = QPointF(0, 0)
        
        # Setup scene
        self._setup_scene()
    
    def _setup_scene(self) -> None:
        """Setup the graphics scene"""
        # Set scene size
        self.scene.setSceneRect(-1000, -1000, 2000, 2000)
        
        # Add grid
        self._add_grid()
        
        # Add axis
        self._add_axis()
    
    def _add_grid(self) -> None:
        """Add grid to scene"""
        if not self._show_grid:
            return
        
        grid_pen = QPen(QColor(40, 50, 60, 80), 1)
        grid_pen.setStyle(Qt.PenStyle.DashLine)
        
        grid_size = self._grid_size
        scene_rect = self.scene.sceneRect()
        
        # Vertical lines
        x = int(math.floor(scene_rect.left() / grid_size)) * grid_size
        while x <= scene_rect.right():
            self.scene.addLine(x, scene_rect.top(), x, scene_rect.bottom(), grid_pen)
            x += grid_size
        
        # Horizontal lines
        y = int(math.floor(scene_rect.top() / grid_size)) * grid_size
        while y <= scene_rect.bottom():
            self.scene.addLine(scene_rect.left(), y, scene_rect.right(), y, grid_pen)
            y += grid_size
    
    def _add_axis(self) -> None:
        """Add coordinate axis to scene"""
        # X axis (red)
        x_pen = QPen(Colors.AXIS_X, 2)
        self.scene.addLine(0, 0, 100, 0, x_pen)
        
        # Y axis (green)
        y_pen = QPen(Colors.AXIS_Y, 2)
        self.scene.addLine(0, 0, 0, -100, y_pen)  # Note: Y is inverted in Qt
        
        # Z axis would be out of screen
    
    def set_skeleton(self, skeleton: Skeleton) -> None:
        """Set the skeleton to display"""
        # Clear existing items
        self._clear_items()
        
        if skeleton is None:
            return
        
        # Add joints
        for joint_id, joint in skeleton.joints.items():
            item = JointItem(joint)
            item.setPos(joint.x, -joint.y)  # Note: Y is inverted
            self.scene.addItem(item)
            self.joint_items[joint_id] = item
        
        # Add bones
        for bone in skeleton.bones:
            from_item = self.joint_items.get(bone.from_joint_id)
            to_item = self.joint_items.get(bone.to_joint_id)
            
            if from_item and to_item:
                bone_item = BoneItem(from_item, to_item)
                self.scene.addItem(bone_item)
                self.bone_items.append(bone_item)
        
        # Add contours
        for contour in skeleton.contours:
            item = ContourItem(contour)
            self.scene.addItem(item)
            self.contour_items.append(item)
        
        # Fit view
        self._fit_view()
    
    def set_reference_contours(self, contours: List[Contour]) -> None:
        """Set reference contours from vectorizer"""
        # Clear existing reference contours
        for item in self.reference_contour_items:
            self.scene.removeItem(item)
        self.reference_contour_items = []
        
        if not contours:
            return
        
        # Add reference contours
        pen = QPen(QColor(255, 255, 255, 60), 1)
        pen.setStyle(Qt.PenStyle.DashLine)
        
        for contour in contours:
            path = QPainterPath()
            if contour.points:
                path.moveTo(QPointF(contour.points[0][0], -contour.points[0][1]))
                for x, y in contour.points[1:]:
                    path.lineTo(QPointF(x, -y))
                if contour.is_closed:
                    path.closeSubpath()
            
            item = QGraphicsPathItem(path)
            item.setPen(pen)
            item.setZValue(-2)
            self.scene.addItem(item)
            self.reference_contour_items.append(item)
    
    def _clear_items(self) -> None:
        """Clear all items from scene"""
        # Clear joint items
        for item in self.joint_items.values():
            self.scene.removeItem(item)
        self.joint_items.clear()
        
        # Clear bone items
        for item in self.bone_items:
            self.scene.removeItem(item)
        self.bone_items = []
        
        # Clear contour items
        for item in self.contour_items:
            self.scene.removeItem(item)
        self.contour_items = []
        
        # Clear reference contours
        for item in self.reference_contour_items:
            self.scene.removeItem(item)
        self.reference_contour_items = []
    
    def _fit_view(self) -> None:
        """Fit view to all items"""
        if not self.joint_items:
            self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            return
        
        # Find bounds of all joints
        min_x = float('inf')
        max_x = float('-inf')
        min_y = float('inf')
        max_y = float('-inf')
        
        for item in self.joint_items.values():
            pos = item.pos()
            min_x = min(min_x, pos.x() - item.radius)
            max_x = max(max_x, pos.x() + item.radius)
            min_y = min(min_y, pos.y() - item.radius)
            max_y = max(max_y, pos.y() + item.radius)
        
        # Add padding
        padding = 50
        min_x -= padding
        max_x += padding
        min_y -= padding
        max_y += padding
        
        # Fit view
        self.fitInView(QRectF(min_x, min_y, max_x - min_x, max_y - min_y), Qt.AspectRatioMode.KeepAspectRatio)
    
    def add_joint(self, joint: Joint) -> JointItem:
        """Add a joint to the scene"""
        item = JointItem(joint)
        item.setPos(joint.x, -joint.y)
        self.scene.addItem(item)
        self.joint_items[joint.id] = item
        return item
    
    def remove_joint(self, joint_id: str) -> None:
        """Remove a joint from the scene"""
        if joint_id in self.joint_items:
            item = self.joint_items[joint_id]
            self.scene.removeItem(item)
            del self.joint_items[joint_id]
    
    def update_joint(self, joint: Joint) -> None:
        """Update a joint in the scene"""
        if joint.id in self.joint_items:
            item = self.joint_items[joint.id]
            item.joint = joint
            item.setPos(joint.x, -joint.y)
            item._update_brush()
    
    def refresh_bones(self, bones: List[Any]) -> None:
        """Refresh bone display"""
        # Clear existing bones
        for item in self.bone_items:
            self.scene.removeItem(item)
        self.bone_items = []
        
        # Add new bones
        for bone in bones:
            from_item = self.joint_items.get(bone.from_joint_id)
            to_item = self.joint_items.get(bone.to_joint_id)
            
            if from_item and to_item:
                bone_item = BoneItem(from_item, to_item)
                self.scene.addItem(bone_item)
                self.bone_items.append(bone_item)
    
    def set_show_grid(self, show: bool) -> None:
        """Show or hide grid"""
        self._show_grid = show
        self._clear_items()
        self._setup_scene()
        # Re-add skeleton
        # This would be handled by the parent
    
    def wheelEvent(self, event) -> None:
        """Handle wheel event for zooming"""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Zoom
            zoom_factor = 1.1 if event.angleDelta().y() > 0 else 0.9
            self.scale(zoom_factor, zoom_factor)
            event.accept()
        else:
            super().wheelEvent(event)
    
    def mousePressEvent(self, event) -> None:
        """Handle mouse press"""
        if event.button() == Qt.MouseButton.MiddleButton:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event) -> None:
        """Handle mouse release"""
        if event.button() == Qt.MouseButton.MiddleButton:
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class SkeletonTab(QWidget):
    """Tab for building and editing skeletons"""
    
    # Signals
    skeleton_loaded = Signal(int)
    skeleton_created = Signal(int)
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        
        self.skeleton = Skeleton()
        self._history: List[Skeleton] = []
        self._history_index: int = -1
        self._reference_contours: List[Contour] = []
        
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
        
        # Left panel - Skeleton view
        left_panel = QFrame()
        left_panel.setStyleSheet("background-color: #10151c; border: 1px solid #1e2833; border-radius: 6px;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(6)
        
        # Skeleton view
        self.skeleton_view = SkeletonView()
        left_layout.addWidget(QLabel("Skeleton View"))
        left_layout.addWidget(self.skeleton_view)
        
        # View controls
        view_controls = QHBoxLayout()
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setFixedSize(30, 30)
        self.btn_zoom_in.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; }")
        self.btn_zoom_out = QPushButton("-")
        self.btn_zoom_out.setFixedSize(30, 30)
        self.btn_zoom_out.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; }")
        self.btn_fit = QPushButton("Fit")
        self.btn_fit.setFixedSize(50, 30)
        self.btn_fit.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; }")
        view_controls.addWidget(self.btn_zoom_in)
        view_controls.addWidget(self.btn_zoom_out)
        view_controls.addWidget(self.btn_fit)
        left_layout.addLayout(view_controls)
        
        splitter.addWidget(left_panel)
        
        # Right panel - Controls
        right_panel = QFrame()
        right_panel.setStyleSheet("background-color: #10151c; border: 1px solid #1e2833; border-radius: 6px;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(6)
        
        # Presets
        preset_group = QGroupBox("Presets")
        preset_group.setStyleSheet("QGroupBox { border: 1px solid #1e2833; border-radius: 6px; padding: 8px; }")
        preset_layout = QHBoxLayout()
        
        self.btn_t_pose = QPushButton("T-Pose")
        self.btn_t_pose.setStyleSheet("""
            QPushButton {
                background-color: rgba(34, 211, 238, 0.12);
                color: #22d3ee;
                border: 1px solid rgba(34, 211, 238, 0.55);
                border-radius: 6px;
                padding: 8px 16px;
            }
        """)
        self.btn_a_pose = QPushButton("A-Pose")
        self.btn_a_pose.setStyleSheet("""
            QPushButton {
                background-color: rgba(34, 211, 238, 0.12);
                color: #22d3ee;
                border: 1px solid rgba(34, 211, 238, 0.55);
                border-radius: 6px;
                padding: 8px 16px;
            }
        """)
        preset_layout.addWidget(self.btn_t_pose)
        preset_layout.addWidget(self.btn_a_pose)
        preset_group.setLayout(preset_layout)
        right_layout.addWidget(preset_group)
        
        # Joint tools
        joint_group = QGroupBox("Joint Tools")
        joint_group.setStyleSheet("QGroupBox { border: 1px solid #1e2833; border-radius: 6px; padding: 8px; }")
        joint_layout = QVBoxLayout()
        
        self.btn_add_joint = QPushButton("Add Joint")
        self.btn_add_joint.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        self.btn_remove_joint = QPushButton("Remove Selected")
        self.btn_remove_joint.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        self.btn_connect = QPushButton("Connect Joints")
        self.btn_connect.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        
        joint_layout.addWidget(self.btn_add_joint)
        joint_layout.addWidget(self.btn_remove_joint)
        joint_layout.addWidget(self.btn_connect)
        
        # Mirror tools
        mirror_layout = QHBoxLayout()
        self.btn_mirror_x = QPushButton("Mirror X")
        self.btn_mirror_x.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        self.btn_mirror_y = QPushButton("Mirror Y")
        self.btn_mirror_y.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        mirror_layout.addWidget(self.btn_mirror_x)
        mirror_layout.addWidget(self.btn_mirror_y)
        joint_layout.addLayout(mirror_layout)
        
        joint_group.setLayout(joint_layout)
        right_layout.addWidget(joint_group)
        
        # Skeleton settings
        settings_group = QGroupBox("Skeleton Settings")
        settings_group.setStyleSheet("QGroupBox { border: 1px solid #1e2833; border-radius: 6px; padding: 8px; }")
        settings_layout = QVBoxLayout()
        
        # Height
        height_layout = QHBoxLayout()
        height_layout.addWidget(QLabel("Height (cm):"))
        self.spin_height = QDoubleSpinBox()
        self.spin_height.setRange(50, 300)
        self.spin_height.setValue(180)
        self.spin_height.setSingleStep(1)
        self.spin_height.setStyleSheet("QDoubleSpinBox { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 4px 8px; }")
        height_layout.addWidget(self.spin_height)
        settings_layout.addLayout(height_layout)
        
        # Symmetry
        symmetry_layout = QHBoxLayout()
        self.chk_mirror_symmetry = QCheckBox("Mirror Symmetry")
        self.chk_mirror_symmetry.setChecked(True)
        self.chk_mirror_symmetry.setStyleSheet("QCheckBox { color: #d7e0ea; spacing: 8px; }")
        symmetry_layout.addWidget(self.chk_mirror_symmetry)
        settings_layout.addLayout(symmetry_layout)
        
        # Floor settings
        floor_layout = QHBoxLayout()
        floor_layout.addWidget(QLabel("Floor Joint:"))
        self.combo_floor = QComboBox()
        self.combo_floor.setStyleSheet("QComboBox { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 4px 8px; }")
        floor_layout.addWidget(self.combo_floor)
        settings_layout.addLayout(floor_layout)
        
        settings_group.setLayout(settings_layout)
        right_layout.addWidget(settings_group)
        
        # Load/Save
        io_group = QGroupBox("File")
        io_group.setStyleSheet("QGroupBox { border: 1px solid #1e2833; border-radius: 6px; padding: 8px; }")
        io_layout = QHBoxLayout()
        
        self.btn_load_skeleton = QPushButton("Load Skeleton")
        self.btn_load_skeleton.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        self.btn_save_skeleton = QPushButton("Save Skeleton")
        self.btn_save_skeleton.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        self.btn_export_json = QPushButton("Export JSON")
        self.btn_export_json.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        
        io_layout.addWidget(self.btn_load_skeleton)
        io_layout.addWidget(self.btn_save_skeleton)
        io_layout.addWidget(self.btn_export_json)
        io_group.setLayout(io_layout)
        right_layout.addWidget(io_group)
        
        # Stats
        self.lbl_stats = QLabel("Joints: 0 | Bones: 0")
        self.lbl_stats.setStyleSheet("color: #7c8b9d; font: 11px 'Consolas';")
        right_layout.addWidget(self.lbl_stats)
        
        # Action buttons
        action_layout = QHBoxLayout()
        self.btn_clear = QPushButton("Clear All")
        self.btn_clear.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        self.btn_generate_bones = QPushButton("Generate Bones")
        self.btn_generate_bones.setStyleSheet("""
            QPushButton {
                background-color: rgba(52, 211, 153, 0.12);
                color: #34d399;
                border: 1px solid rgba(52, 211, 153, 0.55);
                border-radius: 4px;
                padding: 6px 12px;
            }
        """)
        self.btn_send_to_workbench = QPushButton("Send to Workbench")
        self.btn_send_to_workbench.setStyleSheet("""
            QPushButton {
                background-color: rgba(34, 211, 238, 0.12);
                color: #22d3ee;
                border: 1px solid rgba(34, 211, 238, 0.55);
                border-radius: 4px;
                padding: 6px 12px;
            }
        """)
        action_layout.addWidget(self.btn_clear)
        action_layout.addWidget(self.btn_generate_bones)
        action_layout.addWidget(self.btn_send_to_workbench)
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
        
        # Update floor combo
        self._update_floor_combo()
    
    def _connect_signals(self) -> None:
        """Connect signals"""
        # Presets
        self.btn_t_pose.clicked.connect(self.create_preset_t_pose)
        self.btn_a_pose.clicked.connect(self.create_preset_a_pose)
        
        # Joint tools
        self.btn_add_joint.clicked.connect(self.on_add_joint)
        self.btn_remove_joint.clicked.connect(self.on_remove_joint)
        self.btn_connect.clicked.connect(self.on_connect_joints)
        self.btn_mirror_x.clicked.connect(self.on_mirror_x)
        self.btn_mirror_y.clicked.connect(self.on_mirror_y)
        
        # View controls
        self.btn_zoom_in.clicked.connect(self.on_zoom_in)
        self.btn_zoom_out.clicked.connect(self.on_zoom_out)
        self.btn_fit.clicked.connect(self.on_fit_view)
        
        # Settings
        self.spin_height.valueChanged.connect(self.on_height_changed)
        self.chk_mirror_symmetry.stateChanged.connect(self.on_symmetry_changed)
        self.combo_floor.currentTextChanged.connect(self.on_floor_changed)
        
        # File
        self.btn_load_skeleton.clicked.connect(self.on_load_skeleton)
        self.btn_save_skeleton.clicked.connect(self.on_save_skeleton)
        self.btn_export_json.clicked.connect(self.on_export_json)
        
        # Actions
        self.btn_clear.clicked.connect(self.clear_all)
        self.btn_generate_bones.clicked.connect(self.on_generate_bones)
        self.btn_send_to_workbench.clicked.connect(self.on_send_to_workbench)
        
        # Undo/Redo
        self.btn_undo.clicked.connect(self.undo)
        self.btn_redo.clicked.connect(self.redo)
    
    def set_reference_contours(self, contours: List[Contour]) -> None:
        """Set reference contours from vectorizer"""
        self._reference_contours = contours
        self.skeleton_view.set_reference_contours(contours)
    
    def create_preset_t_pose(self) -> None:
        """Create a T-pose skeleton"""
        self.skeleton.create_preset_t_pose()
        self.skeleton_view.set_skeleton(self.skeleton)
        self._update_stats()
        self._update_floor_combo()
        self._save_state("Create T-pose")
        self.skeleton_created.emit(self.skeleton.get_joint_count())
    
    def create_preset_a_pose(self) -> None:
        """Create an A-pose skeleton"""
        self.skeleton.create_preset_a_pose()
        self.skeleton_view.set_skeleton(self.skeleton)
        self._update_stats()
        self._update_floor_combo()
        self._save_state("Create A-pose")
        self.skeleton_created.emit(self.skeleton.get_joint_count())
    
    def on_add_joint(self) -> None:
        """Handle add joint button"""
        # Create a new joint at origin
        joint_id = f"j{self.skeleton._next_id}"
        self.skeleton._next_id += 1
        
        joint = Joint(
            id=joint_id,
            name=f"Joint_{joint_id}",
            role=JointRole.OTHER,
            parent_id=None,
            pair_id=None,
            x=0,
            y=0,
            nx=0,
            ny=0
        )
        
        self.skeleton.add_joint(joint)
        self.skeleton_view.add_joint(joint)
        self._update_stats()
        self._update_floor_combo()
        self._save_state("Add joint")
    
    def on_remove_joint(self) -> None:
        """Handle remove joint button"""
        # For now, remove last joint
        if self.skeleton.joints:
            joint_id = list(self.skeleton.joints.keys())[-1]
            self.skeleton.remove_joint(joint_id)
            self.skeleton_view.remove_joint(joint_id)
            self._update_stats()
            self._update_floor_combo()
            self._save_state("Remove joint")
    
    def on_connect_joints(self) -> None:
        """Handle connect joints button"""
        # For now, just regenerate bones
        self.on_generate_bones()
    
    def on_mirror_x(self) -> None:
        """Handle mirror X button"""
        # Mirror all joints across X axis
        for joint in self.skeleton.joints.values():
            joint.x = -joint.x
            self.skeleton_view.update_joint(joint)
        
        self._update_stats()
        self._save_state("Mirror X")
    
    def on_mirror_y(self) -> None:
        """Handle mirror Y button"""
        # Mirror all joints across Y axis
        for joint in self.skeleton.joints.values():
            joint.y = -joint.y
            self.skeleton_view.update_joint(joint)
        
        self._update_stats()
        self._save_state("Mirror Y")
    
    def on_zoom_in(self) -> None:
        """Handle zoom in button"""
        self.skeleton_view.scale(1.2, 1.2)
    
    def on_zoom_out(self) -> None:
        """Handle zoom out button"""
        self.skeleton_view.scale(0.8, 0.8)
    
    def on_fit_view(self) -> None:
        """Handle fit view button"""
        self.skeleton_view._fit_view()
    
    def on_height_changed(self, value: float) -> None:
        """Handle height change"""
        self.skeleton.parameters['target_height_cm'] = value
    
    def on_symmetry_changed(self, state: int) -> None:
        """Handle symmetry toggle"""
        self.skeleton.parameters['mirror_symmetry'] = (state == Qt.CheckState.Checked)
    
    def on_floor_changed(self, text: str) -> None:
        """Handle floor joint change"""
        self.skeleton.parameters['floor_by_joint'] = text
    
    def on_generate_bones(self) -> None:
        """Handle generate bones button"""
        self.skeleton.generate_bones()
        self.skeleton_view.refresh_bones(self.skeleton.bones)
        self._update_stats()
        self._save_state("Generate bones")
    
    def on_send_to_workbench(self) -> None:
        """Handle send to workbench button"""
        self.skeleton_created.emit(self.skeleton.get_joint_count())
    
    def _update_stats(self) -> None:
        """Update statistics display"""
        self.lbl_stats.setText(f"Joints: {self.skeleton.get_joint_count()} | Bones: {self.skeleton.get_bone_count()}")
    
    def _update_floor_combo(self) -> None:
        """Update floor joint combo box"""
        self.combo_floor.clear()
        for joint in self.skeleton.joints.values():
            self.combo_floor.addItem(joint.name)
        
        # Set current floor joint
        floor_joint = self.skeleton.parameters.get('floor_by_joint', 'Toe_L')
        if floor_joint in [j.name for j in self.skeleton.joints.values()]:
            self.combo_floor.setCurrentText(floor_joint)
    
    def load_skeleton_from_file(self, path: str) -> bool:
        """Load skeleton from JSON file"""
        skeleton = Skeleton.load_from_file(path)
        if skeleton:
            self.skeleton = skeleton
            self.skeleton_view.set_skeleton(skeleton)
            self._update_stats()
            self._update_floor_combo()
            self._save_state(f"Load skeleton from {path}")
            self.skeleton_loaded.emit(self.skeleton.get_joint_count())
            return True
        return False
    
    def on_load_skeleton(self) -> None:
        """Handle load skeleton button"""
        options = QFileDialog.Options()
        file, _ = QFileDialog.getOpenFileName(
            self, "Load Skeleton", "",
            "JSON Files (*.json);;All Files (*)",
            options=options
        )
        
        if file:
            self.load_skeleton_from_file(file)
    
    def on_save_skeleton(self) -> None:
        """Handle save skeleton button"""
        options = QFileDialog.Options()
        file, _ = QFileDialog.getSaveFileName(
            self, "Save Skeleton", "",
            "JSON Files (*.json);;All Files (*)",
            options=options
        )
        
        if file:
            if self.skeleton.save_to_file(file):
                QMessageBox.information(self, "Saved", f"Skeleton saved to {file}")
                self._save_state(f"Save skeleton to {file}")
    
    def on_export_json(self) -> None:
        """Handle export JSON button"""
        self.on_save_skeleton()
    
    def get_skeleton(self) -> Skeleton:
        """Get current skeleton"""
        return self.skeleton
    
    def _save_state(self, description: str = "") -> None:
        """Save current state to history"""
        # Save current skeleton
        current_skeleton = Skeleton()
        current_skeleton.from_dict(self.skeleton.to_dict())
        
        # Trim history
        if len(self._history) > self._history_index + 1:
            self._history = self._history[:self._history_index + 1]
        
        self._history.append(current_skeleton)
        self._history_index = len(self._history) - 1
    
    def undo(self) -> None:
        """Undo last action"""
        if self._history_index > 0:
            self._history_index -= 1
            self.skeleton = self._history[self._history_index]
            self.skeleton_view.set_skeleton(self.skeleton)
            self._update_stats()
            self._update_floor_combo()
    
    def redo(self) -> None:
        """Redo last undone action"""
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            self.skeleton = self._history[self._history_index]
            self.skeleton_view.set_skeleton(self.skeleton)
            self._update_stats()
            self._update_floor_combo()
    
    def clear_all(self) -> None:
        """Clear all data"""
        self.skeleton.clear()
        self.skeleton_view._clear_items()
        self._history = []
        self._history_index = -1
        self._update_stats()
        self._update_floor_combo()
    
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
