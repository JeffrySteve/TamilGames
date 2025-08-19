# Multiple game functions
import cv2
import json
import random
import numpy as np
import math
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
        # Interaction state (new)
        self.hover_word = None
        self.hover_counter = 0
        self.dwell_frames_to_grab = 10  # frames required to grab
        self.snap_radius = 60  # px radius to snap to nearest target
        self.highlight_target_idx = None
        self.drop_hover_counter = 0
        self.drop_dwell_frames = 6  # frames to confirm drop over a target
        
    def load_words(self):
        try:
            with open('assets/words.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data['words']
        except:
            # Minimal fallback if file not found
            return [
                {"tamil": "பூ", "english": "flower"},
                {"tamil": "பால்", "english": "milk"},
                {"tamil": "நீர்", "english": "water"}
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
                'matched': False,
                'mistakes': 0
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
                'matched': False,
                'highlight': False
            }
            self.image_boxes.append(box)
    
    def draw_game_ui(self, img):
        h, w = img.shape[:2]
        
        # Create semi-transparent overlay for better readability
        overlay = img.copy()
        
        # Draw header background
        cv2.rectangle(overlay, (0, 0), (w, 120), (30, 30, 30), -1)
        cv2.addWeighted(overlay, 0.7, img, 0.3, 0, img)
        
        # Draw title with shadow effect
        draw_text(img, "Tamil Drag-Drop Game", (w//2 - 148, 52), (0, 0, 0), 1.4, 4)  # Shadow
        draw_text(img, "Tamil Drag-Drop Game", (w//2 - 150, 50), (255, 215, 0), 1.4, 3)  # Gold title
        
        # Draw score and progress
        progress = f"{self.matches_made}/{len(self.word_boxes)}"
        draw_text(img, f"Score: {self.score}", (50, 90), (255, 255, 255), 1.0, 2)
        draw_text(img, f"Progress: {progress}", (w - 200, 90), (255, 255, 255), 1.0, 2)
        
        # Draw Tamil words section header
        draw_text(img, "Tamil Words", (50, 130), (255, 200, 100), 0.8, 2)
        draw_text(img, "Match words", (w - 250, 130), (255, 200, 100), 0.8, 2)
        
        # Draw word boxes with enhanced styling
        for i, box in enumerate(self.word_boxes):
            x, y, w_box, h_box = box['rect']
            
            if box['matched']:
                # Green gradient for matched boxes
                color = (50, 255, 50)
                bg_color = (0, 80, 0)
            else:
                # Blue gradient for unmatched boxes
                color = (255, 255, 255)
                bg_color = (40, 40, 100)
            
            # Draw background with rounded corners effect
            cv2.rectangle(img, (x-2, y-2), (x + w_box + 2, y + h_box + 2), (0, 0, 0), -1)  # Shadow
            cv2.rectangle(img, (x, y), (x + w_box, y + h_box), bg_color, -1)  # Background
            cv2.rectangle(img, (x, y), (x + w_box, y + h_box), color, 3)  # Border
            
            if not box['matched']:
                # Draw Tamil word with larger font
                draw_text(img, box['word']['tamil'], (x + 15, y + 35), (255, 255, 255), 1.2, 3)
                
                # Add number indicator
                cv2.circle(img, (x + w_box - 20, y + 20), 15, color, -1)
                draw_text(img, str(i+1), (x + w_box - 27, y + 28), (0, 0, 0), 0.6, 2)
        
        # Draw image boxes (target areas) with enhanced styling
        for i, box in enumerate(self.image_boxes):
            x, y, w_box, h_box = box['rect']
            
            if box['matched']:
                color = (50, 255, 50)
                bg_color = (0, 80, 0)
                icon = "✓"
            else:
                # Highlight nearest target when dragging
                color = (0, 255, 255) if box.get('highlight', False) else (100, 150, 255)
                bg_color = (50, 50, 80)
                icon = "?"
            
            # Draw background with shadow
            cv2.rectangle(img, (x-2, y-2), (x + w_box + 2, y + h_box + 2), (0, 0, 0), -1)  # Shadow
            cv2.rectangle(img, (x, y), (x + w_box, y + h_box), bg_color, -1)  # Background
            
            # Draw dashed border for unmatched, solid for matched
            if box['matched']:
                cv2.rectangle(img, (x, y), (x + w_box, y + h_box), color, 3)
            else:
                # Dashed border effect
                dash_length = 10
                for pos in range(0, w_box, dash_length * 2):
                    cv2.line(img, (x + pos, y), (x + min(pos + dash_length, w_box), y), color, 3)
                    cv2.line(img, (x + pos, y + h_box), (x + min(pos + dash_length, w_box), y + h_box), color, 3)
                for pos in range(0, h_box, dash_length * 2):
                    cv2.line(img, (x, y + pos), (x, y + min(pos + dash_length, h_box)), color, 3)
                    cv2.line(img, (x + w_box, y + pos), (x + w_box, y + min(pos + dash_length, h_box)), color, 3)
            
            if not box['matched']:
                # Draw target text
                draw_text(img, "DROP HERE", (x + 45, y + 25), color, 0.7, 2)
                draw_text(img, box['word']['tamil'], (x + 30, y + 55), (255, 255, 255), 0.9, 2)
            else:
                # Draw checkmark for matched
                draw_text(img, "MATCHED!", (x + 50, y + 30), color, 0.8, 2)
                draw_text(img, box['word']['tamil'], (x + 30, y + 55), (200, 255, 200), 0.8, 2)
        
        # Draw enhanced instructions panel
        instruction_y = h - 100
        cv2.rectangle(img, (0, instruction_y), (w, h), (20, 20, 20), -1)  # Dark background
        cv2.rectangle(img, (0, instruction_y), (w, instruction_y + 5), (255, 215, 0), -1)  # Gold line
        
        draw_text(img, "CONTROLS:", (50, instruction_y + 25), (255, 215, 0), 0.7, 2)
        draw_text(img, "👆 Point to navigate", (50, instruction_y + 45), (255, 255, 255), 0.6, 1)
        draw_text(img, "✊ Close fist to grab", (250, instruction_y + 45), (255, 255, 255), 0.6, 1)
        draw_text(img, "✋ Open hand to drop", (450, instruction_y + 45), (255, 255, 255), 0.6, 1)
        draw_text(img, "Press 'Q' to quit", (650, instruction_y + 45), (255, 100, 100), 0.6, 1)
        
        # Progress bar
        bar_width = 300
        bar_height = 20
        bar_x = w//2 - bar_width//2
        bar_y = instruction_y + 70
        
        # Background bar
        cv2.rectangle(img, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (50, 50, 50), -1)
        
        # Progress fill
        progress_width = int((self.matches_made / len(self.word_boxes)) * bar_width)
        if progress_width > 0:
            cv2.rectangle(img, (bar_x, bar_y), (bar_x + progress_width, bar_y + bar_height), (0, 255, 0), -1)
        
        # Progress text
        progress_text = f"{self.matches_made}/{len(self.word_boxes)} Matched"
        draw_text(img, progress_text, (bar_x + bar_width//2 - 60, bar_y + 15), (255, 255, 255), 0.5, 1)
        
        # Game completion celebration
        if self.game_complete:
            # Create celebration overlay
            celebration_overlay = img.copy()
            cv2.rectangle(celebration_overlay, (0, 0), (w, h), (0, 0, 0), -1)
            cv2.addWeighted(celebration_overlay, 0.6, img, 0.4, 0, img)
            
            # Animated text effect (simple version)
            import time
            colors = [(255, 0, 0), (255, 255, 0), (0, 255, 0), (0, 255, 255), (255, 0, 255)]
            color_idx = int(time.time() * 3) % len(colors)
            celebration_color = colors[color_idx]
            
            # Large celebration text
            draw_text(img, "🎉 CONGRATULATIONS! 🎉", (w//2 - 250, h//2 - 50), celebration_color, 1.5, 4)
            draw_text(img, "All Words Matched Successfully!", (w//2 - 200, h//2), (255, 255, 255), 1.0, 2)
            draw_text(img, f"Final Score: {self.score} points", (w//2 - 120, h//2 + 40), (255, 215, 0), 1.0, 2)
            draw_text(img, "Press 'Q' to return to menu", (w//2 - 150, h//2 + 80), (200, 200, 200), 0.8, 2)

    def detect_finger_position(self, img):
        landmarks = self.hand_tracker.get_landmarks(img)
        if not landmarks:
            return None, False, 0.0
        
        # Get confidence score for better stability
        confidence = self.hand_tracker.get_gesture_confidence(landmarks)
        
        # Use improved finger tracking
        index_tip = self.hand_tracker.get_index_finger_tip(landmarks)
        is_grabbing = self.hand_tracker.is_fist(landmarks)
        
        # Only return valid position if confidence is high enough
        if confidence > 0.5 and index_tip:
            return index_tip, is_grabbing, confidence
        
        return None, False, 0.0
    
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
    
    def get_nearest_target(self, pos):
        """Return (index, box, distance) for nearest unmatched target center to pos"""
        if not pos:
            return None, None, float('inf')
        px, py = pos
        best_idx, best_box, best_dist = None, None, float('inf')
        for idx, box in enumerate(self.image_boxes):
            if box['matched']:
                continue
            cx, cy = box['center']
            d = math.hypot(px - cx, py - cy)
            if d < best_dist:
                best_idx, best_box, best_dist = idx, box, d
        return best_idx, best_box, best_dist
    
    def handle_game_logic(self, img):
        finger_pos, is_grabbing, confidence = self.detect_finger_position(img)
        
        if finger_pos and confidence > 0.6:  # Only show cursor if confident
            # Enhanced finger position visualization with confidence
            confidence_color = int(255 * confidence)
            
            if is_grabbing:
                # Grabbing state - red pulsing circle
                import time
                pulse = int(abs(np.sin(time.time() * 5)) * 15) + 10
                cv2.circle(img, finger_pos, pulse, (0, 0, confidence_color), 3)
                cv2.circle(img, finger_pos, 5, (255, 255, 255), -1)
                draw_text(img, "GRABBING", (finger_pos[0] - 30, finger_pos[1] - 30), (0, 0, 255), 0.5, 2)
            else:
                # Normal state - yellow circle with crosshair, opacity based on confidence
                circle_color = (0, confidence_color, confidence_color)
                cv2.circle(img, finger_pos, 15, circle_color, 2)
                cv2.circle(img, finger_pos, 3, (255, 255, 255), -1)
                # Crosshair
                cv2.line(img, (finger_pos[0] - 10, finger_pos[1]), (finger_pos[0] + 10, finger_pos[1]), circle_color, 2)
                cv2.line(img, (finger_pos[0], finger_pos[1] - 10), (finger_pos[0], finger_pos[1] + 10), circle_color, 2)
            
            # Display confidence
            draw_text(img, f"Confidence: {confidence:.1f}", (10, 30), (255, 255, 255), 0.5, 1)
            
            # Dwell-to-grab: require sustained grab over a word box
            if not self.dragging:
                word_box = self.check_word_collision(finger_pos)
                if word_box and not word_box['matched'] and is_grabbing and confidence > 0.7:
                    if self.hover_word is word_box:
                        self.hover_counter += 1
                    else:
                        self.hover_word = word_box
                        self.hover_counter = 1
                    # Visual dwell indicator
                    cv2.circle(img, finger_pos, 20 + min(self.hover_counter, 10), (0, 180, 0), 2)
                    if self.hover_counter >= self.dwell_frames_to_grab:
                        self.current_word = word_box
                        self.dragging = True
                        self.drag_offset = (finger_pos[0] - word_box['center'][0], 
                                          finger_pos[1] - word_box['center'][1])
                        self.hover_word = None
                        self.hover_counter = 0
                else:
                    self.hover_word = None
                    self.hover_counter = 0
            
            elif not is_grabbing and self.dragging:
                # Release: snap to nearest target if within radius, then validate
                nearest_idx, nearest_box, nearest_dist = self.get_nearest_target(finger_pos)
                if nearest_box and nearest_dist <= self.snap_radius:
                    image_box = nearest_box
                else:
                    image_box = self.check_image_collision(finger_pos)

                if image_box and self.check_match(self.current_word, image_box):
                    self.current_word['matched'] = True
                    image_box['matched'] = True
                    self.score += 10
                    self.matches_made += 1
                    # Success visual effect
                    for i in range(3):
                        cv2.circle(img, image_box['center'], 30 + i*10, (0, 255, 0), 3)
                    try:
                        play_sound(f"Correct! {self.current_word['word']['tamil']}")
                    except:
                        print(f"Correct! {self.current_word['word']['tamil']}")
                    if self.matches_made >= len(self.word_boxes):
                        self.game_complete = True
                        try:
                            play_sound("Congratulations! You matched all words!")
                        except:
                            print("Game Complete!")
                else:
                    # Failed match: feedback and track mistakes
                    if self.current_word is not None:
                        self.current_word['mistakes'] = self.current_word.get('mistakes', 0) + 1
                    cv2.circle(img, finger_pos, 25, (0, 0, 255), 3)
                    draw_text(img, "WRONG!", (finger_pos[0] - 25, finger_pos[1] - 40), (0, 0, 255), 0.6, 2)
                self.dragging = False
                self.current_word = None
            
            # Draw dragged word with enhanced visuals
            if self.dragging and self.current_word:
                drag_pos = (finger_pos[0] - self.drag_offset[0], 
                           finger_pos[1] - self.drag_offset[1])
                
                # Shadow effect
                cv2.rectangle(img, 
                            (drag_pos[0] - 102, drag_pos[1] - 42),
                            (drag_pos[0] + 102, drag_pos[1] + 42),
                            (0, 0, 0), -1)
                
                # Main dragged box with glow effect
                cv2.rectangle(img, 
                            (drag_pos[0] - 100, drag_pos[1] - 40),
                            (drag_pos[0] + 100, drag_pos[1] + 40),
                            (255, 255, 0), -1)
                cv2.rectangle(img, 
                            (drag_pos[0] - 100, drag_pos[1] - 40),
                            (drag_pos[0] + 100, drag_pos[1] + 40),
                            (255, 255, 255), 3)
                
                # Dragged text
                draw_text(img, self.current_word['word']['tamil'], 
                         (drag_pos[0] - 80, drag_pos[1] - 10), (0, 0, 0), 1.0, 3)
                
                # Draw connection line from original position
                orig_center = self.current_word['center']
                cv2.line(img, orig_center, drag_pos, (255, 255, 0), 2)
                # Highlight nearest target and show guide line
                nearest_idx, nearest_box, nearest_dist = self.get_nearest_target(drag_pos)
                for ib in self.image_boxes:
                    ib['highlight'] = False
                if nearest_box and nearest_dist <= self.snap_radius:
                    nearest_box['highlight'] = True
                    cv2.line(img, drag_pos, nearest_box['center'], (0, 255, 255), 1)
        
        else:
            # No hand detected - show instruction
            h, w = img.shape[:2]
            draw_text(img, "Show your hand to the camera", (w//2 - 150, h//2), (255, 100, 100), 1.0, 2)
        
        # Clear highlights when not dragging
        if not self.dragging:
            for ib in self.image_boxes:
                ib['highlight'] = False

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

class FingerCountGame:
    def __init__(self):
        self.hand_tracker = HandTracker(max_hands=2, detection_confidence=0.8, tracking_confidence=0.8)
        
        # Tamil numbers dictionary
        self.tamil_numbers = {
            1: "ஒன்று",
            2: "இரண்டு", 
            3: "மூன்று",
            4: "நான்கு",
            5: "ஐந்து",
            6: "ஆறு",
            7: "ஏழு",
            8: "எட்டு",
            9: "ஒன்பது",
            10: "பத்து"
        }
        
        # Game state
        import random
        self.current_target = random.randint(1, 5)  # Start with 1-5 for easier play
        self.score = 0
        self.level = 1
        self.last_correct_time = 0
        self.stable_count_frames = 0
        self.required_stable_frames = 20  # Need stable detection for 20 frames
        self.show_feedback = False
        self.feedback_timer = 0
        self.feedback_message = ""
        self.feedback_color = (0, 255, 0)
        self.game_complete = False
        
        print(f"Tamil Finger Counting Game Started! Target: {self.current_target} ({self.tamil_numbers[self.current_target]})")
        print("Show both hands for counting up to 10 fingers!")
    
    def setup_game(self, img_width, img_height):
        # No special setup needed for finger counting
        pass
    
    def draw_game_ui(self, img):
        h, w = img.shape[:2]
        
        # Draw game UI background
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (w, 150), (20, 30, 50), -1)
        cv2.addWeighted(overlay, 0.8, img, 0.2, 0, img)
        
        # Draw title
        draw_text(img, "Tamil Finger Counting Game", (w//2 - 200, 30), (255, 215, 0), 1.2, 3)
        
        # Draw current challenge
        challenge_text = f"Show: {self.current_target}"
        tamil_text = self.tamil_numbers[self.current_target]
        draw_text(img, challenge_text, (50, 80), (255, 255, 255), 1.0, 2)
        draw_text(img, tamil_text, (200, 80), (100, 255, 255), 1.5, 3)  # Larger Tamil text
        
        # Draw score and level
        draw_text(img, f"Score: {self.score}", (w-200, 50), (255, 255, 255), 0.8, 2)
        draw_text(img, f"Level: {self.level}", (w-200, 80), (255, 255, 255), 0.8, 2)
        
        # Draw instructions
        instruction_y = h - 80
        cv2.rectangle(img, (0, instruction_y), (w, h), (30, 30, 30), -1)
        draw_text(img, "Show fingers on BOTH hands for counting up to 10", (50, instruction_y + 25), (200, 200, 200), 0.7, 2)
        draw_text(img, "Press 'Q' to quit", (50, instruction_y + 50), (255, 100, 100), 0.6, 1)
        
        # Show feedback message
        if self.show_feedback and self.feedback_timer > 0:
            # Create pulsing effect
            pulse = int(50 + 50 * abs(math.sin(self.feedback_timer * 0.2)))
            feedback_bg_color = (self.feedback_color[0]//4, self.feedback_color[1]//4, self.feedback_color[2]//4)
            
            # Feedback background
            feedback_w = 400
            feedback_h = 80
            feedback_x = w//2 - feedback_w//2
            feedback_y = h//2 - 100
            
            cv2.rectangle(img, (feedback_x, feedback_y), (feedback_x + feedback_w, feedback_y + feedback_h), 
                         feedback_bg_color, -1)
            cv2.rectangle(img, (feedback_x, feedback_y), (feedback_x + feedback_w, feedback_y + feedback_h), 
                         self.feedback_color, 3)
            
            # Feedback text
            draw_text(img, self.feedback_message, (feedback_x + 50, feedback_y + 35), self.feedback_color, 1.2, 3)
            
            self.feedback_timer -= 1
            if self.feedback_timer <= 0:
                self.show_feedback = False
        
        # Level indicator
        level_text = "⭐" * self.level
        draw_text(img, f"Level {self.level}: {level_text}", (w//2 - 80, h - 25), (255, 215, 0), 0.8, 2)
        
        # Game completion check
        if self.score >= 100:  # Complete game at 100 points
            self.game_complete = True
            # Draw completion message
            completion_overlay = img.copy()
            cv2.rectangle(completion_overlay, (0, 0), (w, h), (0, 0, 0), -1)
            cv2.addWeighted(completion_overlay, 0.6, img, 0.4, 0, img)
            
            draw_text(img, "🎉 வாழ்த்துகள்! (Congratulations!) 🎉", (w//2 - 250, h//2 - 50), (255, 215, 0), 1.5, 4)
            draw_text(img, "Finger Counting Master!", (w//2 - 150, h//2), (255, 255, 255), 1.0, 2)
            draw_text(img, f"Final Score: {self.score} points", (w//2 - 120, h//2 + 40), (255, 215, 0), 1.0, 2)
            draw_text(img, "Press 'Q' to return to menu", (w//2 - 150, h//2 + 80), (200, 200, 200), 0.8, 2)
    
    def handle_game_logic(self, img):
        h, w = img.shape[:2]
        
        # Get finger count from both hands
        total_fingers, hand_finger_counts = self.hand_tracker.count_all_fingers(img)
        confidence = self.hand_tracker.get_multi_hand_confidence(img)
        
        # Display hand information
        num_hands = len(hand_finger_counts)
        if num_hands > 0:
            # Show detected count for each hand
            detection_color = (0, 255, 0) if total_fingers == self.current_target else (100, 100, 255)
            
            if num_hands == 1:
                draw_text(img, f"Hand 1: {hand_finger_counts[0]} fingers", (50, 120), detection_color, 0.8, 2)
                draw_text(img, f"Total: {total_fingers}", (50, 145), detection_color, 0.9, 2)
            else:
                draw_text(img, f"Left: {hand_finger_counts[0]}, Right: {hand_finger_counts[1] if len(hand_finger_counts) > 1 else 0}", (50, 120), detection_color, 0.8, 2)
                draw_text(img, f"Total: {total_fingers}", (50, 145), detection_color, 0.9, 2)
            
            # Show confidence meter
            conf_color = (0, int(255 * confidence), int(255 * (1 - confidence)))
            draw_text(img, f"Confidence: {confidence:.1f}", (w-250, 120), conf_color, 0.7, 2)
            
            # Check for correct count with stability requirement
            if total_fingers == self.current_target and confidence > 0.6:  # Lower threshold for multi-hand
                self.stable_count_frames += 1
                
                # Draw progress bar for stability
                progress = min(self.stable_count_frames / self.required_stable_frames, 1.0)
                bar_width = 300
                bar_x = w//2 - bar_width//2
                bar_y = h//2 - 50
                
                # Progress bar background
                cv2.rectangle(img, (bar_x, bar_y), (bar_x + bar_width, bar_y + 25), (50, 50, 50), -1)
                cv2.rectangle(img, (bar_x, bar_y), (bar_x + int(bar_width * progress), bar_y + 25), (0, 255, 0), -1)
                draw_text(img, "Hold steady...", (bar_x + 100, bar_y - 15), (255, 255, 255), 0.7, 2)
                
                if self.stable_count_frames >= self.required_stable_frames:
                    # Success!
                    import time
                    current_time = time.time()
                    if current_time - self.last_correct_time > 2:  # Prevent rapid scoring
                        self.score += 10 * self.level  # Higher score for higher levels
                        
                        # Show success feedback
                        self.feedback_message = "சரி! (Correct!)"
                        self.feedback_color = (0, 255, 0)
                        self.show_feedback = True
                        self.feedback_timer = 60  # Show for 60 frames (~2 seconds)
                        
                        # Play success sound (if available)
                        try:
                            play_sound(f"சரி! {self.tamil_numbers[self.current_target]}")
                        except:
                            print(f"Correct! {self.tamil_numbers[self.current_target]}")
                        
                        # Generate next challenge with expanded range
                        if self.score > 0 and self.score % 50 == 0:  # Level up every 50 points
                            self.level = min(self.level + 1, 3)  # Max level 3
                        
                        # Set difficulty based on level - now up to 10!
                        import random
                        if self.level == 1:
                            self.current_target = random.randint(1, 5)
                        elif self.level == 2:
                            self.current_target = random.randint(3, 8)
                        else:
                            self.current_target = random.randint(5, 10)  # Full range!
                        
                        self.stable_count_frames = 0
                        self.last_correct_time = current_time
                        
                        print(f"Correct! New target: {self.current_target} ({self.tamil_numbers[self.current_target]})")
            else:
                self.stable_count_frames = max(0, self.stable_count_frames - 2)  # Faster decay when wrong
        else:
            self.stable_count_frames = max(0, self.stable_count_frames - 1)
            draw_text(img, "Show your hands clearly", (50, 120), (255, 100, 100), 0.9, 2)
            draw_text(img, "Use BOTH hands to count up to 10!", (50, 145), (255, 200, 100), 0.8, 2)

def game_finger_count():
    print("[Game] Starting Tamil Finger Counting...")
    
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    # Anti-shutter settings
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
    cap.set(cv2.CAP_PROP_EXPOSURE, -6)
    
    # Camera warmup
    for _ in range(10):
        cap.read()
    
    # Frame smoothing
    prev_frame = None
    frame_alpha = 0.7
    
    game = FingerCountGame()
    game_initialized = False
    
    while True:
        ret, img = cap.read()
        if not ret:
            continue
        
        # Frame smoothing to reduce shutter
        if prev_frame is not None:
            img = cv2.addWeighted(img, frame_alpha, prev_frame, 1 - frame_alpha, 0)
        prev_frame = img.copy()
        
        img = cv2.flip(img, 1)
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
        
        cv2.imshow("Tamil Finger Counting Game", img)
        
        # Small delay to prevent excessive CPU usage
        import time
        time.sleep(0.03)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or game.game_complete:
            if game.game_complete:
                cv2.waitKey(3000)  # Show completion message for 3 seconds
            break
    
    cap.release()
    cv2.destroyAllWindows()
    print(f"Game ended. Final score: {game.score}, Level reached: {game.level}")

# math imported at top


class Mosquito:
    """Mosquito class for the mosquito killing game"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.alive = True
        self.speed = 2

    def move(self, width, height):
        """Move mosquito randomly within bounds"""
        if self.alive:
            import random
            self.x += random.randint(-self.speed * 5, self.speed * 5)
            self.y += random.randint(-self.speed * 5, self.speed * 5)
            self.x = max(25, min(width - 25, self.x))
            self.y = max(25, min(height - 25, self.y))


class MosquitoKillGame:
    """Tamil Mosquito Killing Game - Learn numbers by killing mosquitoes with pinch gestures"""
    
    def __init__(self):
        self.hand_tracker = HandTracker(max_hands=2)
        self.mosquitoes = []
        self.kill_count = 0
        self.start_time = 0
        self.game_complete = False
        self.game_started = False
        self.total_mosquitoes = 10
        self.game_width = 800
        self.game_height = 600
        
        # Tamil numbers for feedback
        self.tamil_numbers = [
            "ஒன்று", "இரண்டு", "மூன்று", "நான்கு", "ஐந்து", 
            "ஆறு", "ஏழு", "எட்டு", "ஒன்பது", "பத்து"
        ]
        
        # Game state
        self.last_kill_time = 0
        self.kill_message = ""
        self.kill_message_timer = 0
        
    def setup_game(self, width, height):
        """Initialize game with screen dimensions"""
        self.game_width = width
        self.game_height = height
        self.start_new_game()
        
    def start_new_game(self):
        """Start a new mosquito killing game"""
        import random
        import time
        
        self.mosquitoes = []
        for _ in range(self.total_mosquitoes):
            x = random.randint(50, self.game_width - 50)
            y = random.randint(100, self.game_height - 100)
            self.mosquitoes.append(Mosquito(x, y))
        
        self.kill_count = 0
        self.start_time = time.time()
        self.game_complete = False
        self.game_started = True
        self.kill_message = ""
        self.kill_message_timer = 0
        print("Mosquito killing game started!")
        
    def is_pinch_gesture(self, hand_landmarks):
        """Detect pinch gesture between index finger and thumb"""
        if not hand_landmarks:
            return False, None
            
        # Get landmark positions
        thumb_tip = hand_landmarks.landmark[4]  # Thumb tip
        index_tip = hand_landmarks.landmark[8]  # Index finger tip
        
        # Calculate distance between thumb and index finger
        distance = ((thumb_tip.x - index_tip.x) ** 2 + 
                   (thumb_tip.y - index_tip.y) ** 2) ** 0.5
        
        # Return pinch status and index finger position
        is_pinching = distance < 0.05  # Adjust threshold as needed
        return is_pinching, index_tip
        
    def handle_game_logic(self, img):
        """Main game logic for mosquito killing"""
        if not self.game_started or self.game_complete:
            return
            
        import time
        
        # Move all mosquitoes
        for mosquito in self.mosquitoes:
            mosquito.move(self.game_width, self.game_height)
        
        # Process hand landmarks for pinch detection
        if self.hand_tracker.results and self.hand_tracker.results.multi_hand_landmarks:
            for hand_landmarks in self.hand_tracker.results.multi_hand_landmarks:
                is_pinching, index_tip = self.is_pinch_gesture(hand_landmarks)
                
                if is_pinching and index_tip:
                    # Convert normalized coordinates to pixel coordinates
                    ix = int(index_tip.x * self.game_width)
                    iy = int(index_tip.y * self.game_height)
                    
                    # Check collision with mosquitoes
                    for mosquito in self.mosquitoes:
                        if (mosquito.alive and 
                            abs(ix - mosquito.x) < 40 and 
                            abs(iy - mosquito.y) < 40):
                            
                            mosquito.alive = False
                            self.kill_count += 1
                            
                            # Set kill message with Tamil number
                            if self.kill_count <= len(self.tamil_numbers):
                                tamil_num = self.tamil_numbers[self.kill_count - 1]
                                self.kill_message = f"{tamil_num} - Mosquito {self.kill_count} Killed!"
                            else:
                                self.kill_message = f"Mosquito {self.kill_count} Killed!"
                            
                            self.kill_message_timer = time.time()
                            print(f"Mosquito killed! Count: {self.kill_count}")
                            break
        
        # Check for game completion
        if self.kill_count >= self.total_mosquitoes:
            self.game_complete = True
            elapsed_time = time.time() - self.start_time
            print(f"All mosquitoes killed in {elapsed_time:.1f} seconds!")
            
    def draw_game_ui(self, img):
        """Draw game interface and mosquitoes"""
        import cv2
        import time
        
        if not self.game_started:
            # Draw start screen
            cv2.putText(img, "Tamil Mosquito Killing Game", 
                       (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 2)
            cv2.putText(img, "Pinch fingers to kill mosquitoes!", 
                       (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(img, "Learn Tamil numbers 1-10", 
                       (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            return
            
        # Draw mosquitoes
        alive_count = 0
        for mosquito in self.mosquitoes:
            if mosquito.alive:
                alive_count += 1
                # Draw mosquito as a red circle with wings
                cv2.circle(img, (mosquito.x, mosquito.y), 15, (0, 0, 255), -1)
                # Add small wings
                cv2.ellipse(img, (mosquito.x - 10, mosquito.y - 5), (8, 4), 0, 0, 360, (100, 100, 100), -1)
                cv2.ellipse(img, (mosquito.x + 10, mosquito.y - 5), (8, 4), 0, 0, 360, (100, 100, 100), -1)
                
        # Draw hand landmarks and pinch indicator
        if self.hand_tracker.results and self.hand_tracker.results.multi_hand_landmarks:
            for hand_landmarks in self.hand_tracker.results.multi_hand_landmarks:
                # Draw hand landmarks
                self.hand_tracker.mp_draw.draw_landmarks(
                    img, hand_landmarks, self.hand_tracker.mp_hands.HAND_CONNECTIONS)
                
                # Check for pinch and draw indicator
                is_pinching, index_tip = self.is_pinch_gesture(hand_landmarks)
                if is_pinching and index_tip:
                    ix = int(index_tip.x * self.game_width)
                    iy = int(index_tip.y * self.game_height)
                    cv2.circle(img, (ix, iy), 20, (0, 255, 0), 3)  # Green pinch indicator
                
        # Draw game statistics
        cv2.putText(img, f"Killed: {self.kill_count}/{self.total_mosquitoes}", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        cv2.putText(img, f"Remaining: {alive_count}", 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        
        # Show elapsed time
        if not self.game_complete:
            elapsed = time.time() - self.start_time
            cv2.putText(img, f"Time: {elapsed:.1f}s", 
                       (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # Draw kill message
        if self.kill_message and time.time() - self.kill_message_timer < 2.0:
            cv2.putText(img, self.kill_message, 
                       (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        
        # Draw completion message
        if self.game_complete:
            elapsed_time = time.time() - self.start_time
            cv2.putText(img, f"Excellent! All mosquitoes killed!", 
                       (50, self.game_height // 2 - 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
            cv2.putText(img, f"Time: {elapsed_time:.1f} seconds", 
                       (50, self.game_height // 2), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
            cv2.putText(img, "Great job learning Tamil numbers!", 
                       (50, self.game_height // 2 + 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
            
        # Draw Tamil numbers reference
        try:
            from utils import draw_tamil_text
            y_pos = self.game_height - 120
            draw_tamil_text(img, "Tamil Numbers:", (10, y_pos), font_size=20, color=(255, 255, 255))
            
            # Show first 5 numbers on one line
            numbers_line1 = " ".join(self.tamil_numbers[:5])
            draw_tamil_text(img, numbers_line1, (10, y_pos + 30), font_size=16, color=(255, 200, 0))
            
            # Show next 5 numbers on second line
            numbers_line2 = " ".join(self.tamil_numbers[5:])
            draw_tamil_text(img, numbers_line2, (10, y_pos + 55), font_size=16, color=(255, 200, 0))
            
        except Exception as e:
            print(f"Tamil text rendering error: {e}")
            # Fallback to showing numbers in English
            cv2.putText(img, "Learning numbers 1-10 in Tamil", 
                       (10, self.game_height - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)


def game_mosquito_kill():
    """Standalone function to run mosquito killing game"""
    print("[Game] Starting Tamil Mosquito Killing Game...")
    
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    # Camera warmup
    for i in range(10):
        ret, _ = cap.read()
    
    # Frame smoothing variables
    prev_frame = None
    frame_alpha = 0.7
    
    game = MosquitoKillGame()
    game_initialized = False
    
    while True:
        ret, img = cap.read()
        if not ret:
            continue
        
        # Frame smoothing to reduce shutter
        if prev_frame is not None:
            img = cv2.addWeighted(img, frame_alpha, prev_frame, 1 - frame_alpha, 0)
        prev_frame = img.copy()
        
        img = cv2.flip(img, 1)
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
        
        cv2.imshow("Tamil Mosquito Killing Game", img)
        
        # Small delay to prevent excessive CPU usage
        import time
        time.sleep(0.03)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or game.game_complete:
            if game.game_complete:
                cv2.waitKey(3000)  # Show completion message for 3 seconds
            break
    
    cap.release()
    cv2.destroyAllWindows()
    print(f"Game ended. Final kill count: {game.kill_count}")


if __name__ == "__main__":
    print("Tamil Kids Learning Games")
    print("1. Drag-Drop Word Matching")
    print("2. Finger Counting Game") 
    print("3. Mosquito Killing Game")
    
    choice = input("Choose a game (1-3): ")
    
    if choice == "1":
        game_drag_drop()
    elif choice == "2":
        game_finger_count()
    elif choice == "3":
        game_mosquito_kill()
    else:
        print("Invalid choice!")

