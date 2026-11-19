"""
Вкладка конструктора скелета для создания и редактирования скелета персонажа
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
    """Графический элемент для сустава"""
    
    def __init__(self, joint: Joint, radius: float = 8):
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        
        self.joint = joint
        self.radius = radius
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        
        # Устанавливаем цвета в зависимости от типа сустава
        self._update_brush()
        self.setPen(QPen(QColor(255, 255, 255, 180), 1))
    
    def _update_brush(self) -> None:
        """Обновляем кисть в зависимости от свойств сустава"""
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
        """Обработка наведения мыши"""
        self.setScale(1.25)
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event) -> None:
        """Обработка ухода мыши"""
        self.setScale(1.0)
        super().hoverLeaveEvent(event)
    
    def mousePressEvent(self, event) -> None:
        """Обработка нажатия мыши"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.setZValue(10)  # Поднимаем на передний план
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event) -> None:
        """Обработка отпускания мыши"""
        self.setZValue(0)
        super().mouseReleaseEvent(event)
    
    def update_from_joint(self, joint: Joint) -> None:
        """Обновляем из объекта Joint"""
        self.joint = joint
        self.setPos(QPointF(joint.x, joint.y))
        self._update_brush()


class BoneItem(QGraphicsLineItem):
    """Графический элемент для кости"""
    
    def __init__(self, from_joint: JointItem, to_joint: JointItem):
        super().__init__()
        
        self.from_joint = from_joint
        self.to_joint = to_joint
        
        self.setPen(QPen(QColor(100, 100, 100, 200), 2))
        self.setZValue(-1)
        
        self._update_line()
    
    def _update_line(self) -> None:
        """Обновляем линию"""
        line = QLineF(
            self.from_joint.pos(),
            self.to_joint.pos()
        )
        self.setLine(line)
    
    def update_positions(self) -> None:
        """Обновляем позиции"""
        self._update_line()


class ContourItem(QGraphicsPathItem):
    """Графический элемент для контура тела"""
    
    def __init__(self, contour: BodyContour):
        super().__init__()
        
        self.contour = contour
        self.setPen(QPen(Colors.ACCENT_GREEN, 2))
        self._update_path()
    
    def _update_path(self) -> None:
        """Обновляем путь"""
        if not self.contour.points:
            return
        
        path = QPainterPath()
        path.moveTo(QPointF(self.contour.points[0].x, self.contour.points[0].y))
        for point in self.contour.points[1:]:
            path.lineTo(QPointF(point.x, point.y))
        
        self.setPath(path)


