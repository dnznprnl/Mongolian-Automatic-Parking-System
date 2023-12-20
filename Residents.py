import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QListWidget, QMenu, QAction, QMessageBox
import sqlite3

class ResidentsWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Residents List")
        self.setGeometry(100, 100, 400, 300)

        self.residents_label = QLabel("Residents:")
        self.residents_list = QListWidget()
        self.residents_list.addItems(self.get_residents_list())

        layout = QVBoxLayout()
        layout.addWidget(self.residents_label)
        layout.addWidget(self.residents_list)

        self.setLayout(layout)

        self.residents_list.setContextMenuPolicy(3)
        self.residents_list.customContextMenuRequested.connect(self.show_context_menu)

    def get_residents_list(self):
        connection = sqlite3.connect("license_plates.db")
        cursor = connection.cursor()

        residents_list = []
        try:
            cursor.execute("SELECT resident_lp FROM Residents")
            residents = cursor.fetchall()
            residents_list = [str(resident[0]) for resident in residents]
        except sqlite3.Error as e:
            print("Error fetching residents:", e)
        finally:
            connection.close()

        return residents_list

    def show_context_menu(self, pos):
        item = self.residents_list.itemAt(pos)
        if item:
            menu = QMenu(self)

            delete_action = QAction("Delete resident", self)
            delete_action.triggered.connect(lambda: self.delete_resident(item.text()))
            menu.addAction(delete_action)

            menu.exec_(self.residents_list.mapToGlobal(pos))

    def delete_resident(self, license_plate):
        reply = QMessageBox.question(self, 'Delete Resident', f'Do you want to delete resident {license_plate}?',
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            connection = sqlite3.connect("license_plates.db")
            cursor = connection.cursor()

            try:
                cursor.execute("DELETE FROM Residents WHERE resident_lp = ?", (license_plate,))
                connection.commit()

                self.residents_list.clear()
                self.residents_list.addItems(self.get_residents_list())

                QMessageBox.information(self, "Success", f"Resident {license_plate} deleted successfully.")
            except sqlite3.Error as e:
                print("Error deleting resident:", e)
            finally:
                connection.close()

def run_program():
    app = QApplication(sys.argv)
    residents_window = ResidentsWindow()
    residents_window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    run_program()
