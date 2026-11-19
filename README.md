# 3D Vector Pipeline - Python Desktop Application

## Overview
A unified desktop application for 3D character modeling from raster images. Combines vectorization, skeleton construction, and 3D sculpting in a single workflow.

## Features
- **Tab 1: Vectorizer** - Convert raster images (BMP, PNG, JPG) to vector contours with edge detection and background removal
- **Tab 2: Skeleton Builder** - Create and edit character skeletons with mirror symmetry and preset poses
- **Tab 3: 3D Workbench** - Generate 3D mesh from skeleton, sculpt with various tools, and export to GLB format

## Requirements
- Python 3.11+
- See `requirements.txt` for dependencies

## Installation
```bash
pip install -r requirements.txt
```

## Usage
```bash
python main.py
```

## Project Structure
- `main.py` - Main application entry point
- `core/` - Core functionality (vectorization, geometry, 3D generation)
  - `vectorizer.py` - Raster to vector conversion
  - `skeleton.py` - Skeleton data structures and operations
  - `geometry.py` - 3D geometry generation (Marching Cubes, SDF)
  - `sculpting.py` - Sculpting tools implementation
  - `export.py` - GLB export functionality
- `ui/` - User interface components
  - `main_window.py` - Main window with tabs
  - `vectorizer_tab.py` - Vectorizer tab UI
  - `skeleton_tab.py` - Skeleton builder tab UI
  - `workbench_tab.py` - 3D workbench tab UI
  - `styles.py` - Dark theme styles
- `assets/` - Test assets (front.bmp, back.bmp, left.bmp, right.bmp, skeleton_step1.json)

## Keyboard Shortcuts
- **Tab 3 (Workbench)**:
  - Left Click: Inflate (sculpting)
  - Ctrl+Left Click: Deflate (sculpting)
  - Ctrl+Z: Undo
  - Ctrl+Y: Redo
  - X: Toggle X-Mirror

## Technical Details
- **Vectorization**: Uses OpenCV for edge detection, scipy for contour simplification
- **3D Generation**: Uses scikit-image's Marching Cubes for SDF to mesh conversion
- **3D Visualization**: Uses PyVista for interactive 3D viewport
- **Export**: Uses trimesh for GLB export compatible with Unity
- **UI**: PySide6 with modern dark theme

## License
MIT License