class SkeletonView(QGraphicsView):
    """Вид для отображения скелета"""
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # Настройки отображения
        self._zoom: float = 1.0
        self._pan: QPointF = QPointF(0, 0)
        
        # Элементы скелета
        self.joint_items: Dict[str, JointItem] = {}
        self.bone_items: List[BoneItem] = []
        self.contour_items: List[ContourItem] = []
        
        # Референсные контуры
        self.reference_contour_items: List[QGraphicsPathItem] = []
        
        # Настройки
        self._joint_radius: float = 8
        self._show_joint_names: bool = True
        
        # Устанавливаем размеры
        self.setMinimumSize(400, 400)
    
    def set_skeleton(self, skeleton: Optional[Skeleton]) -> None:
        """Устанавливаем скелет"""
        self.clear()
        
        if skeleton is None:
            return
        
        # Создаём элементы для суставов
        for joint_id, joint in skeleton.joints.items():
            item = JointItem(joint, self._joint_radius)
            item.setPos(QPointF(joint.x, joint.y))
            self.scene.addItem(item)
            self.joint_items[joint_id] = item
        
        # Создаём элементы для костей
        for bone in skeleton.bones:
            from_joint_item = self.joint_items.get(bone.from_joint_id)
            to_joint_item = self.joint_items.get(bone.to_joint_id)
            
            if from_joint_item and to_joint_item:
                bone_item = BoneItem(from_joint_item, to_joint_item)
                self.scene.addItem(bone_item)
                self.bone_items.append(bone_item)
        
        # Создаём элементы для контуров
        for contour in skeleton.contours:
            item = ContourItem(contour)
            self.scene.addItem(item)
            self.contour_items.append(item)
        
        # Обновляем вид
        self.fit_to_contents()
    
    def clear(self) -> None:
        """Очищаем вид"""
        self.scene.clear()
        self.joint_items.clear()
        self.bone_items.clear()
        self.contour_items.clear()
        self.reference_contour_items.clear()
    
    def set_reference_contours(self, contours: List[Contour]) -> None:
        """Устанавливаем референсные контуры"""
        # Удаляем старые референсные контуры
        for item in self.reference_contour_items:
            self.scene.removeItem(item)
        self.reference_contour_items.clear()
        
        # Добавляем новые референсные контуры
        for contour in contours:
            path = QPainterPath()
            if contour.points:
                path.moveTo(QPointF(contour.points[0][0], contour.points[0][1]))
                for x, y in contour.points[1:]:
                    path.lineTo(QPointF(x, y))
                if contour.is_closed:
                    path.closeSubpath()
            
            item = QGraphicsPathItem(path)
            item.setPen(QPen(QColor(255, 255, 255, 100), 1, Qt.PenStyle.DashLine))
            self.scene.addItem(item)
            self.reference_contour_items.append(item)
    
    def fit_to_contents(self) -> None:
        """Подгоняем вид под содержимое"""
        if self.scene.items():
            self.scene.setSceneRect(self.scene.itemsBoundingRect())
            self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
    
    def set_zoom(self, zoom: float) -> None:
        """Устанавливаем масштаб"""
        self._zoom = zoom
        self.resetTransform()
        self.scale(zoom, zoom)
    
    def set_pan(self, pan: QPointF) -> None:
        """Устанавливаем смещение"""
        self._pan = pan
        self.resetTransform()
        self.translate(pan.x(), pan.y())
        self.scale(self._zoom, self._zoom)
    
    def mousePressEvent(self, event) -> None:
        """Обработка нажатия мыши"""
        if event.button() == Qt.MouseButton.MiddleButton:
            self._last_pan_pos = event.position().toPointF()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event) -> None:
        """Обработка движения мыши"""
        if hasattr(self, '_last_pan_pos'):
            delta = event.position().toPointF() - self._last_pan_pos
            self._pan += delta
            self.set_pan(self._pan)
            self._last_pan_pos = event.position().toPointF()
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event) -> None:
        """Обработка отпускания мыши"""
        if event.button() == Qt.MouseButton.MiddleButton:
            if hasattr(self, '_last_pan_pos'):
                del self._last_pan_pos
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)
    
    def wheelEvent(self, event) -> None:
        """Обработка колесика мыши"""
        zoom_factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        self._zoom *= zoom_factor
        self.set_zoom(self._zoom)
        event.accept()


