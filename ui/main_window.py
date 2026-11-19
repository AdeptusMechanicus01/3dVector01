"""
Main window for the 3D Vector Pipeline application
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
    Main application window with three tabs
    """
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        
        # Application settings
        self.settings = QSettings("3DVectorPipeline", "App")
        
        # Window setup
        self.setWindowTitle("3D Vector Pipeline - Character Modeling Tool")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 800)
        
        # Apply dark theme
        apply_dark_theme(self)
        
        # Create central widget and layout
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(4, 4, 4, 4)
        self.main_layout.setSpacing(4)
        
        # Create tab widget
        self.tab_widget = QTabWidget(self)
        self.tab_widget.setTabPosition(QTabWidget.North)
        self.tab_widget.setMovable(True)
        self.tab_widget.setTabBarAutoHide(False)
        
        # Create tabs
        self.vectorizer_tab = VectorizerTab(self)
        self.skeleton_tab = SkeletonTab(self)
        self.workbench_tab = WorkbenchTab(self)
        
        # Add tabs
        self.tab_widget.addTab(self.vectorizer_tab, "1. Vectorizer")
        self.tab_widget.addTab(self.skeleton_tab, "2. Skeleton Builder")
        self.tab_widget.addTab(self.workbench_tab, "3. 3D Workbench")
        
        # Add tab widget to main layout
        self.main_layout.addWidget(self.tab_widget)
        
        # Create status bar
        self.status_bar = QStatusBar(self)
        self.status_bar.setSizeGripEnabled(True)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #7c8b9d; font: 11px 'System';")
        self.status_bar.addWidget(self.status_label, 1)
        
        # Version label
        self.version_label = QLabel("v2.0.0")
        self.version_label.setStyleSheet("color: #5b6b7d; font: 10px 'Consolas';")
        self.status_bar.addPermanentWidget(self.version_label)
        
        self.setStatusBar(self.status_bar)
        
        # Create menu bar
        self._create_menu_bar()
        
        # Create toolbars
        self._create_toolbars()
        
        # Connect signals
        self._connect_signals()
        
        # Load initial files if available
        self._load_initial_files()
        
        # Show welcome message
        self.show_welcome_message()
    
    def _create_menu_bar(self) -> None:
        """Create application menu bar"""
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
        
        # File menu
        file_menu = menu_bar.addMenu("File")
        
        # File actions
        self.action_new = QAction("New Project", self)
        self.action_new.setShortcut("Ctrl+N")
        self.action_new.setStatusTip("Create a new project")
        file_menu.addAction(self.action_new)
        
        self.action_open = QAction("Open Project", self)
        self.action_open.setShortcut("Ctrl+O")
        self.action_open.setStatusTip("Open an existing project")
        file_menu.addAction(self.action_open)
        
        self.action_save = QAction("Save Project", self)
        self.action_save.setShortcut("Ctrl+S")
        self.action_save.setStatusTip("Save current project")
        file_menu.addAction(self.action_save)
        
        self.action_save_as = QAction("Save As...", self)
        self.action_save_as.setShortcut("Ctrl+Shift+S")
        self.action_save_as.setStatusTip("Save project as...")
        file_menu.addAction(self.action_save_as)
        
        file_menu.addSeparator()
        
        self.action_import_images = QAction("Import Images", self)
        self.action_import_images.setShortcut("Ctrl+I")
        self.action_import_images.setStatusTip("Import reference images")
        file_menu.addAction(self.action_import_images)
        
        self.action_import_skeleton = QAction("Import Skeleton", self)
        self.action_import_skeleton.setShortcut("Ctrl+Shift+I")
        self.action_import_skeleton.setStatusTip("Import skeleton from JSON")
        file_menu.addAction(self.action_import_skeleton)
        
        file_menu.addSeparator()
        
        self.action_export_glb = QAction("Export to GLB", self)
        self.action_export_glb.setShortcut("Ctrl+E")
        self.action_export_glb.setStatusTip("Export 3D model to GLB format")
        file_menu.addAction(self.action_export_glb)
        
        self.action_export_obj = QAction("Export to OBJ", self)
        self.action_export_obj.setStatusTip("Export 3D model to OBJ format")
        file_menu.addAction(self.action_export_obj)
        
        file_menu.addSeparator()
        
        self.action_exit = QAction("Exit", self)
        self.action_exit.setShortcut("Ctrl+Q")
        self.action_exit.setStatusTip("Exit application")
        file_menu.addAction(self.action_exit)
        
        # Edit menu
        edit_menu = menu_bar.addMenu("Edit")
        
        self.action_undo = QAction("Undo", self)
        self.action_undo.setShortcut("Ctrl+Z")
        self.action_undo.setStatusTip("Undo last action")
        edit_menu.addAction(self.action_undo)
        
        self.action_redo = QAction("Redo", self)
        self.action_redo.setShortcut("Ctrl+Y")
        self.action_redo.setStatusTip("Redo last undone action")
        edit_menu.addAction(self.action_redo)
        
        edit_menu.addSeparator()
        
        self.action_preferences = QAction("Preferences", self)
        self.action_preferences.setShortcut("Ctrl+, ")
        self.action_preferences.setStatusTip("Open preferences")
        edit_menu.addAction(self.action_preferences)
        
        # View menu
        view_menu = menu_bar.addMenu("View")
        
        self.action_reset_camera = QAction("Reset Camera", self)
        self.action_reset_camera.setShortcut("Home")
        self.action_reset_camera.setStatusTip("Reset 3D camera view")
        view_menu.addAction(self.action_reset_camera)
        
        self.action_show_grid = QAction("Show Grid", self)
        self.action_show_grid.setCheckable(True)
        self.action_show_grid.setChecked(True)
        self.action_show_grid.setStatusTip("Show/hide grid in 3D viewport")
        view_menu.addAction(self.action_show_grid)
        
        self.action_show_axis = QAction("Show Axis", self)
        self.action_show_axis.setCheckable(True)
        self.action_show_axis.setChecked(True)
        self.action_show_axis.setStatusTip("Show/hide coordinate axis")
        view_menu.addAction(self.action_show_axis)
        
        # Tools menu
        tools_menu = menu_bar.addMenu("Tools")
        
        self.action_t_pose = QAction("Create T-Pose", self)
        self.action_t_pose.setStatusTip("Create a T-pose skeleton")
        tools_menu.addAction(self.action_t_pose)
        
        self.action_a_pose = QAction("Create A-Pose", self)
        self.action_a_pose.setStatusTip("Create an A-pose skeleton")
        tools_menu.addAction(self.action_a_pose)
        
        tools_menu.addSeparator()
        
        self.action_clear_all = QAction("Clear All", self)
        self.action_clear_all.setStatusTip("Clear all data")
        tools_menu.addAction(self.action_clear_all)
        
        # Help menu
        help_menu = menu_bar.addMenu("Help")
        
        self.action_help = QAction("Help", self)
        self.action_help.setShortcut("F1")
        self.action_help.setStatusTip("Show help")
        help_menu.addAction(self.action_help)
        
        self.action_about = QAction("About", self)
        self.action_about.setStatusTip("Show about dialog")
        help_menu.addAction(self.action_about)
    
    def _create_toolbars(self) -> None:
        """Create application toolbars"""
        # File toolbar
        file_toolbar = self.addToolBar("File")
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
        
        # Edit toolbar
        edit_toolbar = self.addToolBar("Edit")
        edit_toolbar.setObjectName("EditToolbar")
        
        edit_toolbar.addAction(self.action_undo)
        edit_toolbar.addAction(self.action_redo)
        edit_toolbar.addSeparator()
        edit_toolbar.addAction(self.action_preferences)
        
        # View toolbar
        view_toolbar = self.addToolBar("View")
        view_toolbar.setObjectName("ViewToolbar")
        
        view_toolbar.addAction(self.action_reset_camera)
        view_toolbar.addAction(self.action_show_grid)
        view_toolbar.addAction(self.action_show_axis)
    
    def _connect_signals(self) -> None:
        """Connect all signals"""
        # File actions
        self.action_new.triggered.connect(self.on_new_project)
        self.action_open.triggered.connect(self.on_open_project)
        self.action_save.triggered.connect(self.on_save_project)
        self.action_save_as.triggered.connect(self.on_save_as_project)
        self.action_import_images.triggered.connect(self.on_import_images)
        self.action_import_skeleton.triggered.connect(self.on_import_skeleton)
        self.action_export_glb.triggered.connect(self.on_export_glb)
        self.action_export_obj.triggered.connect(self.on_export_obj)
        self.action_exit.triggered.connect(self.close)
        
        # Edit actions
        self.action_undo.triggered.connect(self.on_undo)
        self.action_redo.triggered.connect(self.on_redo)
        self.action_preferences.triggered.connect(self.on_preferences)
        
        # View actions
        self.action_reset_camera.triggered.connect(self.on_reset_camera)
        self.action_show_grid.triggered.connect(self.on_toggle_grid)
        self.action_show_axis.triggered.connect(self.on_toggle_axis)
        
        # Tools actions
        self.action_t_pose.triggered.connect(self.on_create_t_pose)
        self.action_a_pose.triggered.connect(self.on_create_a_pose)
        self.action_clear_all.triggered.connect(self.on_clear_all)
        
        # Help actions
        self.action_help.triggered.connect(self.on_help)
        self.action_about.triggered.connect(self.on_about)
        
        # Tab connections
        self.vectorizer_tab.images_loaded.connect(self.on_images_loaded)
        self.vectorizer_tab.contours_generated.connect(self.on_contours_generated)
        self.skeleton_tab.skeleton_loaded.connect(self.on_skeleton_loaded)
        self.skeleton_tab.skeleton_created.connect(self.on_skeleton_created)
        self.workbench_tab.mesh_ready.connect(self.on_mesh_ready)
    
    def _load_initial_files(self) -> None:
        """Load initial files from repository if available"""
        # Check if we have test assets in the repository
        repo_path = Path(__file__).parent.parent.parent
        
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
            # Load images into vectorizer tab
            if any(f.endswith('.bmp') for f in available_files):
                self.vectorizer_tab.load_test_images(available_files)
            
            # Load skeleton into skeleton tab
            json_files = [f for f in available_files if f.endswith('.json')]
            if json_files:
                self.skeleton_tab.load_skeleton_from_file(json_files[0])
    
    def show_welcome_message(self) -> None:
        """Show welcome message in status bar"""
        self.status_label.setText("Welcome to 3D Vector Pipeline | Load images to start")
    
    def set_status(self, message: str, is_error: bool = False) -> None:
        """Set status bar message"""
        if is_error:
            self.status_label.setStyleSheet("color: #f87171; font: 11px 'System';")
        else:
            self.status_label.setStyleSheet("color: #7c8b9d; font: 11px 'System';")
        self.status_label.setText(message)
    
    # Event handlers
    def on_new_project(self) -> None:
        """Handle new project action"""
        # Confirm if there's unsaved work
        if self._has_unsaved_changes():
            reply = QMessageBox.question(
                self, "New Project",
                "You have unsaved changes. Are you sure you want to create a new project?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # Clear all tabs
        self.vectorizer_tab.clear_all()
        self.skeleton_tab.clear_all()
        self.workbench_tab.clear_all()
        
        self.set_status("New project created")
    
    def on_open_project(self) -> None:
        """Handle open project action"""
        # For now, just show a message
        self.set_status("Open project - Not yet implemented")
        QMessageBox.information(self, "Not Implemented", "Project loading is not yet implemented.")
    
    def on_save_project(self) -> None:
        """Handle save project action"""
        # For now, just show a message
        self.set_status("Save project - Not yet implemented")
        QMessageBox.information(self, "Not Implemented", "Project saving is not yet implemented.")
    
    def on_save_as_project(self) -> None:
        """Handle save as project action"""
        # For now, just show a message
        self.set_status("Save as project - Not yet implemented")
    
    def on_import_images(self) -> None:
        """Handle import images action"""
        # Open file dialog
        options = QFileDialog.Options()
        files, _ = QFileDialog.getOpenFileNames(
            self, "Import Images", "",
            "Image Files (*.bmp *.png *.jpg *.jpeg);;All Files (*)",
            options=options
        )
        
        if files:
            self.vectorizer_tab.load_images(files)
            self.tab_widget.setCurrentIndex(0)  # Switch to vectorizer tab
            self.set_status(f"Loaded {len(files)} images")
    
    def on_import_skeleton(self) -> None:
        """Handle import skeleton action"""
        # Open file dialog
        options = QFileDialog.Options()
        file, _ = QFileDialog.getOpenFileName(
            self, "Import Skeleton", "",
            "JSON Files (*.json);;All Files (*)",
            options=options
        )
        
        if file:
            self.skeleton_tab.load_skeleton_from_file(file)
            self.tab_widget.setCurrentIndex(1)  # Switch to skeleton tab
            self.set_status(f"Loaded skeleton from {file}")
    
    def on_export_glb(self) -> None:
        """Handle export to GLB action"""
        # Get mesh from workbench tab
        mesh = self.workbench_tab.get_current_mesh()
        if mesh is None:
            self.set_status("No mesh to export", is_error=True)
            return
        
        # Open save dialog
        options = QFileDialog.Options()
        file, _ = QFileDialog.getSaveFileName(
            self, "Export to GLB", "",
            "GLB Files (*.glb);;All Files (*)",
            options=options
        )
        
        if file:
            # Export mesh
            success = self.workbench_tab.export_to_glb(file)
            if success:
                self.set_status(f"Exported to {file}")
            else:
                self.set_status("Export failed", is_error=True)
    
    def on_export_obj(self) -> None:
        """Handle export to OBJ action"""
        # Get mesh from workbench tab
        mesh = self.workbench_tab.get_current_mesh()
        if mesh is None:
            self.set_status("No mesh to export", is_error=True)
            return
        
        # Open save dialog
        options = QFileDialog.Options()
        file, _ = QFileDialog.getSaveFileName(
            self, "Export to OBJ", "",
            "OBJ Files (*.obj);;All Files (*)",
            options=options
        )
        
        if file:
            # Export mesh
            success = self.workbench_tab.export_to_obj(file)
            if success:
                self.set_status(f"Exported to {file}")
            else:
                self.set_status("Export failed", is_error=True)
    
    def on_undo(self) -> None:
        """Handle undo action"""
        current_tab = self.tab_widget.currentIndex()
        
        if current_tab == 0:  # Vectorizer
            self.vectorizer_tab.undo()
        elif current_tab == 1:  # Skeleton
            self.skeleton_tab.undo()
        elif current_tab == 2:  # Workbench
            self.workbench_tab.undo()
        
        self.set_status("Undo")
    
    def on_redo(self) -> None:
        """Handle redo action"""
        current_tab = self.tab_widget.currentIndex()
        
        if current_tab == 0:  # Vectorizer
            self.vectorizer_tab.redo()
        elif current_tab == 1:  # Skeleton
            self.skeleton_tab.redo()
        elif current_tab == 2:  # Workbench
            self.workbench_tab.redo()
        
        self.set_status("Redo")
    
    def on_preferences(self) -> None:
        """Handle preferences action"""
        self.set_status("Preferences - Not yet implemented")
    
    def on_reset_camera(self) -> None:
        """Handle reset camera action"""
        if self.tab_widget.currentIndex() == 2:
            self.workbench_tab.reset_camera()
        self.set_status("Camera reset")
    
    def on_toggle_grid(self) -> None:
        """Handle toggle grid action"""
        show = self.action_show_grid.isChecked()
        if self.tab_widget.currentIndex() == 2:
            self.workbench_tab.set_show_grid(show)
        self.set_status(f"Grid {'shown' if show else 'hidden'}")
    
    def on_toggle_axis(self) -> None:
        """Handle toggle axis action"""
        show = self.action_show_axis.isChecked()
        if self.tab_widget.currentIndex() == 2:
            self.workbench_tab.set_show_axis(show)
        self.set_status(f"Axis {'shown' if show else 'hidden'}")
    
    def on_create_t_pose(self) -> None:
        """Handle create T-pose action"""
        self.skeleton_tab.create_preset_t_pose()
        self.tab_widget.setCurrentIndex(1)
        self.set_status("Created T-pose skeleton")
    
    def on_create_a_pose(self) -> None:
        """Handle create A-pose action"""
        self.skeleton_tab.create_preset_a_pose()
        self.tab_widget.setCurrentIndex(1)
        self.set_status("Created A-pose skeleton")
    
    def on_clear_all(self) -> None:
        """Handle clear all action"""
        # Confirm
        reply = QMessageBox.question(
            self, "Clear All",
            "Are you sure you want to clear all data?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.vectorizer_tab.clear_all()
            self.skeleton_tab.clear_all()
            self.workbench_tab.clear_all()
            self.set_status("All data cleared")
    
    def on_help(self) -> None:
        """Handle help action"""
        QMessageBox.information(
            self, "Help",
            "3D Vector Pipeline Help\n\n"
            "Tab 1: Vectorizer - Convert raster images to vector contours\n"
            "Tab 2: Skeleton Builder - Create and edit character skeletons\n"
            "Tab 3: 3D Workbench - Generate and sculpt 3D meshes\n\n"
            "Keyboard Shortcuts:\n"
            "Ctrl+Z: Undo\n"
            "Ctrl+Y: Redo\n"
            "Home: Reset Camera\n"
        )
    
    def on_about(self) -> None:
        """Handle about action"""
        QMessageBox.about(
            self, "About 3D Vector Pipeline",
            "<h2>3D Vector Pipeline</h2>
"
            "<p>Version 2.0.0</p>
"
            "<p>A unified desktop application for 3D character modeling from raster images.</p>
"
            "<p>Features:</p>
"
            "<ul>
"
            "<li>Vectorization of raster images (BMP, PNG, JPG)</li>
"
            "<li>Skeleton construction with mirror symmetry</li>
"
            "<li>3D mesh generation using Marching Cubes</li>
"
            "<li>Sculpting tools (Inflate, Grab, Smooth)</li>
"
            "<li>GLB export for Unity</li>
"
            "</ul>
"
            "<p>Technologies: Python, PySide6, PyVista, OpenCV, scikit-image, trimesh</p>
"
        )
    
    # Signal handlers
    def on_images_loaded(self, count: int) -> None:
        """Handle images loaded signal"""
        self.set_status(f"Loaded {count} images")
    
    def on_contours_generated(self, count: int) -> None:
        """Handle contours generated signal"""
        self.set_status(f"Generated {count} contours")
        # Pass contours to skeleton tab
        contours = self.vectorizer_tab.get_contours()
        if contours:
            self.skeleton_tab.set_reference_contours(contours)
    
    def on_skeleton_loaded(self, joint_count: int) -> None:
        """Handle skeleton loaded signal"""
        self.set_status(f"Loaded skeleton with {joint_count} joints")
    
    def on_skeleton_created(self, joint_count: int) -> None:
        """Handle skeleton created signal"""
        self.set_status(f"Created skeleton with {joint_count} joints")
        # Pass skeleton to workbench tab
        skeleton = self.skeleton_tab.get_skeleton()
        if skeleton:
            self.workbench_tab.set_skeleton(skeleton)
    
    def on_mesh_ready(self, vertex_count: int, face_count: int) -> None:
        """Handle mesh ready signal"""
        self.set_status(f"Mesh ready: {vertex_count} vertices, {face_count} faces")
    
    def _has_unsaved_changes(self) -> bool:
        """Check if there are unsaved changes"""
        # For now, always return False
        # In a real implementation, track changes in each tab
        return False
    
    def closeEvent(self, event) -> None:
        """Handle close event"""
        if self._has_unsaved_changes():
            reply = QMessageBox.question(
                self, "Exit",
                "You have unsaved changes. Are you sure you want to exit?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
    
    def keyPressEvent(self, event) -> None:
        """Handle key press events"""
        # Pass to current tab
        current_tab = self.tab_widget.currentWidget()
        if current_tab:
            current_tab.keyPressEvent(event)
        else:
            super().keyPressEvent(event)
    
    def keyReleaseEvent(self, event) -> None:
        """Handle key release events"""
        current_tab = self.tab_widget.currentWidget()
        if current_tab:
            current_tab.keyReleaseEvent(event)
        else:
            super().keyReleaseEvent(event)


if __name__ == "__main__":
    # For testing
    from PySide6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
