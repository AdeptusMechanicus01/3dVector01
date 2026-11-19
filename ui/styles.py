"""
Style definitions for dark theme UI
"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QPalette, QFont, QIcon
from PySide6.QtWidgets import QStyleFactory


class Colors:
    """Color palette for dark theme"""
    # Background colors
    BG_PRIMARY = QColor(10, 14, 19)      # #0a0e13
    BG_SECONDARY = QColor(16, 21, 32)    # #101520
    BG_TERTIARY = QColor(13, 18, 24)     # #0d1218
    BG_PANEL = QColor(22, 27, 38)       # #161b26
    BG_PANEL2 = QColor(26, 33, 44)      # #1a212c
    
    # Text colors
    TEXT_PRIMARY = QColor(215, 224, 234)  # #d7e0ea
    TEXT_SECONDARY = QColor(124, 139, 157) # #7c8b9d
    TEXT_DIM = QColor(91, 107, 125)       # #5b6b7d
    
    # Accent colors
    ACCENT_CYAN = QColor(34, 211, 238)    # #22d3ee
    ACCENT_ORANGE = QColor(251, 191, 36)  # #fbbf24
    ACCENT_GREEN = QColor(52, 211, 153)   # #34d399
    ACCENT_RED = QColor(248, 113, 113)    # #f87171
    ACCENT_BLUE = QColor(56, 189, 248)    # #38bdf8
    
    # Status colors
    SUCCESS = QColor(52, 211, 153)       # #34d399
    WARNING = QColor(251, 191, 36)       # #fbbf24
    ERROR = QColor(248, 113, 113)        # #f87171
    INFO = QColor(34, 211, 238)          # #22d3ee
    
    # Border colors
    BORDER_LIGHT = QColor(30, 40, 51)    # #1e2833
    BORDER_DARK = QColor(38, 49, 63)      # #26313f
    
    # 3D viewport colors
    VIEWPORT_BG = QColor(5, 10, 15)      # Very dark for 3D
    GRID_COLOR = QColor(40, 50, 60)      # Grid lines
    AXIS_X = QColor(248, 113, 113)        # Red for X axis
    AXIS_Y = QColor(52, 211, 153)        # Green for Y axis
    AXIS_Z = QColor(56, 189, 248)        # Blue for Z axis
    
    # Reference slide colors
    SLIDE_FRONT = QColor(52, 211, 153, 180)  # Green
    SLIDE_BACK = QColor(251, 191, 36, 180)   # Orange
    SLIDE_LEFT = QColor(56, 189, 248, 180)  # Blue
    SLIDE_RIGHT = QColor(248, 113, 113, 180) # Red


class Fonts:
    """Font definitions"""
    SANS = "System"
    MONO = "Consolas"
    
    @staticmethod
    def get_font(size: int = 10, weight: QFont.Weight = QFont.Normal, family: str = SANS) -> QFont:
        font = QFont(family, size)
        font.setWeight(weight)
        return font


class StyleSheet:
    """Central style sheet manager"""
    
    @staticmethod
    def get_main_stylesheet() -> str:
        """Get the main application stylesheet"""
        return """
        /* Main Application */
        QMainWindow {
            background-color: #0a0e13;
        }
        
        /* Central Widget */
        QWidget#centralWidget {
            background-color: #0a0e13;
        }
        
        /* Tab Widget */
        QTabWidget {
            background-color: #0d1218;
            border: 1px solid #1e2833;
            border-radius: 8px;
        }
        
        QTabWidget::pane {
            background-color: #10151c;
            border: 1px solid #1e2833;
            border-radius: 6px;
            margin: 4px;
        }
        
        QTabBar {
            background-color: #0d1218;
            border: none;
            qproperty-drawBase: false;
        }
        
        QTabBar::tab {
            background-color: #10151c;
            color: #7c8b9d;
            padding: 10px 20px;
            border: 1px solid #1e2833;
            border-bottom: none;
            border-radius: 6px 6px 0 0;
            font: 700 10px "System";
            letter-spacing: 1px;
        }
        
        QTabBar::tab:selected {
            background-color: #161b26;
            color: #d7e0ea;
            border-color: #22d3ee;
        }
        
        QTabBar::tab:hover {
            background-color: #1a212c;
            color: #d7e0ea;
        }
        
        /* Buttons */
        QPushButton {
            background-color: #141b24;
            color: #d7e0ea;
            border: 1px solid #1e2833;
            border-radius: 6px;
            padding: 8px 16px;
            font: 600 11px "System";
            letter-spacing: 0.5px;
            min-width: 80px;
        }
        
        QPushButton:hover {
            border-color: #22d3ee;
            color: #ffffff;
            background-color: rgba(34, 211, 238, 0.1);
        }
        
        QPushButton:pressed {
            background-color: rgba(34, 211, 238, 0.2);
            border-color: #22d3ee;
        }
        
        QPushButton:disabled {
            color: #5b6b7d;
            border-color: #1e2833;
            background-color: #10151c;
        }
        
        /* Accent Buttons */
        QPushButton.acc {
            background-color: rgba(34, 211, 238, 0.12);
            border-color: rgba(34, 211, 238, 0.55);
            color: #22d3ee;
        }
        
        QPushButton.acc:hover {
            background-color: rgba(34, 211, 238, 0.25);
        }
        
        /* Group Box */
        QGroupBox {
            background-color: #10151c;
            border: 1px solid #1e2833;
            border-radius: 8px;
            margin-top: 10px;
            padding: 12px;
        }
        
        QGroupBox::title {
            color: #7c8b9d;
            font: 700 10px "System";
            letter-spacing: 1.2px;
            text-transform: uppercase;
            padding-left: 8px;
            border-left: 2px solid #22d3ee;
        }
        
        /* Labels */
        QLabel {
            color: #d7e0ea;
            font: 12px "System";
        }
        
        QLabel.dim {
            color: #7c8b9d;
        }
        
        QLabel.highlight {
            color: #22d3ee;
        }
        
        /* Line Edits */
        QLineEdit {
            background-color: #141b24;
            color: #d7e0ea;
            border: 1px solid #1e2833;
            border-radius: 5px;
            padding: 6px 10px;
            font: 12px "Consolas";
        }
        
        QLineEdit:hover {
            border-color: #26313f;
        }
        
        QLineEdit:focus {
            border-color: #22d3ee;
            outline: none;
        }
        
        /* Spin Box */
        QSpinBox, QDoubleSpinBox {
            background-color: #141b24;
            color: #d7e0ea;
            border: 1px solid #1e2833;
            border-radius: 5px;
            padding: 4px 8px;
            font: 12px "Consolas";
        }
        
        QSpinBox:hover, QDoubleSpinBox:hover {
            border-color: #26313f;
        }
        
        QSpinBox:focus, QDoubleSpinBox:focus {
            border-color: #22d3ee;
            outline: none;
        }
        
        /* Check Box */
        QCheckBox {
            spacing: 8px;
            color: #d7e0ea;
            font: 12px "System";
        }
        
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border: 1px solid #1e2833;
            border-radius: 4px;
            background-color: #141b24;
        }
        
        QCheckBox::indicator:checked {
            background-color: rgba(34, 211, 238, 0.25);
            border-color: #22d3ee;
        }
        
        QCheckBox::indicator:hover {
            border-color: #26313f;
        }
        
        /* Radio Button */
        QRadioButton {
            spacing: 8px;
            color: #d7e0ea;
            font: 12px "System";
        }
        
        QRadioButton::indicator {
            width: 16px;
            height: 16px;
            border: 1px solid #1e2833;
            border-radius: 8px;
            background-color: #141b24;
        }
        
        QRadioButton::indicator:checked {
            background-color: rgba(34, 211, 238, 0.25);
            border-color: #22d3ee;
        }
        
        /* Slider */
        QSlider::groove:horizontal {
            height: 6px;
            background-color: #141b24;
            border: 1px solid #1e2833;
            border-radius: 3px;
        }
        
        QSlider::handle:horizontal {
            width: 16px;
            height: 16px;
            margin: -5px 0;
            border-radius: 8px;
            background-color: #22d3ee;
        }
        
        QSlider::handle:horizontal:hover {
            background-color: #34d399;
        }
        
        QSlider::add-page:horizontal {
            background-color: #26313f;
            border-radius: 3px;
        }
        
        QSlider::sub-page:horizontal {
            background-color: rgba(34, 211, 238, 0.3);
            border-radius: 3px;
        }
        
        /* Combo Box */
        QComboBox {
            background-color: #141b24;
            color: #d7e0ea;
            border: 1px solid #1e2833;
            border-radius: 5px;
            padding: 6px 10px;
            font: 12px "System";
        }
        
        QComboBox:hover {
            border-color: #26313f;
        }
        
        QComboBox:focus {
            border-color: #22d3ee;
            outline: none;
        }
        
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        
        QComboBox QAbstractItemView {
            background-color: #10151c;
            color: #d7e0ea;
            border: 1px solid #1e2833;
            selection-background-color: rgba(34, 211, 238, 0.3);
            selection-color: #ffffff;
        }
        
        /* Scroll Bar */
        QScrollBar:vertical, QScrollBar:horizontal {
            background-color: #0c1117;
            border: none;
            border-radius: 4px;
        }
        
        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
            background-color: #243040;
            border-radius: 4px;
            min-height: 20px;
            min-width: 20px;
        }
        
        QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
            background-color: #31445c;
        }
        
        QScrollBar::add-line, QScrollBar::sub-line {
            background: none;
            border: none;
        }
        
        /* Status Bar */
        QStatusBar {
            background-color: #0d1218;
            color: #7c8b9d;
            border-top: 1px solid #1e2833;
            font: 11px "System";
        }
        
        /* Status indicators */
        QLabel.status {
            padding: 4px 8px;
            border-radius: 4px;
            font: 700 10px "Consolas";
            letter-spacing: 1px;
        }
        
        QLabel.status.ok {
            color: #34d399;
            background-color: rgba(52, 211, 153, 0.1);
            border: 1px solid rgba(52, 211, 153, 0.45);
        }
        
        QLabel.status.busy {
            color: #fbbf24;
            background-color: rgba(251, 191, 36, 0.1);
            border: 1px solid rgba(251, 191, 36, 0.45);
        }
        
        QLabel.status.err {
            color: #f87171;
            background-color: rgba(248, 113, 113, 0.1);
            border: 1px solid rgba(248, 113, 113, 0.5);
        }
        
        /* Frame */
        QFrame {
            background-color: #10151c;
            border: 1px solid #1e2833;
            border-radius: 6px;
        }
        
        /* Splitter */
        QSplitter::handle {
            background-color: #1e2833;
            width: 1px;
            height: 1px;
        }
        
        /* Tool Tip */
        QToolTip {
            background-color: #1a212c;
            color: #d7e0ea;
            border: 1px solid #26313f;
            border-radius: 4px;
            padding: 6px 10px;
            font: 11px "System";
        }
        """
    
    @staticmethod
    def get_tab_stylesheet() -> str:
        """Get stylesheet specifically for tab widgets"""
        return StyleSheet.get_main_stylesheet()
    
    @staticmethod
    def get_button_stylesheet() -> str:
        """Get stylesheet for buttons"""
        return """
        QPushButton {
            background-color: #141b24;
            color: #d7e0ea;
            border: 1px solid #1e2833;
            border-radius: 6px;
            padding: 8px 16px;
            font: 600 11px "System";
            min-width: 80px;
        }
        
        QPushButton:hover {
            border-color: #22d3ee;
            color: #ffffff;
            background-color: rgba(34, 211, 238, 0.1);
        }
        
        QPushButton:pressed {
            background-color: rgba(34, 211, 238, 0.2);
            border-color: #22d3ee;
        }
        
        QPushButton:disabled {
            color: #5b6b7d;
            border-color: #1e2833;
            background-color: #10151c;
        }
        
        QPushButton.acc {
            background-color: rgba(34, 211, 238, 0.12);
            border-color: rgba(34, 211, 238, 0.55);
            color: #22d3ee;
        }
        
        QPushButton.warn {
            background-color: rgba(251, 191, 36, 0.12);
            border-color: rgba(251, 191, 36, 0.55);
            color: #fbbf24;
        }
        """
    
    @staticmethod
    def get_input_stylesheet() -> str:
        """Get stylesheet for input widgets"""
        return """
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            background-color: #141b24;
            color: #d7e0ea;
            border: 1px solid #1e2833;
            border-radius: 5px;
            padding: 6px 10px;
            font: 12px "Consolas";
        }
        
        QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {
            border-color: #26313f;
        }
        
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
            border-color: #22d3ee;
            outline: none;
        }
        """


class IconManager:
    """Manager for application icons"""
    
    ICONS = {
        'load': "load",
        'save': "save",
        'undo': "undo",
        'redo': "redo",
        'add': "add",
        'remove': "remove",
        'clear': "clear",
        'settings': "settings",
        'export': "export",
        'camera': "camera",
        'brush': "brush",
        'grab': "grab",
        'smooth': "smooth",
        'inflate': "inflate",
        'x_mirror': "x_mirror",
    }
    
    @staticmethod
    def get_icon(name: str) -> QIcon:
        """Get icon by name (placeholder implementation)"""
        # In a real application, you would load actual icons
        # For now, return empty icon
        return QIcon()


def apply_dark_theme(app) -> None:
    """Apply dark theme to application"""
    # Set dark palette
    dark_palette = QPalette()
    
    # Base colors
    dark_palette.setColor(QPalette.Window, Colors.BG_PRIMARY)
    dark_palette.setColor(QPalette.WindowText, Colors.TEXT_PRIMARY)
    dark_palette.setColor(QPalette.Base, Colors.BG_SECONDARY)
    dark_palette.setColor(QPalette.AlternateBase, Colors.BG_TERTIARY)
    dark_palette.setColor(QPalette.ToolTipBase, Colors.BG_PANEL)
    dark_palette.setColor(QPalette.ToolTipText, Colors.TEXT_PRIMARY)
    dark_palette.setColor(QPalette.Text, Colors.TEXT_PRIMARY)
    dark_palette.setColor(QPalette.Button, Colors.BG_SECONDARY)
    dark_palette.setColor(QPalette.ButtonText, Colors.TEXT_PRIMARY)
    dark_palette.setColor(QPalette.BrightText, Colors.ACCENT_CYAN)
    dark_palette.setColor(QPalette.Link, Colors.ACCENT_CYAN)
    dark_palette.setColor(QPalette.Highlight, Colors.ACCENT_CYAN)
    dark_palette.setColor(QPalette.HighlightedText, Colors.BG_PRIMARY)
    
    # Disabled colors
    dark_palette.setColor(QPalette.Disabled, QPalette.Text, Colors.TEXT_DIM)
    dark_palette.setColor(QPalette.Disabled, QPalette.ButtonText, Colors.TEXT_DIM)
    
    # Apply palette
    app.setPalette(dark_palette)
    
    # Set style
    app.setStyle(QStyleFactory.create("Fusion"))
    
    # Apply stylesheet
    app.setStyleSheet(StyleSheet.get_main_stylesheet())
