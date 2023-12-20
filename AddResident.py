import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QVBoxLayout, QPushButton, QMessageBox
import sqlite3
import re
import random

class LicensePlateDialog(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Enter License Plate")
        self.setGeometry(100, 100, 720, 480)

        self.license_plate_label = QLabel("Enter the license plate:")
        self.license_plate_entry = QLineEdit()
        self.submit_button = QPushButton("Submit")
        self.cancel_button = QPushButton("Cancel")

        layout = QVBoxLayout()
        layout.addWidget(self.license_plate_label)
        layout.addWidget(self.license_plate_entry)
        layout.addWidget(self.submit_button)
        layout.addWidget(self.cancel_button)

        self.setLayout(layout)

        self.should_close_main = False

        self.submit_button.clicked.connect(self.submit)
        self.cancel_button.clicked.connect(self.cancel)

    def submit(self):
        license_plate = self.license_plate_entry.text()

        # Check if the license plate is already in the table
        if self.is_license_plate_exist(license_plate):
            QMessageBox.critical(self, "Error", "Хэрэглэгч бүртгэлтэй байна")
            return

        # Continue with the rest of the logic if the license plate is not in the table
        if self.is_valid_license_plate(license_plate):
            self.add_resident(license_plate)
        else:
            QMessageBox.critical(self, "Error", "Улсын дугаарыг зөв оруулна уу")

        self.should_close_main = False

    def cancel(self):
        self.should_close_main = False
        self.close()

    def is_valid_license_plate(self, license_plate):
        return (
            len(license_plate) == 7
            and license_plate[:4].isdigit()
            and re.match("[А-ЯӨҮа-яөү]{3}", license_plate[4:])
        )

    def is_license_plate_exist(self, license_plate):
        connection = sqlite3.connect("license_plates.db")
        cursor = connection.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM Residents WHERE resident_lp = ?", (license_plate,))
            count = cursor.fetchone()[0]
            return count > 0
        except sqlite3.Error as e:
            print("Error checking if license plate exists:", e)
        finally:
            connection.close()

        return False

    def add_resident(self, license_plate):
        if not self.is_valid_license_plate(license_plate):
            QMessageBox.critical(self, "Error", "Улсын дугаарыг зөв оруулна уу")
            return

        connection = sqlite3.connect("license_plates.db")
        cursor = connection.cursor()

        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Residents (
                    resident_id INTEGER PRIMARY KEY,
                    resident_lp TEXT
                )
            ''')

            resident_id = random.randint(1, 1000)

            cursor.execute("INSERT INTO Residents (resident_id, resident_lp) VALUES (?, ?)", (resident_id, license_plate))
            connection.commit()

            print("Амжилттай бүртгэгдлээ")
            print(f"Assigned resident_id: {resident_id}")
            QMessageBox.information(self, "Success", "Амжилттай бүртгэгдлээ")
        except sqlite3.Error as e:
            print("Error adding resident:", e)
            QMessageBox.critical(self, "Error", f"Error adding resident: {e}")
        finally:
            connection.close()

def run_program():
    app = QApplication(sys.argv)
    dialog = LicensePlateDialog()
    dialog.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    run_program()
