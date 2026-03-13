import cv2 as cv
import mediapipe as mp
import numpy as np
from poseEstimation import poseModule as pose

cap = cv.VideoCapture(0)
c1 = pose.poseDetect()

# Direction & counters
dir1 = 0
rcount = 0

# Stability variables
bad_posture_frames = 0
good_posture_frames = 0
current_msg = ""
required_frames = 7

while True:

    success, img = cap.read()
    if not success or img is None:
        continue

    c1.poseDetection(img)
    c1.findPose(img, draw=False)

    if not hasattr(c1, "poses") or len(c1.poses) == 0:
        cv.putText(img, "NO PERSON DETECTED",
                   (40, 60), cv.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)
        cv.imshow("Lateral Raise Trainer", img)
        cv.waitKey(1)
        continue

    lmList = c1.poses

    # ------------------- ARM ANGLES ------------------- #

    # shoulder–elbow–wrist
    left_elbow  = c1.findAngle(img, 11, 13, 15,)
    right_elbow = c1.findAngle(img, 12, 14, 16)

    # hip-shoulder-wrist
    right_arm = c1.findAngle(img, 24, 12, 14)
    left_arm = c1.findAngle(img, 23, 11, 13)

    # torso
    back_angle = c1.findAngle(img, 24, 12, 11,draw=False)

    if left_arm is None or right_arm is None or back_angle is None:
        cv.putText(img, "BODY NOT FULLY DETECTED",
                   (40, 60), cv.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)
        cv.imshow("Lateral Raise Trainer", img)
        cv.waitKey(1)
        continue

    # ---------------- RANGE MAPPING ---------------- #

    # arms down ≈ 170°, arms up ≈ 70–90°
    min_angle = 30
    max_angle = 87

    min_el_angle = 150
    max_el_angle = 166

    def calc_range(left_arm,right_arm,min_angle,max_angle):

        left_arm_c  = np.clip(left_arm,  min_angle, max_angle)
        right_arm_c = np.clip(right_arm, min_angle, max_angle)

        left_range  = np.interp(left_arm_c,  (min_angle, max_angle), (100, 0))
        right_range = np.interp(right_arm_c, (min_angle, max_angle), (100, 0))

        return (left_range + right_range) / 2

    avg_range = calc_range(left_arm,right_arm,min_angle,max_angle)

    avg_range2 = calc_range(left_elbow,right_elbow,min_el_angle,max_el_angle)

    # ---------------- POSTURE CHECK ---------------- #

    dx_left = abs(lmList[15][1] - lmList[11][1])
    dx_right = abs(lmList[16][1] - lmList[12][1])

    dy_left = abs(lmList[15][2] - lmList[11][2])
    dy_right = abs(lmList[16][2] - lmList[12][2])

    new_msg = ""

    # upright torso
    if back_angle < 65 or back_angle > 135:
        new_msg = "KEEP YOUR BACK STRAIGHT!"

    # arms together
    # elif abs(left_range - right_range) > 30:
    #     new_msg = "RAISE BOTH ARMS EVENLY!"

    elif dx_left < dy_left and dx_right < dy_right:
        new_msg = "move both hands sideways."
    # going too high
    elif left_arm > 100 or right_arm > 100:
        new_msg = "DON'T GO ABOVE SHOULDERS!"
    # elbow bending    
    # elif avg_range2 < 5:
    #     new_msg = "bend elbows a little bit"    
    else:
        new_msg = ""

    # -------- Stability Filter -------- #

    if new_msg != "":
        bad_posture_frames += 1
        good_posture_frames = 0

        if bad_posture_frames >= required_frames:
            current_msg = new_msg

    else:
        good_posture_frames += 1
        bad_posture_frames = 0

        if good_posture_frames >= required_frames:
            current_msg = ""

    # ---------------- REP COUNT ---------------- #

    # arms up
    if avg_range < 10 and current_msg == "":
        if dir1 == 0:
            rcount += 0.5
            dir1 = 1

    # arms down
    if avg_range > 90 and current_msg == "":
        if dir1 == 1:
            rcount += 0.5
            dir1 = 0

    # ---------------- DISPLAY ---------------- #

    cv.putText(img, f"Lateral Raises: {int(rcount)}", (40, 120),
               cv.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)
    
    cv.putText(img, f"left arm: {int(left_arm)}", (40, 140),
               cv.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)
    
    cv.putText(img, f"right arm: {int(right_arm)}", (40, 170),
               cv.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)

    cv.putText(img, f"Height: {int(avg_range)}%", (40, 190),
               cv.FONT_HERSHEY_PLAIN, 1.5, (255, 255, 0), 2)
    
    cv.putText(img, f"Height2: {int(avg_range2)}%", (40, 210),
               cv.FONT_HERSHEY_PLAIN, 1.5, (255, 255, 0), 2)

    if current_msg != "":
        cv.putText(img, current_msg, (40, 60),
                   cv.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)

    cv.imshow("Shoulder Lateral Raise Trainer", img)

    if cv.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv.destroyAllWindows()
