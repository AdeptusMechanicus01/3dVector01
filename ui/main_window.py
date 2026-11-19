"""
Главное окно приложения 3D Vector Pipeline
"""

import sys
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QStatusBar, QLabel, QFileDialog, QMessageBox, QSplitter
)
from PySide6.QtCore import Qt, QSize, Signal, Slot, QSettings
from PySide6.QtGui import QAction, QIcon

from .styles import apply_dark_theme, Colors, StyleSheet
from .vectorizer_tab import VectorizerTab
from .skeleton_tab import SkeletonTab
from .workbench_tab import WorkbenchTab


class MainWindow(QMainWindow):
    """
    Главное окно приложения с тремя вкладками
    """
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        
        # Настройки приложения
        self.settings = QSettings("3DVectorPipeline", "App")
        
        # Настройка окна
        self.setWindowTitle("3D Vector Pipeline - Конструктор 3D персонажей")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 800)
        
        # Применяем тёмную тему
        apply_dark_theme(self)
        
        # Создаём центральный виджет и компоновку
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(4, 4, 4, 4)
        self.main_layout.setSpacing(4)
        
        # Создаём виджет вкладок
        self.tab_widget = QTabWidget(self)
        self.tab_widget.setTabPosition(QTabWidget.North)
        self.tab_widget.setMovable(True)
        self.tab_widget.setTabBarAutoHide(False)
        
        # Создаём вкладки
        self.vectorizer_tab = VectorizerTab(self)
        self.skeleton_tab = SkeletonTab(self)
        self.workbench_tab = WorkbenchTab(self)
        
        # Добавляем вкладки с русскими названиями
        self.tab_widget.addTab(self.vectorizer_tab, "1. Векторизатор")
        self.tab_widget.addTab(self.skeleton_tab, "2. Конструктор скелета")
        self.tab_widget.addTab(self.workbench_tab, "3. 3D Верстак")
        
        # Добавляем виджет вкладок в главную компоновку
        self.main_layout.addWidget(self.tab_widget)
        
        # Создаём строку состояния
        self.status_bar = QStatusBar(self)
        self.status_bar.setSizeGripEnabled(True)
        
        # Метка состояния
        self.status_label = QLabel("Готово")
        self.status_label.setStyleSheet("color: #7c8b9d; font: 11px 'System';")
        self.status_bar.addWidget(self.status_label, 1)
        
        # Метка версии
        self.version_label = QLabel("v2.0.0")
        self.version_label.setStyleSheet("color: #5b6b7d; font: 10px 'Consolas';")
        self.status_bar.addPermanentWidget(self.version_label)
        
        self.setStatusBar(self.status_bar)
        
        # Создаём меню
        self._create_menu_bar()
        
        # Создаём панели инструментов
        self._create_toolbars()
        
        # Подключаем сигналы
        self._connect_signals()
        
        # Загружаем начальные файлы
        self._load_initial_files()
        
        # Показываем приветственное сообщение
        self.show_welcome_message()
    
    def _create_menu_bar(self) -> None:
        """Создаём панель меню"""
        menu_bar = self.menuBar()
        menu_bar.setStyleSheet("""
            QMenuBar {
                background-color: #0d1218;
                color: #d7e0ea;
                border-bottom: 1px solid #1e2833;
                font: 11px "System";
            }
            
            QMenuBar::item {
                background: transparent;
                padding: 4px 8px;
            }
            
            QMenuBar::item:selected {
                background-color: rgba(34, 211, 238, 0.2);
            }
            
            QMenu {
                background-color: #10151c;
                color: #d7e0ea;
                border: 1px solid #1e2833;
                padding: 4px;
                font: 11px "System";
            }
            
            QMenu::item {
                background: transparent;
                padding: 6px 24px 6px 8px;
            }
            
            QMenu::item:selected {
                background-color: rgba(34, 211, 238, 0.2);
                color: #ffffff;
            }
            
            QMenu::separator {
                height: 1px;
                background-color: #1e2833;
                margin: 4px 0;
            }
        """)
        
        # Меню Файл
        file_menu = menu_bar.addMenu("Файл")
        
        self.action_new = QAction("Новый проект", self)
        self.action_new.setShortcut("Ctrl+N")
        self.action_new.setStatusTip("Создать новый проект")
        file_menu.addAction(self.action_new)
        
        self.action_open = QAction("Открыть проект", self)
        self.action_open.setShortcut("Ctrl+O")
        self.action_open.setStatusTip("Открыть существующий проект")
        file_menu.addAction(self.action_open)
        
        self.action_save = QAction("Сохранить проект", self)
        self.action_save.setShortcut("Ctrl+S")
        self.action_save.setStatusTip("Сохранить текущий проект")
        file_menu.addAction(self.action_save)
        
        self.action_save_as = QAction("Сохранить как...", self)
        self.action_save_as.setShortcut("Ctrl+Shift+S")
        self.action_save_as.setStatusTip("Сохранить проект как...")
        file_menu.addAction(self.action_save_as)
        
        file_menu.addSeparator()
        
        self.action_import_images = QAction("Импорт изображений", self)
        self.action_import_images.setShortcut("Ctrl+I")
        self.action_import_images.setStatusTip("Импортировать референсные изображения")
        file_menu.addAction(self.action_import_images)
        
        self.action_import_skeleton = QAction("Импорт скелета", self)
        self.action_import_skeleton.setShortcut("Ctrl+Shift+I")
        self.action_import_skeleton.setStatusTip("Импортировать скелет из JSON")
        file_menu.addAction(self.action_import_skeleton)
        
        file_menu.addSeparator()
        
        self.action_export_glb = QAction("Экспорт в GLB", self)
        self.action_export_glb.setShortcut("Ctrl+E")
        self.action_export_glb.setStatusTip("Экспортировать 3D модель в формат GLB")
        file_menu.addAction(self.action_export_glb)
        
        self.action_export_obj = QAction("Экспорт в OBJ", self)
        self.action_export_obj.setStatusTip("Экспортировать 3D модель в формат OBJ")
        file_menu.addAction(self.action_export_obj)
        
        file_menu.addSeparator()
        
        self.action_exit = QAction("Выход", self)
        self.action_exit.setShortcut("Ctrl+Q")
        self.action_exit.setStatusTip("Выйти из приложения")
        file_menu.addAction(self.action_exit)
        
        # Меню Правка
        edit_menu = menu_bar.addMenu("Правка")
        
        self.action_undo = QAction("Отменить", self)
        self.action_undo.setShortcut("Ctrl+Z")
        self.action_undo.setStatusTip("Отменить последнее действие")
        edit_menu.addAction(self.action_undo)
        
        self.action_redo = QAction("Вернуть", self)
        self.action_redo.setShortcut("Ctrl+Y")
        self.action_redo.setStatusTip("Вернуть отменённое действие")
        edit_menu.addAction(self.action_redo)
        
        edit_menu.addSeparator()
        
        self.action_preferences = QAction("Настройки", self)
        self.action_preferences.setShortcut("Ctrl+, ")
        self.action_preferences.setStatusTip("Открыть настройки")
        edit_menu.addAction(self.action_preferences)
        
        # Меню Вид
        view_menu = menu_bar.addMenu("Вид")
        
        self.action_reset_camera = QAction("Сбросить камеру", self)
        self.action_reset_camera.setShortcut("Home")
        self.action_reset_camera.setStatusTip("Сбросить вид 3D камеры")
        view_menu.addAction(self.action_reset_camera)
        
        self.action_show_grid = QAction("Показать сетку", self)
        self.action_show_grid.setCheckable(True)
        self.action_show_grid.setChecked(True)
        self.action_show_grid.setStatusTip("Показать/скрыть сетку в 3D вьюпорте")
        view_menu.addAction(self.action_show_grid)
        
        self.action_show_axis = QAction("Показать оси", self)
        self.action_show_axis.setCheckable(True)
        self.action_show_axis.setChecked(True)
        self.action_show_axis.setStatusTip("Показать/скрыть координатные оси")
        view_menu.addAction(self.action_show_axis)
        
        # Меню Инструменты
        tools_menu = menu_bar.addMenu("Инструменты")
        
        self.action_t_pose = QAction("Создать T-Pose", self)
        self.action_t_pose.setStatusTip("Создать скелет в T-pozе")
        tools_menu.addAction(self.action_t_pose)
        
        self.action_a_pose = QAction("Создать A-Pose", self)
        self.action_a_pose.setStatusTip("Создать скелет в A-pozе")
        tools_menu.addAction(self.action_a_pose)
        
        tools_menu.addSeparator()
        
        self.action_clear_all = QAction("Очистить всё", self)
        self.action_clear_all.setStatusTip("Очистить все данные")
        tools_menu.addAction(self.action_clear_all)
        
        # Меню Справка
        help_menu = menu_bar.addMenu("Справка")
        
        self.action_help = QAction("Справка", self)
        self.action_help.setShortcut("F1")
        self.action_help.setStatusTip("Показать справку")
        help_menu.addAction(self.action_help)
        
        self.action_about = QAction("О программе", self)
        self.action_about.setStatusTip("Показать информацию о программе")
        help_menu.addAction(self.action_about)
    
    def _create_toolbars(self) -> None:
        """Создаём панели инструментов"""
        # Панель Файл
        file_toolbar = self.addToolBar("Файл")
        file_toolbar.setObjectName("FileToolbar")
        file_toolbar.setStyleSheet("""
            QToolBar {
                background-color: #0d1218;
                border-bottom: 1px solid #1e2833;
                padding: 4px;
            }
        """)
        
        file_toolbar.addAction(self.action_new)
        file_toolbar.addAction(self.action_open)
        file_toolbar.addAction(self.action_save)
        file_toolbar.addSeparator()
        file_toolbar.addAction(self.action_import_images)
        file_toolbar.addAction(self.action_import_skeleton)
        file_toolbar.addSeparator()
        file_toolbar.addAction(self.action_export_glb)
        
        # Панель Правка
        edit_toolbar = self.addToolBar("Правка")
        edit_toolbar.setObjectName("EditToolbar")
        
        edit_toolbar.addAction(self.action_undo)
        edit_toolbar.addAction(self.action_redo)
        edit_toolbar.addSeparator()
        edit_toolbar.addAction(self.action_preferences)
        
        # Панель Вид
        view_toolbar = self.addToolBar("Вид")
        view_toolbar.setObjectName("ViewToolbar")
        
        view_toolbar.addAction(self.action_reset_camera)
        view_toolbar.addAction(self.action_show_grid)
        view_toolbar.addAction(self.action_show_axis)
    
    def _connect_signals(self) -> None:
        """Подключаем все сигналы"""
        # Действия Файл
        self.action_new.triggered.connect(self.on_new_project)
        self.action_open.triggered.connect(self.on_open_project)
        self.action_save.triggered.connect(self.on_save_project)
        self.action_save_as.triggered.connect(self.on_save_as_project)
        self.action_import_images.triggered.connect(self.on_import_images)
        self.action_import_skeleton.triggered.connect(self.on_import_skeleton)
        self.action_export_glb.triggered.connect(self.on_export_glb)
        self.action_export_obj.triggered.connect(self.on_export_obj)
        self.action_exit.triggered.connect(self.close)
        
        # Действия Правка
        self.action_undo.triggered.connect(self.on_undo)
        self.action_redo.triggered.connect(self.on_redo)
        self.action_preferences.triggered.connect(self.on_preferences)
        
        # Действия Вид
        self.action_reset_camera.triggered.connect(self.on_reset_camera)
        self.action_show_grid.triggered.connect(self.on_toggle_grid)
        self.action_show_axis.triggered.connect(self.on_toggle_axis)
        
        # Действия Инструменты
        self.action_t_pose.triggered.connect(self.on_create_t_pose)
        self.action_a_pose.triggered.connect(self.on_create_a_pose)
        self.action_clear_all.triggered.connect(self.on_clear_all)
        
        # Действия Справка
        self.action_help.triggered.connect(self.on_help)
        self.action_about.triggered.connect(self.on_about)
        
        # Сигналы вкладок
        self.vectorizer_tab.images_loaded.connect(self.on_images_loaded)
        self.vectorizer_tab.contours_generated.connect(self.on_contours_generated)
        self.skeleton_tab.skeleton_loaded.connect(self.on_skeleton_loaded)
        self.skeleton_tab.skeleton_created.connect(self.on_skeleton_created)
        self.workbench_tab.mesh_ready.connect(self.on_mesh_ready)
    
    def _load_initial_files(self) -> None:
        """Загружаем начальные файлы из репозитория"""
        repo_path = Path(__file__).parent.parent
        
        test_files = [
            'front.bmp', 'back.bmp', 'left.bmp', 'right.bmp',
            'skeleton_step1.json'
        ]
        
        available_files = []
        for f in test_files:
            file_path = repo_path / f
            if file_path.exists():
                available_files.append(str(file_path))
        
        if len(available_files) > 0:
            # Загружаем изображения во вкладку векторизатора
            if any(f.endswith('.bmp') for f in available_files):
                self.vectorizer_tab.load_test_images(available_files)
            
            # Загружаем скелет во вкладку скелета
            json_files = [f for f in available_files if f.endswith('.json')]
            if json_files:
                self.skeleton_tab.load_skeleton_from_file(json_files[0])
    
    def show_welcome_message(self) -> None:
        """Показываем приветственное сообщение"""
        self.status_label.setText("Добро пожаловать в 3D Vector Pipeline | Загрузите изображения для начала работы")
    
    def set_status(self, message: str, is_error: bool = False) -> None:
        """Устанавливаем сообщение в строке состояния"""
        if is_error:
            self.status_label.setStyleSheet("color: #f87171; font: 11px 'System';")
        else:
            self.status_label.setStyleSheet("color: #7c8b9d; font: 11px 'System';")
        self.status_label.setText(message)
    
    # Обработчики событий
    def on_new_project(self) -> None:
        """Обработка создания нового проекта"""
        if self._has_unsaved_changes():
            reply = QMessageBox.question(
                self, "Новый проект",
                "У вас есть несохранённые изменения. Вы уверены, что хотите создать новый проект?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        self.vectorizer_tab.clear_all()
        self.skeleton_tab.clear_all()
        self.workbench_tab.clear_all()
        self.set_status("Создан новый проект")
    
    def on_open_project(self) -> None:
        """Обработка открытия проекта"""
        self.set_status("Открытие проекта - ещё не реализовано")
        QMessageBox.information(self, "Не реализовано", "Загрузка проекта пока не реализована.")
    
    def on_save_project(self) -> None:
        """Обработка сохранения проекта"""
        self.set_status("Сохранение проекта - ещё не реализовано")
    
    def on_save_as_project(self) -> None:
        """Обработка сохранения проекта как..."""
        self.set_status("Сохранение проекта как... - ещё не реализовано")
    
    def on_import_images(self) -> None:
        """Обработка импорта изображений"""
        options = QFileDialog.Options()
        files, _ = QFileDialog.getOpenFileNames(
            self, "Импорт изображений", "",
            "Изображения (*.bmp *.png *.jpg *.jpeg);;Все файлы (*)",
            options=options
        )
        
        if files:
            self.vectorizer_tab.load_images(files)
            self.tab_widget.setCurrentIndex(0)
            self.set_status(f"Загружено {len(files)} изображений")
    
    def on_import_skeleton(self) -> None:
        """Обработка импорта скелета"""
        options = QFileDialog.Options()
        file, _ = QFileDialog.getOpenFileName(
            self, "Импорт скелета", "",
            "JSON файлы (*.json);;Все файлы (*)",
            options=options
        )
        
        if file:
            self.skeleton_tab.load_skeleton_from_file(file)
            self.tab_widget.setCurrentIndex(1)
            self.set_status(f"Загружен скелет из {file}")
    
    def on_export_glb(self) -> None:
        """Обработка экспорта в GLB"""
        mesh = self.workbench_tab.get_current_mesh()
        if mesh is None:
            self.set_status("Нет сетки для экспорта", is_error=True)
            return
        
        options = QFileDialog.Options()
        file, _ = QFileDialog.getSaveFileName(
            self, "Экспорт в GLB", "",
            "GLB файлы (*.glb);;Все файлы (*)",
            options=options
        )
        
        if file:
            success = self.workbench_tab.export_to_glb(file)
            if success:
                self.set_status(f"Экспортировано в {file}")
            else:
                self.set_status("Ошибка экспорта", is_error=True)
    
    def on_export_obj(self) -> None:
        """Обработка экспорта в OBJ"""
        mesh = self.workbench_tab.get_current_mesh()
        if mesh is None:
            self.set_status("Нет сетки для экспорта", is_error=True)
            return
        
        options = QFileDialog.Options()
        file, _ = QFileDialog.getSaveFileName(
            self, "Экспорт в OBJ", "",
            "OBJ файлы (*.obj);;Все файлы (*)",
            options=options
        )
        
        if file:
            success = self.workbench_tab.export_to_obj(file)
            if success:
                self.set_status(f"Экспортировано в {file}")
            else:
                self.set_status("Ошибка экспорта", is_error=True)
    
    def on_undo(self) -> None:
        """Обработка отмены"""
        current_tab = self.tab_widget.currentIndex()
        
        if current_tab == 0:
            self.vectorizer_tab.undo()
        elif current_tab == 1:
            self.skeleton_tab.undo()
        elif current_tab == 2:
            self.workbench_tab.undo()
        
        self.set_status("Отменено")
    
    def on_redo(self) -> None:
        """Обработка возврата"""
        current_tab = self.tab_widget.currentIndex()
        
        if current_tab == 0:
            self.vectorizer_tab.redo()
        elif current_tab == 1:
            self.skeleton_tab.redo()
        elif current_tab == 2:
            self.workbench_tab.redo()
        
        self.set_status("Возвращено")
    
    def on_preferences(self) -> None:
        """Обработка настроек"""
        self.set_status("Настройки - ещё не реализовано")
    
    def on_reset_camera(self) -> None:
        """Обработка сброса камеры"""
        if self.tab_widget.currentIndex() == 2:
            self.workbench_tab.reset_camera()
        self.set_status("Камера сброшена")
    
    def on_toggle_grid(self) -> None:
        """Обработка переключения сетки"""
        show = self.action_show_grid.isChecked()
        if self.tab_widget.currentIndex() == 2:
            self.workbench_tab.set_show_grid(show)
        self.set_status(f"Сетка {'показана' if show else 'скрыта'}")
    
    def on_toggle_axis(self) -> None:
        """Обработка переключения осей"""
        show = self.action_show_axis.isChecked()
        if self.tab_widget.currentIndex() == 2:
            self.workbench_tab.set_show_axis(show)
        self.set_status(f"Оси {'показаны' if show else 'скрыты'}")
    
    def on_create_t_pose(self) -> None:
        """Обработка создания T-Pose"""
        self.skeleton_tab.create_preset_t_pose()
        self.tab_widget.setCurrentIndex(1)
        self.set_status("Создан скелет в T-Pose")
    
    def on_create_a_pose(self) -> None:
        """Обработка создания A-Pose"""
        self.skeleton_tab.create_preset_a_pose()
        self.tab_widget.setCurrentIndex(1)
        self.set_status("Создан скелет в A-Pose")
    
    def on_clear_all(self) -> None:
        """Обработка очистки всего"""
        reply = QMessageBox.question(
            self, "Очистить всё",
            "Вы уверены, что хотите очистить все данные?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.vectorizer_tab.clear_all()
            self.skeleton_tab.clear_all()
            self.workbench_tab.clear_all()
            self.set_status("Все данные очищены")
    
    def on_help(self) -> None:
        """Обработка справки"""
        QMessageBox.information(
            self, "Справка",
            "3D Vector Pipeline - Справка\n\n"
            "Вкладка 1: Векторизатор - Преобразование растровых изображений в векторные контуры\n"
            "Вкладка 2: Конструктор скелета - Создание и редактирование скелета персонажа\n"
            "Вкладка 3: 3D Верстак - Генерация и скульптинг 3D сеток\n\n"
            "Горячие клавиши:\n"
            "Ctrl+Z: Отменить\n"
            "Ctrl+Y: Вернуть\n"
            "Home: Сбросить камеру\n"
        )
    
    def on_about(self) -> None:
        """Обработка информации о программе"""
        about_html = """<h2>3D Vector Pipeline</h2>
<p>Версия 2.0.0</p>
<p>Унифицированное десктопное приложение для 3D моделирования персонажей из растровых изображений.</p>
<p>Возможности:</p>
<ul>
<li>Векторизация растровых изображений (BMP, PNG, JPG)</li>
<li>Создание скелета с зеркальной симметрией</li>
<li>Генерация 3D сетки с использованием Marching Cubes</li>
<li>Инструменты скульптинга (Inflate, Grab, Smooth)</li>
<li>Экспорт в формат GLB для Unity</li>
</ul>
<p>Технологии: Python, PySide6, PyVista, OpenCV, scikit-image, trimesh</p>"""
        QMessageBox.about(self, "О программе 3D Vector Pipeline", about_html)
    
    # Обработчики сигналов
    def on_images_loaded(self, count: int) -> None:
        """Обработка загрузки изображений"""
        self.set_status(f"Загружено {count} изображений")
    
    def on_contours_generated(self, count: int) -> None:
        """Обработка генерации контуров"""
        self.set_status(f"Сгенерировано {count} контуров")
        contours = self.vectorizer_tab.get_contours()
        if contours:
            self.skeleton_tab.set_reference_contours(contours)
    
    def on_skeleton_loaded(self, joint_count: int) -> None:
        """Обработка загрузки скелета"""
        self.set_status(f"Загружен скелет с {joint_count} суставами")
    
    def on_skeleton_created(self, joint_count: int) -> None:
        """Обработка создания скелета"""
        self.set_status(f"Создан скелет с {joint_count} суставами")
        skeleton = self.skeleton_tab.get_skeleton()
        if skeleton:
            self.workbench_tab.set_skeleton(skeleton)
    
    def on_mesh_ready(self, vertex_count: int, face_count: int) -> None:
        """Обработка готовности сетки"""
        self.set_status(f"Сетка готова: {vertex_count} вершин, {face_count} граней")
    
    def _has_unsaved_changes(self) -> bool:
        """Проверяем есть ли несохранённые изменения"""
        return False
    
    def closeEvent(self, event) -> None:
        """Обработка закрытия окна"""
        if self._has_unsaved_changes():
            reply = QMessageBox.question(
                self, "Выход",
                "У вас есть несохранённые изменения. Вы уверены, что хотите выйти?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
    
    def keyPressEvent(self, event) -> None:
        """Обработка нажатия клавиш"""
        current_tab = self.tab_widget.currentWidget()
        if current_tab:
            current_tab.keyPressEvent(event)
        else:
            super().keyPressEvent(event)
    
    def keyReleaseEvent(self, event) -> None:
        """Обработка отпускания клавиш"""
        current_tab = self.tab_widget.currentWidget()
        if current_tab:
            current_tab.keyReleaseEvent(event)
        else:
            super().keyReleaseEvent(event)


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
