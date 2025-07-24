# Utility functions
def draw_text(img, text, pos, color=(255,255,255), scale=1, thickness=2):
    import cv2
    cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)

def calculate_distance(p1, p2):
    import math
    return math.hypot(p2[0]-p1[0], p2[1]-p1[1])

def play_sound(text):
    import pyttsx3
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()
