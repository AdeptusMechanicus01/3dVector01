#!/usr/bin/env python3
"""
3D Vector Pipeline - Main Application Entry Point

A unified desktop application for 3D character modeling from raster images.
Combines vectorization, skeleton construction, and 3D sculpting in a single workflow.
"""

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import Qt modules first to avoid issues
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QSettings

# Import application modules
from ui.main_window import MainWindow


def main():
    """Main application entry point"""
    # Create Qt application
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("3D Vector Pipeline")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("AdeptusMechanicus01")
    app.setOrganizationDomain("github.com")
    
    # Set high DPI scaling for better appearance on high-res displays
    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Execute application
    return app.exec()


if __name__ == "__main__":
    # Run application
    try:
        sys.exit(main())
    except Exception as e:
        print(f"Application error: {e}")
        sys.exit(1)
