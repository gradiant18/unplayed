import os
import platform
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QFileDialog,
)


class FindExe(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select the executable you want to use")
        self.main_layout = QVBoxLayout()
        self.executable_path = None

        self.find_executables()
        self.display_paths()
        self.setLayout(self.main_layout)

    def find_executables(self):
        system = platform.system()
        self.executable_paths = []
        steam = os.path.join("Steam", "steamapps", "common")
        tmuf = "TrackMania United"
        tmnf = "TrackMania Nations Forever"

        if system == "Windows":
            steam_paths = [
                os.path.join(str(os.getenv("ProgramFiles")), steam, tmuf),
                os.path.join(str(os.getenv("ProgramFiles")), steam, tmnf),
                os.path.join(str(os.getenv("ProgramFiles(x86)")), steam, tmuf),
                os.path.join(str(os.getenv("ProgramFiles(x86)")), steam, tmnf),
            ]
        elif system == "Linux":
            steam_paths = [
                os.path.expanduser(f"~/.local/share/Steam/steamapps/common/{tmuf}"),
                os.path.expanduser(f"~/.local/share/Steam/steamapps/common/{tmnf}"),
            ]
        else:
            return

        for path in steam_paths:
            executable_path = os.path.join(path, "TmForever.exe")
            if os.path.exists(executable_path):
                self.executable_paths.append(executable_path)

    def display_paths(self):
        for path in self.executable_paths:
            row = QHBoxLayout()
            label = QLabel(path)
            button = QPushButton("Select")
            button.clicked.connect(lambda _, p=path: self.return_path(p))
            row.addWidget(label)
            row.addWidget(button)
            self.main_layout.addLayout(row)

        other_button = QPushButton("Other Path")
        other_button.clicked.connect(self.open_file_dialog)
        self.main_layout.addWidget(other_button)

    def return_path(self, path):
        self.executable_path = path
        self.accept()

    def open_file_dialog(self):
        filepath = QFileDialog.getOpenFileName(self, "Select TmForever.exe")[0]
        if filepath:
            self.return_path(filepath)


class FindTracks(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select the Tracks directory")
        self.main_layout = QVBoxLayout()
        self.track_folder_path = None

        self.find_track_folders()
        self.display_paths()
        self.setLayout(self.main_layout)

    def find_track_folders(self):
        self.track_folder_paths = []

        if platform.system() == "Windows":
            dir_paths = [
                os.path.join(str(os.getenv("HOMEPATH")), "Documents", "TrackMania", "Tracks"),
                os.path.join(str(os.getenv("HOMEPATH")), "OneDrive", "Documents", "TrackMania", "Tracks")
            ]
        elif platform.system() == "Linux":
            dir_paths = [
                os.path.expanduser(
                    "~/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks"
                ),
                os.path.expanduser(
                    "~/.local/share/Steam/steamapps/compatdata/11020/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks"
                ),
            ]
        else:
            return

        for path in dir_paths:
            if os.path.exists(path):
                self.track_folder_paths.append(path)

    def display_paths(self):
        for path in self.track_folder_paths:
            row = QHBoxLayout()
            label = QLabel(path)
            button = QPushButton("Select")
            button.clicked.connect(lambda _, p=path: self.return_path(p))
            row.addWidget(label)
            row.addWidget(button)
            self.main_layout.addLayout(row)

        other_button = QPushButton("Other Path")
        other_button.clicked.connect(self.open_file_dialog)
        self.main_layout.addWidget(other_button)

    def return_path(self, path):
        self.track_folder_path = path
        self.accept()

    def open_file_dialog(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Tracks Folder")
        if folder_path:
            self.return_path(folder_path)
