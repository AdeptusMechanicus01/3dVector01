"""
Вкладка векторизатора для преобразования растровых изображений в векторные контуры
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
from PySide6.QtCore import Qt, Signal, QSize, QPoint, QRect, QTimer, QPointF
from PySide6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QPainterPath

from core.vectorizer import Vectorizer, Contour, ROI
from ui.styles import Colors, Fonts


class ImageCanvas(QLabel):
    """Холст для отображения и редактирования изображений"""
    
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
        self._pan: QPointF = QPointF(0, 0)
        
        self.setMouseTracking(True)
    
    def set_image(self, pixmap: QPixmap) -> None:
        """Устанавливаем изображение для отображения"""
        self._image = pixmap
        self._update_display()
    
    def set_contours(self, contours: List[Contour]) -> None:
        """Устанавливаем контуры для отображения"""
        self._contours = contours
        self._update_display()
    
    def set_roi(self, roi: Optional[ROI]) -> None:
        """Устанавливаем область интереса"""
        self._roi = roi
        self._update_display()
    
    def clear(self) -> None:
        """Очищаем холст"""
        self._image = None
        self._contours = []
        self._roi = None
        self._update_display()
    
    def _update_display(self) -> None:
        """Обновляем отображение"""
        if self._image is None:
            self.setPixmap(QPixmap())
            return
        
        # Создаём новое изображение для рисования
        display_pixmap = self._image.copy()
        
        # Рисуем контуры
        if self._contours:
            self._draw_contours(display_pixmap)
        
        # Рисуем ROI
        if self._roi:
            self._draw_roi(display_pixmap)
        
        self.setPixmap(display_pixmap)
    
    def _draw_contours(self, pixmap: QPixmap) -> None:
        """Рисуем контуры на изображении"""
        painter = QPainter(pixmap)
        
        # Кисть для внешних контуров
        pen_external = QPen(Colors.ACCENT_CYAN)
        pen_external.setWidth(2)
        
        # Кисть для внутренних контуров
        pen_internal = QPen(Colors.ACCENT_ORANGE)
        pen_internal.setWidth(1)
        
        for contour in self._contours:
            if len(contour.points) < 2:
                continue
            
            # Преобразуем точки контура в QPointF
            path = QPainterPath()
            path.moveTo(QPointF(contour.points[0][0], contour.points[0][1]))
            for x, y in contour.points[1:]:
                path.lineTo(QPointF(x, y))
            
            if contour.is_closed:
                path.closeSubpath()
            
            # Выбираем кисть в зависимости от типа контура
            if contour.is_external:
                painter.setPen(pen_external)
            else:
                painter.setPen(pen_internal)
            
            painter.drawPath(path)
        
        painter.end()
    
    def _draw_roi(self, pixmap: QPixmap) -> None:
        """Рисуем область интереса"""
        painter = QPainter(pixmap)
        pen = QPen(QColor(255, 255, 255, 180), 1, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        
        if self._roi:
            x, y, w, h = self._roi.x, self._roi.y, self._roi.width, self._roi.height
            painter.drawRect(QRect(int(x), int(y), int(w), int(h)))
        
        painter.end()
    
    def fit_to_viewport(self) -> None:
        """Подгоняем изображение под размер виджета"""
        if self._image is None:
            return
        
        # Получаем размер виджета
        widget_width = self.width()
        widget_height = self.height()
        
        # Получаем размер изображения
        image_width = self._image.width()
        image_height = self._image.height()
        
        # Вычисляем масштаб для подгонки
        scale_w = widget_width / max(image_width, 1)
        scale_h = widget_height / max(image_height, 1)
        self._zoom = min(scale_w, scale_h) * 0.95  # 5% отступ
        
        # Центрируем изображение
        self._pan = QPointF(
            (widget_width - image_width * self._zoom) / 2,
            (widget_height - image_height * self._zoom) / 2
        )
        
        self._update_display()
    
    def mousePressEvent(self, event) -> None:
        """Обработка нажатия мыши"""
        if self._image is None:
            return
        
        if event.button() == Qt.MouseButton.LeftButton:
            self._selection_start = event.position().toPoint()
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event) -> None:
        """Обработка движения мыши"""
        if self._selection_start is not None:
            # Создаём ROI на основе выделения
            current_pos = event.position().toPoint()
            x1 = min(self._selection_start.x(), current_pos.x())
            y1 = min(self._selection_start.y(), current_pos.y())
            x2 = max(self._selection_start.x(), current_pos.x())
            y2 = max(self._selection_start.y(), current_pos.y())
            
            self._roi = ROI(x=x1, y=y1, width=x2-x1, height=y2-y1)
            self._update_display()
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event) -> None:
        """Обработка отпускания мыши"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._selection_start = None
        
        super().mouseReleaseEvent(event)


