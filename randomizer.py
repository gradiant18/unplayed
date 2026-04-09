import os
import pickle
import platform
import sys
from default_data import default_data
from gui import MainWindow
from PyQt6.QtWidgets import QApplication

if platform.system() == "Windows":
    app_dir = os.path.join(str(os.getenv("APPDATA")), "unplayed")
    if not os.path.exists(app_dir):
        os.mkdir(app_dir)
elif platform.system() == "Linux":
    app_dir = os.path.expanduser("~/.unplayed")
    if not os.path.exists(app_dir):
        os.mkdir(app_dir)
else:
    app_dir = ""

# empty log.txt
with open(os.path.join(app_dir, "log.log"), "w") as file:
    file.write("")

data_path = os.path.join(app_dir, "data.bin")
if os.path.exists(data_path):
    with open(data_path, "rb") as file:
        data = pickle.load(file)
else:
    print("Loading default data")
    data = default_data

data["app_dir"] = app_dir
data["debug"] = len(sys.argv) == 2

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow(data)
    window.show()
    app.exec()
