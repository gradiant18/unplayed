from datetime import datetime, timedelta
import sys
import time
from game import Game
import threading
import pickle
from PyQt6.QtCore import QDateTime, QTime
from PyQt6.QtWidgets import (
    QApplication,
    QDateTimeEdit,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QProgressBar,
    QTabWidget,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Randomizer")

        with open("config.bin", "rb") as file:
            self.config = pickle.load(file)

        # Tab 1

        # next_mode
        self.combo = QComboBox()
        self.combo.addItems(["author", "gold", "silver", "bronze", "finished"])
        self.combo.setCurrentText(self.config["game_rules"]["next_mode"])
        self.combo.currentTextChanged.connect(
            lambda val: self.on_input("next_mode", val)
        )

        # track_limit
        self.track_spin = QSpinBox()
        self.track_spin.setMinimum(0)
        self.track_spin.setMaximum(1000)
        self.track_spin.setValue(self.config["game_rules"]["track_limit"])
        self.track_spin.valueChanged.connect(
            lambda val: self.on_input("track_limit", val)
        )

        # time_limit
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm:ss")
        limit = int(self.config["game_rules"]["time_limit"].total_seconds())
        self.time_edit.setTime(QTime(0, 0, 0).addSecs(limit))
        self.time_edit.timeChanged.connect(lambda val: self.on_input("time_limit", val))

        # site
        self.site = QComboBox()
        self.site.addItems(["TMUF-X", "TMNF-X", "TMO-X", "TMN-X", "TMS-X"])
        self.site.setCurrentText(self.config["game_rules"]["site"])
        self.site.currentTextChanged.connect(lambda val: self.on_input("site", val))

        # uploadedafter
        self.after = QDateTimeEdit()
        self.after.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        seconds = int(self.config["track_rules"]["uploadedafter"].timestamp())
        self.after.setDateTime(QDateTime().fromSecsSinceEpoch(seconds))
        self.after.dateTimeChanged.connect(
            lambda val: self.on_input("uploadedafter", val)
        )

        # uploadedbefore
        self.before = QDateTimeEdit()
        self.before.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        seconds = int(self.config["track_rules"]["uploadedbefore"].timestamp())
        self.before.setDateTime(QDateTime().fromSecsSinceEpoch(seconds))
        self.before.dateTimeChanged.connect(
            lambda val: self.on_input("uploadedbefore", val)
        )

        dates = QHBoxLayout()
        dates.addWidget(self.after)
        dates.addWidget(self.before)

        self.start_button = QPushButton("Start")
        self.start_button.setStyleSheet("background-color: green")
        self.start_button.clicked.connect(self.start)

        self.save_button = QPushButton("Save Config")
        self.save_button.clicked.connect(self.save_config)

        main = QHBoxLayout()
        main.addWidget(self.combo)
        main.addWidget(self.track_spin)
        main.addWidget(self.time_edit)

        tab = QVBoxLayout()
        tab.addLayout(main)
        tab.addWidget(self.site)
        tab.addLayout(dates)
        tab.addWidget(self.start_button)
        tab.addWidget(self.save_button)
        tab1 = QWidget()
        tab1.setLayout(tab)

        # Tab 2
        self.tracks = QLabel()
        self.track_progress = QProgressBar()
        self.track_progress.setValue(0)
        thing1 = QHBoxLayout()
        thing1.addWidget(self.tracks)
        thing1.addWidget(self.track_progress)

        self.times = QLabel()
        self.time_progress = QProgressBar()
        self.time_progress.setValue(0)
        thing2 = QHBoxLayout()
        thing2.addWidget(self.times)
        thing2.addWidget(self.time_progress)

        bars = QVBoxLayout()
        bars.addLayout(thing1)
        bars.addLayout(thing2)

        self.reload_button = QPushButton("Reload Track")
        self.reload_button.setStyleSheet("background-color: yellow")
        self.reload_button.clicked.connect(self.reload)

        self.skip_button = QPushButton("Skip Track")
        self.skip_button.setStyleSheet("background-color: orange")
        self.skip_button.clicked.connect(self.skip)

        self.stop_button = QPushButton("Stop")
        self.stop_button.setStyleSheet("background-color: grey")
        self.stop_button.clicked.connect(self.stop)
        self.stop_button.setEnabled(False)

        buttons = QHBoxLayout()
        buttons.addWidget(self.reload_button)
        buttons.addWidget(self.skip_button)
        buttons.addWidget(self.stop_button)

        tab = QVBoxLayout()
        tab.addLayout(bars)
        tab.addLayout(buttons)
        tab2 = QWidget()
        tab2.setLayout(tab)

        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(tab1, "Tab 1")
        self.tab_widget.addTab(tab2, "Tab 2")
        self.tab_widget.setTabEnabled(1, False)

        self.setCentralWidget(self.tab_widget)

        self.test = None

    def stinky(self):
        print(self.config)

    def start(self):
        self.stop_button.setStyleSheet("background-color: red")
        self.start_button.setStyleSheet("background-color: grey")
        self.stop_button.setEnabled(True)
        self.start_button.setEnabled(False)

        self.session = Game(self.config)
        threading.Thread(target=self.update_progress, daemon=True).start()
        self.session.start()

        self.tab_widget.setCurrentIndex(1)
        self.tab_widget.setTabEnabled(0, False)
        self.tab_widget.setTabEnabled(1, True)

    def skip(self):
        self.session.skip()

    def reload(self):
        self.session.reload()

    def stop(self):
        self.session.stop()
        self.save_config()

        self.stop_button.setStyleSheet("background-color: grey")
        self.start_button.setStyleSheet("background-color: green")
        self.stop_button.setEnabled(False)
        self.start_button.setEnabled(True)
        self.tab_widget.setCurrentIndex(0)
        self.tab_widget.setTabEnabled(0, True)
        self.tab_widget.setTabEnabled(1, False)

    def update_progress(self):
        while not self.session.stopped:
            if self.session.track_limit:
                self.track_progress.setEnabled(True)
                self.track_progress.setMaximum(self.session.track_limit)
                self.track_progress.setValue(len(self.session.finished))

                progress = f"{len(self.session.finished)}/{self.session.track_limit}"
                self.tracks.setText(f"{progress:^10}")

            if self.session.time_limit:
                start_time = self.session.start_time
                stop_time = self.session.stop_time
                if not stop_time:
                    continue
                max = stop_time.timestamp() - start_time.timestamp()
                self.time_progress.setMaximum(int(max))

                progress = int(max) - (stop_time.timestamp() - time.time())
                self.time_progress.setValue(int(progress))
                self.times.setText(f"{self.session.get_time_left():^10}")
            else:
                self.times.setText("          ")

            time.sleep(0.1)

        self.stop()

    def on_input(self, key, value):
        if key in ["time_limit", "track_limit", "next_mode", "site"]:
            if key == "time_limit":
                print(value, type(value))
                print(value.toPyTime())
                self.config["game_rules"][key] = timedelta(
                    hours=value.hour(), minutes=value.minute(), seconds=value.second()
                )
                print(f"Widget {key} changed. new value: {value}")
            else:
                self.config["game_rules"][key] = value
                print(f"Widget {key} changed. new value: {value}")
        else:
            print(value)
            if key == "uploadedafter" or key == "uploadedbefore":
                self.config["track_rules"][key] = datetime.fromtimestamp(
                    value.toSecsSinceEpoch()
                )
                print(f"Widget {key} changed. new value: {value.toSecsSinceEpoch()}")

    def save_config(self):
        with open("config.bin", "wb") as file:
            pickle.dump(self.config, file)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    app.exec()
