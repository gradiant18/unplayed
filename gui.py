import sys
from datetime import datetime
import time
from game import Game
import threading
import yaml

from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QGridLayout,
    QWidget,
    QComboBox,
    QProgressBar,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My App")

        # game buttons
        self.start_button = QPushButton("Start")
        self.start_button.setStyleSheet("background-color: green")
        self.start_button.clicked.connect(self.start)

        self.skip_button = QPushButton("Skip Track")
        self.skip_button.setStyleSheet("background-color: yellow")
        self.skip_button.clicked.connect(self.skip)

        self.reload_button = QPushButton("Reload Track")
        self.reload_button.setStyleSheet("background-color: orange")
        self.reload_button.clicked.connect(self.reload)

        self.stop_button = QPushButton("Stop")
        self.stop_button.setStyleSheet("background-color: gray")
        self.stop_button.clicked.connect(self.stop)
        self.stop_button.setEnabled(False)

        buttons = QGridLayout()
        buttons.addWidget(self.start_button, 0, 0)
        buttons.addWidget(self.skip_button, 1, 0)
        buttons.addWidget(self.reload_button, 1, 1)
        buttons.addWidget(self.stop_button, 0, 1)

        self.track_progress = QProgressBar()
        self.track_progress.setValue(0)
        self.time_progress = QProgressBar()
        self.time_progress.setValue(0)

        # self.button = QPushButton("update medal picture")
        # self.button.clicked.connect(self.on_click)
        self.medal = QLabel()
        pixmap = QPixmap("")
        self.medal.setPixmap(pixmap)

        self.status = QLabel()

        with open("config.yaml") as file:
            self.config = yaml.safe_load(file)

        self.mode_input = "author"
        self.combo = QComboBox()
        self.combo.addItems(["author", "gold", "silver", "bronze", "finished"])
        self.combo.currentTextChanged.connect(self.on_input)

        layout = QVBoxLayout()
        layout.addWidget(self.combo)
        layout.addLayout(buttons)
        layout.addWidget(self.track_progress)
        layout.addWidget(self.time_progress)
        layout.addWidget(self.status)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def start(self):
        # ui
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.stop_button.setStyleSheet("background-color: red")
        self.start_button.setStyleSheet("background-color: gray")

        # Game
        self.session = Game(self.config)
        threading.Thread(target=self.update_status, daemon=True).start()
        threading.Thread(target=self.update_progress, daemon=True).start()
        self.session.start()

    def skip(self):
        self.session.skip()

    def reload(self):
        self.session.reload()

    def stop(self):
        self.session.stop()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.start_button.setStyleSheet("background-color: green")
        self.stop_button.setStyleSheet("background-color: gray")

    def update_progress(self):
        while not self.session.stopped:
            if self.session.track_limit:
                self.track_progress.setMaximum(self.session.track_limit)
                self.track_progress.setValue(len(self.session.finished))
            if self.session.time_limit:
                start_time = self.session.start_time
                stop_time = self.session.stop_time
                if not stop_time:
                    continue
                max = stop_time.timestamp() - start_time.timestamp()
                self.time_progress.setMaximum(int(max))

                progress = time.time() - stop_time.timestamp()
                self.time_progress.setValue(int(progress))

    def update_status(self):
        self.status.setText("Starting up...")
        while not self.session.stopped:
            if not self.session.get_current():
                continue

            tracks_played = f"Tracks Played: {len(self.session.finished)} | "

            tracks_left = ""
            if self.session.track_limit:
                tracks_left = f"Tracks Left: {self.session.get_tracks_left()} | "

            time_left = ""
            if self.session.stop_time:
                time_left = f"Time Left: {self.session.get_time_left()} | "

            current_medal = ""
            if self.session.mode != "finished" or "bronze":
                medal = "None"
                if self.session.current.medal:
                    medal = self.session.current.medal.capitalize()
                current_medal = f"Current Medal: {medal} | "

            current_track = f"Current Track: {self.session.current.name}"
            status = (
                f"{tracks_played}{tracks_left}{time_left}{current_medal}{current_track}"
            )
            self.status.setText(status)
            time.sleep(0.1)
        self.status.setText("All done")

    def on_input(self, changed):
        self.config["next_mode"] = changed

    def on_click(self):
        if self.mode_input != "None":
            self.medal.setPixmap(QPixmap(f"medals/{self.mode_input}"))
        else:
            self.medal.setPixmap(QPixmap())


app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec()
