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
class Contour:
    """Представляет векторный контур с точками и метаданными"""
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
            # Фоллбэк: упрощение путём удаления каждых вторых точек
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
    
    def get_bounding_box(self) -> Tuple[float, float, float, float]:
        """Получить ограничивающий прямоугольник"""
        if not self.points:
            return (0, 0, 0, 0)
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        return (min(xs), min(ys), max(xs), max(ys))


@dataclass
class ROI:
    """Область интереса для обрезки"""
    x: float
    y: float
    width: float
    height: float
    
    def to_slice(self) -> Tuple[slice, slice]:
        """Преобразовать в срезы numpy"""
        return (slice(int(self.y), int(self.y + self.height)), 
                slice(int(self.x), int(self.x + self.width)))
    
    def contains(self, x: float, y: float) -> bool:
        """Проверить, находится ли точка внутри ROI"""
        return (self.x <= x <= self.x + self.width and 
                self.y <= y <= self.y + self.height)


class Vectorizer:
    """
    Главный класс векторизатора для преобразования растровых изображений в векторные контуры
    """
    
    def __init__(self):
        self._image: Optional[np.ndarray] = None
        self._original_image: Optional[np.ndarray] = None
        self._roi: Optional[ROI] = None
        self._contours: List[Contour] = []
        self._test_images: List[str] = []
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
        """Загрузить изображение из файла"""
        try:
            if CV_AVAILABLE:
                # Используем OpenCV
                if isinstance(path, str) and Path(path).exists():
                    self._original_image = cv2.imread(path, cv2.IMREAD_UNCHANGED)
                elif isinstance(path, bytes):
                    self._original_image = cv2.imdecode(np.frombuffer(path, np.uint8), cv2.IMREAD_UNCHANGED)
                else:
                    return False
                
                if self._original_image is None:
                    return False
                
                # Конвертируем BGR в RGB
                if len(self._original_image.shape) == 3 and self._original_image.shape[2] == 3:
                    self._original_image = cv2.cvtColor(self._original_image, cv2.COLOR_BGR2RGB)
            else:
                # Используем PIL
                with Image.open(path) as img:
                    self._original_image = np.array(img)
                    if len(self._original_image.shape) == 3 and self._original_image.shape[2] == 4:
                        # RGBA to RGB
                        self._original_image = self._original_image[:, :, :3]
            
            self._image = self._original_image.copy()
            self._contours = []
            self._roi = None
            return True
            
        except Exception as e:
            print(f"Ошибка загрузки изображения: {e}")
            return False
    
    def load_image_from_pil(self, pil_image: Image.Image) -> bool:
        """Загрузить изображение из PIL Image"""
        try:
            self._original_image = np.array(pil_image)
            if len(self._original_image.shape) == 3 and self._original_image.shape[2] == 4:
                # RGBA to RGB
                self._original_image = self._original_image[:, :, :3]
            elif len(self._original_image.shape) == 3 and self._original_image.shape[2] == 3:
                # Ensure RGB
                pass
            
            self._image = self._original_image.copy()
            self._contours = []
            self._roi = None
            return True
        except Exception as e:
            print(f"Ошибка загрузки PIL изображения: {e}")
            return False
    
    def get_image(self) -> Optional[np.ndarray]:
        """Получить текущее изображение (с применённым ROI)"""
        if self._image is None:
            return None
        
        img = self._image.copy()
        
        if self._roi:
            sy, sx = self._roi.to_slice()
            img = img[sy, sx]
        
        return img
    
    def get_original_image(self) -> Optional[np.ndarray]:
        """Получить оригинальное изображение"""
        return self._original_image
    
    def set_roi(self, roi: ROI) -> None:
        """Установить область интереса"""
        self._roi = roi
    
    def clear_roi(self) -> None:
        """Очистить область интереса"""
        self._roi = None
    
    def get_roi(self) -> Optional[ROI]:
        """Получить текущий ROI"""
        return self._roi
    
    def set_parameter(self, name: str, value: Any) -> None:
        """Установить параметр векторизации"""
        if name in self._parameters:
            self._parameters[name] = value
    
    def get_parameter(self, name: str) -> Any:
        """Получить параметр векторизации"""
        return self._parameters.get(name)
    
    def _preprocess_image(self, img: np.ndarray) -> np.ndarray:
        """Предобработка изображения для обнаружения краёв"""
        # Конвертируем в оттенки серого
        if len(img.shape) == 3:
            if CV_AVAILABLE:
                gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            else:
                # Ручная конвертация в оттенки серого
                gray = np.dot(img[...,:3], [0.2989, 0.5870, 0.1140]).astype(np.uint8)
        else:
            gray = img.copy()
        
        # Применяем размытие по Гауссу
        blur = self._parameters['blur_radius']
        if blur > 0:
            if CV_AVAILABLE:
                gray = cv2.GaussianBlur(gray, (0, 0), sigmaX=blur)
            elif SCIPY_AVAILABLE:
                gray = ndimage.gaussian_filter(gray, sigma=blur)
        
        return gray
    
    def _detect_edges(self, gray: np.ndarray) -> np.ndarray:
        """Обнаружение краёв с помощью Кэнни"""
        if CV_AVAILABLE:
            thresh1 = self._parameters['canny_threshold1']
            thresh2 = self._parameters['canny_threshold2']
            edges = cv2.Canny(gray, thresh1, thresh2, apertureSize=3)
            return edges
        else:
            # Фоллбэк: простой пороговый фильтр
            thresh = self._parameters['canny_threshold1']
            edges = gray > thresh
            return edges.astype(np.uint8) * 255
    
    def _find_contours(self, edges: np.ndarray) -> List[np.ndarray]:
        """Поиск контуров из изображения краёв"""
        if CV_AVAILABLE:
            contours, hierarchy = cv2.findContours(
                edges, 
                cv2.RETR_TREE, 
                cv2.CHAIN_APPROX_SIMPLE
            )
            return [c.squeeze() for c in contours]
        elif SKIMAGE_AVAILABLE:
            # Используем scikit-image
            contours = find_contours(edges, level=0.5)
            return [c.astype(np.float32) for c in contours]
        else:
            # Простой фоллбэк
            return []
    
    def _filter_contours(self, contours: List[np.ndarray]) -> List[Contour]:
        """Фильтрация и обработка контуров"""
        results = []
        
        img = self.get_image()
        if img is None:
            return results
        
        img_height, img_width = img.shape[:2]
        min_area = 10
        
        for i, contour in enumerate(contours):
            if len(contour) < 3:
                continue
            
            # Вычисляем площадь
            if CV_AVAILABLE:
                area = cv2.contourArea(contour)
            else:
                # Ручной расчёт площади
                area = abs(np.sum(
                    contour[:, 0] * np.roll(contour[:, 1], 1) - 
                    contour[:, 1] * np.roll(contour[:, 0], 1)
                )) / 2
            
            if area < min_area:
                continue
            
            # Проверяем, не покрывает ли контур всю картинку (фон)
            bounding_rect = cv2.boundingRect(contour) if CV_AVAILABLE else (0, 0, img_width, img_height)
            x, y, w, h = bounding_rect
            
            if self._parameters['remove_background']:
                area_ratio = (w * h) / (img_width * img_height)
                if area_ratio > 0.95:
                    continue
            
            # Создаём объект Contour
            points = [(float(p[0]), float(p[1])) for p in contour]
            
            # Определяем, внешний это контур или внутренний
            is_external = True
            if self._parameters['detect_internal_edges']:
                # Для простоты помечаем все как внешние
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
        Главный метод векторизации
        Преобразует текущее изображение в векторные контуры
        """
        img = self.get_image()
        if img is None:
            return []
        
        # Предобработка
        gray = self._preprocess_image(img)
        
        # Обнаружение краёв
        edges = self._detect_edges(gray)
        
        # Поиск контуров
        contours = self._find_contours(edges)
        
        # Фильтрация и создание объектов Contour
        self._contours = self._filter_contours(contours)
        
        # Упрощение контуров
        epsilon = self._parameters['simplification_epsilon']
        if epsilon > 0:
            self._contours = [c.simplify(epsilon) for c in self._contours]
        
        return self._contours
    
    def get_contours(self) -> List[Contour]:
        """Получить текущие контуры"""
        return self._contours
    
    def clear_contours(self) -> None:
        """Очистить все контуры"""
        self._contours = []
    
    def get_silhouette(self) -> Optional[Contour]:
        """Получить основной внешний силуэт (самый большой контур)"""
        if not self._contours:
            return None
        
        # Находим самый большой контур по площади
        max_area = -1
        max_contour = None
        
        for contour in self._contours:
            if not contour.is_external:
                continue
            
            # Вычисляем площадь с помощью формулы шнурка
            pts = contour.to_numpy()
            if CV_AVAILABLE:
                area = cv2.contourArea(pts)
            else:
                area = abs(np.sum(pts[:, 0] * np.roll(pts[:, 1], 1) - pts[:, 1] * np.roll(pts[:, 0], 1))) / 2
            
            if area > max_area:
                max_area = area
                max_contour = contour
        
        return max_contour
    
    def get_internal_contours(self) -> List[Contour]:
        """Получить все внутренние контуры (дырки, детали)"""
        return [c for c in self._contours if not c.is_external]
    
    def to_svg(self, width: int = 1024, height: int = 1024) -> str:
        """Преобразовать контуры в SVG"""
        parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
        
        for contour in self._contours:
            path = contour.to_svg_path()
            if path:
                color_hex = f"#{contour.color[0]:02x}{contour.color[1]:02x}{contour.color[2]:02x}"
                parts.append(f'<path d="{path}" fill="none" stroke="{color_hex}" stroke-width="1"/>')
        
        parts.append('</svg>')
        return '\n'.join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Экспорт контуров в словарь для сериализации в JSON"""
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
        """Создать векторизатор из словаря"""
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
    """Удобная функция для создания и загрузки векторизатора из файла"""
    vec = Vectorizer()
    if vec.load_image(path):
        return vec
    return None
