from default_data import default_data
from gui import MainWindow
from PyQt6.QtWidgets import QApplication
import sys
import os
import pickle

if os.path.exists("data.bin"):
    with open("data.bin", "rb") as file:
        data = pickle.load(file)
else:
    print("Loading default data")
    data = default_data

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow(data)
    window.show()
    app.exec()
