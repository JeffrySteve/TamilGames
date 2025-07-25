# Diagnostic version of main.py for debugging camera issues

import sys
import tkinter as tk

def test_camera_basic():
    """Test basic camera functionality"""
    try:
        import cv2
        print("✅ OpenCV imported successfully")
        
        # Test camera access
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print("✅ Camera 0 is working - captured a frame")
                print(f"   Frame shape: {frame.shape}")
            else:
                print("❌ Camera 0 opened but cannot read frames")
            cap.release()
        else:
            print("❌ Cannot open camera 0")
            
    except ImportError as e:
        print(f"❌ OpenCV import error: {e}")
    except Exception as e:
        print(f"❌ Camera test error: {e}")

def test_dependencies():
    """Test all required dependencies"""
    print("🔍 Testing dependencies...")
    
    # Test OpenCV
    try:
        import cv2
        print(f"✅ OpenCV version: {cv2.__version__}")
    except ImportError:
        print("❌ OpenCV not installed")
        return False
    
    # Test MediaPipe
    try:
        import mediapipe as mp
        print(f"✅ MediaPipe version: {mp.__version__}")
    except ImportError:
        print("❌ MediaPipe not installed")
        return False
    
    # Test PIL/Pillow
    try:
        from PIL import Image, ImageTk
        print(f"✅ PIL/Pillow available")
    except ImportError:
        print("❌ PIL/Pillow not installed")
        return False
    
    # Test numpy
    try:
        import numpy as np
        print(f"✅ NumPy version: {np.__version__}")
    except ImportError:
        print("❌ NumPy not installed")
        return False
    
    return True

def main():
    print("🎥 Tamil Games - Diagnostic Mode")
    print("=" * 50)
    
    # Test dependencies first
    if not test_dependencies():
        print("\n❌ Some dependencies are missing!")
        print("Please install with: pip install opencv-python mediapipe pillow numpy")
        input("Press Enter to exit...")
        return
    
    print("\n🔍 Testing camera access...")
    test_camera_basic()
    
    print("\n🚀 Starting GUI application...")
    
    try:
        from gui_menu_simple import TamilGamesGUI
        print("✅ GUI module imported successfully")
        
        app = TamilGamesGUI()
        print("✅ GUI app created successfully")
        
        # Make sure the window is visible and focused
        app.root.lift()
        app.root.attributes('-topmost', True)
        app.root.after_idle(lambda: app.root.attributes('-topmost', False))
        app.root.focus_force()
        
        # Display diagnostic info
        print("\n💡 Diagnostic Tips:")
        print("   - If camera test above worked, camera hardware is OK")
        print("   - Try different games to see which one has camera issues")
        print("   - Check console output for error messages")
        print("   - Press F11 for fullscreen mode")
        print("   - Try Camera Settings to test camera preview")
        
        app.run()
        
    except ImportError as e:
        print(f"❌ Error importing GUI: {e}")
        print("Check if all files are present:")
        print("  - gui_menu_simple.py")
        print("  - game_logic.py")
        print("  - hand_tracker.py")
        print("  - utils.py")
        input("Press Enter to exit...")
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
