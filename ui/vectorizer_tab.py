"""
Vectorizer tab for converting raster images to vector contours
"""

import os
import numpy as np
from typing import List, Optional, Tuple
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
    QComboBox, QSlider, QSplitter, QFileDialog, QMessageBox,
    QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal, QSize, QPoint, QRect, QTimer
from PySide6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QPainterPath

from core.vectorizer import Vectorizer, Contour, ROI
from ui.styles import Colors, Fonts


class ImageCanvas(QLabel):
    """Canvas for displaying and editing images"""
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setMinimumSize(300, 300)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: #141b24; border: 1px solid #1e2833;")
        
        self._image: Optional[QPixmap] = None
        self._contours: List[Contour] = []
        self._roi: Optional[ROI] = None
        self._selection_start: Optional[QPoint] = None
        self._zoom: float = 1.0
        self._pan: QPoint = QPoint(0, 0)
        
        self.setMouseTracking(True)
    
    def set_image(self, pixmap: QPixmap) -> None:
        """Set the image to display"""
        self._image = pixmap
        self._update_display()
    
    def set_contours(self, contours: List[Contour]) -> None:
        """Set contours to display"""
        self._contours = contours
        self._update_display()
    
    def set_roi(self, roi: Optional[ROI]) -> None:
        """Set region of interest"""
        self._roi = roi
        self._update_display()
    
    def clear(self) -> None:
        """Clear the canvas"""
        self._image = None
        self._contours = []
        self._roi = None
        self._update_display()
    
    def _update_display(self) -> None:
        """Update the display"""
        if self._image is None:
            self.setPixmap(QPixmap())
            return
        
        # Create a new pixmap for drawing
        display_pixmap = self._image.copy()
        
        # Draw contours
        if self._contours:
            self._draw_contours(display_pixmap)
        
        # Draw ROI
        if self._roi:
            self._draw_roi(display_pixmap)
        
        self.setPixmap(display_pixmap)
    
    def _draw_contours(self, pixmap: QPixmap) -> None:
        """Draw contours on the pixmap"""
        painter = QPainter(pixmap)
        
        # Set pen for external contours
        pen_external = QPen(Colors.ACCENT_CYAN)
        pen_external.setWidth(2)
        
        # Set pen for internal contours
        pen_internal = QPen(Colors.ACCENT_ORANGE)
        pen_internal.setWidth(1)
        
        for contour in self._contours:
            if len(contour.points) < 2:
                continue
            
            # Convert contour points to QPointF
            path = QPainterPath()
            path.moveTo(QPointF(contour.points[0][0], contour.points[0][1]))
            for x, y in contour.points[1:]:
                path.lineTo(QPointF(x, y))
            
            if contour.is_closed:
                path.closeSubpath()
            
            # Set pen based on contour type
            if contour.is_external:
                painter.setPen(pen_external)
            else:
                painter.setPen(pen_internal)
            
            painter.drawPath(path)
        
        painter.end()
    
    def _draw_roi(self, pixmap: QPixmap) -> None:
        """Draw ROI rectangle on the pixmap"""
        if self._roi is None:
            return
        
        painter = QPainter(pixmap)
        
        # Set pen for ROI
        pen = QPen(Colors.ACCENT_CYAN)
        pen.setWidth(2)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        
        # Draw rectangle
        rect = QRect(
            int(self._roi.x),
            int(self._roi.y),
            int(self._roi.width),
            int(self._roi.height)
        )
        painter.drawRect(rect)
        
        # Fill with semi-transparent color
        painter.fillRect(
            rect,
            QColor(34, 211, 238, 40)
        )
        
        painter.end()
    
    def mousePressEvent(self, event) -> None:
        """Handle mouse press"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._selection_start = event.position().toPoint()
            self._update_display()
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event) -> None:
        """Handle mouse move"""
        if self._selection_start and self._image:
            current_pos = event.position().toPoint()
            
            # Create ROI
            x1 = min(self._selection_start.x(), current_pos.x())
            y1 = min(self._selection_start.y(), current_pos.y())
            x2 = max(self._selection_start.x(), current_pos.x())
            y2 = max(self._selection_start.y(), current_pos.y())
            
            self._roi = ROI(x=x1, y=y1, width=x2 - x1, height=y2 - y1)
            self._update_display()
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event) -> None:
        """Handle mouse release"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._selection_start = None
        
        super().mouseReleaseEvent(event)


