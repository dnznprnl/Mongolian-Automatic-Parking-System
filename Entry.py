import cv2
import pytesseract
import time
import re
import sqlite3
from datetime import datetime
from collections import Counter
import os
import sys
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from ultralytics import YOLO
font_size = 20
font_color = (0, 0, 255)

try:
    custom_font = ImageFont.truetype("arial.ttf", font_size)
except Exception as e:
    print("Arial font could not be loaded. Using default font.")
    custom_font = ImageFont.load_default()

license_plate_detector = YOLO('license_plate_detector.pt')

# Database - рүү холбогдох
conn = sqlite3.connect('license_plates.db')

# SQL query ажиллуулах cursor объект
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS entry_plates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plate_number TEXT NOT NULL,
        timestamp DATETIME NOT NULL
    )
''')

conn.commit()
conn.close()

def restart_program():
    python = sys.executable
    os.execl(python, python, *sys.argv)

cap = cv2.VideoCapture(0)

cap.set(3, 640)  # width
cap.set(4, 480)  # height

min_area = 500

count = 0
start_time = time.time()

# Илрүүлсэн номерыг хадгалах
detected_plates = []

# Датабаз-д хадгалахаас өмнө шалгах удаа
consecutive_detection_threshold = 10

# Батлагдсан улсын дугаар
confirmed_plate = None
confirmed_plate_count = 0

inserted_plates = set()

# Улсын дугаар датабаз-д байгаа эсэхийг шалгах
def is_plate_exists(plate_number):
    conn = sqlite3.connect('license_plates.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM entry_plates WHERE plate_number = ?', (plate_number,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

status_window = np.zeros((480, 600, 3), dtype=np.uint8)

current_frame_plates = []

plates_folder = "plates"

while True:
    success, img = cap.read()

    license_plates = license_plate_detector(img)[0]

    for license_plate in license_plates.boxes.data.tolist():
        x1, y1, x2, y2, score, class_id = license_plate

        cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)

        # process license plate
        license_plate_crop = img[int(y1):int(y2), int(x1): int(x2), :]
        license_plate_crop_gray = cv2.cvtColor(license_plate_crop, cv2.COLOR_BGR2GRAY)
        _, license_plate_crop_thresh = cv2.threshold(license_plate_crop_gray, 64, 255, cv2.THRESH_BINARY_INV)

        cv2.imwrite(f"{plates_folder}/roi_{count}.jpg", license_plate_crop)

        saved_img = cv2.imread(f"plates/roi_{count}.jpg")
        saved_img_gray = cv2.cvtColor(saved_img, cv2.COLOR_BGR2GRAY)
        #cv2.imshow("saved_img_gray", saved_img_gray)
        saved_img_gray = cv2.resize(saved_img_gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        #cv2.imshow("saved_img_resize", saved_img_gray)
        saved_img_gray = cv2.GaussianBlur(saved_img_gray, (5, 5), 0)
        #cv2.imshow("saved_img_blured", saved_img_gray)
        _, img_thresh = cv2.threshold(saved_img_gray, 128, 255, cv2.THRESH_BINARY_INV)

        license_plate_number = pytesseract.image_to_string(img_thresh, lang='mon', config='--oem 3 --psm 6')

        filtered_license_plate = re.sub(r'[^0-9АБВГДЕЗИКЛМНОӨПРСТУҮХЦЧЭЯ]', '', license_plate_number)

            # улсын дугаарын формат
        if re.match(r'^\d{4}[А-ЯҮӨ]{3}$', filtered_license_plate):
            current_frame_plates.append(filtered_license_plate)

            text_file_path = f"{plates_folder}/plate_{count}.txt"
            with open(text_file_path, "w", encoding="utf-8") as f:
                f.write(filtered_license_plate)

    detected_plates.extend(current_frame_plates)

    detected_plates = detected_plates[-consecutive_detection_threshold:]

    plate_counter = Counter(detected_plates)

    most_common_plate = plate_counter.most_common(1)

    if most_common_plate:
        most_common_plate_number = most_common_plate[0][0]

        if confirmed_plate == most_common_plate_number:
            confirmed_plate_count += 1
        else:
            confirmed_plate = most_common_plate_number
            confirmed_plate_count = 1

        if (
            confirmed_plate_count >= consecutive_detection_threshold
            and confirmed_plate not in inserted_plates
            and not is_plate_exists(confirmed_plate)
        ):
            conn = sqlite3.connect('license_plates.db')
            cursor = conn.cursor()
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('INSERT INTO entry_plates (plate_number, timestamp) VALUES (?, ?)', (confirmed_plate, timestamp))
            conn.commit()
            conn.close()

            inserted_plates.add(confirmed_plate)

            status_window = np.zeros((480, 600, 3), dtype=np.uint8)

            status_img = Image.fromarray(status_window)
            draw = ImageDraw.Draw(status_img)
            draw.text((10, 50), f"Registered: {confirmed_plate}", font=custom_font, fill=font_color)
            draw.text((10, 100), "Тавтай морилно уу", font=custom_font, fill=(0, 255, 0))
            status_window = np.array(status_img)

    elapsed_time = time.time() - start_time

    if elapsed_time > 0.5:
        #cv2.rectangle(img, (0, 200), (640, 300), (0, 255, 0), cv2.FILLED)
        #cv2.putText(img, "Burtgegdlee", (150, 265), cv2.FONT_HERSHEY_COMPLEX_SMALL, 2, (0, 0, 255), 2)

        count += 1
        start_time = time.time()

    combined_window = np.hstack((img, status_window))
    cv2.imshow("Combined Result", combined_window)

    for file_name in os.listdir(plates_folder):
        file_path = os.path.join(plates_folder, file_name)
        creation_time = os.path.getctime(file_path)
        current_time = time.time()
        age = current_time - creation_time

        if age > 3:
            os.remove(file_path)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()