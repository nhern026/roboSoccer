"""
Run this script standalone to find the right HSV range for your ball under
your arena lighting.

    python hsv_calibrate.py          # uses camera index 0
    python hsv_calibrate.py 1        # uses camera index 1

Drag the sliders until only the ball shows as white in the mask window.
Press 'p' to print the current values — paste them into cv_pipeline.py.
Press 'q' to quit.
"""

import sys
import cv2
import numpy as np


def nothing(_): pass


def main(cam_index: int = 0):
    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        print(f"Cannot open camera {cam_index}")
        sys.exit(1)

    cv2.namedWindow("HSV Calibrate")
    cv2.namedWindow("Mask")

    defaults = {
        "H Low": 5,  "H High": 20,
        "S Low": 150, "S High": 255,
        "V Low": 150, "V High": 255,
    }

    for name, val in defaults.items():
        cv2.createTrackbar(name, "HSV Calibrate", val, 255, nothing)

    print("Adjust sliders. Press 'p' to print values, 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        blurred = cv2.GaussianBlur(frame, (11, 11), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

        h_lo = cv2.getTrackbarPos("H Low",  "HSV Calibrate")
        h_hi = cv2.getTrackbarPos("H High", "HSV Calibrate")
        s_lo = cv2.getTrackbarPos("S Low",  "HSV Calibrate")
        s_hi = cv2.getTrackbarPos("S High", "HSV Calibrate")
        v_lo = cv2.getTrackbarPos("V Low",  "HSV Calibrate")
        v_hi = cv2.getTrackbarPos("V High", "HSV Calibrate")

        lower = np.array([h_lo, s_lo, v_lo])
        upper = np.array([h_hi, s_hi, v_hi])
        mask = cv2.inRange(hsv, lower, upper)

        cv2.imshow("HSV Calibrate", frame)
        cv2.imshow("Mask", mask)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key == ord("p"):
            print(f"\n# Paste into cv_pipeline.py:")
            print(f"HSV_LOWER = np.array([{h_lo}, {s_lo}, {v_lo}])")
            print(f"HSV_UPPER = np.array([{h_hi}, {s_hi}, {v_hi}])\n")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    main(idx)