class ContourPreview(QWidget):
    """Widget for previewing vector contours"""
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self.setStyleSheet("background-color: #141b24; border: 1px solid #1e2833;")
        
        self._contours: List[Contour] = []
        self._scale: float = 1.0
        self._offset: QPoint = QPoint(0, 0)
    
    def set_contours(self, contours: List[Contour]) -> None:
        """Set contours to display"""
        self._contours = contours
        self._calculate_scale_and_offset()
        self.update()
    
    def clear(self) -> None:
        """Clear contours"""
        self._contours = []
        self.update()
    
    def _calculate_scale_and_offset(self) -> None:
        """Calculate scale and offset to center contours"""
        if not self._contours:
            return
        
        # Find bounds
        min_x = float('inf')
        max_x = float('-inf')
        min_y = float('inf')
        max_y = float('-inf')
        
        for contour in self._contours:
            for x, y in contour.points:
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)
        
        width = max_x - min_x
        height = max_y - min_y
        
        if width == 0 or height == 0:
            return
        
        # Calculate scale to fit
        widget_width = self.width() - 20
        widget_height = self.height() - 20
        
        self._scale = min(widget_width / width, widget_height / height) * 0.9
        
        # Calculate offset to center
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        
        self._offset = QPoint(
            int(self.width() / 2 - center_x * self._scale),
            int(self.height() / 2 - center_y * self._scale)
        )
    
    def paintEvent(self, event) -> None:
        """Handle paint event"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Clear background
        painter.fillRect(self.rect(), QColor(20, 27, 36))
        
        # Draw contours
        pen_external = QPen(Colors.ACCENT_CYAN)
        pen_external.setWidth(2)
        
        pen_internal = QPen(Colors.ACCENT_ORANGE)
        pen_internal.setWidth(1)
        
        for contour in self._contours:
            if len(contour.points) < 2:
                continue
            
            path = QPainterPath()
            first = True
            for x, y in contour.points:
                px = int(x * self._scale + self._offset.x())
                py = int(y * self._scale + self._offset.y())
                if first:
                    path.moveTo(px, py)
                    first = False
                else:
                    path.lineTo(px, py)
            
            if contour.is_closed:
                path.closeSubpath()
            
            if contour.is_external:
                painter.setPen(pen_external)
            else:
                painter.setPen(pen_internal)
            
            painter.drawPath(path)


class VectorizerTab(QWidget):
    """Tab for vectorizing raster images"""
    
    # Signals
    images_loaded = Signal(int)
    contours_generated = Signal(int)
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        
        self.vectorizer = Vectorizer()
        self._current_image_path: Optional[str] = None
        self._history: List[List[Contour]] = []
        self._history_index: int = -1
        
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
        
        # Left panel - Image and controls
        left_panel = QFrame()
        left_panel.setStyleSheet("background-color: #10151c; border: 1px solid #1e2833; border-radius: 6px;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(6)
        
        # Image canvas
        self.canvas = ImageCanvas()
        left_layout.addWidget(QLabel("Source Image"))
        left_layout.addWidget(self.canvas)
        
        # ROI controls
        roi_group = QGroupBox("ROI (Region of Interest)")
        roi_group.setStyleSheet("QGroupBox { border: 1px solid #1e2833; border-radius: 6px; padding: 8px; }")
        roi_layout = QHBoxLayout()
        
        self.btn_crop = QPushButton("Crop to ROI")
        self.btn_crop.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        self.btn_roi_clear = QPushButton("Clear ROI")
        self.btn_roi_clear.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        self.btn_src_fit = QPushButton("Fit Image")
        self.btn_src_fit.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        
        roi_layout.addWidget(self.btn_crop)
        roi_layout.addWidget(self.btn_roi_clear)
        roi_layout.addWidget(self.btn_src_fit)
        roi_group.setLayout(roi_layout)
        left_layout.addWidget(roi_group)
        
        # Vectorization controls
        vector_group = QGroupBox("Vectorization")
        vector_group.setStyleSheet("QGroupBox { border: 1px solid #1e2833; border-radius: 6px; padding: 8px; }")
        vector_layout = QVBoxLayout()
        
        # Blur
        blur_layout = QHBoxLayout()
        blur_layout.addWidget(QLabel("Blur Radius:"))
        self.spin_blur = QSpinBox()
        self.spin_blur.setRange(0, 20)
        self.spin_blur.setValue(3)
        self.spin_blur.setStyleSheet("QSpinBox { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 4px 8px; }")
        blur_layout.addWidget(self.spin_blur)
        vector_layout.addLayout(blur_layout)
        
        # Canny thresholds
        canny_layout = QHBoxLayout()
        canny_layout.addWidget(QLabel("Canny Thresholds:"))
        self.spin_canny1 = QSpinBox()
        self.spin_canny1.setRange(0, 255)
        self.spin_canny1.setValue(50)
        self.spin_canny1.setStyleSheet("QSpinBox { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 4px 8px; }")
        canny_layout.addWidget(self.spin_canny1)
        canny_layout.addWidget(QLabel("/"))
        self.spin_canny2 = QSpinBox()
        self.spin_canny2.setRange(0, 255)
        self.spin_canny2.setValue(150)
        self.spin_canny2.setStyleSheet("QSpinBox { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 4px 8px; }")
        canny_layout.addWidget(self.spin_canny2)
        vector_layout.addLayout(canny_layout)
        
        # Simplification
        simplify_layout = QHBoxLayout()
        simplify_layout.addWidget(QLabel("Simplification:"))
        self.dspin_epsilon = QDoubleSpinBox()
        self.dspin_epsilon.setRange(0.1, 10.0)
        self.dspin_epsilon.setValue(1.0)
        self.dspin_epsilon.setSingleStep(0.1)
        self.dspin_epsilon.setStyleSheet("QDoubleSpinBox { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 4px 8px; }")
        simplify_layout.addWidget(self.dspin_epsilon)
        vector_layout.addLayout(simplify_layout)
        
        # Options
        options_layout = QHBoxLayout()
        self.chk_remove_bg = QCheckBox("Remove Background")
        self.chk_remove_bg.setChecked(True)
        self.chk_remove_bg.setStyleSheet("QCheckBox { color: #d7e0ea; spacing: 8px; }")
        options_layout.addWidget(self.chk_remove_bg)
        self.chk_internal_edges = QCheckBox("Detect Internal Edges")
        self.chk_internal_edges.setChecked(True)
        self.chk_internal_edges.setStyleSheet("QCheckBox { color: #d7e0ea; spacing: 8px; }")
        options_layout.addWidget(self.chk_internal_edges)
        vector_layout.addLayout(options_layout)
        
        # Vectorize button
        self.btn_vectorize = QPushButton("Vectorize Image")
        self.btn_vectorize.setStyleSheet("""
            QPushButton {
                background-color: rgba(34, 211, 238, 0.12);
                color: #22d3ee;
                border: 1px solid rgba(34, 211, 238, 0.55);
                border-radius: 6px;
                padding: 8px 16px;
                font: 600 11px "System";
            }
            QPushButton:hover {
                background-color: rgba(34, 211, 238, 0.25);
            }
        """)
        vector_layout.addWidget(self.btn_vectorize)
        
        vector_group.setLayout(vector_layout)
        left_layout.addWidget(vector_group)
        
        # Load/Save buttons
        io_layout = QHBoxLayout()
        self.btn_load = QPushButton("Load Image")
        self.btn_load.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        self.btn_sample = QPushButton("Load Sample")
        self.btn_sample.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        self.btn_save_svg = QPushButton("Save SVG")
        self.btn_save_svg.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        io_layout.addWidget(self.btn_load)
        io_layout.addWidget(self.btn_sample)
        io_layout.addWidget(self.btn_save_svg)
        left_layout.addLayout(io_layout)
        
        splitter.addWidget(left_panel)
        
        # Right panel - Contour preview and info
        right_panel = QFrame()
        right_panel.setStyleSheet("background-color: #10151c; border: 1px solid #1e2833; border-radius: 6px;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(6)
        
        # Contour preview
        right_layout.addWidget(QLabel("Vector Contours"))
        self.contour_preview = ContourPreview()
        right_layout.addWidget(self.contour_preview)
        
        # Stats
        self.lbl_stats = QLabel("No contours")
        self.lbl_stats.setStyleSheet("color: #7c8b9d; font: 11px 'Consolas';")
        right_layout.addWidget(self.lbl_stats)
        
        # Contour list
        self.lbl_contours = QLabel("External: 0 | Internal: 0")
        self.lbl_contours.setStyleSheet("color: #7c8b9d; font: 11px 'Consolas';")
        right_layout.addWidget(self.lbl_contours)
        
        # Silhouette info
        self.lbl_silhouette = QLabel("Silhouette: None")
        self.lbl_silhouette.setStyleSheet("color: #7c8b9d; font: 11px 'Consolas';")
        right_layout.addWidget(self.lbl_silhouette)
        
        # Action buttons
        action_layout = QHBoxLayout()
        self.btn_clear = QPushButton("Clear All")
        self.btn_clear.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        self.btn_copy = QPushButton("Copy to Skeleton")
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background-color: rgba(52, 211, 153, 0.12);
                color: #34d399;
                border: 1px solid rgba(52, 211, 153, 0.55);
                border-radius: 4px;
                padding: 6px 12px;
            }
        """)
        action_layout.addWidget(self.btn_clear)
        action_layout.addWidget(self.btn_copy)
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
        splitter.setSizes([300, 200])
        
        main_layout.addWidget(splitter)
    
    def _connect_signals(self) -> None:
        """Connect signals"""
        # ROI buttons
        self.btn_crop.clicked.connect(self.on_crop)
        self.btn_roi_clear.clicked.connect(self.on_clear_roi)
        self.btn_src_fit.clicked.connect(self.on_fit_image)
        
        # Vectorization
        self.btn_vectorize.clicked.connect(self.on_vectorize)
        
        # Load/Save
        self.btn_load.clicked.connect(self.on_load_image)
        self.btn_sample.clicked.connect(self.on_load_sample)
        self.btn_save_svg.clicked.connect(self.on_save_svg)
        
        # Actions
        self.btn_clear.clicked.connect(self.clear_all)
        self.btn_copy.clicked.connect(self.on_copy_to_skeleton)
        
        # Undo/Redo
        self.btn_undo.clicked.connect(self.undo)
        self.btn_redo.clicked.connect(self.redo)
        
        # Parameter changes
        self.spin_blur.valueChanged.connect(self.on_parameter_changed)
        self.spin_canny1.valueChanged.connect(self.on_parameter_changed)
        self.spin_canny2.valueChanged.connect(self.on_parameter_changed)
        self.dspin_epsilon.valueChanged.connect(self.on_parameter_changed)
        self.chk_remove_bg.stateChanged.connect(self.on_parameter_changed)
        self.chk_internal_edges.stateChanged.connect(self.on_parameter_changed)
    
    def load_images(self, paths: List[str]) -> None:
        """Load multiple images"""
        if not paths:
            return
        
        # Load first image
        self.load_image(paths[0])
        
        # Store other paths for reference
        self._image_paths = paths
        self.images_loaded.emit(len(paths))
    
    def load_test_images(self, paths: List[str]) -> None:
        """Load test images from repository"""
        self.load_images(paths)
    
    def load_image(self, path: str) -> bool:
        """Load an image from file"""
        if not os.path.exists(path):
            return False
        
        try:
            # Load with vectorizer
            if self.vectorizer.load_image(path):
                self._current_image_path = path
                
                # Update display
                img = self.vectorizer.get_image()
                if img is not None:
                    self._display_image(img)
                
                # Clear contours
                self.vectorizer.clear_contours()
                self.contour_preview.clear()
                self._update_stats()
                
                # Clear history
                self._history = []
                self._history_index = -1
                
                return True
        except Exception as e:
            print(f"Error loading image: {e}")
            return False
        
        return False
    
    def _display_image(self, img: np.ndarray) -> None:
        """Display image on canvas"""
        # Convert numpy array to QPixmap
        if len(img.shape) == 3:
            height, width, channels = img.shape
            if channels == 3:
                # RGB image
                qimg = QImage(img.data, width, height, QImage.Format_RGB888)
            elif channels == 4:
                # RGBA image
                qimg = QImage(img.data, width, height, QImage.Format_ARGB32)
            else:
                return
        elif len(img.shape) == 2:
            # Grayscale image
            height, width = img.shape
            qimg = QImage(img.data, width, height, QImage.Format_Grayscale8)
        else:
            return
        
        pixmap = QPixmap.fromImage(qimg)
        self.canvas.set_image(pixmap)
    
    def on_load_image(self) -> None:
        """Handle load image button click"""
        options = QFileDialog.Options()
        file, _ = QFileDialog.getOpenFileName(
            self, "Load Image", "",
            "Image Files (*.bmp *.png *.jpg *.jpeg);;All Files (*)",
            options=options
        )
        
        if file:
            self.load_image(file)
    
    def on_load_sample(self) -> None:
        """Handle load sample button click"""
        # Try to load from repository
        repo_path = Path(__file__).parent.parent.parent
        
        # Look for BMP files
        bmp_files = [
            repo_path / 'front.bmp',
            repo_path / 'back.bmp',
            repo_path / 'left.bmp',
            repo_path / 'right.bmp'
        ]
        
        available = [f for f in bmp_files if f.exists()]
        
        if available:
            # Load first available
            self.load_image(str(available[0]))
            self._image_paths = [str(f) for f in available]
            self.images_loaded.emit(len(available))
        else:
            QMessageBox.information(self, "No Samples", "No sample images found in repository.")
    
    def on_crop(self) -> None:
        """Handle crop to ROI button"""
        roi = self.canvas.get_roi()
        if roi is None:
            QMessageBox.information(self, "No ROI", "Please select a region of interest first.")
            return
        
        # Apply ROI to vectorizer
        self.vectorizer.set_roi(roi)
        
        # Update display
        img = self.vectorizer.get_image()
        if img is not None:
            self._display_image(img)
        
        # Clear ROI
        self.canvas.set_roi(None)
    
    def on_clear_roi(self) -> None:
        """Handle clear ROI button"""
        self.canvas.set_roi(None)
        self.vectorizer.clear_roi()
    
    def on_fit_image(self) -> None:
        """Handle fit image button"""
        # For now, just clear ROI
        self.on_clear_roi()
    
    def on_parameter_changed(self) -> None:
        """Handle parameter change"""
        # Update vectorizer parameters
        self.vectorizer.set_parameter('blur_radius', self.spin_blur.value())
        self.vectorizer.set_parameter('canny_threshold1', self.spin_canny1.value())
        self.vectorizer.set_parameter('canny_threshold2', self.spin_canny2.value())
        self.vectorizer.set_parameter('simplification_epsilon', self.dspin_epsilon.value())
        self.vectorizer.set_parameter('remove_background', self.chk_remove_bg.isChecked())
        self.vectorizer.set_parameter('detect_internal_edges', self.chk_internal_edges.isChecked())
    
    def on_vectorize(self) -> None:
        """Handle vectorize button"""
        if self.vectorizer.get_image() is None:
            QMessageBox.warning(self, "No Image", "Please load an image first.")
            return
        
        try:
            # Save state to history
            self._save_state()
            
            # Vectorize
            contours = self.vectorizer.vectorize()
            
            # Update display
            self.canvas.set_contours(contours)
            self.contour_preview.set_contours(contours)
            self._update_stats()
            
            # Emit signal
            self.contours_generated.emit(len(contours))
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Vectorization failed: {str(e)}")
    
    def _save_state(self) -> None:
        """Save current contours to history"""
        # Save current contours
        current_contours = [c for c in self.vectorizer.get_contours()]
        
        # Trim history
        if len(self._history) > self._history_index + 1:
            self._history = self._history[:self._history_index + 1]
        
        self._history.append(current_contours)
        self._history_index = len(self._history) - 1
    
    def undo(self) -> None:
        """Undo last vectorization"""
        if self._history_index > 0:
            self._history_index -= 1
            contours = self._history[self._history_index]
            
            # Update vectorizer
            self.vectorizer.clear_contours()
            for contour in contours:
                self.vectorizer._contours.append(contour)
            
            # Update display
            self.canvas.set_contours(contours)
            self.contour_preview.set_contours(contours)
            self._update_stats()
    
    def redo(self) -> None:
        """Redo last undone action"""
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            contours = self._history[self._history_index]
            
            # Update vectorizer
            self.vectorizer.clear_contours()
            for contour in contours:
                self.vectorizer._contours.append(contour)
            
            # Update display
            self.canvas.set_contours(contours)
            self.contour_preview.set_contours(contours)
            self._update_stats()
    
    def _update_stats(self) -> None:
        """Update statistics display"""
        contours = self.vectorizer.get_contours()
        
        external_count = sum(1 for c in contours if c.is_external)
        internal_count = sum(1 for c in contours if not c.is_external)
        
        self.lbl_contours.setText(f"External: {external_count} | Internal: {internal_count}")
        self.lbl_stats.setText(f"Total contours: {len(contours)}")
        
        # Get silhouette
        silhouette = self.vectorizer.get_silhouette()
        if silhouette:
            area = self._calculate_contour_area(silhouette)
            self.lbl_silhouette.setText(f"Silhouette: {len(silhouette.points)} points, area: {area:.1f}")
        else:
            self.lbl_silhouette.setText("Silhouette: None")
    
    def _calculate_contour_area(self, contour: Contour) -> float:
        """Calculate area of a contour"""
        if len(contour.points) < 3:
            return 0
        
        area = 0
        points = contour.points
        n = len(points)
        
        for i in range(n):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % n]
            area += (x1 * y2) - (x2 * y1)
        
        return abs(area) / 2
    
    def on_save_svg(self) -> None:
        """Handle save SVG button"""
        contours = self.vectorizer.get_contours()
        if not contours:
            QMessageBox.information(self, "No Contours", "No contours to save.")
            return
        
        options = QFileDialog.Options()
        file, _ = QFileDialog.getSaveFileName(
            self, "Save SVG", "",
            "SVG Files (*.svg);;All Files (*)",
            options=options
        )
        
        if file:
            try:
                svg = self.vectorizer.to_svg()
                with open(file, 'w', encoding='utf-8') as f:
                    f.write(svg)
                QMessageBox.information(self, "Saved", f"SVG saved to {file}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save SVG: {str(e)}")
    
    def on_copy_to_skeleton(self) -> None:
        """Handle copy to skeleton button"""
        contours = self.vectorizer.get_contours()
        if not contours:
            QMessageBox.information(self, "No Contours", "No contours to copy.")
            return
        
        # Emit signal with contours
        # The main window will handle passing to skeleton tab
        self.contours_generated.emit(len(contours))
    
    def get_contours(self) -> List[Contour]:
        """Get current contours"""
        return self.vectorizer.get_contours()
    
    def clear_all(self) -> None:
        """Clear all data"""
        self.vectorizer.clear_contours()
        self.vectorizer.clear_roi()
        self.canvas.clear()
        self.contour_preview.clear()
        self._history = []
        self._history_index = -1
        self._current_image_path = None
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
