# Hand tracking utilities with improved stability
import mediapipe as mp
import cv2
import numpy as np
from collections import deque
import math

class HandTracker:
    def __init__(self, max_hands=2, detection_confidence=0.6, tracking_confidence=0.7, processing_scale=0.75):
        self.mp_hands = mp.solutions.hands

        # Optimized MediaPipe configuration for better detection
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_hands,
            min_detection_confidence=detection_confidence,  # Lowered for better detection
            min_tracking_confidence=tracking_confidence,    # Lowered for better tracking
            model_complexity=0  # Use lighter model for better performance and stability
        )

        self.mp_draw = mp.solutions.drawing_utils

        # Processing scale for performance (process smaller frame for speed)
        self.processing_scale = max(0.5, min(1.0, processing_scale))

        # Enhanced smoothing and filtering
        self.landmark_history = deque(maxlen=3)  # Reduced for faster response
        self.finger_state_history = deque(maxlen=2)  # Faster finger state changes
        self.gesture_confidence_threshold = 0.5  # Lowered threshold

        # Improved gesture stability
        self.last_gesture = None
        self.gesture_counter = 0
        self.gesture_stability_frames = 2  # Reduced for faster response

        # Better position smoothing
        self.smoothed_landmarks = None
        self.smoothing_factor = 0.5  # Lighter smoothing for better responsiveness

    def find_hands(self, img, draw=True):
        # Enhanced preprocessing for better hand detection
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Optional slight Gaussian blur to reduce noise
        img_rgb = cv2.GaussianBlur(img_rgb, (3, 3), 0)

        # Downscale for processing to improve performance
        if self.processing_scale < 1.0:
            small = cv2.resize(img_rgb, None, fx=self.processing_scale, fy=self.processing_scale, interpolation=cv2.INTER_AREA)
            self.results = self.hands.process(small)
        else:
            self.results = self.hands.process(img_rgb)

        if self.results.multi_hand_landmarks:
            for handLms in self.results.multi_hand_landmarks:
                if draw:
                    # Draw landmarks with enhanced visibility
                    self.mp_draw.draw_landmarks(
                        img, handLms, self.mp_hands.HAND_CONNECTIONS,
                        self.mp_draw.DrawingSpec(color=(0, 255, 0), thickness=3, circle_radius=3),
                        self.mp_draw.DrawingSpec(color=(255, 255, 255), thickness=2)
                    )

                    # Add hand detection confidence indicator
                    h, w, _ = img.shape
                    cv2.putText(img, f"Hand Detected", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            # No hands detected; avoid noisy console/UI text here
            pass

        return img

    def get_landmarks(self, img):
        landmarks = []
        if self.results.multi_hand_landmarks:
            for handLms in self.results.multi_hand_landmarks:
                frame_landmarks = []
                for id, lm in enumerate(handLms.landmark):
                    h, w, c = img.shape
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    frame_landmarks.append((id, cx, cy))
                landmarks = frame_landmarks
                
                # Apply smoothing
                landmarks = self.smooth_landmarks(landmarks)
                break  # Only process first hand
        
        return landmarks
    
    # Removed earlier duplicate of get_all_landmarks/count_all_fingers to keep single, consistent implementations below
    
    def get_all_landmarks(self, img):
        """Get landmarks for all detected hands"""
        all_landmarks = []
        if self.results.multi_hand_landmarks:
            h, w, _ = img.shape
            for handLms in self.results.multi_hand_landmarks:
                landmarks = []
                for id, lm in enumerate(handLms.landmark):
                    x, y = int(lm.x * w), int(lm.y * h)
                    landmarks.append((id, x, y))
                all_landmarks.append(landmarks)
        return all_landmarks
    
    def count_all_fingers(self, img):
        """Count fingers on all detected hands and return total count and individual counts"""
        all_landmarks = self.get_all_landmarks(img)
        hand_finger_counts = []
        total_fingers = 0
        
        for landmarks in all_landmarks:
            if landmarks and len(landmarks) >= 21:  # Full hand detected
                finger_count = self.count_fingers_from_landmarks(landmarks)
                hand_finger_counts.append(finger_count)
                total_fingers += finger_count
        
        return total_fingers, hand_finger_counts
    
    def count_fingers_from_landmarks(self, landmarks):
        """Count fingers from landmark data"""
        if not landmarks or len(landmarks) < 21:
            return 0
        
        # Convert landmarks to position list
        landmark_positions = [(lm[1], lm[2]) for lm in landmarks]
        
        # Finger tip and pip landmarks
        tip_ids = [4, 8, 12, 16, 20]  # Thumb, Index, Middle, Ring, Pinky tips
        pip_ids = [3, 6, 10, 14, 18]  # Corresponding pip joints
        
        fingers = []
        
        # Thumb (special case - check x-coordinate)
        if landmark_positions[tip_ids[0]][0] > landmark_positions[pip_ids[0]][0]:
            fingers.append(1)
        else:
            fingers.append(0)
        
        # Other fingers (check y-coordinate)
        for i in range(1, 5):
            if landmark_positions[tip_ids[i]][1] < landmark_positions[pip_ids[i]][1]:
                fingers.append(1)
            else:
                fingers.append(0)
        
        return sum(fingers)
    
    def get_multi_hand_confidence(self, img):
        """Get confidence score for multi-hand detection"""
        if not self.results.multi_hand_landmarks:
            return 0.0
        
        # Calculate average confidence across all hands
        confidences = []
        all_landmarks = self.get_all_landmarks(img)
        for landmarks in all_landmarks:
            if landmarks and len(landmarks) >= 21:
                # Simple confidence based on landmark consistency and hand completeness
                confidence = min(1.0, len(landmarks) / 21.0)  # 21 landmarks per hand
                confidences.append(confidence)
        
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    def smooth_landmarks(self, landmarks):
        """Apply temporal smoothing to reduce jitter"""
        if not landmarks:
            return landmarks
        
        # Add current landmarks to history
        self.landmark_history.append(landmarks)
        
        if len(self.landmark_history) < 2:
            return landmarks
        
        # Calculate smoothed positions
        smoothed = []
        for i, (id, x, y) in enumerate(landmarks):
            # Weighted average of recent positions
            total_weight = 0
            weighted_x = 0
            weighted_y = 0
            
            for j, hist_landmarks in enumerate(self.landmark_history):
                if i < len(hist_landmarks):
                    weight = (j + 1) / len(self.landmark_history)  # More recent = higher weight
                    weighted_x += hist_landmarks[i][1] * weight
                    weighted_y += hist_landmarks[i][2] * weight
                    total_weight += weight
            
            if total_weight > 0:
                smooth_x = int(weighted_x / total_weight)
                smooth_y = int(weighted_y / total_weight)
                smoothed.append((id, smooth_x, smooth_y))
            else:
                smoothed.append((id, x, y))
        
        return smoothed
    
    def get_finger_states(self, landmarks):
        """Get stable finger up/down states with hysteresis"""
        if not landmarks:
            return None
        
        # Finger tip and pip landmarks
        finger_tips = [4, 8, 12, 16, 20]  # Thumb, Index, Middle, Ring, Pinky
        finger_pips = [3, 6, 10, 14, 18]
        finger_mcps = [2, 5, 9, 13, 17]  # MCP joints for additional stability
        
        current_fingers = []
        
        for i in range(5):
            tip_id = finger_tips[i]
            pip_id = finger_pips[i]
            mcp_id = finger_mcps[i]
            
            # Get coordinates
            tip_pos = next((lm for lm in landmarks if lm[0] == tip_id), None)
            pip_pos = next((lm for lm in landmarks if lm[0] == pip_id), None)
            mcp_pos = next((lm for lm in landmarks if lm[0] == mcp_id), None)
            
            if tip_pos and pip_pos and mcp_pos:
                if i == 0:  # Thumb - horizontal check
                    # Check if thumb tip is to the right of pip (for right hand)
                    finger_up = tip_pos[1] > pip_pos[1]
                else:  # Other fingers - vertical check with MCP reference
                    # Check if tip is above pip AND pip is above mcp
                    finger_up = (tip_pos[2] < pip_pos[2]) and (pip_pos[2] < mcp_pos[2])
                
                current_fingers.append(1 if finger_up else 0)
            else:
                current_fingers.append(0)
        
        # Add to history for stability
        self.finger_state_history.append(current_fingers)
        
        # Return most consistent state
        return self.get_stable_finger_state()
    
    def get_stable_finger_state(self):
        """Get the most stable finger state from recent history"""
        if len(self.finger_state_history) < 2:
            return self.finger_state_history[-1] if self.finger_state_history else [0, 0, 0, 0, 0]
        
        # Calculate consensus from recent frames
        stable_fingers = []
        for finger_idx in range(5):
            finger_votes = [frame[finger_idx] for frame in self.finger_state_history if finger_idx < len(frame)]
            
            if finger_votes:
                # Use majority vote with bias toward previous state
                up_votes = sum(finger_votes)
                down_votes = len(finger_votes) - up_votes
                
                # Add slight bias to previous state for stability
                if len(self.finger_state_history) >= 2:
                    prev_state = self.finger_state_history[-2][finger_idx] if finger_idx < len(self.finger_state_history[-2]) else 0
                    if prev_state == 1:
                        up_votes += 0.5
                    else:
                        down_votes += 0.5
                
                stable_fingers.append(1 if up_votes > down_votes else 0)
            else:
                stable_fingers.append(0)
        
        return stable_fingers
    
    def count_fingers(self, landmarks):
        """Count fingers with improved stability"""
        finger_states = self.get_finger_states(landmarks)
        return sum(finger_states) if finger_states else None
    
    def is_fist(self, landmarks, threshold=0.15):
        """Detect fist gesture with improved accuracy"""
        if not landmarks:
            return False
        
        finger_states = self.get_finger_states(landmarks)
        if not finger_states:
            return False
        
        # Check if all fingers are down
        fingers_down = sum(finger_states) == 0
        
        # Additional check: measure compactness of hand
        if fingers_down:
            # Get bounding box of hand
            xs = [lm[1] for lm in landmarks]
            ys = [lm[2] for lm in landmarks]
            
            if xs and ys:
                width = max(xs) - min(xs)
                height = max(ys) - min(ys)
                
                # Fist should be more compact
                aspect_ratio = width / height if height > 0 else 1
                compactness = min(width, height) / max(width, height) if max(width, height) > 0 else 0
                
                return compactness > threshold
        
        return fingers_down
    
    def get_index_finger_tip(self, landmarks):
        """Get smoothed index finger tip position"""
        if not landmarks:
            return None
        
        index_tip = next((lm for lm in landmarks if lm[0] == 8), None)
        if index_tip:
            return (index_tip[1], index_tip[2])
        return None
    
    def calculate_distance(self, pos1, pos2):
        """Calculate Euclidean distance between two points"""
        if pos1 and pos2:
            return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
        return float('inf')
    
    def is_pointing(self, landmarks):
        """Detect pointing gesture (only index finger up)"""
        finger_states = self.get_finger_states(landmarks)
        if not finger_states:
            return False
        
        # Only index finger should be up
        expected_pattern = [0, 1, 0, 0, 0]  # thumb, index, middle, ring, pinky
        return finger_states == expected_pattern
    
    def get_gesture_confidence(self, landmarks):
        """Get confidence score for current gesture detection"""
        if not landmarks or not self.results.multi_hand_landmarks:
            return 0.0
        
        # Basic confidence from MediaPipe detection
        base_confidence = 0.8  # MediaPipe doesn't directly provide confidence
        
        # Reduce confidence if hand is at edge of frame
        hand_landmarks = self.results.multi_hand_landmarks[0]
        center_x = sum([lm.x for lm in hand_landmarks.landmark]) / len(hand_landmarks.landmark)
        center_y = sum([lm.y for lm in hand_landmarks.landmark]) / len(hand_landmarks.landmark)
        
        # Reduce confidence if too close to edges
        edge_penalty = 0
        if center_x < 0.1 or center_x > 0.9 or center_y < 0.1 or center_y > 0.9:
            edge_penalty = 0.3
        
        return max(0.0, base_confidence - edge_penalty)