class SkeletonTab(QWidget):
    """Вкладка для создания и редактирования скелета"""
    
    # Сигналы
    skeleton_loaded = Signal(int)
    skeleton_created = Signal(int)
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        
        self.skeleton = Skeleton()
        self._history: List[Dict[str, Any]] = []
        self._history_index: int = -1
        self._selected_joint: Optional[JointItem] = None
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self) -> None:
        """Настройка пользовательского интерфейса"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        
        # Создаём разделитель
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(8)
        splitter.setStyleSheet("QSplitter::handle { background-color: #1e2833; }")
        
        # Левая панель - Панель инструментов
        left_panel = QFrame()
        left_panel.setStyleSheet("background-color: #10151c; border: 1px solid #1e2833; border-radius: 6px;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(6)
        
        # Группа Скелет
        skeleton_group = QGroupBox("Скелет")
        skeleton_group.setStyleSheet("QGroupBox { border: 1px solid #1e2833; border-radius: 6px; padding: 8px; }")
        skeleton_layout = QVBoxLayout()
        
        # Кнопки создания скелета
        self.btn_t_pose = QPushButton("Создать T-Pose")
        self.btn_t_pose.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 8px 16px; }")
        skeleton_layout.addWidget(self.btn_t_pose)
        
        self.btn_a_pose = QPushButton("Создать A-Pose")
        self.btn_a_pose.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 8px 16px; }")
        skeleton_layout.addWidget(self.btn_a_pose)
        
        self.btn_clear = QPushButton("Очистить скелет")
        self.btn_clear.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 8px 16px; }")
        skeleton_layout.addWidget(self.btn_clear)
        
        skeleton_group.setLayout(skeleton_layout)
        left_layout.addWidget(skeleton_group)
        
        # Группа Параметры
        params_group = QGroupBox("Параметры")
        params_group.setStyleSheet("QGroupBox { border: 1px solid #1e2833; border-radius: 6px; padding: 8px; }")
        params_layout = QVBoxLayout()
        
        # Высота персонажа
        height_layout = QHBoxLayout()
        height_layout.addWidget(QLabel("Высота (см):"))
        self.spin_height = QSpinBox()
        self.spin_height.setRange(100, 300)
        self.spin_height.setValue(180)
        self.spin_height.setStyleSheet("QSpinBox { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 4px 8px; }")
        height_layout.addWidget(self.spin_height)
        params_layout.addLayout(height_layout)
        
        # Зеркальная симметрия
        self.chk_mirror = QCheckBox("Зеркальная симметрия")
        self.chk_mirror.setChecked(True)
        self.chk_mirror.setStyleSheet("QCheckBox { color: #d7e0ea; }")
        params_layout.addWidget(self.chk_mirror)
        
        # Определение пола
        floor_layout = QHBoxLayout()
        floor_layout.addWidget(QLabel("Определять пол по:"))
        self.combo_floor = QComboBox()
        self.combo_floor.addItems(["Toe_L", "Toe_R", "Ankle_L", "Ankle_R"])
        self.combo_floor.setStyleSheet("QComboBox { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 4px 8px; }")
        floor_layout.addWidget(self.combo_floor)
        params_layout.addLayout(floor_layout)
        
        params_group.setLayout(params_layout)
        left_layout.addWidget(params_group)
        
        # Группа Загрузка/Сохранение
        io_group = QGroupBox("Загрузка/Сохранение")
        io_group.setStyleSheet("QGroupBox { border: 1px solid #1e2833; border-radius: 6px; padding: 8px; }")
        io_layout = QVBoxLayout()
        
        self.btn_load = QPushButton("Загрузить скелет...")
        self.btn_load.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 8px 16px; }")
        io_layout.addWidget(self.btn_load)
        
        self.btn_save = QPushButton("Сохранить скелет...")
        self.btn_save.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 8px 16px; }")
        io_layout.addWidget(self.btn_save)
        
        io_group.setLayout(io_layout)
        left_layout.addWidget(io_group)
        
        # Статистика
        self.lbl_stats = QLabel("Суставы: 0 | Кости: 0 | Контуры: 0")
        self.lbl_stats.setStyleSheet("color: #7c8b9d; font: 10px 'Consolas';")
        left_layout.addWidget(self.lbl_stats)
        
        left_layout.addStretch()
        
        # Правая панель - Вид скелета
        right_panel = QFrame()
        right_panel.setStyleSheet("background-color: #10151c; border: 1px solid #1e2833; border-radius: 6px;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(6)
        
        right_layout.addWidget(QLabel("Вид скелета"))
        self.skeleton_view = SkeletonView()
        right_layout.addWidget(self.skeleton_view)
        
        # Добавляем панели в разделитель
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 600])
        
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
    
    def _connect_signals(self) -> None:
        """Подключаем сигналы"""
        self.btn_t_pose.clicked.connect(self.create_preset_t_pose)
        self.btn_a_pose.clicked.connect(self.create_preset_a_pose)
        self.btn_clear.clicked.connect(self.clear_all)
        self.btn_load.clicked.connect(self.on_load_skeleton)
        self.btn_save.clicked.connect(self.on_save_skeleton)
        
        # Обновляем параметры
        self.spin_height.valueChanged.connect(self._update_parameters)
        self.chk_mirror.stateChanged.connect(self._update_parameters)
        self.combo_floor.currentTextChanged.connect(self._update_parameters)
    
    def _update_parameters(self) -> None:
        """Обновляем параметры скелета"""
        self.skeleton.parameters['target_height_cm'] = self.spin_height.value()
        self.skeleton.parameters['mirror_symmetry'] = self.chk_mirror.isChecked()
        self.skeleton.parameters['floor_by_joint'] = self.combo_floor.currentText()
        
        # Обновляем отображение
        self._update_stats()
    
    def _update_stats(self) -> None:
        """Обновляем статистику"""
        self.lbl_stats.setText(
            f"Суставы: {self.skeleton.get_joint_count()} | "
            f"Кости: {self.skeleton.get_bone_count()} | "
            f"Контуры: {len(self.skeleton.contours)}"
        )
    
    def set_reference_contours(self, contours: List[Contour]) -> None:
        """Устанавливаем референсные контуры"""
        self.skeleton_view.set_reference_contours(contours)
    
    def set_skeleton(self, skeleton: Skeleton) -> None:
        """Устанавливаем скелет"""
        self.skeleton = skeleton
        self.skeleton_view.set_skeleton(skeleton)
        self._update_parameters_from_skeleton()
        self._update_stats()
    
    def get_skeleton(self) -> Skeleton:
        """Получаем текущий скелет"""
        return self.skeleton
    
    def _update_parameters_from_skeleton(self) -> None:
        """Обновляем параметры из скелета"""
        self.spin_height.setValue(self.skeleton.parameters.get('target_height_cm', 180))
        self.chk_mirror.setChecked(self.skeleton.parameters.get('mirror_symmetry', True))
        self.combo_floor.setCurrentText(self.skeleton.parameters.get('floor_by_joint', 'Toe_L'))
    
    def create_preset_t_pose(self) -> None:
        """Создаём скелет в T-Pose"""
        self.skeleton.create_preset_t_pose()
        self.skeleton_view.set_skeleton(self.skeleton)
        self._update_stats()
        self._save_state(f"Создан T-Pose скелет")
        self.skeleton_created.emit(self.skeleton.get_joint_count())
    
    def create_preset_a_pose(self) -> None:
        """Создаём скелет в A-Pose"""
        self.skeleton.create_preset_a_pose()
        self.skeleton_view.set_skeleton(self.skeleton)
        self._update_stats()
        self._save_state(f"Создан A-Pose скелет")
        self.skeleton_created.emit(self.skeleton.get_joint_count())
    
    def _save_state(self, description: str = "") -> None:
        """Сохраняем состояние в историю"""
        state = self.skeleton.to_dict()
        # Очищаем кости из истории для экономии места
        state['skeleton3D']['bones'] = []
        
        self._history = self._history[:self._history_index + 1]
        self._history.append(state)
        self._history_index = len(self._history) - 1
    
    def undo(self) -> bool:
        """Отменяем последнее действие"""
        if self._history_index > 0:
            self._history_index -= 1
            self.skeleton.from_dict(self._history[self._history_index])
            self.skeleton_view.set_skeleton(self.skeleton)
            self._update_stats()
            return True
        return False
    
    def redo(self) -> bool:
        """Возвращаем отменённое действие"""
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            self.skeleton.from_dict(self._history[self._history_index])
            self.skeleton_view.set_skeleton(self.skeleton)
            self._update_stats()
            return True
        return False
    
    def load_skeleton_from_file(self, path: str) -> bool:
        """Загружаем скелет из файла"""
        skeleton = Skeleton.load_from_file(path)
        if skeleton:
            self.skeleton = skeleton
            self.skeleton_view.set_skeleton(skeleton)
            self._update_parameters_from_skeleton()
            self._update_stats()
            self._save_state(f"Загружен скелет из {path}")
            self.skeleton_loaded.emit(self.skeleton.get_joint_count())
            return True
        return False
    
    def on_load_skeleton(self) -> None:
        """Обработка загрузки скелета"""
        options = QFileDialog.Options()
        file, _ = QFileDialog.getOpenFileName(
            self, "Загрузить скелет", "",
            "JSON файлы (*.json);;Все файлы (*)",
            options=options
        )
        
        if file:
            self.load_skeleton_from_file(file)
    
    def on_save_skeleton(self) -> None:
        """Обработка сохранения скелета"""
        options = QFileDialog.Options()
        file, _ = QFileDialog.getSaveFileName(
            self, "Сохранить скелет", "",
            "JSON файлы (*.json);;Все файлы (*)",
            options=options
        )
        
        if file:
            self.skeleton.save_to_file(file)
            self.set_status(f"Скелет сохранён в {file}")
    
    def clear_all(self) -> None:
        """Очищаем всё"""
        self.skeleton.clear()
        self.skeleton_view.clear()
        self._history = []
        self._history_index = -1
        self._update_stats()
    
    def set_status(self, message: str) -> None:
        """Устанавливаем сообщение в строке состояния"""
        # Это будет обрабатываться в главном окне
        pass


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    tab = SkeletonTab()
    tab.show()
    sys.exit(app.exec())