class ContourPreview(QLabel):
    """Предпросмотр контуров"""
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: #141b24; border: 1px solid #1e2833;")
        
        self._contours: List[Contour] = []
    
    def set_contours(self, contours: List[Contour]) -> None:
        """Устанавливаем контуры"""
        self._contours = contours
        self._update_display()
    
    def clear(self) -> None:
        """Очищаем"""
        self._contours = []
        self.setPixmap(QPixmap())
    
    def _update_display(self) -> None:
        """Обновляем отображение"""
        if not self._contours:
            self.setPixmap(QPixmap())
            return
        
        # Создаём изображение для рисования
        pixmap = QPixmap(400, 400)
        pixmap.fill(QColor(13, 18, 24))
        
        painter = QPainter(pixmap)
        pen = QPen(Colors.ACCENT_CYAN)
        pen.setWidth(2)
        painter.setPen(pen)
        
        # Находим границы контуров
        min_x = min(p[0] for c in self._contours for p in c.points)
        min_y = min(p[1] for c in self._contours for p in c.points)
        max_x = max(p[0] for c in self._contours for p in c.points)
        max_y = max(p[1] for c in self._contours for p in c.points)
        
        width = max_x - min_x
        height = max_y - min_y
        
        if width == 0 or height == 0:
            painter.end()
            self.setPixmap(pixmap)
            return
        
        # Масштабируем и центрируем
        scale = min(350 / width, 350 / height)
        offset_x = (400 - width * scale) / 2 - min_x * scale
        offset_y = (400 - height * scale) / 2 - min_y * scale
        
        for contour in self._contours:
            if len(contour.points) < 2:
                continue
            
            path = QPainterPath()
            first_x = contour.points[0][0] * scale + offset_x
            first_y = contour.points[0][1] * scale + offset_y
            path.moveTo(QPointF(first_x, first_y))
            
            for x, y in contour.points[1:]:
                path.lineTo(QPointF(x * scale + offset_x, y * scale + offset_y))
            
            if contour.is_closed:
                path.closeSubpath()
            
            painter.drawPath(path)
        
        painter.end()
        self.setPixmap(pixmap)


