#!/usr/bin/env python3
"""
Test script for 3D Vector Pipeline application
"""

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        from core.vectorizer import Vectorizer, Contour, ROI
        print("✓ core.vectorizer")
    except ImportError as e:
        print(f"✗ core.vectorizer: {e}")
        return False
    
    try:
        from core.skeleton import Skeleton, Joint, JointRole, BodyContour
        print("✓ core.skeleton")
    except ImportError as e:
        print(f"✗ core.skeleton: {e}")
        return False
    
    try:
        from core.geometry import Mesh, MeshGenerator, SDFGenerator, ReferenceSlide
        print("✓ core.geometry")
    except ImportError as e:
        print(f"✗ core.geometry: {e}")
        return False
    
    try:
        from core.sculpting import SculptingTools, BrushSettings, SculptTool
        print("✓ core.sculpting")
    except ImportError as e:
        print(f"✗ core.sculpting: {e}")
        return False
    
    try:
        from core.export import GLBExporter, ExportManager
        print("✓ core.export")
    except ImportError as e:
        print(f"✗ core.export: {e}")
        return False
    
    return True


def test_vectorizer():
    """Test vectorizer functionality"""
    print("\nTesting vectorizer...")
    
    from core.vectorizer import Vectorizer, Contour, ROI
    
    # Create vectorizer
    vec = Vectorizer()
    print("✓ Vectorizer created")
    
    # Test contour creation
    contour = Contour(
        points=[(0, 0), (1, 0), (1, 1), (0, 1)],
        is_closed=True,
        is_external=True
    )
    print("✓ Contour created")
    
    # Test ROI creation
    roi = ROI(x=0, y=0, width=100, height=100)
    print("✓ ROI created")
    
    return True


def test_skeleton():
    """Test skeleton functionality"""
    print("\nTesting skeleton...")
    
    from core.skeleton import Skeleton, Joint, JointRole
    
    # Create skeleton
    skeleton = Skeleton()
    print("✓ Skeleton created")
    
    # Create T-pose
    skeleton.create_preset_t_pose()
    print(f"✓ T-pose created with {skeleton.get_joint_count()} joints")
    
    # Create A-pose
    skeleton.create_preset_a_pose()
    print(f"✓ A-pose created with {skeleton.get_joint_count()} joints")
    
    # Test JSON serialization
    json_str = skeleton.to_json()
    print("✓ Skeleton serialized to JSON")
    
    # Test loading from JSON
    skeleton2 = Skeleton.from_json(json_str)
    print("✓ Skeleton loaded from JSON")
    
    return True


def test_geometry():
    """Test geometry functionality"""
    print("\nTesting geometry...")
    
    from core.geometry import Mesh, MeshGenerator, SDFGenerator
    
    # Create mesh generator
    gen = MeshGenerator()
    print("✓ MeshGenerator created")
    
    # Create SDF generator
    sdf_gen = SDFGenerator()
    print("✓ SDFGenerator created")
    
    return True


def test_sculpting():
    """Test sculpting functionality"""
    print("\nTesting sculpting...")
    
    from core.sculpting import SculptingTools, BrushSettings, SculptTool
    
    # Create sculpting tools
    tools = SculptingTools()
    print("✓ SculptingTools created")
    
    # Create brush settings
    brush = BrushSettings()
    print("✓ BrushSettings created")
    
    return True


def test_export():
    """Test export functionality"""
    print("\nTesting export...")
    
    from core.export import GLBExporter, ExportManager
    
    # Create exporter
    exporter = GLBExporter()
    print("✓ GLBExporter created")
    
    # Create export manager
    manager = ExportManager()
    print("✓ ExportManager created")
    
    return True


def test_skeleton_loading():
    """Test loading skeleton from file"""
    print("\nTesting skeleton file loading...")
    
    from core.skeleton import Skeleton
    
    # Load skeleton from file
    skeleton = Skeleton.load_from_file('skeleton_step1.json')
    if skeleton:
        print(f"✓ Loaded skeleton with {skeleton.get_joint_count()} joints")
        print(f"✓ Loaded {skeleton.get_bone_count()} bones")
        return True
    else:
        print("✗ Failed to load skeleton from file")
        return False


def test_qt_application():
    """Test Qt application (non-GUI)"""
    print("\nTesting Qt application...")
    
    # Test that Qt can be imported
    try:
        from PySide6.QtWidgets import QApplication, QLabel
        from PySide6.QtCore import Qt
        print("✓ PySide6 imports work")
        return True
    except ImportError as e:
        print(f"✗ PySide6 imports: {e}")
        return False


def test_assets():
    """Test loading assets from repository"""
    print("\nTesting assets...")
    
    from pathlib import Path
    
    # Check for test assets
    assets = ['front.bmp', 'back.bmp', 'left.bmp', 'right.bmp', 'skeleton_step1.json']
    repo_path = Path(__file__).parent
    
    found = []
    for asset in assets:
        asset_path = repo_path / asset
        if asset_path.exists():
            found.append(asset)
            print(f"✓ Found {asset}")
    
    if found:
        print(f"✓ Found {len(found)} test assets")
    else:
        print("✗ No test assets found")
    
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("3D Vector Pipeline - Test Suite")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Vectorizer", test_vectorizer),
        ("Skeleton", test_skeleton),
        ("Geometry", test_geometry),
        ("Sculpting", test_sculpting),
        ("Export", test_export),
        ("Skeleton Loading", test_skeleton_loading),
        ("Qt Application", test_qt_application),
        ("Assets", test_assets),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"✗ {name} test failed")
        except Exception as e:
            failed += 1
            print(f"✗ {name} test failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
