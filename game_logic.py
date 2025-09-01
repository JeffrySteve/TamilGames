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
        self.snap_radius = 45  # px radius to snap to nearest target
        self.highlight_target_idx = None
        self.drop_hover_counter = 0
        self.drop_dwell_frames = 6  # frames to confirm drop over a target
        # New latched dragging state
        self.drag_latched = False
        self.last_finger_pos = None
    
    def _fit_text_scale(self, text, box_width, base_scale=1.0):
        """Approximate a font scale so text fits within a given box width."""
        try:
            avg_char_px = 22.0  # conservative Tamil glyph width at scale 1.0
            padding = 28.0
            max_w = max(30.0, box_width - padding)
            need = avg_char_px * max(1, len(text)) * base_scale
            if need <= max_w:
                return base_scale
            scale = max(0.5, max_w / (avg_char_px * max(1, len(text))))
            return min(base_scale, scale)
        except Exception:
            return max(0.5, min(1.0, base_scale))
        
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

        # Responsive vertical layout so all pairs fit, even on shorter windows
        n = len(selected_words)
        header_h = 120
        footer_h = 100
        top_margin = header_h + 10
        bottom_margin = footer_h + 10
        usable_h = max(100, img_height - (top_margin + bottom_margin))

        base_w, base_h = 160, 60
        min_gap = 16
        # Compute scale if space is tight
        needed_h = n * base_h + (n + 1) * min_gap
        if usable_h < needed_h:
            scale_y = max(0.65, usable_h / float(needed_h))
            h_box = max(40, int(base_h * scale_y))
            gap = max(8, int(min_gap * scale_y))
        else:
            h_box = base_h
            # Distribute remaining space as gaps
            gap = max(min_gap, int((usable_h - n * h_box) / (n + 1)))
        w_box = base_w  # keep width constant for readability

        # Precompute row Y positions
        row_y = []
        cur_y = top_margin + gap
        for _ in range(n):
            row_y.append(cur_y)
            cur_y += h_box + gap

        # Setup word boxes (left side)
        self.word_boxes = []
        for i, word in enumerate(selected_words):
            y = row_y[i]
            x = 50
            box = {
                'word': word,
                'rect': (x, y, w_box, h_box),
                'center': (x + w_box // 2, y + h_box // 2),
                'matched': False,
                'mistakes': 0
            }
            self.word_boxes.append(box)

        # Setup image boxes (right side) - shuffled
        self.image_boxes = []
        shuffled_words = selected_words.copy()
        random.shuffle(shuffled_words)

        for i, word in enumerate(shuffled_words):
            y = row_y[i]
            x = img_width - (w_box + 50)
            box = {
                'word': word,
                'rect': (x, y, w_box, h_box),
                'center': (x + w_box // 2, y + h_box // 2),
                'matched': False,
                'highlight': False
            }
            self.image_boxes.append(box)
    
    def draw_game_ui(self, img):
        h, w = img.shape[:2]

        # Header overlay
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (w, 120), (30, 30, 30), -1)
        cv2.addWeighted(overlay, 0.7, img, 0.3, 0, img)

        # Title
        draw_text(img, "Tamil Drag-Drop Game", (w//2 - 148, 52), (0, 0, 0), 1.4, 4)
        draw_text(img, "Tamil Drag-Drop Game", (w//2 - 150, 50), (255, 215, 0), 1.4, 3)

        # Score and progress
        progress = f"{self.matches_made}/{len(self.word_boxes)}"
        draw_text(img, f"Score: {self.score}", (50, 90), (255, 255, 255), 1.0, 2)
        draw_text(img, f"Progress: {progress}", (w - 200, 90), (255, 255, 255), 1.0, 2)

        # Section headers
        draw_text(img, "English Words", (50, 130), (255, 200, 100), 0.8, 2)
        draw_text(img, "Match Tamil", (w - 250, 130), (255, 200, 100), 0.8, 2)

        # Left: English words
        for i, box in enumerate(self.word_boxes):
            x, y, w_box, h_box = box['rect']
            if box['matched']:
                color = (50, 255, 50)
                bg = (0, 80, 0)
            else:
                color = (255, 255, 255)
                bg = (40, 40, 100)
            cv2.rectangle(img, (x-2, y-2), (x + w_box + 2, y + h_box + 2), (0, 0, 0), -1)
            cv2.rectangle(img, (x, y), (x + w_box, y + h_box), bg, -1)
            cv2.rectangle(img, (x, y), (x + w_box, y + h_box), color, 3)
            if not box['matched']:
                txt_y = y + max(22, int(h_box * 0.62))
                scale = self._fit_text_scale(box['word']['english'], w_box, 1.0)
                draw_text(img, box['word']['english'], (x + 12, txt_y), (255, 255, 255), scale, 2)
                bubble_r = 12 if h_box < 50 else 15
                cv2.circle(img, (x + w_box - 20, y + 18), bubble_r, color, -1)
                draw_text(img, str(i+1), (x + w_box - 27, y + 26), (0, 0, 0), 0.6, 2)

        # Right: Tamil target boxes
        for i, box in enumerate(self.image_boxes):
            x, y, w_box, h_box = box['rect']
            if box['matched']:
                color = (50, 255, 50)
                bg = (0, 80, 0)
            else:
                color = (0, 255, 255) if box.get('highlight', False) else (100, 150, 255)
                bg = (50, 50, 80)
            cv2.rectangle(img, (x-2, y-2), (x + w_box + 2, y + h_box + 2), (0, 0, 0), -1)
            cv2.rectangle(img, (x, y), (x + w_box, y + h_box), bg, -1)
            if box['matched']:
                cv2.rectangle(img, (x, y), (x + w_box, y + h_box), color, 3)
            else:
                dash = 10
                for pos in range(0, w_box, dash * 2):
                    cv2.line(img, (x + pos, y), (x + min(pos + dash, w_box), y), color, 3)
                    cv2.line(img, (x + pos, y + h_box), (x + min(pos + dash, w_box), y + h_box), color, 3)
                for pos in range(0, h_box, dash * 2):
                    cv2.line(img, (x, y + pos), (x, y + min(pos + dash, h_box)), color, 3)
                    cv2.line(img, (x + w_box, y + pos), (x + w_box, y + min(pos + dash, h_box)), color, 3)
            if not box['matched']:
                drop_y = y + max(16, int(h_box * 0.32))
                tamil_y = y + max(28, int(h_box * 0.75))
                drop_scale = self._fit_text_scale("DROP HERE", w_box, 0.7)
                word_scale = self._fit_text_scale(box['word']['tamil'], w_box, 0.9)
                draw_text(img, "DROP HERE", (x + 12, drop_y), color, drop_scale, 2)
                draw_text(img, box['word']['tamil'], (x + 12, tamil_y), (255, 255, 255), word_scale, 2)
            else:
                draw_text(img, "MATCHED!", (x + 50, y + 30), color, 0.8, 2)
                word_scale = self._fit_text_scale(box['word']['tamil'], w_box, 0.8)
                draw_text(img, box['word']['tamil'], (x + 12, y + max(28, int(h_box * 0.72))), (200, 255, 200), word_scale, 2)

        # Instructions panel (no emoji)
        instruction_y = h - 100
        cv2.rectangle(img, (0, instruction_y), (w, h), (20, 20, 20), -1)
        cv2.rectangle(img, (0, instruction_y), (w, instruction_y + 5), (255, 215, 0), -1)
        draw_text(img, "CONTROLS:", (50, instruction_y + 25), (255, 215, 0), 0.7, 2)
        draw_text(img, "Point to navigate", (50, instruction_y + 45), (255, 255, 255), 0.6, 1)
        draw_text(img, "Pinch to pick", (250, instruction_y + 45), (255, 255, 255), 0.6, 1)
        draw_text(img, "Move onto answer to drop", (450, instruction_y + 45), (255, 255, 255), 0.6, 1)
        draw_text(img, "Press 'Q' to quit", (700, instruction_y + 45), (255, 100, 100), 0.6, 1)

        # Progress bar
        bar_width, bar_height = 300, 20
        bar_x = w//2 - bar_width//2
        bar_y = instruction_y + 70
        cv2.rectangle(img, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (50, 50, 50), -1)
        progress_width = int((self.matches_made / max(1, len(self.word_boxes))) * bar_width)
        if progress_width > 0:
            cv2.rectangle(img, (bar_x, bar_y), (bar_x + progress_width, bar_y + bar_height), (0, 255, 0), -1)
        draw_text(img, f"{self.matches_made}/{len(self.word_boxes)} Matched", (bar_x + bar_width//2 - 60, bar_y + 15), (255, 255, 255), 0.5, 1)

        # Completion overlay
        if self.game_complete:
            overlay2 = img.copy()
            cv2.rectangle(overlay2, (0, 0), (w, h), (0, 0, 0), -1)
            cv2.addWeighted(overlay2, 0.6, img, 0.4, 0, img)
            draw_text(img, "CONGRATULATIONS!", (w//2 - 200, h//2 - 50), (0, 255, 255), 1.5, 4)
            draw_text(img, "All Words Matched Successfully!", (w//2 - 200, h//2), (255, 255, 255), 1.0, 2)
            draw_text(img, f"Final Score: {self.score} points", (w//2 - 120, h//2 + 40), (255, 215, 0), 1.0, 2)
            draw_text(img, "Press 'Q' to return to menu", (w//2 - 150, h//2 + 80), (200, 200, 200), 0.8, 2)

    def detect_finger_position(self, img):
        """Return (index_tip_pos, is_pinching, confidence)."""
        landmarks = self.hand_tracker.get_landmarks(img)
        if not landmarks:
            return None, False, 0.0

        # Confidence estimate
        confidence = self.hand_tracker.get_gesture_confidence(landmarks)

        # Index finger tip
        index_tip = self.hand_tracker.get_index_finger_tip(landmarks)

        # Pinch detection using pixel distance between thumb tip (4) and index tip (8)
        thumb_tip = next((lm for lm in landmarks if lm[0] == 4), None)
        idx_tip = next((lm for lm in landmarks if lm[0] == 8), None)
        is_pinching = False
        if thumb_tip and idx_tip:
            h, w = img.shape[:2]
            px_dist = math.hypot(thumb_tip[1] - idx_tip[1], thumb_tip[2] - idx_tip[2])
            pinch_thresh = max(15, int(min(w, h) * 0.035))  # relative to frame size
            is_pinching = px_dist < pinch_thresh

        if index_tip and confidence > 0.4:
            return index_tip, is_pinching, confidence
        return None, False, confidence
    
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
        finger_pos, is_pinching, confidence = self.detect_finger_position(img)

        # Track last known position for stability when tracking drops briefly
        if finger_pos is not None:
            self.last_finger_pos = finger_pos

        if (finger_pos or self.last_finger_pos) and confidence > 0.5:  # Only show cursor if confident
            # Enhanced finger position visualization with confidence
            confidence_color = int(255 * confidence)
            
            if is_pinching and not self.dragging:
                # Grabbing state - red pulsing circle
                import time
                pulse = int(abs(np.sin(time.time() * 5)) * 15) + 10
                p = finger_pos if finger_pos else self.last_finger_pos
                cv2.circle(img, p, pulse, (0, 0, confidence_color), 3)
                cv2.circle(img, p, 5, (255, 255, 255), -1)
                draw_text(img, "PINCH", (p[0] - 20, p[1] - 30), (0, 0, 255), 0.5, 2)
            else:
                # Normal state - yellow circle with crosshair, opacity based on confidence
                circle_color = (0, confidence_color, confidence_color)
                p = finger_pos if finger_pos else self.last_finger_pos
                cv2.circle(img, p, 15, circle_color, 2)
                cv2.circle(img, p, 3, (255, 255, 255), -1)
                # Crosshair
                cv2.line(img, (p[0] - 10, p[1]), (p[0] + 10, p[1]), circle_color, 2)
                cv2.line(img, (p[0], p[1] - 10), (p[0], p[1] + 10), circle_color, 2)
            
            # Display confidence
            draw_text(img, f"Confidence: {confidence:.1f}", (10, 30), (255, 255, 255), 0.5, 1)
            
            # Pinch-to-pick with latched dragging
            if not self.dragging:
                p = finger_pos if finger_pos else self.last_finger_pos
                if p:
                    word_box = self.check_word_collision(p)
                    if word_box and not word_box['matched'] and is_pinching and confidence > 0.6:
                        # Latch drag until correct drop
                        self.current_word = word_box
                        self.dragging = True
                        self.drag_latched = True
                        self.drag_offset = (p[0] - word_box['center'][0], p[1] - word_box['center'][1])
                        # Visual feedback
                        cv2.circle(img, p, 25, (0, 255, 0), 2)
            
            # Draw dragged word with enhanced visuals
            if self.dragging and self.current_word:
                p = finger_pos if finger_pos else self.last_finger_pos
                if not p:
                    # No tracking; keep original center as a fallback
                    p = self.current_word['center']
                drag_pos = (p[0] - self.drag_offset[0], p[1] - self.drag_offset[1])
                
                # Shadow effect (adjusted for smaller box 160x60)
                cv2.rectangle(img,
                              (drag_pos[0] - 82, drag_pos[1] - 32),
                              (drag_pos[0] + 82, drag_pos[1] + 32),
                              (0, 0, 0), -1)

                # Main dragged box with glow effect (160x60)
                cv2.rectangle(img,
                              (drag_pos[0] - 80, drag_pos[1] - 30),
                              (drag_pos[0] + 80, drag_pos[1] + 30),
                              (255, 255, 0), -1)
                cv2.rectangle(img,
                              (drag_pos[0] - 80, drag_pos[1] - 30),
                              (drag_pos[0] + 80, drag_pos[1] + 30),
                              (255, 255, 255), 3)

                # Dragged text (English on left side), fit to 160x60 box
                drag_text = self.current_word['word']['english']
                drag_scale = self._fit_text_scale(drag_text, 160 - 24, 1.0)
                draw_text(img, drag_text,
                          (drag_pos[0] - 80 + 12, drag_pos[1] + 6), (0, 0, 0), drag_scale, 3)
                
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
                    # Auto-drop only if it's the correct target
                    if self.check_match(self.current_word, nearest_box):
                        # Perform drop and scoring
                        self.current_word['matched'] = True
                        nearest_box['matched'] = True
                        self.score += 10
                        self.matches_made += 1
                        # Success visuals
                        for i in range(3):
                            cv2.circle(img, nearest_box['center'], 30 + i*10, (0, 255, 0), 3)
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
                        # Reset drag state after successful drop
                        self.dragging = False
                        self.drag_latched = False
                        self.current_word = None
                    else:
                        # Indicate wrong target subtly
                        draw_text(img, "Wrong target", (drag_pos[0] - 50, drag_pos[1] - 55), (0, 0, 255), 0.5, 1)
        
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
        self.feedback_started_at = 0.0
        self.feedback_duration = 1.5  # seconds to fade out
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
        
        # Show feedback message with 1.5s fade-out
        if self.show_feedback:
            import time
            elapsed = time.time() - self.feedback_started_at
            if elapsed <= self.feedback_duration:
                alpha = max(0.0, 1.0 - (elapsed / self.feedback_duration))
                overlay_fb = img.copy()
                fb_w, fb_h = 420, 90
                fb_x = w//2 - fb_w//2
                fb_y = h//2 - 110
                bg = (self.feedback_color[0]//6, self.feedback_color[1]//6, self.feedback_color[2]//6)
                cv2.rectangle(overlay_fb, (fb_x, fb_y), (fb_x + fb_w, fb_y + fb_h), bg, -1)
                cv2.rectangle(overlay_fb, (fb_x, fb_y), (fb_x + fb_w, fb_y + fb_h), self.feedback_color, 2)
                draw_text(overlay_fb, self.feedback_message, (fb_x + 40, fb_y + 45), self.feedback_color, 1.2, 3)
                cv2.addWeighted(overlay_fb, alpha, img, 1 - alpha, 0, img)
            else:
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
            
            draw_text(img, "🎉 வாழ்த்துகள்! 🎉", (w//2 - 250, h//2 - 50), (255, 215, 0), 1.5, 4)
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
                        
                        # Show success feedback (fade out in 1.5s)
                        self.feedback_message = "சரி!"
                        self.feedback_color = (0, 255, 0)
                        self.show_feedback = True
                        self.feedback_started_at = current_time
                        self.feedback_duration = 1.5
                        
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


class ColorRecognitionGame:
    """Color Recognition Game - Show a target color; user points at that color in camera view"""

    def __init__(self):
        self.hand_tracker = HandTracker(max_hands=1, detection_confidence=0.7, tracking_confidence=0.7)
        # HSV ranges for common colors (H:0-179, S/V:0-255)
        # Each entry has one or more ranges to cover hue wrap (e.g., red)
        self.color_ranges = [
            {"name": "RED", "ranges": [((0, 120, 80), (10, 255, 255)), ((160, 120, 80), (179, 255, 255))], "bgr": (0, 0, 255)},
            {"name": "GREEN", "ranges": [((35, 80, 80), (85, 255, 255))], "bgr": (0, 200, 0)},
            {"name": "BLUE", "ranges": [((90, 80, 80), (130, 255, 255))], "bgr": (255, 0, 0)},
            {"name": "YELLOW", "ranges": [((20, 120, 120), (35, 255, 255))], "bgr": (0, 255, 255)},
            {"name": "ORANGE", "ranges": [((10, 120, 120), (20, 255, 255))], "bgr": (0, 165, 255)},
            {"name": "PURPLE", "ranges": [((130, 60, 60), (160, 255, 255))], "bgr": (255, 0, 255)},
        ]

        import random
        self.target = random.choice(self.color_ranges)
        self.score = 0
        self.rounds_done = 0
        self.total_rounds = 6
        self.stable_frames = 0
        self.required_stable_frames = 15
        self.show_feedback = False
        self.feedback_message = ""
        self.feedback_color = (0, 255, 0)
        self.feedback_started_at = 0.0
        self.feedback_duration = 1.5
        self.game_complete = False

    def setup_game(self, img_w, img_h):
        self.img_w = img_w
        self.img_h = img_h

    def _matches_target(self, hsv_pixel):
        h, s, v = int(hsv_pixel[0]), int(hsv_pixel[1]), int(hsv_pixel[2])
        for low, high in self.target["ranges"]:
            (lh, ls, lv), (hh, hs, hv) = low, high
            if lh <= h <= hh and ls <= s <= hs and lv <= v <= hv:
                return True
        return False

    def _choose_next_target(self):
        import random
        # Avoid repeating same target back-to-back
        options = [c for c in self.color_ranges if c["name"] != self.target["name"]]
        self.target = random.choice(options) if options else random.choice(self.color_ranges)

    def draw_game_ui(self, img):
        h, w = img.shape[:2]
        # Header
        header = img.copy()
        cv2.rectangle(header, (0, 0), (w, 110), (25, 35, 55), -1)
        cv2.addWeighted(header, 0.8, img, 0.2, 0, img)
        draw_text(img, "Color Recognition Game", (w//2 - 180, 35), (255, 215, 0), 1.2, 3)

        # Target panel
        draw_text(img, f"Find: {self.target['name']}", (50, 80), (255, 255, 255), 0.9, 2)
        cv2.rectangle(img, (200, 52), (260, 92), self.target["bgr"], -1)
        draw_text(img, f"Score: {self.score}", (w - 220, 60), (255, 255, 255), 0.8, 2)
        draw_text(img, f"Round: {self.rounds_done}/{self.total_rounds}", (w - 260, 85), (255, 255, 255), 0.7, 1)

        # Instructions footer
        footer_y = h - 80
        cv2.rectangle(img, (0, footer_y), (w, h), (30, 30, 30), -1)
        draw_text(img, "Point your index finger at something that matches the color", (50, footer_y + 25), (200, 200, 200), 0.7, 2)
        draw_text(img, "Press 'Q' to quit", (50, footer_y + 50), (255, 100, 100), 0.6, 1)

        # Feedback fade overlay
        if self.show_feedback:
            import time
            elapsed = time.time() - self.feedback_started_at
            if elapsed <= self.feedback_duration:
                alpha = max(0.0, 1.0 - (elapsed / self.feedback_duration))
                ov = img.copy()
                panel_w, panel_h = 480, 90
                px = w//2 - panel_w//2
                py = h//2 - 120
                bg = (self.feedback_color[0]//6, self.feedback_color[1]//6, self.feedback_color[2]//6)
                cv2.rectangle(ov, (px, py), (px + panel_w, py + panel_h), bg, -1)
                cv2.rectangle(ov, (px, py), (px + panel_w, py + panel_h), self.feedback_color, 2)
                draw_text(ov, self.feedback_message, (px + 30, py + 45), self.feedback_color, 1.0, 3)
                cv2.addWeighted(ov, alpha, img, 1 - alpha, 0, img)
            else:
                self.show_feedback = False

        # Completion overlay
        if self.game_complete:
            ov2 = img.copy()
            cv2.rectangle(ov2, (0, 0), (w, h), (0, 0, 0), -1)
            cv2.addWeighted(ov2, 0.6, img, 0.4, 0, img)
            draw_text(img, "Great job!", (w//2 - 100, h//2 - 40), (0, 255, 255), 1.2, 3)
            draw_text(img, f"Final Score: {self.score}", (w//2 - 120, h//2), (255, 255, 255), 1.0, 2)
            draw_text(img, "Press 'Q' to return to menu", (w//2 - 150, h//2 + 40), (200, 200, 200), 0.8, 2)

    def handle_game_logic(self, img):
        if self.game_complete:
            return
        h, w = img.shape[:2]

        # Draw target color mask softly (optional visual aid)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask_total = None
        for low, high in self.target["ranges"]:
            m = cv2.inRange(hsv, low, high)
            mask_total = m if mask_total is None else cv2.bitwise_or(mask_total, m)
        if mask_total is not None:
            mask_blur = cv2.GaussianBlur(mask_total, (21, 21), 0)
            colored = (np.dstack([mask_blur]*3) // 255) * np.array(self.target["bgr"], dtype=np.uint8)
            img[:] = cv2.addWeighted(img, 1.0, colored, 0.15, 0)
        # Use index finger tip as pointer (hand landmarks already computed in caller via find_hands)
        # Here we only extract landmarks from existing results without re-running detection
        landmarks = self.hand_tracker.get_landmarks(img)
        p = self.hand_tracker.get_index_finger_tip(landmarks)
        if p is not None:
            x, y = int(p[0]), int(p[1])
            cv2.circle(img, (x, y), 8, (0, 255, 255), -1)
            # Sample local average color around pointer to reduce noise
            x0, y0 = max(0, x - 4), max(0, y - 4)
            x1, y1 = min(w - 1, x + 4), min(h - 1, y + 4)
            patch = img[y0:y1 + 1, x0:x1 + 1]
            if patch.size > 0:
                hsv_px = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
                mean_hsv = hsv_px.reshape(-1, 3).mean(axis=0)
                if self._matches_target(mean_hsv):
                    self.stable_frames += 1
                    cv2.putText(img, "MATCH", (x + 12, y - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                else:
                    self.stable_frames = max(0, self.stable_frames - 2)
        else:
            # No hand
            self.stable_frames = max(0, self.stable_frames - 1)

        # Success condition
        if self.stable_frames >= self.required_stable_frames:
            import time
            self.score += 10
            self.rounds_done += 1
            self.feedback_message = f"Correct! That's {self.target['name']}"
            self.feedback_color = (0, 255, 0)
            self.show_feedback = True
            self.feedback_started_at = time.time()
            self.feedback_duration = 1.5
            self.stable_frames = 0
            if self.rounds_done >= self.total_rounds:
                self.game_complete = True
            else:
                self._choose_next_target()

def game_color_recognition():
    print("[Game] Starting Color Recognition...")
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)
    for _ in range(8):
        cap.read()
    game = ColorRecognitionGame()
    prev = None
    alpha = 0.75
    init = False
    while True:
        ret, img = cap.read()
        if not ret or img is None:
            continue
        if prev is not None and prev.shape == img.shape:
            img = cv2.addWeighted(img, alpha, prev, 1-alpha, 0)
        prev = img.copy()
        img = cv2.flip(img, 1)
        h, w = img.shape[:2]
        if not init:
            game.setup_game(w, h)
            init = True
        img = game.hand_tracker.find_hands(img, draw=True)
        game.handle_game_logic(img)
        game.draw_game_ui(img)
        cv2.imshow("Color Recognition Game", img)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or game.game_complete:
            if game.game_complete:
                cv2.waitKey(2000)
            break
    cap.release()
    cv2.destroyAllWindows()


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

