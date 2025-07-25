# Utility functions
from PIL import ImageFont, ImageDraw, Image
import numpy as np
import cv2
import os

def draw_tamil_text(img, text, position=(50, 50), font_size=40, color=(255, 255, 255)):
    """
    Draw Tamil text on OpenCV image using PIL for proper Unicode support
    Returns the modified image with Tamil text drawn
    """
    try:
        # Convert OpenCV image (BGR) to PIL Image (RGB)
        img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        
        # Try Tamil-supporting fonts in order of preference
        font_paths = [
            "assets/fonts/Latha.ttf",  # Local Tamil font (already exists!)
            "C:/Windows/Fonts/LATHA.TTF",  # System Tamil font on Windows
            "C:/Windows/Fonts/Mangal.ttf",  # Another Tamil font
            "C:/Windows/Fonts/arial.ttf",
        ]
        
        font = None
        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, font_size)
                    break
            except:
                continue
        
        if font is None:
            font = ImageFont.load_default()
        
        draw = ImageDraw.Draw(img_pil)
        # Convert BGR color to RGB for PIL
        rgb_color = (color[2], color[1], color[0])
        draw.text(position, text, font=font, fill=rgb_color)
        
        # Convert back to OpenCV image (BGR)
        img_result = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        return img_result
        
    except Exception as e:
        print(f"Error drawing Tamil text: {e}")
        # Fallback to OpenCV text
        cv2.putText(img, text, position, cv2.FONT_HERSHEY_SIMPLEX, font_size/30, color, 2, cv2.LINE_AA)
        return img

def draw_text(img, text, pos, color=(255,255,255), scale=1, thickness=2):
    """
    Enhanced text drawing function that automatically handles Tamil text
    """
    font_size = max(12, int(scale * 30))
    
    # Check if text contains Tamil characters (Unicode range for Tamil: U+0B80-U+0BFF)
    has_tamil = any('\u0b80' <= char <= '\u0bff' for char in text)
    
    if has_tamil:
        # Use Tamil-specific rendering
        img[:] = draw_tamil_text(img, text, pos, font_size, color)[:]
    else:
        # Use regular OpenCV text for English/numbers
        cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)

def calculate_distance(p1, p2):
    import math
    return math.hypot(p2[0]-p1[0], p2[1]-p1[1])

def play_sound(text):
    import pyttsx3
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()
