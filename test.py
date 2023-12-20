import cv2
from ultralytics import YOLO
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import time

license_plate_detector = YOLO('license_plate_detector.pt')

cap = cv2.VideoCapture(0)

while True:
    success, img = cap.read()

    # Use YOLOv8 for license plate detection
    license_plates = license_plate_detector(img)[0]

    for license_plate in license_plates.boxes.data.tolist():
        x1, y1, x2, y2, score, class_id = license_plate

        cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)

        # process license plate
        license_plate_crop = img[int(y1):int(y2), int(x1): int(x2), :]
        cv2.imshow("roi", license_plate_crop)
        license_plate_crop_gray = cv2.cvtColor(license_plate_crop, cv2.COLOR_BGR2GRAY)
        _, license_plate_crop_thresh = cv2.threshold(license_plate_crop_gray, 64, 255, cv2.THRESH_BINARY_INV)

    # Show the result in a window
    cv2.imshow("License Plate Detection", img)

    # Break the loop if 'q' key is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the camera and close the window
cap.release()
cv2.destroyAllWindows()
