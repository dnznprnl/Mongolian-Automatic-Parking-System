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

font_size = 20
font_color = (0, 0, 255)

try:
    custom_font = ImageFont.truetype("arial.ttf", font_size)
except Exception as e:
    print("Arial font could not be loaded. Using default font.")
    custom_font = ImageFont.load_default()


harcascade = "model/haarcascade_russian_plate_number.xml"

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

while True:
    success, img = cap.read()

    plate_cascade = cv2.CascadeClassifier(harcascade)

    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    plates = plate_cascade.detectMultiScale(img_gray, 1.1, 4)

    current_frame_plates = []

    for (x, y, w, h) in plates:
        area = w * h

        if area > min_area:
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(img, "License Plate", (x, y - 5), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (255, 0, 255), 2)

            img_roi = img[y: y + h, x:x + w]

            cv2.imwrite(f"plates/roi_{count}.jpg", img_roi)

            saved_img = cv2.imread(f"plates/roi_{count}.jpg")
            saved_img_gray = cv2.cvtColor(saved_img, cv2.COLOR_BGR2GRAY)
            #cv2.imshow("saved_img_gray", saved_img_gray)
            saved_img_gray = cv2.resize(saved_img_gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            #cv2.imshow("saved_img_resize", saved_img_gray)
            saved_img_gray = cv2.GaussianBlur(saved_img_gray, (5, 5), 0)
            #cv2.imshow("saved_img_blured", saved_img_gray)
            ret, thresh = cv2.threshold(saved_img_gray, 0, 255, cv2.THRESH_OTSU | cv2.THRESH_BINARY_INV)

            license_plate_number = pytesseract.image_to_string(saved_img_gray, lang='mon', config='--oem 3 --psm 6')

            filtered_license_plate = re.sub(r'[^0-9АБВГДЕЗИКЛМНОӨПРСТУҮХЦЧЭЯ]', '', license_plate_number)

            # улсын дугаарын формат
            if re.match(r'^\d{4}[А-ЯҮӨ]{3}$', filtered_license_plate):
                current_frame_plates.append(filtered_license_plate)

                text_file_path = f"plates/plate_{count}.txt"
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

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
