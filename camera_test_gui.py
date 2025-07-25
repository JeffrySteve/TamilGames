#!/usr/bin/env python3
"""
Minimal camera display test for debugging GUI integration
"""

import tkinter as tk
import cv2
import threading
import time
from PIL import Image, ImageTk

class CameraTest:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Camera Display Test")
        self.root.geometry("800x600")
        self.root.configure(bg="#000000")
        
        # Create canvas
        self.canvas = tk.Canvas(self.root, bg="#000000")
        self.canvas.pack(fill='both', expand=True)
        
        # Control variables
        self.running = False
        self.photo = None
        
        # Control buttons
        button_frame = tk.Frame(self.root, bg="#333333")
        button_frame.pack(fill='x', pady=5)
        
        start_btn = tk.Button(button_frame, text="▶️ Start Camera", 
                             command=self.start_camera, font=("Arial", 12))
        start_btn.pack(side='left', padx=10)
        
        stop_btn = tk.Button(button_frame, text="⏹️ Stop Camera", 
                            command=self.stop_camera, font=("Arial", 12))
        stop_btn.pack(side='left', padx=10)
        
        quit_btn = tk.Button(button_frame, text="❌ Quit", 
                            command=self.quit_app, font=("Arial", 12))
        quit_btn.pack(side='right', padx=10)
        
        # Status label
        self.status_label = tk.Label(button_frame, text="📹 Camera Ready", 
                                   font=("Arial", 10), fg="white", bg="#333333")
        self.status_label.pack(side='right', padx=20)
        
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
    
    def start_camera(self):
        if not self.running:
            self.running = True
            self.status_label.config(text="📹 Starting camera...")
            self.root.update_idletasks()
            threading.Thread(target=self.camera_thread, daemon=True).start()
    
    def stop_camera(self):
        self.running = False
        self.status_label.config(text="📹 Camera stopped")
    
    def quit_app(self):
        self.running = False
        self.root.quit()
        self.root.destroy()
    
    def camera_thread(self):
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                self.status_label.config(text="❌ Camera failed to open")
                return
            
            # Basic camera settings
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 30)
            
            self.status_label.config(text="📹 Camera running")
            
            frame_count = 0
            
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    continue
                
                frame_count += 1
                
                # Mirror and resize
                frame = cv2.flip(frame, 1)
                
                # Add frame counter
                cv2.putText(frame, f"Frame: {frame_count}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                # Update display
                self.update_display(frame)
                
                # Update status occasionally
                if frame_count % 100 == 1:
                    self.status_label.config(text=f"📹 Frame {frame_count}")
                
                time.sleep(0.03)  # ~30 FPS
            
            cap.release()
            self.status_label.config(text="📹 Camera stopped")
            
        except Exception as e:
            print(f"Camera thread error: {e}")
            self.status_label.config(text=f"❌ Error: {e}")
    
    def update_display(self, frame):
        try:
            # Get canvas dimensions
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width <= 1 or canvas_height <= 1:
                return
            
            # Convert to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(frame_rgb)
            
            # Resize to fit canvas
            img_aspect = img_pil.width / img_pil.height
            canvas_aspect = canvas_width / canvas_height
            
            if img_aspect > canvas_aspect:
                new_width = canvas_width
                new_height = int(canvas_width / img_aspect)
            else:
                new_height = canvas_height
                new_width = int(canvas_height * img_aspect)
            
            img_pil = img_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            self.photo = ImageTk.PhotoImage(img_pil)
            
            # Update canvas
            self.canvas.delete("all")
            
            x_offset = (canvas_width - new_width) // 2
            y_offset = (canvas_height - new_height) // 2
            
            self.canvas.create_image(x_offset, y_offset, anchor=tk.NW, image=self.photo)
            
        except Exception as e:
            print(f"Display update error: {e}")
    
    def run(self):
        print("🎥 Camera Display Test")
        print("Click 'Start Camera' to begin")
        self.root.mainloop()

if __name__ == "__main__":
    app = CameraTest()
    app.run()
