"""
Модуль векторизации для преобразования растровых изображений в векторные контуры
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
from PIL import Image
import io

# Пробуем импортировать OpenCV
try:
    import cv2
    CV_AVAILABLE = True
except ImportError:
    CV_AVAILABLE = False
    print("Warning: OpenCV not available, using PIL fallback")

# Пробуем импортировать scipy
try:
    from scipy import ndimage
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("Warning: scipy not available")

# Пробуем импортировать skimage
try:
    from skimage.measure import find_contours, approximate_polygon
    SKIMAGE_AVAILABLE = True
except ImportError:
    SKIMAGE_AVAILABLE = False
    print("Warning: scikit-image not available")


@dataclass
class ROI:
    """Регион интереса (область выделения)"""
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0
    
    def to_dict(self) -> Dict[str, float]:
        return {'x': self.x, 'y': self.y, 'width': self.width, 'height': self.height}
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'ROI':
        return cls(
            x=data.get('x', 0),
            y=data.get('y', 0),
            width=data.get('width', 0),
            height=data.get('height', 0)
        )


@dataclass
class Contour:
    """Представляет векторный контур с точками"""
    points: List[Tuple[float, float]]  # Список точек (x, y)
    is_closed: bool = True
    is_external: bool = True
    color: Tuple[int, int, int] = (255, 255, 255)
    
    def to_svg_path(self) -> str:
        """Преобразовать контур в SVG путь"""
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
        """Преобразовать в numpy массив формы (N, 2)"""
        return np.array(self.points, dtype=np.float32)
    
    def simplify(self, epsilon: float = 1.0) -> 'Contour':
        """Упростить контур с использованием алгоритма Рамера-Дугласа-Пекера"""
        if len(self.points) < 3:
            return self
        
        if SKIMAGE_AVAILABLE:
            pts = self.to_numpy()
            simplified = approximate_polygon(pts, tolerance=epsilon)
            return Contour(
                points=[(float(p[0]), float(p[1])) for p in simplified],
                is_closed=self.is_closed,
                is_external=self.is_external,
                color=self.color
            )
        else:
            # Фоллбэк: удаление каждых N точек
            simplified = [self.points[i] for i in range(0, len(self.points), max(1, int(epsilon)))]
            return Contour(
                points=simplified,
                is_closed=self.is_closed,
                is_external=self.is_external,
                color=self.color
            )
    
    def translate(self, dx: float, dy: float) -> 'Contour':
        """Сдвинуть контур на dx, dy"""
        return Contour(
            points=[(x + dx, y + dy) for x, y in self.points],
            is_closed=self.is_closed,
            is_external=self.is_external,
            color=self.color
        )
    
    def scale(self, sx: float, sy: float) -> 'Contour':
        """Масштабировать контур"""
        return Contour(
            points=[(x * sx, y * sy) for x, y in self.points],
            is_closed=self.is_closed,
            is_external=self.is_external,
            color=self.color
        )
    
    def get_bounds(self) -> Tuple[float, float, float, float]:
        """Получить границы контура (x_min, y_min, x_max, y_max)"""
        if len(self.points) == 0:
            return (0, 0, 0, 0)
        
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        return (min(xs), min(ys), max(xs), max(ys))


class Vectorizer:
    """
    Основной класс для векторизации растровых изображений
    """
    
    def __init__(self):
        self.contours: List[Contour] = []
        self.roi: Optional[ROI] = None
        self.image: Optional[np.ndarray] = None
        self.image_path: Optional[Path] = None
    
    def load_image(self, path: str) -> bool:
        """
        Загрузить изображение из файла
        
        Args:
            path: Путь к файлу изображения
            
        Returns:
            True если загрузка успешна
        """
        try:
            self.image_path = Path(path)
            
            # Пробуем загрузить через PIL
            pil_image = Image.open(path)
            
            # Конвертируем в grayscale numpy массив
            if pil_image.mode == 'RGB':
                self.image = np.array(pil_image.convert('L'))
            elif pil_image.mode == 'RGBA':
                self.image = np.array(pil_image.convert('L'))
            else:
                self.image = np.array(pil_image)
            
            # Инвертируем если нужно (белый фон -> черный)
            # Проверяем какой цвет преобладает в углах
            corners = [
                self.image[0, 0],
                self.image[0, -1],
                self.image[-1, 0],
                self.image[-1, -1]
            ]
            avg_corner = np.mean(corners)
            
            # Если углы светлые, инвертируем
            if avg_corner > 128:
                self.image = 255 - self.image
            
            self.contours = []
            return True
            
        except Exception as e:
            print(f"Ошибка загрузки изображения: {e}")
            return False
    
    def set_roi(self, roi: ROI) -> None:
        """Установить регион интереса"""
        self.roi = roi
    
    def clear_roi(self) -> None:
        """Очистить регион интереса"""
        self.roi = None
    
    def vectorize(self, threshold: int = 128, simplify_epsilon: float = 1.0, 
                  remove_background: bool = True) -> List[Contour]:
        """
        Векторизовать текущее изображение
        
        Args:
            threshold: Порог бинаризации (0-255)
            simplify_epsilon: Параметр упрощения контуров
            remove_background: Удалять ли фон
            
        Returns:
            Список контуров
        """
        if self.image is None:
            return []
        
        # Применяем ROI если установлен
        if self.roi:
            img = self._apply_roi(self.image, self.roi)
        else:
            img = self.image.copy()
        
        # Бинаризация
        binary = self._binarize(img, threshold)
        
        # Удаление фона
        if remove_background:
            binary = self._remove_background(binary)
        
        # Поиск контуров
        contours = self._find_contours(binary)
        
        # Упрощение контуров
        simplified_contours = []
        for contour in contours:
            simplified = contour.simplify(simplify_epsilon)
            if len(simplified.points) >= 3:
                simplified_contours.append(simplified)
        
        # Разделение на внешние и внутренние
        self.contours = self._classify_contours(simplified_contours)
        
        return self.contours
    
    def _apply_roi(self, img: np.ndarray, roi: ROI) -> np.ndarray:
        """Применить ROI к изображению"""
        x, y, w, h = int(roi.x), int(roi.y), int(roi.width), int(roi.height)
        
        # Проверяем границы
        x = max(0, x)
        y = max(0, y)
        w = min(w, img.shape[1] - x)
        h = min(h, img.shape[0] - y)
        
        if w <= 0 or h <= 0:
            return img
        
        return img[y:y+h, x:x+w]
    
    def _binarize(self, img: np.ndarray, threshold: int = 128) -> np.ndarray:
        """Бинаризовать изображение"""
        if CV_AVAILABLE:
            _, binary = cv2.threshold(img, threshold, 255, cv2.THRESH_BINARY)
        else:
            binary = (img > threshold).astype(np.uint8) * 255
        
        return binary
    
    def _remove_background(self, binary: np.ndarray) -> np.ndarray:
        """Удалить фон (самую большую связную область)"""
        if CV_AVAILABLE:
            # Находим все контуры
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if len(contours) == 0:
                return binary
            
            # Находим самую большую область (фон)
            areas = [cv2.contourArea(c) for c in contours]
            largest_idx = np.argmax(areas)
            
            # Создаем маску без фона
            mask = np.zeros_like(binary)
            for i, contour in enumerate(contours):
                if i != largest_idx:
                    cv2.drawContours(mask, [contour], -1, 255, -1)
            
            return mask
        else:
            # Фоллбэк: инвертируем если центр темный
            center = binary[binary.shape[0]//2, binary.shape[1]//2]
            if center == 0:
                return binary
            else:
                return 255 - binary
    
    def _find_contours(self, binary: np.ndarray) -> List[Contour]:
        """Найти контуры на бинарном изображении"""
        contours = []
        
        if CV_AVAILABLE:
            # Находим контуры
            cv_contours, hierarchy = cv2.findContours(
                binary, 
                cv2.RETR_TREE, 
                cv2.CHAIN_APPROX_SIMPLE
            )
            
            # Конвертируем в наши контуры
            for i, contour in enumerate(cv_contours):
                # Определяем внешний или внутренний
                is_external = hierarchy[0][i][3] == -1 if len(hierarchy) > 0 else True
                
                points = [(float(p[0][0]), float(p[0][1])) for p in contour]
                
                new_contour = Contour(
                    points=points,
                    is_closed=True,
                    is_external=is_external,
                    color=(255, 255, 255) if is_external else (255, 165, 0)
                )
                contours.append(new_contour)
        elif SKIMAGE_AVAILABLE:
            # Используем skimage
            labeled = ndimage.label(binary > 0)[0]
            slices = ndimage.find_objects(labeled)
            
            for i, slice_tuple in enumerate(slices):
                # Извлекаем регион
                region = binary[slice_tuple]
                
                # Проверяем размер региона
                if region.shape[0] < 2 or region.shape[1] < 2:
                    continue
                
                try:
                    # Находим контуры
                    sk_contours = find_contours(region, level=0.5)
                    
                    for contour in sk_contours:
                        # Конвертируем координаты обратно
                        points = []
                        for j, (y, x) in enumerate(contour):
                            # Добавляем смещение от среза
                            actual_y = y + slice_tuple[0].start if len(slice_tuple) > 0 else y
                            actual_x = x + slice_tuple[1].start if len(slice_tuple) > 1 else x
                            points.append((float(actual_x), float(actual_y)))
                        
                        if len(points) >= 3:
                            contours.append(Contour(
                                points=points,
                                is_closed=True,
                                is_external=True,
                                color=(255, 255, 255)
                            ))
                except Exception as e:
                    print(f"Error finding contours in region: {e}")
                    continue
        else:
            # Фоллбэк: простой алгоритм
            contours = self._find_contours_fallback(binary)
        
        return contours
    
    def _find_contours_fallback(self, binary: np.ndarray) -> List[Contour]:
        """Простой фоллбэк для поиска контуров"""
        # Ищем границы
        edges = np.zeros_like(binary)
        h, w = binary.shape
        
        for y in range(1, h-1):
            for x in range(1, w-1):
                if binary[y, x] != binary[y-1, x] or \
                   binary[y, x] != binary[y+1, x] or \
                   binary[y, x] != binary[y, x-1] or \
                   binary[y, x] != binary[y, x+1]:
                    edges[y, x] = 255
        
        # Собираем точки в контуры
        points = np.argwhere(edges > 0)
        
        if len(points) == 0:
            return []
        
        # Сортируем по углу от центра
        center = np.mean(points, axis=0)
        angles = np.arctan2(points[:, 1] - center[1], points[:, 0] - center[0])
        sorted_indices = np.argsort(angles)
        sorted_points = points[sorted_indices]
        
        contour_points = [(float(p[1]), float(p[0])) for p in sorted_points]
        
        return [Contour(
            points=contour_points,
            is_closed=True,
            is_external=True,
            color=(255, 255, 255)
        )]
    
    def _classify_contours(self, contours: List[Contour]) -> List[Contour]:
        """Классифицировать контуры на внешние и внутренние"""
        if len(contours) <= 1:
            for c in contours:
                c.is_external = True
            return contours
        
        # Сортируем по площади (внешние обычно больше)
        def contour_area(c: Contour) -> float:
            if len(c.points) < 3:
                return 0
            # Простой расчет площади по формуле шнурка
            area = 0
            for i in range(len(c.points)):
                x1, y1 = c.points[i]
                x2, y2 = c.points[(i+1) % len(c.points)]
                area += (x1 * y2 - x2 * y1)
            return abs(area) / 2
        
        sorted_contours = sorted(contours, key=contour_area, reverse=True)
        
        # Самый большой - внешний
        if sorted_contours:
            sorted_contours[0].is_external = True
            sorted_contours[0].color = (255, 255, 255)
        
        # Остальные - внутренние
        for c in sorted_contours[1:]:
            c.is_external = False
            c.color = (255, 165, 0)
        
        return sorted_contours
    
    def get_external_contours(self) -> List[Contour]:
        """Получить только внешние контуры"""
        return [c for c in self.contours if c.is_external]
    
    def get_internal_contours(self) -> List[Contour]:
        """Получить только внутренние контуры"""
        return [c for c in self.contours if not c.is_external]
    
    def get_silhouette(self) -> Optional[Contour]:
        """Получить основной силуэт (самый большой внешний контур)"""
        external = self.get_external_contours()
        if not external:
            return None
        
        # Сортируем по количеству точек
        external.sort(key=lambda c: len(c.points), reverse=True)
        return external[0]
    
    def clear(self) -> None:
        """Очистить все данные"""
        self.contours = []
        self.roi = None
        self.image = None
        self.image_path = None
    
    def clear_contours(self) -> None:
        """Очистить только контуры"""
        self.contours = []
