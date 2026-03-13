import sys
import time
from game import Game
import threading
import yaml
from PyQt6.QtCore import QTime
from PyQt6.QtWidgets import (
    QApplication,
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

        with open("config.yaml") as file:
            self.config = yaml.safe_load(file)

        # Tab 1
        self.combo = QComboBox()
        self.combo.addItems(["author", "gold", "silver", "bronze", "finished"])
        self.combo.setCurrentText(self.config["next_mode"])
        self.combo.currentTextChanged.connect(
            lambda val: self.on_input("next_mode", val)
        )

        self.track_spin = QSpinBox()
        self.track_spin.setMinimum(0)
        self.track_spin.setMaximum(1000)
        self.track_spin.setValue(self.config["track_limit"])
        self.track_spin.valueChanged.connect(
            lambda val: self.on_input("track_limit", val)
        )

        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm:ss")

        self.times = self.config["time_limit"]
        if isinstance(self.times, int):
            hours, remainder = divmod(self.times, 3600)
            minutes, seconds = divmod(remainder, 60)
            qtime = QTime(hours, minutes, seconds)
        else:
            qtime = QTime(
                int(self.times[:2]), int(self.times[3:5]), int(self.times[6:])
            )
        print(self.times, qtime)
        self.time_edit.setTime(qtime)
        self.time_edit.timeChanged.connect(lambda val: self.on_input("time_limit", val))

        self.start_button = QPushButton("Start")
        self.start_button.setStyleSheet("background-color: green")
        self.start_button.clicked.connect(self.start)

        self.print_button = QPushButton("Print Config")
        self.print_button.clicked.connect(self.stinky)

        main = QHBoxLayout()
        main.addWidget(self.combo)
        main.addWidget(self.track_spin)
        main.addWidget(self.time_edit)

        tab = QVBoxLayout()
        tab.addLayout(main)
        tab.addWidget(self.print_button)
        tab.addWidget(self.start_button)
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
                self.track_progress.setMaximum(self.session.track_limit)
                self.track_progress.setValue(len(self.session.finished))

                yes = f"{len(self.session.finished)}/{self.session.track_limit}"
                self.tracks.setText(f"{yes:^10}")

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

            time.sleep(0.1)

        self.stop_button.setStyleSheet("background-color: grey")
        self.start_button.setStyleSheet("background-color: green")
        self.stop_button.setEnabled(False)
        self.start_button.setEnabled(True)
        self.tab_widget.setCurrentIndex(0)
        self.tab_widget.setTabEnabled(0, True)
        self.tab_widget.setTabEnabled(1, False)

    def on_input(self, key, value):
        if key == "time_limit":
            self.config[key] = value.toString("HH:mm:ss")
            print(f"Widget {key} changed. new value: {value.toString('HH:mm:ss')}")
        else:
            self.config[key] = value
            print(f"Widget {key} changed. new value: {value}")


app = QApplication(sys.argv)
window = MainWindow()
window.show()

app.exec()
