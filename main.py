# Entry point with GUI menu for Tamil Kids Learning Games

import sys
import tkinter as tk

def main():
    try:
        from gui_menu_simple import TamilGamesGUI
        print("🚀 Starting Tamil Kids Learning Games...")
        app = TamilGamesGUI()
        
        # Make sure the window is visible and focused
        app.root.lift()
        app.root.attributes('-topmost', True)
        app.root.after_idle(lambda: app.root.attributes('-topmost', False))
        app.root.focus_force()
        
        # Display initial instructions
        print("💡 Tips:")
        print("   - Press F11 to toggle fullscreen mode")
        print("   - Press ESC to exit fullscreen")
        print("   - Click 'Fullscreen Mode' button in menu")
        print("   - Larger window provides better game experience!")
        
        app.run()
    except ImportError as e:
        print(f"❌ Error: Required modules not found - {e}")
        print("Please install required packages: pip install opencv-python mediapipe pillow")
        input("Press Enter to exit...")
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
