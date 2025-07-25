#!/usr/bin/env python3
"""
Quick camera test to debug the camera visibility issue
"""

import cv2
import time

def test_camera():
    print("🔍 Testing camera access...")
    
    # Test camera 0 (default)
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Error: Could not open camera 0")
        return False
    
    print("✅ Camera 0 opened successfully")
    
    # Set basic properties
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    print("📹 Starting camera preview...")
    print("Press 'q' to quit")
    
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        
        if not ret:
            print(f"❌ Failed to read frame {frame_count}")
            continue
            
        frame_count += 1
        
        # Mirror the frame
        frame = cv2.flip(frame, 1)
        
        # Add frame counter
        cv2.putText(frame, f"Frame: {frame_count}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        cv2.putText(frame, "Press 'q' to quit", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Show the frame
        cv2.imshow("Camera Test", frame)
        
        # Check for 'q' key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    print(f"✅ Camera test completed. Total frames: {frame_count}")
    return True

if __name__ == "__main__":
    print("🎥 Tamil Games - Camera Test")
    print("=" * 40)
    
    try:
        test_camera()
    except Exception as e:
        print(f"❌ Camera test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 40)
    print("🎮 If this test works, the camera is functional!")
    input("Press Enter to exit...")
