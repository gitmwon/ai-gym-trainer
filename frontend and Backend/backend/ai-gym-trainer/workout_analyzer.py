import cv2 as cv
import numpy as np
import sys
import os

# Add workout_tracker to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'workout_tracker'))

from poseEstimation import poseModule as pose

class WorkoutAnalyzer:
    def __init__(self, workout_type):
        self.workout_type = workout_type
        self.detector = pose.poseDetect()
        self.reset_state()
        
    def reset_state(self):
        """Reset workout state"""
        self.reps = 0
        self.dir = 0
        self.feedback = ""
        self.form_score = 100
        self.bad_posture_frames = 0
        self.good_posture_frames = 0
        self.required_frames = 7
        
    def analyze_frame(self, frame):
        """Analyze a single frame and return workout data"""
        try:
            # Detect pose and draw skeleton
            self.detector.poseDetection(frame, draw=True)  # Enable drawing
            lmList = self.detector.findPose(frame, draw=False)
            
            # Store lmList for skeleton drawing
            self.detector.lmList = lmList if lmList else []
            
            # Route to specific workout analyzer
            if self.workout_type == 'leg/squats':
                return self.analyze_squats(frame)
            elif self.workout_type == 'bicep/bicep_curl':
                return self.analyze_bicep_curl(frame)
            elif self.workout_type == 'chest/pushupcheck':
                return self.analyze_pushups(frame)
            elif self.workout_type == 'leg/lunges':
                return self.analyze_lunges(frame)
            elif self.workout_type == 'shoulder/lateral':
                return self.analyze_lateral_raises(frame)
            else:
                return {
                    'reps': 0,
                    'feedback': 'Workout type not supported yet',
                    'formScore': 0,
                    'angles': {}
                }
                
        except Exception as e:
            print(f'❌ Analyzer error: {str(e)}')
            import traceback
            traceback.print_exc()
            return {
                'reps': self.reps,
                'feedback': f'Error: {str(e)}',
                'formScore': 0,
                'angles': {}
            }
    
    def analyze_squats(self, frame):
        """Squat analysis logic"""
        # Check if pose is detected
        if not hasattr(self.detector, 'poses') or not self.detector.poses or len(self.detector.poses) < 29:
            return {
                'reps': self.reps,
                'feedback': 'BODY NOT FULLY DETECTED',
                'formScore': 0,
                'angles': {}
            }
        
        # Get angles (MediaPipe landmark indices)
        right_knee = self.detector.findAngle(frame, 24, 26, 28, draw=False)
        left_knee = self.detector.findAngle(frame, 23, 25, 27, draw=False)
        back_angle = self.detector.findAngle(frame, 24, 12, 11, draw=False)
        
        if right_knee is None or left_knee is None or back_angle is None:
            return {
                'reps': self.reps,
                'feedback': 'BODY NOT FULLY DETECTED',
                'formScore': 0,
                'angles': {}
            }
        
        print(f'🔍 Squat angles - Right knee: {right_knee:.1f}, Left knee: {left_knee:.1f}, Back: {back_angle:.1f}')
        
        # Map angles to range
        min_angle = 70
        max_angle = 170
        right_range = np.interp(right_knee, (min_angle, max_angle), (100, 0))
        left_range = np.interp(left_knee, (min_angle, max_angle), (100, 0))
        
        print(f'📊 Squat range - Right: {right_range:.1f}, Left: {left_range:.1f}, Dir: {self.dir}')
        
        # Posture check
        new_msg = ""
        self.form_score = 100
        
        if back_angle < 65 or back_angle > 135:
            new_msg = "KEEP YOUR BACK STRAIGHT!"
            self.form_score -= 20
        elif abs(right_range - left_range) > 35:
            new_msg = "BEND BOTH KNEES EQUALLY!"
            self.form_score -= 15
        elif right_knee > 155 and left_knee > 155:
            new_msg = "GO LOWER!"
            self.form_score -= 10
        
        # Stability filter
        if new_msg != "":
            self.bad_posture_frames += 1
            self.good_posture_frames = 0
            if self.bad_posture_frames >= self.required_frames:
                self.feedback = new_msg
        else:
            self.good_posture_frames += 1
            self.bad_posture_frames = 0
            if self.good_posture_frames >= self.required_frames:
                self.feedback = ""
        
        # Rep counting
        if right_range >= 95 and self.feedback == "":
            if self.dir == 0:
                self.reps += 0.5
                self.dir = 1
                print(f'⬆️ Squat UP - Reps: {self.reps}')
        
        if right_range <= 10 and self.feedback == "":
            if self.dir == 1:
                self.reps += 0.5
                self.dir = 0
                print(f'⬇️ Squat DOWN - Reps: {self.reps}')
        
        return {
            'reps': int(self.reps),
            'feedback': self.feedback,
            'formScore': max(0, self.form_score),
            'angles': {
                'rightKnee': int(right_knee),
                'leftKnee': int(left_knee),
                'back': int(back_angle)
            }
        }
    
    def analyze_bicep_curl(self, frame):
        """Bicep curl analysis logic"""
        # Check if pose is detected
        if not hasattr(self.detector, 'poses') or not self.detector.poses or len(self.detector.poses) < 17:
            return {
                'reps': self.reps,
                'feedback': 'UPPER BODY NOT DETECTED',
                'formScore': 0,
                'angles': {}
            }
        
        # Get angles
        right = self.detector.findAngle(frame, 16, 14, 12, draw=False)
        left = self.detector.findAngle(frame, 11, 13, 15, draw=False)
        back_angle = self.detector.findAngle(frame, 24, 12, 11, draw=False)
        
        if right is None or left is None:
            return {
                'reps': self.reps,
                'feedback': 'ARMS NOT DETECTED',
                'formScore': 0,
                'angles': {}
            }
        
        print(f'🔍 Bicep curl angles - Right arm: {right:.1f}, Left arm: {left:.1f}')
        
        # Map angles
        min_angle = 15
        max_angle = 170
        right_range = np.interp(right, (min_angle, max_angle), (0, 100))
        left_range = np.interp(left, (min_angle, max_angle), (0, 100))
        
        print(f'📊 Bicep range - Right: {right_range:.1f}, Left: {left_range:.1f}, Dir: {self.dir}')
        
        # Posture check
        new_msg = ""
        self.form_score = 100
        
        if back_angle and (back_angle < 70 or back_angle > 110):
            new_msg = "KEEP YOUR BACK STRAIGHT!"
            self.form_score -= 20
        elif abs(right_range - left_range) > 40:
            new_msg = "BOTH HANDS NOT SYNCED!"
            self.form_score -= 15
        
        # Stability filter
        if new_msg != "":
            self.bad_posture_frames += 1
            self.good_posture_frames = 0
            if self.bad_posture_frames >= self.required_frames:
                self.feedback = new_msg
        else:
            self.good_posture_frames += 1
            self.bad_posture_frames = 0
            if self.good_posture_frames >= self.required_frames:
                self.feedback = ""
        
        # Rep counting (using right arm)
        if right_range <= 10 and self.feedback == "":
            if self.dir == 0:
                self.reps += 0.5
                self.dir = 1
                print(f'💪 Curl UP - Reps: {self.reps}')
        if right_range > 90 and self.feedback == "":
            if self.dir == 1:
                self.reps += 0.5
                self.dir = 0
                print(f'💪 Curl DOWN - Reps: {self.reps}')
        
        return {
            'reps': int(self.reps),
            'feedback': self.feedback,
            'formScore': max(0, self.form_score),
            'angles': {
                'rightArm': int(right),
                'leftArm': int(left),
                'back': int(back_angle) if back_angle else 0
            }
        }
    
    def analyze_pushups(self, frame):
        """Push-up analysis logic"""
        # Get angles
        right_elbow = self.detector.findAngle(frame, 12, 14, 16)
        left_elbow = self.detector.findAngle(frame, 11, 13, 15)
        
        if right_elbow is None or left_elbow is None:
            return {
                'reps': self.reps,
                'feedback': 'BODY NOT FULLY DETECTED',
                'formScore': 0,
                'angles': {}
            }
        
        avg_angle = (right_elbow + left_elbow) / 2
        
        # Posture check
        self.form_score = 100
        if avg_angle > 160:
            self.feedback = "Lower your body"
            self.form_score = 60
        elif avg_angle < 90:
            self.feedback = "Push up!"
            self.form_score = 80
        else:
            self.feedback = ""
            self.form_score = 100
        
        # Rep counting
        if avg_angle > 160:
            self.dir = 0
        if avg_angle < 90 and self.dir == 0:
            self.dir = 1
            self.reps += 1
        
        return {
            'reps': int(self.reps),
            'feedback': self.feedback,
            'formScore': self.form_score,
            'angles': {
                'rightElbow': int(right_elbow),
                'leftElbow': int(left_elbow)
            }
        }
    
    def analyze_lunges(self, frame):
        """Lunge analysis logic"""
        # Get angles
        left_knee = self.detector.findAngle(frame, 23, 25, 27)
        right_knee = self.detector.findAngle(frame, 24, 26, 28)
        back_angle = self.detector.findAngle(frame, 24, 12, 11)
        
        if left_knee is None or right_knee is None or back_angle is None:
            return {
                'reps': self.reps,
                'feedback': 'BODY NOT FULLY DETECTED',
                'formScore': 0,
                'angles': {}
            }
        
        # Map angles
        min_angle = 70
        max_angle = 170
        left_range = np.interp(left_knee, (min_angle, max_angle), (100, 0))
        right_range = np.interp(right_knee, (min_angle, max_angle), (100, 0))
        avg_range = (left_range + right_range) / 2
        
        # Posture check
        new_msg = ""
        self.form_score = 100
        
        if back_angle < 65 or back_angle > 135:
            new_msg = "KEEP YOUR BACK STRAIGHT!"
            self.form_score -= 20
        elif abs(left_range - right_range) > 50:
            new_msg = "BEND BOTH LEGS!"
            self.form_score -= 15
        elif left_knee > 155 and right_knee > 155:
            new_msg = "GO LOWER!"
            self.form_score -= 10
        
        # Stability filter
        if new_msg != "":
            self.bad_posture_frames += 1
            self.good_posture_frames = 0
            if self.bad_posture_frames >= self.required_frames:
                self.feedback = new_msg
        else:
            self.good_posture_frames += 1
            self.bad_posture_frames = 0
            if self.good_posture_frames >= self.required_frames:
                self.feedback = ""
        
        # Rep counting
        if avg_range >= 95 and self.feedback == "":
            if self.dir == 0:
                self.reps += 0.5
                self.dir = 1
        if avg_range <= 10 and self.feedback == "":
            if self.dir == 1:
                self.reps += 0.5
                self.dir = 0
        
        return {
            'reps': int(self.reps),
            'feedback': self.feedback,
            'formScore': max(0, self.form_score),
            'angles': {
                'leftKnee': int(left_knee),
                'rightKnee': int(right_knee),
                'back': int(back_angle)
            }
        }
    
    def analyze_lateral_raises(self, frame):
        """Lateral raise analysis logic"""
        # Get angles
        left_arm = self.detector.findAngle(frame, 23, 11, 13)
        right_arm = self.detector.findAngle(frame, 24, 12, 14)
        back_angle = self.detector.findAngle(frame, 24, 12, 11)
        
        if left_arm is None or right_arm is None or back_angle is None:
            return {
                'reps': self.reps,
                'feedback': 'BODY NOT FULLY DETECTED',
                'formScore': 0,
                'angles': {}
            }
        
        # Map angles
        min_angle = 30
        max_angle = 87
        left_range = np.interp(np.clip(left_arm, min_angle, max_angle), (min_angle, max_angle), (100, 0))
        right_range = np.interp(np.clip(right_arm, min_angle, max_angle), (min_angle, max_angle), (100, 0))
        avg_range = (left_range + right_range) / 2
        
        # Posture check
        new_msg = ""
        self.form_score = 100
        
        if back_angle < 65 or back_angle > 135:
            new_msg = "KEEP YOUR BACK STRAIGHT!"
            self.form_score -= 20
        elif left_arm > 100 or right_arm > 100:
            new_msg = "DON'T GO ABOVE SHOULDERS!"
            self.form_score -= 15
        
        # Stability filter
        if new_msg != "":
            self.bad_posture_frames += 1
            self.good_posture_frames = 0
            if self.bad_posture_frames >= self.required_frames:
                self.feedback = new_msg
        else:
            self.good_posture_frames += 1
            self.bad_posture_frames = 0
            if self.good_posture_frames >= self.required_frames:
                self.feedback = ""
        
        # Rep counting
        if avg_range < 10 and self.feedback == "":
            if self.dir == 0:
                self.reps += 0.5
                self.dir = 1
        if avg_range > 90 and self.feedback == "":
            if self.dir == 1:
                self.reps += 0.5
                self.dir = 0
        
        return {
            'reps': int(self.reps),
            'feedback': self.feedback,
            'formScore': max(0, self.form_score),
            'angles': {
                'leftArm': int(left_arm),
                'rightArm': int(right_arm),
                'back': int(back_angle)
            }
        }