class VectorizerTab(QWidget):
    """Вкладка для векторизации растровых изображений"""
    
    # Сигналы
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
        """Настройка пользовательского интерфейса"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        
        # Создаём разделитель
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(8)
        splitter.setStyleSheet("QSplitter::handle { background-color: #1e2833; }")
        
        # Левая панель - Изображение и элементы управления
        left_panel = QFrame()
        left_panel.setStyleSheet("background-color: #10151c; border: 1px solid #1e2833; border-radius: 6px;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(6)
        
        # Холст для изображения
        self.canvas = ImageCanvas()
        left_layout.addWidget(QLabel("Исходное изображение"))
        left_layout.addWidget(self.canvas)
        
        # Элементы управления ROI
        roi_group = QGroupBox("ROI (Область интереса)")
        roi_group.setStyleSheet("QGroupBox { border: 1px solid #1e2833; border-radius: 6px; padding: 8px; }")
        roi_layout = QHBoxLayout()
        
        self.btn_crop = QPushButton("Обрезать по ROI")
        self.btn_crop.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        self.btn_roi_clear = QPushButton("Очистить ROI")
        self.btn_roi_clear.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        self.btn_fit = QPushButton("Подогнать изображение")
        self.btn_fit.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 6px 12px; }")
        
        roi_layout.addWidget(self.btn_crop)
        roi_layout.addWidget(self.btn_roi_clear)
        roi_layout.addWidget(self.btn_fit)
        roi_group.setLayout(roi_layout)
        left_layout.addWidget(roi_group)
        
        # Элементы управления векторизацией
        vector_group = QGroupBox("Векторизация")
        vector_group.setStyleSheet("QGroupBox { border: 1px solid #1e2833; border-radius: 6px; padding: 8px; }")
        vector_layout = QVBoxLayout()
        
        # Размытие
        blur_layout = QHBoxLayout()
        blur_layout.addWidget(QLabel("Радиус размытия:"))
        self.spin_blur = QSpinBox()
        self.spin_blur.setRange(0, 20)
        self.spin_blur.setValue(3)
        self.spin_blur.setStyleSheet("QSpinBox { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 4px 8px; }")
        blur_layout.addWidget(self.spin_blur)
        vector_layout.addLayout(blur_layout)
        
        # Пороги Кэнни
        canny_layout = QHBoxLayout()
        canny_layout.addWidget(QLabel("Пороги Кэнни:"))
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
        
        # Упрощение
        simplify_layout = QHBoxLayout()
        simplify_layout.addWidget(QLabel("Упрощение:"))
        self.dspin_epsilon = QDoubleSpinBox()
        self.dspin_epsilon.setRange(0.1, 10.0)
        self.dspin_epsilon.setValue(1.0)
        self.dspin_epsilon.setSingleStep(0.1)
        self.dspin_epsilon.setStyleSheet("QDoubleSpinBox { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 4px 8px; }")
        simplify_layout.addWidget(self.dspin_epsilon)
        vector_layout.addLayout(simplify_layout)
        
        # Удаление фона
        self.chk_remove_bg = QCheckBox("Удалить фон")
        self.chk_remove_bg.setChecked(True)
        self.chk_remove_bg.setStyleSheet("QCheckBox { color: #d7e0ea; }")
        vector_layout.addWidget(self.chk_remove_bg)
        
        # Обнаружение внутренних краёв
        self.chk_internal = QCheckBox("Обнаруживать внутренние контуры")
        self.chk_internal.setChecked(True)
        self.chk_internal.setStyleSheet("QCheckBox { color: #d7e0ea; }")
        vector_layout.addWidget(self.chk_internal)
        
        vector_group.setLayout(vector_layout)
        left_layout.addWidget(vector_group)
        
        # Кнопки векторизации
        vector_buttons = QHBoxLayout()
        self.btn_vectorize = QPushButton("Векторизовать")
        self.btn_vectorize.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 8px 16px; }")
        self.btn_clear = QPushButton("Очистить")
        self.btn_clear.setStyleSheet("QPushButton { background-color: #141b24; color: #d7e0ea; border: 1px solid #1e2833; border-radius: 4px; padding: 8px 16px; }")
        vector_buttons.addWidget(self.btn_vectorize)
        vector_buttons.addWidget(self.btn_clear)
        left_layout.addLayout(vector_buttons)
        
        # Статистика
        self.lbl_stats = QLabel("Изображение: нет | Контуры: 0")
        self.lbl_stats.setStyleSheet("color: #7c8b9d; font: 10px 'Consolas';")
        left_layout.addWidget(self.lbl_stats)
        
        # Правая панель - Предпросмотр контуров
        right_panel = QFrame()
        right_panel.setStyleSheet("background-color: #10151c; border: 1px solid #1e2833; border-radius: 6px;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(6)
        
        right_layout.addWidget(QLabel("Предпросмотр контуров"))
        self.contour_preview = ContourPreview()
        right_layout.addWidget(self.contour_preview)
        
        # Добавляем панели в разделитель
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([600, 400])
        
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
    
    def _connect_signals(self) -> None:
        """Подключаем сигналы"""
        self.btn_crop.clicked.connect(self.on_crop)
        self.btn_roi_clear.clicked.connect(self.on_clear_roi)
        self.btn_fit.clicked.connect(self.on_fit_image)
        self.btn_vectorize.clicked.connect(self.on_vectorize)
        self.btn_clear.clicked.connect(self.on_clear)
        
        # Обновляем параметры при изменении
        self.spin_blur.valueChanged.connect(self._update_parameters)
        self.spin_canny1.valueChanged.connect(self._update_parameters)
        self.spin_canny2.valueChanged.connect(self._update_parameters)
        self.dspin_epsilon.valueChanged.connect(self._update_parameters)
        self.chk_remove_bg.stateChanged.connect(self._update_parameters)
        self.chk_internal.stateChanged.connect(self._update_parameters)
    
    def _update_parameters(self) -> None:
        """Обновляем параметры векторизатора"""
        self.vectorizer.set_parameter('blur_radius', self.spin_blur.value())
        self.vectorizer.set_parameter('canny_threshold1', self.spin_canny1.value())
        self.vectorizer.set_parameter('canny_threshold2', self.spin_canny2.value())
        self.vectorizer.set_parameter('simplification_epsilon', self.dspin_epsilon.value())
        self.vectorizer.set_parameter('remove_background', self.chk_remove_bg.isChecked())
        self.vectorizer.set_parameter('detect_internal_edges', self.chk_internal.isChecked())
    
    def _update_stats(self) -> None:
        """Обновляем статистику"""
        img = self.vectorizer.get_image()
        contours = self.vectorizer.get_contours()
        
        img_info = "нет"
        if img is not None:
            img_info = f"{img.shape[1]}x{img.shape[0]}"
        
        self.lbl_stats.setText(f"Изображение: {img_info} | Контуры: {len(contours)}")
    
    def load_images(self, paths: List[str]) -> None:
        """Загружаем изображения"""
        for path in paths:
            self.load_image(path)
    
    def load_image(self, path: str) -> bool:
        """Загружаем изображение из файла"""
        if not os.path.exists(path):
            return False
        
        try:
            if self.vectorizer.load_image(path):
                self._current_image_path = path
                
                # Обновляем отображение
                img = self.vectorizer.get_image()
                if img is not None:
                    self._display_image(img)
                
                # Очищаем контуры
                self.vectorizer.clear_contours()
                self.contour_preview.clear()
                self._update_stats()
                
                # Очищаем историю
                self._history = []
                self._history_index = -1
                
                # Испускаем сигнал
                self.images_loaded.emit(1)
                
                return True
        except Exception as e:
            print(f"Ошибка загрузки изображения: {e}")
            return False
        
        return False
    
    def load_test_images(self, paths: List[str]) -> None:
        """Загружаем тестовые изображения"""
        self.clear_all()
        
        # Фильтруем только изображения
        image_paths = [p for p in paths if p.lower().endswith(('.bmp', '.png', '.jpg', '.jpeg'))]
        
        if image_paths:
            # Загружаем первое изображение
            self.load_image(image_paths[0])
            
            # Если есть другие изображения, сохраняем их в векторизаторе
            if len(image_paths) > 1:
                self.vectorizer._test_images = image_paths[1:]
        
        self._update_stats()
    
    def _display_image(self, img: np.ndarray) -> None:
        """Отображаем изображение на холсте"""
        if img is None:
            self.canvas.clear()
            return
        
        # Преобразуем numpy массив в QImage
        height, width = img.shape[:2]
        
        if len(img.shape) == 3 and img.shape[2] == 3:
            # RGB изображение
            qimg = QImage(img.data, width, height, QImage.Format_RGB888)
        elif len(img.shape) == 3 and img.shape[2] == 4:
            # RGBA изображение
            qimg = QImage(img.data, width, height, QImage.Format_ARGB32)
        else:
            # Черно-белое изображение
            qimg = QImage(img.data, width, height, QImage.Format_Grayscale8)
        
        # Преобразуем в QPixmap
        pixmap = QPixmap.fromImage(qimg)
        
        # Масштабируем под размер холста
        canvas_size = self.canvas.size()
        scaled_pixmap = pixmap.scaled(
            canvas_size.width(), 
            canvas_size.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        self.canvas.set_image(scaled_pixmap)
        self.canvas.fit_to_viewport()
    
    def on_crop(self) -> None:
        """Обработка обрезки по ROI"""
        if self.vectorizer._roi:
            # Применяем ROI
            img = self.vectorizer.get_image()
            if img is not None:
                sy, sx = self.vectorizer._roi.to_slice()
                cropped = img[sy, sx]
                self.vectorizer._image = cropped
                self._display_image(cropped)
                self.vectorizer.clear_roi()
                self.canvas.set_roi(None)
                self._update_stats()
    
    def on_clear_roi(self) -> None:
        """Обработка очистки ROI"""
        self.vectorizer.clear_roi()
        self.canvas.set_roi(None)
    
    def on_fit_image(self) -> None:
        """Обработка подгонки изображения"""
        self.canvas.fit_to_viewport()
    
    def on_vectorize(self) -> None:
        """Обработка векторизации"""
        if self.vectorizer.get_image() is None:
            QMessageBox.warning(self, "Предупреждение", "Сначала загрузите изображение!")
            return
        
        try:
            # Выполняем векторизацию
            contours = self.vectorizer.vectorize()
            
            # Обновляем отображение
            self.canvas.set_contours(contours)
            self.contour_preview.set_contours(contours)
            
            # Сохраняем в историю
            self._save_state(contours)
            
            # Испускаем сигнал
            self.contours_generated.emit(len(contours))
            
            self._update_stats()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка векторизации: {e}")
    
    def on_clear(self) -> None:
        """Обработка очистки"""
        self.vectorizer.clear_contours()
        self.canvas.clear()
        self.contour_preview.clear()
        self._update_stats()
    
    def _save_state(self, contours: List[Contour]) -> None:
        """Сохраняем состояние в историю"""
        # Удаляем состояния после текущего индекса
        self._history = self._history[:self._history_index + 1]
        
        # Сохраняем копию контуров
        contours_copy = [Contour(
            points=c.points.copy(),
            is_closed=c.is_closed,
            is_external=c.is_external,
            color=c.color
        ) for c in contours]
        
        self._history.append(contours_copy)
        self._history_index = len(self._history) - 1
    
    def undo(self) -> None:
        """Отменяем последнее действие"""
        if self._history_index > 0:
            self._history_index -= 1
            contours = self._history[self._history_index]
            self.vectorizer._contours = contours
            self.canvas.set_contours(contours)
            self.contour_preview.set_contours(contours)
            self._update_stats()
    
    def redo(self) -> None:
        """Возвращаем отменённое действие"""
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            contours = self._history[self._history_index]
            self.vectorizer._contours = contours
            self.canvas.set_contours(contours)
            self.contour_preview.set_contours(contours)
            self._update_stats()
    
    def get_contours(self) -> List[Contour]:
        """Получаем текущие контуры"""
        return self.vectorizer.get_contours()
    
    def clear_all(self) -> None:
        """Очищаем всё"""
        self.vectorizer.clear_contours()
        self.vectorizer.clear_roi()
        self.canvas.clear()
        self.contour_preview.clear()
        self._current_image_path = None
        self._history = []
        self._history_index = -1
        self._update_stats()


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    tab = VectorizerTab()
    tab.show()
    sys.exit(app.exec())
