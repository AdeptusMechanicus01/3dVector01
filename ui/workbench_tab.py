"""
Вкладка 3D верстака для генерации и скульптинга 3D сеток
"""

import os
import numpy as np
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
    QComboBox, QSlider, QSplitter, QFileDialog, QMessageBox,
    QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal, QSize, QPoint, QTimer
from PySide6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QBrush

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
    """3D вьюпорт на основе PyVista"""
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        
        self._plotter: Optional[pv.Plotter] = None
        self._mesh: Optional[pv.PolyData] = None
        self._reference_slides: List[ReferenceSlide] = []
        self._show_grid: bool = True
        self._show_axis: bool = True
        
        # Мышиное взаимодействие
        self._last_mouse_pos: Optional[QPoint] = None
        self._is_dragging: bool = False
        self._is_rotating: bool = False
        
        # Инициализация
        self._init_viewport()
    
    def _init_viewport(self) -> None:
        """Инициализация 3D вьюпорта"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        if not PV_AVAILABLE:
            # Создаём запасной вариант
            self.lbl_fallback = QLabel("PyVista недоступен. Установите: pip install pyvista pyvistaqt")
            self.lbl_fallback.setStyleSheet("color: #f87171; font: 14px 'System';")
            layout.addWidget(self.lbl_fallback)
            self.setLayout(layout)
            self.setMinimumSize(400, 400)
            return
        
        try:
            # Создаём PyVista plotter
            self._plotter = pv.Plotter()
            
            # Настраиваем plotter
            self._plotter.set_background(Colors.VIEWPORT_BG)
            
            # Добавляем сетку
            if self._show_grid:
                self._add_grid()
            
            # Добавляем оси
            if self._show_axis:
                self._add_axis()
            
            # Настраиваем камеру
            self._plotter.camera_position = 'xy'
            self._plotter.camera.zoom(1.5)
            
            # Показываем в виджете
            self._plotter.show(auto_close=False)
            
            # Добавляем в компоновку
            layout.addWidget(self._plotter.ren_win)
            self.setLayout(layout)
            
            # Устанавливаем минимальный размер
            self.setMinimumSize(400, 400)
        except Exception as e:
            # Запасной вариант если PyVista не работает
            self.lbl_fallback = QLabel(f"Ошибка PyVista: {str(e)}")
            self.lbl_fallback.setStyleSheet("color: #f87171; font: 14px 'System';")
            layout.addWidget(self.lbl_fallback)
            self.setLayout(layout)
            self.setMinimumSize(400, 400)
    
    def _add_grid(self) -> None:
        """Добавляем сетку в вьюпорт"""
        if self._plotter is None:
            return
        
        # Создаём сетку
        grid = pv.Plane(center=(0, 0, 0), direction=(0, 0, 1), i_size=10, j_size=10)
        grid_lines = grid.lines('x').lines('y')
        self._plotter.add_mesh(
            grid_lines,
            color=Colors.GRID_COLOR,
            line_width=1,
            opacity=0.5
        )
    
    def _add_axis(self) -> None:
        """Добавляем координатные оси"""
        if self._plotter is None:
            return
        
        # Добавляем оси
        self._plotter.show_axes(
            xlabel='X', ylabel='Y', zlabel='Z',
            x_color=Colors.AXIS_X, y_color=Colors.AXIS_Y, z_color=Colors.AXIS_Z,
            xtitle='X', ytitle='Y', ztitle='Z'
        )
    
    def set_mesh(self, mesh: Optional[Mesh]) -> None:
        """Устанавливаем сетку для отображения"""
        if not PV_AVAILABLE:
            return
        
        if self._plotter is None:
            self._init_viewport()
            if self._plotter is None:
                return
        
        # Удаляем старую сетку
        if self._mesh is not None:
            self._plotter.remove_actor(self._mesh)
        
        if mesh is not None:
            try:
                # Конвертируем в PyVista
                self._mesh = mesh.to_pyvista()
                
                # Добавляем в plotter
                self._plotter.add_mesh(
                    self._mesh,
                    color='white',
                    show_edges=True,
                    edge_color=Colors.BORDER_LIGHT,
                    opacity=1.0
                )
            except Exception as e:
                print(f"Ошибка отображения сетки: {e}")
                return
        else:
            self._mesh = None
        
        # Сбрасываем камеру
        self._plotter.reset_camera()
        self._plotter.camera.zoom(1.5)
        
        # Рендерим
        self._plotter.render()
    
    def add_reference_slide(self, slide: ReferenceSlide) -> None:
        """Добавляем референсный слайд"""
        if not PV_AVAILABLE or self._plotter is None:
            return
        
        self._reference_slides.append(slide)
        self._update_reference_slides()
    
    def remove_reference_slide(self, index: int) -> None:
        """Удаляем референсный слайд"""
        if 0 <= index < len(self._reference_slides):
            self._reference_slides.pop(index)
            self._update_reference_slides()
    
    def clear_reference_slides(self) -> None:
        """Очищаем все референсные слайды"""
        self._reference_slides = []
        self._update_reference_slides()
    
    def _update_reference_slides(self) -> None:
        """Обновляем отображение референсных слайдов"""
        if not PV_AVAILABLE or self._plotter is None:
            return
        
        # Удаляем все акторы слайдов
        for actor_name in [f"slide_{i}" for i in range(len(self._reference_slides) + 10)]:
            try:
                self._plotter.remove_actor(actor_name)
            except:
                pass
        
        # Добавляем слайды
        for i, slide in enumerate(self._reference_slides):
            if slide.image is not None and len(slide.image.shape) >= 2:
                h, w = slide.image.shape[:2]
                plane = pv.Plane(center=slide.position, direction=(0, 0, 1), i_size=w/100, j_size=h/100)
                self._plotter.add_mesh(plane, name=f"slide_{i}", color='white', opacity=slide.opacity)
        
        self._plotter.render()
    
    def set_show_grid(self, show: bool) -> None:
        """Показать/скрыть сетку"""
        self._show_grid = show
        # Примечание: сетка добавляется при инициализации, нужно пересоздать вьюпорт
    
    def set_show_axis(self, show: bool) -> None:
        """Показать/скрыть оси"""
        self._show_axis = show
        # Примечание: оси добавляются при инициализации, нужно пересоздать вьюпорт
    
    def reset_camera(self) -> None:
        """Сбросить камеру"""
        if self._plotter is not None:
            self._plotter.reset_camera()
            self._plotter.camera_position = 'xy'
            self._plotter.camera.zoom(1.5)
            self._plotter.render()
    
    def get_camera_position(self) -> Optional[Tuple[float, float, float]]:
        """Получить текущую позицию камеры"""
        if self._plotter is not None:
            return self._plotter.camera.position
        return None
    
    def set_camera_position(self, position: Tuple[float, float, float]) -> None:
        """Установить позицию камеры"""
        if self._plotter is not None:
            self._plotter.camera.position = position
            self._plotter.render()
    
    def mousePressEvent(self, event) -> None:
        """Обработка нажатия мыши"""
        if not PV_AVAILABLE or self._plotter is None:
            return
        
        self._last_mouse_pos = event.position().toPoint()
        self._is_dragging = True
        
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_rotating = True
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event) -> None:
        """Обработка движения мыши"""
        if not PV_AVAILABLE or self._plotter is None or not self._is_dragging:
            return
        
        current_pos = event.position().toPoint()
        delta = current_pos - self._last_mouse_pos
        
        if self._is_rotating:
            # Вращаем камеру
            self._plotter.camera.azimuth = delta.x() * 0.5
            self._plotter.camera.elevation = delta.y() * 0.5
            self._plotter.render()
        
        self._last_mouse_pos = current_pos
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event) -> None:
        """Обработка отпускания мыши"""
        self._is_dragging = False
        self._is_rotating = False
        super().mouseReleaseEvent(event)


class WorkbenchTab(QWidget):
    """Вкладка 3D верстака"""
    
    # Сигналы
    mesh_ready = Signal(int, int)
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        
        self._mesh: Optional[Mesh] = None
        self._skeleton: Optional[Skeleton] = None
        self._mesh_generator = MeshGenerator()
        self._sculpting_tools = SculptingTools()
        self._exporter = GLBExporter()
        
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
        
        # Левая панель - 3D вьюпорт
        left_panel = QFrame()
        left_panel.setStyleSheet("background-color: #10151c; border: 1px solid #1e2833; border-radius: 6px;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(6)
        
        left_layout.addWidget(QLabel("3D Вьюпорт"))
        self.viewport = Viewport3D()
        left_layout.addWidget(self.viewport)
        
        # Группа Генерация
        gen_group = QGroupBox("Генерация")
        gen_group.setStyleSheet("QGroupBox { border: 1px solid #1e2833; border-radius: 6px; padding: 8px; }")
        gen_layout = QHBoxLayout()
        
        self.btn_generate = QPushButton("Генерировать сетку")
        self.btn_generate.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 8px 16px; }")
        gen_layout.addWidget(self.btn_generate)
        
        self.btn_clear_mesh = QPushButton("Очистить сетку")
        self.btn_clear_mesh.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 8px 16px; }")
        gen_layout.addWidget(self.btn_clear_mesh)
        
        gen_group.setLayout(gen_layout)
        left_layout.addWidget(gen_group)
        
        # Группа Инструменты скульптинга
        sculpt_group = QGroupBox("Скульптинг")
        sculpt_group.setStyleSheet("QGroupBox { border: 1px solid #1e2833; border-radius: 6px; padding: 8px; }")
        sculpt_layout = QVBoxLayout()
        
        # Инструменты
        tool_layout = QHBoxLayout()
        tool_layout.addWidget(QLabel("Инструмент:"))
        self.combo_tool = QComboBox()
        self.combo_tool.addItems(["Inflate", "Grab", "Smooth"])
        self.combo_tool.setStyleSheet("QComboBox { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 4px 8px; }")
        tool_layout.addWidget(self.combo_tool)
        sculpt_layout.addLayout(tool_layout)
        
        # Радиус кисти
        radius_layout = QHBoxLayout()
        radius_layout.addWidget(QLabel("Радиус кисти:"))
        self.dspin_radius = QDoubleSpinBox()
        self.dspin_radius.setRange(0.01, 5.0)
        self.dspin_radius.setValue(0.5)
        self.dspin_radius.setSingleStep(0.05)
        self.dspin_radius.setStyleSheet("QDoubleSpinBox { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 4px 8px; }")
        radius_layout.addWidget(self.dspin_radius)
        sculpt_layout.addLayout(radius_layout)
        
        # Сила
        strength_layout = QHBoxLayout()
        strength_layout.addWidget(QLabel("Сила:"))
        self.dspin_strength = QDoubleSpinBox()
        self.dspin_strength.setRange(0.01, 1.0)
        self.dspin_strength.setValue(0.5)
        self.dspin_strength.setSingleStep(0.05)
        self.dspin_strength.setStyleSheet("QDoubleSpinBox { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 4px 8px; }")
        strength_layout.addWidget(self.dspin_strength)
        sculpt_layout.addLayout(strength_layout)
        
        # Зеркало по X
        self.chk_x_mirror = QCheckBox("Зеркало по X")
        self.chk_x_mirror.setChecked(False)
        self.chk_x_mirror.setStyleSheet("QCheckBox { color: #d7e0ea; }")
        sculpt_layout.addWidget(self.chk_x_mirror)
        
        # Кнопки скульптинга
        sculpt_buttons = QHBoxLayout()
        self.btn_undo_sculpt = QPushButton("Отменить")
        self.btn_undo_sculpt.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 8px 16px; }")
        self.btn_redo_sculpt = QPushButton("Вернуть")
        self.btn_redo_sculpt.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 8px 16px; }")
        sculpt_buttons.addWidget(self.btn_undo_sculpt)
        sculpt_buttons.addWidget(self.btn_redo_sculpt)
        sculpt_layout.addLayout(sculpt_buttons)
        
        sculpt_group.setLayout(sculpt_layout)
        left_layout.addWidget(sculpt_group)
        
        # Статистика
        self.lbl_stats = QLabel("Сетка: нет | Вершины: 0 | Грани: 0")
        self.lbl_stats.setStyleSheet("color: #7c8b9d; font: 10px 'Consolas';")
        left_layout.addWidget(self.lbl_stats)
        
        # Правая панель - Параметры
        right_panel = QFrame()
        right_panel.setStyleSheet("background-color: #10151c; border: 1px solid #1e2833; border-radius: 6px;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(6)
        
        right_layout.addWidget(QLabel("Параметры генерации"))
        
        # Параметры SDF
        sdf_group = QGroupBox("SDF Генерация")
        sdf_group.setStyleSheet("QGroupBox { border: 1px solid #1e2833; border-radius: 6px; padding: 8px; }")
        sdf_layout = QVBoxLayout()
        
        grid_layout = QHBoxLayout()
        grid_layout.addWidget(QLabel("Размер сетки:"))
        self.spin_grid_size = QSpinBox()
        self.spin_grid_size.setRange(32, 256)
        self.spin_grid_size.setValue(128)
        self.spin_grid_size.setStyleSheet("QSpinBox { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 4px 8px; }")
        grid_layout.addWidget(self.spin_grid_size)
        sdf_layout.addLayout(grid_layout)
        
        sdf_group.setLayout(sdf_layout)
        right_layout.addWidget(sdf_group)
        
        # Экспорт
        export_group = QGroupBox("Экспорт")
        export_group.setStyleSheet("QGroupBox { border: 1px solid #1e2833; border-radius: 6px; padding: 8px; }")
        export_layout = QVBoxLayout()
        
        self.btn_export_glb = QPushButton("Экспорт в GLB")
        self.btn_export_glb.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 8px 16px; }")
        export_layout.addWidget(self.btn_export_glb)
        
        export_group.setLayout(export_layout)
        right_layout.addWidget(export_group)
        
        right_layout.addStretch()
        
        # Добавляем панели в разделитель
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([600, 300])
        
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
    
    def _connect_signals(self) -> None:
        """Подключаем сигналы"""
        self.btn_generate.clicked.connect(self.on_generate_mesh)
        self.btn_clear_mesh.clicked.connect(self.on_clear_mesh)
        self.btn_export_glb.clicked.connect(self.on_export_glb)
        self.btn_undo_sculpt.clicked.connect(self.on_undo_sculpt)
        self.btn_redo_sculpt.clicked.connect(self.on_redo_sculpt)
        
        # Обновляем параметры
        self.combo_tool.currentTextChanged.connect(self._update_sculpt_settings)
        self.dspin_radius.valueChanged.connect(self._update_sculpt_settings)
        self.dspin_strength.valueChanged.connect(self._update_sculpt_settings)
        self.chk_x_mirror.stateChanged.connect(self._update_sculpt_settings)
    
    def _update_sculpt_settings(self) -> None:
        """Обновляем настройки скульптинга"""
        tool_map = {
            "Inflate": SculptTool.INFLATE,
            "Grab": SculptTool.GRAB,
            "Smooth": SculptTool.SMOOTH
        }
        
        brush = BrushSettings(
            radius=self.dspin_radius.value(),
            strength=self.dspin_strength.value(),
            tool=tool_map.get(self.combo_tool.currentText(), SculptTool.INFLATE),
            use_x_mirror=self.chk_x_mirror.isChecked()
        )
        
        self._sculpting_tools.set_brush_settings(brush)
    
    def set_skeleton(self, skeleton: Skeleton) -> None:
        """Устанавливаем скелет"""
        self._skeleton = skeleton
        self._generate_mesh_from_skeleton()
    
    def get_current_mesh(self) -> Optional[Mesh]:
        """Получаем текущую сетку"""
        return self._mesh
    
    def _generate_mesh_from_skeleton(self) -> None:
        """Генерируем сетку из скелета"""
        if self._skeleton is None:
            return
        
        try:
            # Пока простая генерация - создаём капсулы для каждой кости
            mesh = self._mesh_generator.generate_skeleton_mesh(
                self._skeleton.joints,
                [b.to_dict() for b in self._skeleton.bones]
            )
            
            if mesh:
                self._mesh = mesh
                self.viewport.set_mesh(mesh)
                self._update_stats()
                self.mesh_ready.emit(len(mesh.vertices), len(mesh.faces))
        except Exception as e:
            print(f"Ошибка генерации сетки из скелета: {e}")
    
    def on_generate_mesh(self) -> None:
        """Обработка генерации сетки"""
        if self._skeleton is None:
            QMessageBox.warning(self, "Предупреждение", "Сначала загрузите скелет!")
            return
        
        self._generate_mesh_from_skeleton()
    
    def on_clear_mesh(self) -> None:
        """Обработка очистки сетки"""
        self._mesh = None
        self.viewport.set_mesh(None)
        self._update_stats()
    
    def on_export_glb(self) -> None:
        """Обработка экспорта в GLB"""
        if self._mesh is None:
            QMessageBox.warning(self, "Предупреждение", "Сначала сгенерируйте сетку!")
            return
        
        options = QFileDialog.Options()
        file, _ = QFileDialog.getSaveFileName(
            self, "Экспорт в GLB", "",
            "GLB файлы (*.glb);;Все файлы (*)",
            options=options
        )
        
        if file:
            try:
                # Масштабируем в метры (180 см = 1.8 м)
                scale = 1.8 / self._skeleton.calculate_height() if self._skeleton else 1.0
                success = self._mesh.save_to_glb(file, scale=scale)
                
                if success:
                    QMessageBox.information(self, "Успех", f"Сетка экспортирована в {file}")
                else:
                    QMessageBox.critical(self, "Ошибка", "Не удалось экспортировать сетку")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка экспорта: {e}")
    
    def export_to_glb(self, path: str) -> bool:
        """Экспорт в GLB"""
        if self._mesh is None:
            return False
        
        try:
            scale = 1.8 / self._skeleton.calculate_height() if self._skeleton else 1.0
            return self._mesh.save_to_glb(path, scale=scale)
        except Exception as e:
            print(f"Ошибка экспорта в GLB: {e}")
            return False
    
    def export_to_obj(self, path: str) -> bool:
        """Экспорт в OBJ"""
        if self._mesh is None:
            return False
        
        try:
            # Используем trimesh для экспорта в OBJ
            import trimesh
            tm = self._mesh.to_trimesh()
            scale = 1.8 / self._skeleton.calculate_height() if self._skeleton else 1.0
            tm.vertices *= scale
            tm.export(path, file_type='obj')
            return True
        except Exception as e:
            print(f"Ошибка экспорта в OBJ: {e}")
            return False
    
    def on_undo_sculpt(self) -> None:
        """Обработка отмены скульптинга"""
        if self._sculpting_tools.undo():
            self._update_mesh_from_sculpting()
    
    def on_redo_sculpt(self) -> None:
        """Обработка возврата скульптинга"""
        if self._sculpting_tools.redo():
            self._update_mesh_from_sculpting()
    
    def _update_mesh_from_sculpting(self) -> None:
        """Обновляем сетку из инструментов скульптинга"""
        sculpted_mesh = self._sculpting_tools.get_mesh()
        if sculpted_mesh:
            self._mesh = Mesh(
                vertices=sculpted_mesh.vertices,
                faces=sculpted_mesh.faces,
                normals=sculpted_mesh.vertex_normals
            )
            self.viewport.set_mesh(self._mesh)
            self._update_stats()
    
    def set_show_grid(self, show: bool) -> None:
        """Показать/скрыть сетку"""
        self.viewport.set_show_grid(show)
    
    def set_show_axis(self, show: bool) -> None:
        """Показать/скрыть оси"""
        self.viewport.set_show_axis(show)
    
    def reset_camera(self) -> None:
        """Сбросить камеру"""
        self.viewport.reset_camera()
    
    def _update_stats(self) -> None:
        """Обновляем статистику"""
        if self._mesh:
            self.lbl_stats.setText(
                f"Сетка: да | Вершины: {len(self._mesh.vertices)} | Грани: {len(self._mesh.faces)}"
            )
        else:
            self.lbl_stats.setText("Сетка: нет | Вершины: 0 | Грани: 0")
    
    def undo(self) -> None:
        """Отменить последнее действие"""
        self.on_undo_sculpt()
    
    def redo(self) -> None:
        """Вернуть отменённое действие"""
        self.on_redo_sculpt()
    
    def clear_all(self) -> None:
        """Очистить всё"""
        self._mesh = None
        self._skeleton = None
        self.viewport.set_mesh(None)
        self.viewport.clear_reference_slides()
        self._update_stats()


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    tab = WorkbenchTab()
    tab.show()
    sys.exit(app.exec())
