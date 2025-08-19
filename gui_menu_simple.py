# Simple GUI Menu for Tamil Kids Learning Games
import tkinter as tk
from tkinter import ttk
import threading
import math
import time
import cv2
import numpy as np
import traceback

# Toggle verbose debug logging here
DEBUG = False

class SimpleButton(tk.Button):
    def __init__(self, parent, text, command, bg_color="#4CAF50", **kwargs):
        super().__init__(parent, text=text, command=command, 
                        bg=bg_color, fg="white", font=("Arial", 12, "bold"),
                        relief="raised", bd=3, **kwargs)

class TamilGamesGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Tamil Kids Learning Games")
        
        # Fullscreen support
        self.is_fullscreen = False
        self.root.geometry("900x700")  # Increased default size
        self.root.configure(bg="#1e3c72")
        self.root.resizable(True, True)  # Allow resizing
        
        # Bind fullscreen toggle (F11 key)
        self.root.bind('<F11>', self.toggle_fullscreen)
        self.root.bind('<Escape>', self.exit_fullscreen)
        
        # Game state variables
        self.game_running = False
        self.game_canvas = None
        self.photo = None
        self.selected_camera = 0  # Default camera index
        
        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.create_main_menu()

    # --- Camera helpers ---
    def _camera_is_black(self, frame):
        try:
            if frame is None or frame.size == 0:
                return True
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            return float(np.mean(gray)) < 8.0  # very dark/black threshold
        except Exception:
            return True

    def _warmup_and_check(self, cap, frames=8):
        last = None
        for _ in range(frames):
            ret, f = cap.read()
            if not ret:
                continue
            last = f
        return last, (last is not None and not self._camera_is_black(last))

    def _init_camera(self, device_index, width, height, fps):
        # Try DirectShow + MJPG at requested settings
        def open_cap(backend=None):
            try:
                return cv2.VideoCapture(device_index, backend) if backend is not None else cv2.VideoCapture(device_index)
            except Exception:
                return cv2.VideoCapture(device_index)

        tried = []

        # 1) DSHOW + MJPG
        cap = open_cap(cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, fps)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        frame, ok = self._warmup_and_check(cap)
        if ok:
            if DEBUG:
                print("Camera OK: DSHOW+MJPG")
            return cap
        tried.append("DSHOW+MJPG")

        # 2) Enable auto exposure and retry on same cap
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)  # auto on (DirectShow convention)
        cap.set(cv2.CAP_PROP_EXPOSURE, 0)  # reset
        frame, ok = self._warmup_and_check(cap)
        if ok:
            if DEBUG:
                print("Camera OK after auto-exposure: DSHOW+MJPG")
            return cap
        tried.append("auto-exp")

        # 3) DSHOW without MJPG (default codec)
        cap.release()
        cap = open_cap(cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FOURCC, 0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, fps)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        frame, ok = self._warmup_and_check(cap)
        if ok:
            if DEBUG:
                print("Camera OK: DSHOW default codec")
            return cap
        tried.append("DSHOW+default")

        # 4) Default backend
        cap.release()
        cap = open_cap(None)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, fps)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        frame, ok = self._warmup_and_check(cap)
        if ok:
            if DEBUG:
                print("Camera OK: default backend")
            return cap
        tried.append("default backend")

        # 5) Safer baseline: 640x480 @ 30 FPS, default backend
        cap.release()
        cap = open_cap(None)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
        frame, ok = self._warmup_and_check(cap)
        if ok:
            if DEBUG:
                print("Camera OK: baseline 640x480@30")
            return cap
        tried.append("baseline 640x480@30")

        # Failed
        cap.release()
        print(f"❌ Camera initialization failed. Tried: {', '.join(tried)}")
        return None
    
    def toggle_fullscreen(self, event=None):
        """Toggle between fullscreen and windowed mode"""
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes('-fullscreen', self.is_fullscreen)
        
        if self.is_fullscreen:
            print("Switched to fullscreen mode (Press F11 or ESC to exit)")
        else:
            print("Switched to windowed mode")
        
        # Refresh the current view
        if hasattr(self, 'current_view'):
            if self.current_view == 'menu':
                self.create_main_menu()
    
    def exit_fullscreen(self, event=None):
        """Exit fullscreen mode"""
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.root.attributes('-fullscreen', False)
            print("Exited fullscreen mode")
    
    def set_fullscreen_mode(self):
        """Set application to fullscreen mode"""
        self.is_fullscreen = True
        self.root.attributes('-fullscreen', True)
        self.create_main_menu()  # Refresh menu for fullscreen
        
    def create_main_menu(self):
        # Clear the window
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Track current view
        self.current_view = 'menu'
        
        # Main frame
        main_frame = tk.Frame(self.root, bg="#1e3c72")
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Top control frame for fullscreen and other options
        control_frame = tk.Frame(main_frame, bg="#1e3c72")
        control_frame.pack(fill='x', pady=(0, 10))
        
        # Fullscreen button
        fullscreen_text = "🖥️ Exit Fullscreen" if self.is_fullscreen else "🖥️ Fullscreen Mode"
        fullscreen_btn = SimpleButton(control_frame, fullscreen_text, self.toggle_fullscreen, 
                                    bg_color="#34495E", width=15)
        fullscreen_btn.pack(side='right')
        
        # Fullscreen instructions
        if not self.is_fullscreen:
            instructions = tk.Label(control_frame, text="Press F11 for fullscreen", 
                                  font=("Arial", 10), fg="#CCCCCC", bg="#1e3c72")
            instructions.pack(side='right', padx=(0, 10))
        
        # Title
        title_size = 28 if self.is_fullscreen else 24
        title_label = tk.Label(main_frame, text="🎮 TAMIL KIDS LEARNING GAMES 🎮", 
                              font=("Arial", title_size, "bold"), fg="#FFD700", bg="#1e3c72")
        title_label.pack(pady=(20, 30))
        
        # Subtitle
        subtitle_size = 16 if self.is_fullscreen else 14
        subtitle = tk.Label(main_frame, text="Choose your learning adventure!", 
                           font=("Arial", subtitle_size), fg="#FFFFFF", bg="#1e3c72")
        subtitle.pack(pady=10)
        
        # Button frame
        button_frame = tk.Frame(main_frame, bg="#1e3c72")
        button_frame.pack(expand=True, pady=30)
        
        # Menu buttons with adjusted size for fullscreen
        button_width = 40 if self.is_fullscreen else 30
        button_height = 3 if self.is_fullscreen else 2
        
        buttons = [
            ("🎯 Drag-Drop Word Matching", self.start_drag_drop, "#4CAF50"),
            ("🖐️ Finger Counting Game", self.start_finger_count, "#2196F3"),
            ("🦟 Mosquito Killing Game", self.start_mosquito_kill, "#E91E63"),
            ("✍️ Air Tracing Letters", self.start_air_trace, "#FF9800"),
            ("🎨 Color Recognition", self.start_color_game, "#9C27B0"),
            ("🔢 Number Learning", self.start_number_game, "#FF5722"),
            ("📹 Camera Settings", self.show_camera_settings, "#607D8B"),
            ("🚪 Exit", self.exit_game, "#F44336")
        ]
        
        for i, (text, command, color) in enumerate(buttons):
            btn = SimpleButton(button_frame, text, command, bg_color=color, 
                             width=button_width, height=button_height)
            btn.pack(pady=12 if self.is_fullscreen else 10, padx=20, fill='x')
        
        # Footer with camera info and controls
        footer_frame = tk.Frame(main_frame, bg="#1e3c72")
        footer_frame.pack(side='bottom', pady=20)
        
        camera_info = tk.Label(footer_frame, text=f"📹 Current Camera: Device {self.selected_camera}", 
                              font=("Arial", 10), fg="#CCCCCC", bg="#1e3c72")
        camera_info.pack()
        
        footer = tk.Label(footer_frame, text="🌟 Made with ❤️ for Tamil Kids 🌟", 
                         font=("Arial", 12), fg="#FFFFFF", bg="#1e3c72")
        footer.pack(pady=(5, 0))
    
    def on_closing(self):
        """Handle window closing event"""
        self.game_running = False
        try:
            cv2.destroyAllWindows()
        except:
            pass
        self.root.quit()
        self.root.destroy()
    
    def start_drag_drop(self):
        self.hide_menu()
        self.run_drag_drop_game()
    
    def start_finger_count(self):
        self.hide_menu()
        self.run_finger_count_game()
    
    def start_mosquito_kill(self):
        self.hide_menu()
        self.run_mosquito_kill_game()
    
    def start_air_trace(self):
        self.show_coming_soon("✍️ Air Tracing Letters")
    
    def start_color_game(self):
        self.show_coming_soon("🎨 Color Recognition")
    
    def start_number_game(self):
        self.show_coming_soon("🔢 Number Learning")
    
    def get_available_cameras(self):
        """Detect available camera devices"""
        available_cameras = []
        for i in range(5):  # Check first 5 camera indices
            # Prefer DirectShow backend on Windows for lower latency
            try:
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            except Exception:
                cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    available_cameras.append(i)
            cap.release()
        return available_cameras
    
    def show_camera_settings(self):
        """Show camera selection window"""
        # Create camera settings window
        settings_window = tk.Toplevel(self.root)
        settings_window.title("📹 Camera Settings")
        settings_window.geometry("500x400")
        settings_window.configure(bg="#1e3c72")
        settings_window.resizable(False, False)
        
        # Center the window
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Title
        title_label = tk.Label(settings_window, text="📹 Camera Settings", 
                              font=("Arial", 18, "bold"), fg="#FFD700", bg="#1e3c72")
        title_label.pack(pady=20)
        
        # Current camera info
        current_label = tk.Label(settings_window, 
                                text=f"Current Camera: Device {self.selected_camera}", 
                                font=("Arial", 12), fg="#FFFFFF", bg="#1e3c72")
        current_label.pack(pady=10)
        
        # Detecting cameras message
        status_label = tk.Label(settings_window, text="🔍 Detecting available cameras...", 
                               font=("Arial", 12), fg="#FFFF00", bg="#1e3c72")
        status_label.pack(pady=10)
        
        # Camera selection frame
        camera_frame = tk.Frame(settings_window, bg="#1e3c72")
        camera_frame.pack(pady=20, padx=40, fill='both', expand=True)
        
        # Progress bar (fake scanning effect)
        progress = ttk.Progressbar(settings_window, mode='indeterminate')
        progress.pack(pady=10, padx=40, fill='x')
        progress.start()
        
        def detect_and_show_cameras():
            """Detect cameras in background thread"""
            available_cameras = self.get_available_cameras()
            
            # Update UI in main thread
            def update_ui():
                progress.stop()
                progress.destroy()
                
                if not available_cameras:
                    status_label.config(text="❌ No cameras detected!", fg="#FF4444")
                    no_cam_label = tk.Label(camera_frame, 
                                           text="Please check your camera connections\nand try again.", 
                                           font=("Arial", 12), fg="#FFFFFF", bg="#1e3c72")
                    no_cam_label.pack(pady=20)
                else:
                    status_label.config(text=f"✅ Found {len(available_cameras)} camera(s):", fg="#44FF44")
                    
                    # Create radio buttons for camera selection
                    camera_var = tk.IntVar(value=self.selected_camera)
                    
                    for cam_index in available_cameras:
                        camera_text = f"📷 Camera {cam_index}"
                        if cam_index == 0:
                            camera_text += " (Default)"
                        
                        radio_btn = tk.Radiobutton(camera_frame, text=camera_text, 
                                                  variable=camera_var, value=cam_index,
                                                  font=("Arial", 12), fg="#FFFFFF", bg="#1e3c72",
                                                  selectcolor="#4CAF50", activebackground="#1e3c72")
                        radio_btn.pack(anchor='w', pady=5, padx=20)
                    
                    # Test camera button
                    def test_camera():
                        test_index = camera_var.get()
                        self.test_camera_preview(test_index)
                    
                    test_btn = SimpleButton(camera_frame, "🔍 Test Selected Camera", 
                                          test_camera, bg_color="#2196F3", width=20)
                    test_btn.pack(pady=15)
                    
                    # Save button
                    def save_camera_settings():
                        self.selected_camera = camera_var.get()
                        current_label.config(text=f"Current Camera: Device {self.selected_camera}")
                        # Show confirmation
                        status_label.config(text=f"✅ Camera {self.selected_camera} selected!", fg="#44FF44")
                        settings_window.after(1500, settings_window.destroy)
                    
                    save_btn = SimpleButton(camera_frame, "💾 Save Settings", 
                                          save_camera_settings, bg_color="#4CAF50", width=20)
                    save_btn.pack(pady=10)
                
                # Close button
                close_btn = SimpleButton(settings_window, "❌ Close", 
                                        settings_window.destroy, bg_color="#F44336", width=15)
                close_btn.pack(side='bottom', pady=20)
            
            settings_window.after(2000, update_ui)  # Simulate scanning delay
        
        # Start detection in background
        threading.Thread(target=detect_and_show_cameras, daemon=True).start()
    
    def test_camera_preview(self, camera_index):
        """Show a test preview of the selected camera"""
        preview_window = tk.Toplevel(self.root)
        preview_window.title(f"📷 Camera {camera_index} Preview")
        preview_window.geometry("640x520")
        preview_window.configure(bg="#000000")
        
        # Title
        title_label = tk.Label(preview_window, text=f"Camera {camera_index} Test Preview", 
                              font=("Arial", 14, "bold"), fg="#FFFFFF", bg="#000000")
        title_label.pack(pady=10)
        
        # Canvas for video
        preview_canvas = tk.Canvas(preview_window, width=640, height=480, bg="#000000")
        preview_canvas.pack()
        
        # Control buttons
        control_frame = tk.Frame(preview_window, bg="#000000")
        control_frame.pack(fill='x', pady=5)
        
        close_btn = SimpleButton(control_frame, "✅ Looks Good", 
                                preview_window.destroy, bg_color="#4CAF50")
        close_btn.pack(side='right', padx=10)
        
        # Start camera preview
        # Prefer DirectShow backend on Windows; configure for smooth preview
        try:
            cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        except Exception:
            cap = cv2.VideoCapture(camera_index)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        preview_running = True
        
        def update_preview():
            if preview_running and preview_window.winfo_exists():
                ret, frame = cap.read()
                if ret:
                    frame = cv2.flip(frame, 1)
                    frame = cv2.resize(frame, (640, 480))
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Convert to tkinter format
                    from PIL import Image, ImageTk
                    img_pil = Image.fromarray(frame_rgb)
                    img_tk = ImageTk.PhotoImage(img_pil)
                    
                    preview_canvas.delete("all")
                    preview_canvas.create_image(320, 240, image=img_tk)
                    preview_canvas.image = img_tk  # Keep reference
                    
                preview_window.after(30, update_preview)
        
        def on_preview_close():
            nonlocal preview_running
            preview_running = False
            cap.release()
            preview_window.destroy()
        
        preview_window.protocol("WM_DELETE_WINDOW", on_preview_close)
        update_preview()
    
    def show_coming_soon(self, feature):
        # Create a simple coming soon window
        popup = tk.Toplevel(self.root)
        popup.title("Coming Soon")
        popup.geometry("400x200")
        popup.configure(bg="#1e3c72")
        popup.resizable(False, False)
        
        # Center the popup
        popup.transient(self.root)
        popup.grab_set()
        
        label = tk.Label(popup, text=f"🚧 {feature}\nComing Soon! 🚧", 
                        font=("Arial", 16), fg="#FFFFFF", bg="#1e3c72")
        label.pack(expand=True, pady=50)
        
        ok_btn = SimpleButton(popup, "OK", popup.destroy, width=10)
        ok_btn.pack(pady=20)
    
    def hide_menu(self):
        for widget in self.root.winfo_children():
            widget.destroy()
    
    def show_menu(self):
        self.game_running = False
        try:
            cv2.destroyAllWindows()
        except:
            pass
        self.create_main_menu()
    
    def create_game_header(self, title):
        # Adjust header size for fullscreen
        header_height = 100 if self.is_fullscreen else 80
        title_font_size = 18 if self.is_fullscreen else 16
        
        header_frame = tk.Frame(self.root, bg="#1e3c72", height=header_height)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)
        
        # Left side - Back button and fullscreen toggle
        left_frame = tk.Frame(header_frame, bg="#1e3c72")
        left_frame.pack(side='left', padx=20, pady=10)
        
        # Back to menu button
        back_btn = SimpleButton(left_frame, "⬅️ Back to Menu", self.show_menu, 
                              bg_color="#FF5722", width=12)
        back_btn.pack(side='left', padx=(0, 10))
        
        # Fullscreen toggle in games
        fullscreen_text = "🖥️ Exit FS" if self.is_fullscreen else "🖥️ Fullscreen"
        fullscreen_btn = SimpleButton(left_frame, fullscreen_text, self.toggle_fullscreen, 
                                    bg_color="#34495E", width=10)
        fullscreen_btn.pack(side='left')
        
        # Center - Game title
        title_label = tk.Label(header_frame, text=title, 
                              font=("Arial", title_font_size, "bold"), 
                              fg="#FFD700", bg="#1e3c72")
        title_label.pack(expand=True)
        
        # Right side - Instructions
        if not self.is_fullscreen:
            instruction_label = tk.Label(header_frame, text="Press F11 for fullscreen", 
                                       font=("Arial", 9), fg="#CCCCCC", bg="#1e3c72")
            instruction_label.pack(side='right', padx=20, pady=10)
        
        return header_frame
    
    def run_drag_drop_game(self):
        try:
            from game_logic import DragDropGame
            
            self.create_game_header("🎯 Drag-Drop Word Matching")
            
            game_frame = tk.Frame(self.root, bg="#000000")
            game_frame.pack(fill='both', expand=True)
            
            self.game_canvas = tk.Canvas(game_frame, bg="#000000")
            self.game_canvas.pack(fill='both', expand=True)
            
            # Force canvas to update its size
            self.root.update_idletasks()
            
            self.game_running = True
            # Small delay to ensure canvas is ready
            self.root.after(100, lambda: threading.Thread(target=self._drag_drop_thread, daemon=True).start())
            
        except ImportError as e:
            self.show_error(f"Game module not found: {e}")
    
    def _drag_drop_thread(self):
        # Robust camera open with fallbacks
        cap = self._init_camera(self.selected_camera, 800, 600, 60)
        if cap is None:
            self.show_error("Camera failed to initialize. Try Camera Settings and a different device.")
            self.game_running = False
            if self.root.winfo_exists():
                self.root.after(100, self.show_menu)
            return
        
        # Frame smoothing variables for anti-shutter
        prev_frame = None
        frame_alpha = 0.8  # Smoothing factor (higher = less smoothing)
        
        try:
            from game_logic import DragDropGame
            game = DragDropGame()
            game_initialized = False
            
            print("Starting drag-drop game with smooth video...")
            
            while self.game_running and self.root.winfo_exists():
                ret, img = cap.read()
                
                if not ret or img is None:
                    continue
                
                # Anti-shutter frame smoothing
                if prev_frame is not None and prev_frame.shape == img.shape:
                    img = cv2.addWeighted(img, frame_alpha, prev_frame, 1 - frame_alpha, 0)
                prev_frame = img.copy()
                
                # Simple mirror flip
                img = cv2.flip(img, 1)
                h, w = img.shape[:2]
                
                if not game_initialized:
                    game.setup_game(w, h)
                    game_initialized = True
                
                # Process hand tracking
                try:
                    img = game.hand_tracker.find_hands(img, draw=True)
                    game.handle_game_logic(img)
                    game.draw_game_ui(img)
                except Exception as e:
                    print(f"Hand tracking error: {e}")
                    continue
                
                # Update canvas
                try:
                    self.update_canvas(img)
                except Exception as e:
                    print(f"Canvas update error: {e}")
                    continue
                
                # Controlled frame rate for smooth video (~50-60 FPS)
                import time
                time.sleep(0.018)
                
                if game.game_complete:
                    print("Game completed!")
                    self.game_running = False
                    if self.root.winfo_exists():
                        self.root.after(2000, self.show_menu)
                    break
                    
        except Exception as e:
            print(f"Game error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            try:
                cap.release()
                cv2.destroyAllWindows()
                print("Camera resources released")
            except:
                pass
    
    def run_finger_count_game(self):
        try:
            self.create_game_header("🖐️ Tamil Finger Counting Game")
            
            game_frame = tk.Frame(self.root, bg="#000000")
            game_frame.pack(fill='both', expand=True)
            
            self.game_canvas = tk.Canvas(game_frame, bg="#000000")
            self.game_canvas.pack(fill='both', expand=True)
            
            # Force canvas to update its size
            self.root.update_idletasks()
            
            self.game_running = True
            # Small delay to ensure canvas is ready
            self.root.after(100, lambda: threading.Thread(target=self._finger_count_thread, daemon=True).start())
            
        except Exception as e:
            self.show_error(f"Error starting game: {e}")
    
    def _finger_count_thread(self):
        # Use the new FingerCountGame class from game_logic.py
        try:
            from game_logic import FingerCountGame
            import cv2
            import time
            
            # Robust camera open with fallbacks
            cap = self._init_camera(self.selected_camera, 800, 600, 60)
            if cap is None:
                self.show_error("Camera failed to initialize. Try Camera Settings and a different device.")
                return
            
            # Simple camera warmup
            print("Starting camera...")
            for i in range(5):
                ret, _ = cap.read()
                time.sleep(0.1)
            
            game = FingerCountGame()
            game_initialized = False
            
            print("Starting finger counting game...")
            
            # Frame smoothing state
            prev_frame = None
            frame_alpha = 0.8

            while self.game_running and self.root.winfo_exists():
                ret, img = cap.read()
                if not ret or img is None:
                    continue
                
                # Anti-shutter frame smoothing
                if prev_frame is not None and prev_frame.shape == img.shape:
                    img = cv2.addWeighted(img, frame_alpha, prev_frame, 1 - frame_alpha, 0)
                prev_frame = img.copy()

                # Simple mirror flip
                img = cv2.flip(img, 1)
                h, w = img.shape[:2]
                
                # Initialize game on first frame
                if not game_initialized:
                    game.setup_game(w, h)
                    game_initialized = True
                
                # Process hand tracking
                try:
                    img = game.hand_tracker.find_hands(img, draw=True)
                    game.handle_game_logic(img)
                    game.draw_game_ui(img)
                except Exception as e:
                    print(f"Hand tracking error: {e}")
                    continue
                
                # Update canvas
                try:
                    self.update_canvas(img)
                except Exception as e:
                    print(f"Canvas update error: {e}")
                    continue
                
                # Check for game completion
                if game.game_complete:
                    print("Game completed!")
                    time.sleep(2)
                    break
                
                # Simple frame rate control (~50-60 FPS)
                time.sleep(0.018)
                
        except Exception as e:
            print(f"Error initializing finger count game: {e}")
            # Fallback error message
            try:
                if hasattr(self, 'canvas'):
                    self.canvas.create_text(400, 200, text=f"Finger Count Game Error: {e}", 
                                          font=("Arial", 16), fill="red")
            except:
                pass
        finally:
            if 'cap' in locals():
                cap.release()
            print("Finger count game thread finished.")
            self.game_running = False
            # Return to menu when game ends
            if self.root.winfo_exists():
                self.root.after(100, self.show_menu)
    
    def run_mosquito_kill_game(self):
        try:
            self.create_game_header("🦟 Tamil Mosquito Killing Game")
            
            game_frame = tk.Frame(self.root, bg="#000000")
            game_frame.pack(fill='both', expand=True)
            
            self.game_canvas = tk.Canvas(game_frame, bg="#000000")
            self.game_canvas.pack(fill='both', expand=True)
            
            # Force canvas to update its size
            self.root.update_idletasks()
            
            self.game_running = True
            # Small delay to ensure canvas is ready
            self.root.after(100, lambda: threading.Thread(target=self._mosquito_kill_thread, daemon=True).start())
            
        except Exception as e:
            self.show_error(f"Error starting mosquito game: {e}")

    def _mosquito_kill_thread(self):
        # Use the new MosquitoKillGame class from game_logic.py
        try:
            from game_logic import MosquitoKillGame
            import cv2
            import time
            
            # Robust camera open with fallbacks
            cap = self._init_camera(self.selected_camera, 800, 600, 60)
            if cap is None:
                self.show_error("Camera failed to initialize. Try Camera Settings and a different device.")
                return
            
            # Simple camera warmup
            print("Starting camera...")
            for i in range(5):
                ret, _ = cap.read()
                time.sleep(0.1)
            
            game = MosquitoKillGame()
            game_initialized = False
            
            print("Starting mosquito killing game...")
            
            # Frame smoothing state
            prev_frame = None
            frame_alpha = 0.8

            while self.game_running and self.root.winfo_exists():
                ret, img = cap.read()
                if not ret or img is None:
                    continue
                
                # Anti-shutter frame smoothing
                if prev_frame is not None and prev_frame.shape == img.shape:
                    img = cv2.addWeighted(img, frame_alpha, prev_frame, 1 - frame_alpha, 0)
                prev_frame = img.copy()

                # Simple mirror flip
                img = cv2.flip(img, 1)
                h, w = img.shape[:2]
                
                # Initialize game on first frame
                if not game_initialized:
                    game.setup_game(w, h)
                    game_initialized = True
                
                # Process hand tracking
                try:
                    img = game.hand_tracker.find_hands(img, draw=True)
                    game.handle_game_logic(img)
                    game.draw_game_ui(img)
                except Exception as e:
                    print(f"Hand tracking error: {e}")
                    continue
                
                # Update canvas
                try:
                    self.update_canvas(img)
                except Exception as e:
                    print(f"Canvas update error: {e}")
                    continue
                
                # Check for game completion
                if game.game_complete:
                    print("Game completed!")
                    time.sleep(2)
                    break
                
                # Simple frame rate control (~50-60 FPS)
                time.sleep(0.018)
                
        except Exception as e:
            print(f"Error initializing mosquito kill game: {e}")
            # Fallback error message
            try:
                if hasattr(self, 'canvas'):
                    self.canvas.create_text(400, 200, text=f"Mosquito Kill Game Error: {e}", 
                                          font=("Arial", 16), fill="red")
            except:
                pass
        finally:
            if 'cap' in locals():
                cap.release()
            print("Mosquito kill game thread finished.")
            self.game_running = False
            # Return to menu when game ends
            if self.root.winfo_exists():
                self.root.after(100, self.show_menu)
    
    def update_canvas(self, img):
        try:
            from PIL import Image, ImageTk
            
            # Debug: Check if canvas exists
            if not hasattr(self, 'game_canvas') or self.game_canvas is None:
                print("❌ Canvas update error: game_canvas not initialized")
                return
            
            # Get current canvas dimensions
            canvas_width = self.game_canvas.winfo_width()
            canvas_height = self.game_canvas.winfo_height()
            
            # Debug: Print canvas dimensions (only first few times)
            if canvas_width <= 1 or canvas_height <= 1:
                if DEBUG:
                    print(f"⚠️ Canvas not ready: {canvas_width}x{canvas_height}")
                # Try again later
                self.root.after(10, lambda: self.update_canvas(img))
                return
            
            # Validate image before processing
            if img is None or img.size == 0:
                if DEBUG:
                    print("❌ Invalid image received for canvas update")
                return
            
            # Only print debug info occasionally
            if not hasattr(self, '_debug_counter'):
                self._debug_counter = 0
            self._debug_counter += 1
            
            if DEBUG and self._debug_counter % 100 == 1:  # Print every 100th frame
                print(f"📷 Canvas update: img={img.shape}, canvas={canvas_width}x{canvas_height}")
            
            # Convert BGR to RGB
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Create PIL image
            img_pil = Image.fromarray(img_rgb)
            
            # Resize to fit canvas while maintaining aspect ratio
            img_aspect = img_pil.width / img_pil.height
            canvas_aspect = canvas_width / canvas_height
            
            if img_aspect > canvas_aspect:
                # Image is wider, fit to width
                new_width = canvas_width
                new_height = int(canvas_width / img_aspect)
            else:
                # Image is taller, fit to height
                new_height = canvas_height
                new_width = int(canvas_height * img_aspect)
            
            # Resize with high quality
            img_pil = img_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            self.photo = ImageTk.PhotoImage(img_pil)
            
            # Clear canvas and add new image
            self.game_canvas.delete("all")
            
            # Center the image on canvas
            x_offset = (canvas_width - new_width) // 2
            y_offset = (canvas_height - new_height) // 2
            
            self.game_canvas.create_image(x_offset, y_offset, anchor=tk.NW, image=self.photo)
            
            # Only print success message occasionally
            if DEBUG and self._debug_counter % 100 == 1:
                print("✅ Canvas updated successfully")
                
        except ImportError:
            print("❌ PIL/Pillow not available for image processing")
        except Exception as e:
            print(f"❌ Canvas update error: {e}")
            import traceback
            traceback.print_exc()
            # Don't raise exception to prevent crashes
    
    def show_error(self, message):
        popup = tk.Toplevel(self.root)
        popup.title("Error")
        popup.geometry("400x200")
        popup.configure(bg="#1e3c72")
        popup.resizable(False, False)
        
        popup.transient(self.root)
        popup.grab_set()
        
        label = tk.Label(popup, text=f"❌ Error:\n{message}", 
                        font=("Arial", 12), fg="#FFFFFF", bg="#1e3c72")
        label.pack(expand=True, pady=30)
        
        ok_btn = SimpleButton(popup, "OK", lambda: [popup.destroy(), self.show_menu()], width=10)
        ok_btn.pack(pady=20)
    
    def exit_game(self):
        popup = tk.Toplevel(self.root)
        popup.title("Exit Confirmation")
        popup.geometry("350x200")
        popup.configure(bg="#1e3c72")
        popup.resizable(False, False)
        
        popup.transient(self.root)
        popup.grab_set()
        popup.protocol("WM_DELETE_WINDOW", popup.destroy)
        
        msg_label = tk.Label(popup, text="👋 Thank you for playing!\n🌟 Keep learning Tamil! 🌟", 
                           font=("Arial", 12), fg="#FFFFFF", bg="#1e3c72")
        msg_label.pack(pady=30)
        
        btn_frame = tk.Frame(popup, bg="#1e3c72")
        btn_frame.pack(pady=20)
        
        yes_btn = SimpleButton(btn_frame, "Yes, Exit", self.on_closing, 
                              bg_color="#F44336", width=12)
        yes_btn.pack(side='left', padx=10)
        
        no_btn = SimpleButton(btn_frame, "Keep Playing", popup.destroy, 
                             bg_color="#4CAF50", width=12)
        no_btn.pack(side='left', padx=10)
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = TamilGamesGUI()
    app.run()
