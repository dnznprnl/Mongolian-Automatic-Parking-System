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
error_font_color = (0, 0, 255)

try:
    custom_font = ImageFont.truetype("arial.ttf", font_size)
except Exception as e:
    print("Arial font could not be loaded. Using default font.")
    custom_font = ImageFont.load_default()

harcascade = "model/haarcascade_russian_plate_number.xml"

conn = sqlite3.connect('license_plates.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS Customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plate_number TEXT NOT NULL,
        payment INTEGER NOT NULL,
        date DATETIME NOT NULL
    )
''')
conn.commit()

cap = cv2.VideoCapture(0)

cap.set(3, 640)  # width
cap.set(4, 480)  # height

min_area = 500

count = 0
start_time = time.time()

detected_plates = []

consecutive_detection_threshold = 10

confirmed_plate = None
confirmed_plate_count = 0

inserted_plates = set()

def is_plate_exists(plate_number):
    cursor.execute('SELECT * FROM entry_plates WHERE plate_number = ?', (plate_number,))
    result = cursor.fetchone()
    return result is not None

def calculate_payment(entry_timestamp):
    free_duration = 30 * 60  # 30 minutes in seconds
    time_in_parking = time.time() - entry_timestamp
    payment = max(0, ((time_in_parking - free_duration) // (30 * 60)) * 1000)
    return payment

def display_time_parked(entry_timestamp):
    time_parked_seconds = int(time.time() - entry_timestamp)
    hours, remainder = divmod(time_parked_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours} hours {minutes} minutes"

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
            saved_img_gray = cv2.resize(saved_img_gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            saved_img_gray = cv2.GaussianBlur(saved_img_gray, (5, 5), 0)
            ret, thresh = cv2.threshold(saved_img_gray, 0, 255, cv2.THRESH_OTSU | cv2.THRESH_BINARY_INV)

            license_plate_number = pytesseract.image_to_string(saved_img_gray, lang='mon', config='--oem 3 --psm 6')

            filtered_license_plate = re.sub(r'[^0-9АБВГДЕЗИКЛМНОӨПРСТУҮХЦЧЭЯ]', '', license_plate_number)

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
            and is_plate_exists(confirmed_plate)
        ):
            cursor.execute('SELECT * FROM entry_plates WHERE plate_number = ?', (confirmed_plate,))
            entry_result = cursor.fetchone()

            if entry_result:
                entry_timestamp = datetime.strptime(entry_result[2], '%Y-%m-%d %H:%M:%S').timestamp()
                payment = calculate_payment(entry_timestamp)

                status_img = Image.fromarray(np.zeros((480, 600, 3), dtype=np.uint8))
                draw = ImageDraw.Draw(status_img)
                draw.text((10, 50), f"Улсын дугаар : {confirmed_plate}", font=custom_font, fill=font_color)
                draw.text((10, 100), f"Төлбөр: ${payment}", font=custom_font, fill=(0, 255, 0))

                draw.text((10, 150), f"Хугацаа: {display_time_parked(entry_timestamp)}", font=custom_font, fill=(255, 255, 255))

                status_window = np.array(status_img)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('T') or key == ord('t'):
                    cv2.rectangle(img, (0, 200), (640, 300), (0, 0, 0), cv2.FILLED)
                    print("Amjilttai tulugdluu")
                    status_window = np.zeros((480, 600, 3), dtype=np.uint8)
                    cursor.execute('INSERT INTO Customers (plate_number, payment, date) VALUES (?, ?, ?)',
                                    (confirmed_plate, payment, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    cursor.execute('DELETE FROM entry_plates WHERE plate_number = ?', (confirmed_plate,))
                    conn.commit()

            else:
                status_img = Image.fromarray(np.zeros((480, 600, 3), dtype=np.uint8))
                draw = ImageDraw.Draw(status_img)
                draw.text((10, 50), "Та дахин уншуулна уу?", font=custom_font, fill=error_font_color)
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
