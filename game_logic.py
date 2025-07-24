# Multiple game functions
import cv2
import json
import random
import numpy as np
from hand_tracker import HandTracker
from utils import draw_text, calculate_distance, play_sound

class DragDropGame:
    def __init__(self):
        self.hand_tracker = HandTracker()
        self.words = self.load_words()
        self.current_word = None
        self.word_boxes = []
        self.image_boxes = []
        self.dragging = False
        self.drag_offset = (0, 0)
        self.score = 0
        self.matches_made = 0
        self.game_complete = False
        
    def load_words(self):
        try:
            with open('assets/words.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data['words']
        except:
            return [
                {"tamil": "பூ", "english": "flower", "image": "flower.png"},
                {"tamil": "பால்", "english": "milk", "image": "milk.png"},
                {"tamil": "நீர்", "english": "water", "image": "water.png"}
            ]
    
    def setup_game(self, img_width, img_height):
        # Select 3 random words for this round
        selected_words = random.sample(self.words, min(3, len(self.words)))
        
        # Setup word boxes (left side)
        self.word_boxes = []
        for i, word in enumerate(selected_words):
            y = 150 + i * 120
            box = {
                'word': word,
                'rect': (50, y, 200, 80),
                'center': (150, y + 40),
                'matched': False
            }
            self.word_boxes.append(box)
        
        # Setup image boxes (right side) - shuffled
        self.image_boxes = []
        shuffled_words = selected_words.copy()
        random.shuffle(shuffled_words)
        
        for i, word in enumerate(shuffled_words):
            y = 150 + i * 120
            box = {
                'word': word,
                'rect': (img_width - 250, y, 200, 80),
                'center': (img_width - 150, y + 40),
                'matched': False
            }
            self.image_boxes.append(box)
    
    def draw_game_ui(self, img):
        h, w = img.shape[:2]
        
        # Draw title
        draw_text(img, "Tamil Drag-Drop Game", (w//2 - 150, 50), (0, 255, 255), 1.2, 3)
        draw_text(img, f"Score: {self.score}", (w//2 - 50, 100), (255, 255, 255), 0.8, 2)
        
        # Draw word boxes
        for box in self.word_boxes:
            color = (0, 255, 0) if box['matched'] else (255, 255, 255)
            x, y, w_box, h_box = box['rect']
            cv2.rectangle(img, (x, y), (x + w_box, y + h_box), color, 2)
            
            if not box['matched']:
                # Draw Tamil word
                draw_text(img, box['word']['tamil'], (x + 10, y + 30), color, 0.8, 2)
                draw_text(img, box['word']['english'], (x + 10, y + 60), (200, 200, 200), 0.6, 1)
        
        # Draw image boxes (target areas)
        for box in self.image_boxes:
            color = (0, 255, 0) if box['matched'] else (100, 100, 255)
            x, y, w_box, h_box = box['rect']
            cv2.rectangle(img, (x, y), (x + w_box, y + h_box), color, 2)
            
            if not box['matched']:
                # Draw placeholder for image
                draw_text(img, "Drop here", (x + 50, y + 25), color, 0.6, 1)
                draw_text(img, box['word']['english'], (x + 30, y + 50), (200, 200, 200), 0.7, 2)
        
        # Draw instructions
        draw_text(img, "Use index finger to drag Tamil words to matching images", 
                 (50, h - 80), (255, 255, 0), 0.6, 1)
        draw_text(img, "Close fist to grab, open to release", 
                 (50, h - 50), (255, 255, 0), 0.6, 1)
        draw_text(img, "Press 'q' to quit", 
                 (50, h - 20), (255, 255, 0), 0.6, 1)
        
        if self.game_complete:
            draw_text(img, "CONGRATULATIONS! All matched!", 
                     (w//2 - 200, h//2), (0, 255, 0), 1.5, 3)

    def detect_finger_position(self, img):
        landmarks = self.hand_tracker.get_landmarks(img)
        if not landmarks:
            return None, False
        
        # Get index finger tip (landmark 8)
        index_tip = None
        thumb_tip = None
        
        for id, x, y in landmarks:
            if id == 8:  # Index finger tip
                index_tip = (x, y)
            elif id == 4:  # Thumb tip
                thumb_tip = (x, y)
        
        if index_tip and thumb_tip:
            # Check if hand is in fist (thumb and index close together)
            distance = calculate_distance(index_tip, thumb_tip)
            is_grabbing = distance < 50  # Adjust threshold as needed
            return index_tip, is_grabbing
        
        return index_tip, False
    
    def check_word_collision(self, finger_pos):
        for box in self.word_boxes:
            if box['matched']:
                continue
            x, y, w, h = box['rect']
            if x <= finger_pos[0] <= x + w and y <= finger_pos[1] <= y + h:
                return box
        return None
    
    def check_image_collision(self, finger_pos):
        for box in self.image_boxes:
            if box['matched']:
                continue
            x, y, w, h = box['rect']
            if x <= finger_pos[0] <= x + w and y <= finger_pos[1] <= y + h:
                return box
        return None
    
    def check_match(self, word_box, image_box):
        return word_box['word']['english'] == image_box['word']['english']
    
    def handle_game_logic(self, img):
        finger_pos, is_grabbing = self.detect_finger_position(img)
        
        if finger_pos:
            # Draw finger position
            cv2.circle(img, finger_pos, 10, (0, 255, 255), -1)
            
            if is_grabbing and not self.dragging:
                # Start dragging
                word_box = self.check_word_collision(finger_pos)
                if word_box:
                    self.current_word = word_box
                    self.dragging = True
                    self.drag_offset = (finger_pos[0] - word_box['center'][0], 
                                      finger_pos[1] - word_box['center'][1])
            
            elif not is_grabbing and self.dragging:
                # Stop dragging and check for match
                image_box = self.check_image_collision(finger_pos)
                if image_box and self.check_match(self.current_word, image_box):
                    # Successful match!
                    self.current_word['matched'] = True
                    image_box['matched'] = True
                    self.score += 10
                    self.matches_made += 1
                    
                    # Play success sound
                    try:
                        play_sound(f"Correct! {self.current_word['word']['tamil']}")
                    except:
                        print(f"Correct! {self.current_word['word']['tamil']}")
                    
                    # Check if game is complete
                    if self.matches_made >= len(self.word_boxes):
                        self.game_complete = True
                        try:
                            play_sound("Congratulations! You matched all words!")
                        except:
                            print("Game Complete!")
                
                self.dragging = False
                self.current_word = None
            
            # Draw dragged word
            if self.dragging and self.current_word:
                drag_pos = (finger_pos[0] - self.drag_offset[0], 
                           finger_pos[1] - self.drag_offset[1])
                cv2.rectangle(img, 
                            (drag_pos[0] - 100, drag_pos[1] - 40),
                            (drag_pos[0] + 100, drag_pos[1] + 40),
                            (255, 255, 0), 2)
                draw_text(img, self.current_word['word']['tamil'], 
                         (drag_pos[0] - 80, drag_pos[1]), (255, 255, 0), 0.8, 2)

def game_drag_drop():
    print("[Game] Starting Drag-Drop Matching...")
    
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    game = DragDropGame()
    game_initialized = False
    
    while True:
        ret, img = cap.read()
        if not ret:
            break
        
        img = cv2.flip(img, 1)  # Mirror the image
        h, w = img.shape[:2]
        
        # Initialize game on first frame
        if not game_initialized:
            game.setup_game(w, h)
            game_initialized = True
        
        # Process hand tracking
        img = game.hand_tracker.find_hands(img, draw=True)
        
        # Handle game logic
        game.handle_game_logic(img)
        
        # Draw game UI
        game.draw_game_ui(img)
        
        cv2.imshow("Tamil Drag-Drop Game", img)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or game.game_complete:
            if game.game_complete:
                cv2.waitKey(3000)  # Show completion message for 3 seconds
            break
    
    cap.release()
    cv2.destroyAllWindows()
    print(f"Game ended. Final score: {game.score}")

def game_finger_count():
    print("[Game] Starting Finger Counting...")
    # TODO: Add webcam loop, finger counting detection and Tamil TTS feedback using Copilot here
    pass

