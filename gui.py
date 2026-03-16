from datetime import datetime, timedelta
import sys
import time
from game import Game
from exchange import sites
import pickle
from PyQt6.QtCore import QDateTime, QTime, QTimer
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
        self.mode_label = QLabel(text="Next Mode")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Author", "Gold", "Silver", "Bronze", "Finished"])
        self.mode_combo.setCurrentText(self.config["game_rules"]["next_mode"])
        self.mode_combo.currentTextChanged.connect(
            lambda val: self.game_rule_changed("next_mode", val.lower())
        )
        mode = QVBoxLayout()
        mode.addWidget(self.mode_label)
        mode.addWidget(self.mode_combo)

        # track_limit
        self.track_label = QLabel(text="Track Limit")
        self.track_spin = QSpinBox()
        self.track_spin.setMinimum(0)
        self.track_spin.setMaximum(1000)
        self.track_spin.setValue(self.config["game_rules"]["track_limit"])
        self.track_spin.valueChanged.connect(
            lambda val: self.game_rule_changed("track_limit", val)
        )
        track = QVBoxLayout()
        track.addWidget(self.track_label)
        track.addWidget(self.track_spin)

        # time_limit
        self.time_label = QLabel(text="Time Limit")
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm:ss")
        limit = int(self.config["game_rules"]["time_limit"].total_seconds())
        self.time_edit.setTime(QTime(0, 0, 0).addSecs(limit))
        self.time_edit.timeChanged.connect(
            lambda val: self.game_rule_changed("time_limit", val)
        )
        tme = QVBoxLayout()
        tme.addWidget(self.time_label)
        tme.addWidget(self.time_edit)

        # site
        self.site_label = QLabel(text="Site")
        self.site = QComboBox()
        self.site.addItems(["TMUF-X", "TMNF-X", "TMO-X", "TMN-X", "TMS-X"])
        self.site.setCurrentText(self.config["game_rules"]["site"])
        self.site.currentTextChanged.connect(
            lambda val: self.game_rule_changed("site", val)
        )
        site = QVBoxLayout()
        site.addWidget(self.site_label)
        site.addWidget(self.site)

        # tag
        self.tag_label = QLabel(text="Tag")
        self.tag = QComboBox()
        self.tag.addItem("Any")
        self.tag.addItems(sites[self.site.currentText()]["tags"])
        if self.config["track_rules"]["tag"] is None:
            self.tag.setCurrentText("Any")
        else:
            self.tag.setCurrentIndex(self.config["track_rules"]["tag"] + 1)
        self.tag.currentTextChanged.connect(
            lambda val: self.track_rule_changed("tag", val)
        )
        tag = QVBoxLayout()
        tag.addWidget(self.tag_label)
        tag.addWidget(self.tag)

        # uploadedafter
        self.after_label = QLabel(text="Uploaded After")
        self.after = QDateTimeEdit()
        self.after.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        seconds = int(self.config["track_rules"]["uploadedafter"].timestamp())
        self.after.setDateTime(QDateTime().fromSecsSinceEpoch(seconds))
        self.after.dateTimeChanged.connect(
            lambda val: self.track_rule_changed("uploadedafter", val)
        )
        after = QVBoxLayout()
        after.addWidget(self.after_label)
        after.addWidget(self.after)

        # uploadedbefore
        self.before_label = QLabel(text="Uploaded Before")
        self.before = QDateTimeEdit()
        self.before.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        seconds = int(self.config["track_rules"]["uploadedbefore"].timestamp())
        self.before.setDateTime(QDateTime().fromSecsSinceEpoch(seconds))
        self.before.dateTimeChanged.connect(
            lambda val: self.track_rule_changed("uploadedbefore", val)
        )
        before = QVBoxLayout()
        before.addWidget(self.before_label)
        before.addWidget(self.before)

        # authortimemin
        self.at_min_label = QLabel(text="Min AT")
        self.at_min = QTimeEdit()
        self.at_min.setDisplayFormat("HH:mm:ss")
        min = self.config["track_rules"]["authortimemin"]
        self.at_min.setTime(QTime(0, 0, 0).fromMSecsSinceStartOfDay(min))
        self.at_min.timeChanged.connect(
            lambda val: self.track_rule_changed("authortimemin", val)
        )
        at_min = QVBoxLayout()
        at_min.addWidget(self.at_min_label)
        at_min.addWidget(self.at_min)

        # authortimemax
        self.at_max_label = QLabel(text="Max AT")
        self.at_max = QTimeEdit()
        self.at_max.setDisplayFormat("HH:mm:ss")
        max = self.config["track_rules"]["authortimemax"]
        self.at_max.setTime(QTime(0, 0, 0).fromMSecsSinceStartOfDay(max))
        self.at_max.timeChanged.connect(
            lambda val: self.track_rule_changed("authortimemax", val)
        )
        at_max = QVBoxLayout()
        at_max.addWidget(self.at_max_label)
        at_max.addWidget(self.at_max)

        self.start_button = QPushButton("Start")
        self.start_button.setStyleSheet("background-color: green")
        self.start_button.clicked.connect(self.start)

        self.save_button = QPushButton("Save Config")
        self.save_button.clicked.connect(self.save_config)

        main = QHBoxLayout()
        main.addLayout(mode)
        main.addLayout(track)
        main.addLayout(tme)

        main2 = QHBoxLayout()
        main2.addLayout(site)
        main2.addLayout(after)
        main2.addLayout(before)

        main3 = QHBoxLayout()
        main3.addLayout(tag)
        main3.addLayout(at_min)
        main3.addLayout(at_max)

        tab = QVBoxLayout()
        tab.addLayout(main)
        tab.addLayout(main2)
        tab.addLayout(main3)
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
        self.tab_widget.addTab(tab1, "Config")
        self.tab_widget.addTab(tab2, "Game")
        self.tab_widget.setTabEnabled(1, False)

        self.setCentralWidget(self.tab_widget)
        self.setMinimumSize(self.minimumSizeHint())
        self.setMaximumSize(self.minimumSizeHint())

        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self.update_progress)

    def start(self):
        self.setWindowTitle("Randomizer")
        self.stop_button.setStyleSheet("background-color: red")
        self.start_button.setStyleSheet("background-color: grey")
        self.stop_button.setEnabled(True)
        self.start_button.setEnabled(False)

        self.config["debug"] = len(sys.argv) == 2
        self.config["track_rules"]["mood"] = None

        self.session = Game(self.config)
        self.progress_timer.start(100)
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

        if reason := self.session.stop_reason:
            self.setWindowTitle(f"Randomizer | {reason}")

        self.stop_button.setStyleSheet("background-color: grey")
        self.start_button.setStyleSheet("background-color: green")
        self.stop_button.setEnabled(False)
        self.start_button.setEnabled(True)
        self.tab_widget.setCurrentIndex(0)
        self.tab_widget.setTabEnabled(0, True)
        self.tab_widget.setTabEnabled(1, False)

    def update_progress(self):
        if self.session.stopped:
            self.progress_timer.stop()
            self.stop()
            return

        if self.session.track_limit:
            self.track_progress.setEnabled(True)
            self.track_progress.setMaximum(self.session.track_limit)
            self.track_progress.setValue(len(self.session.finished))

            progress = f"{len(self.session.finished)}/{self.session.track_limit}"
            self.tracks.setText(f"{progress:^10}")

        if self.session.time_limit:
            start_time = self.session.start_time
            stop_time = self.session.stop_time

            if stop_time:
                max = stop_time.timestamp() - start_time.timestamp()
                self.time_progress.setMaximum(int(max))

                progress = int(max) - (stop_time.timestamp() - time.time())
                self.time_progress.setValue(int(progress))
                self.times.setText(f"{self.session.get_time_left():^10}")
        else:
            self.times.setText("          ")

    def game_rule_changed(self, key, value):
        if key == "time_limit":
            self.config["game_rules"][key] = timedelta(
                hours=value.hour(), minutes=value.minute(), seconds=value.second()
            )
        elif key == "site" and False:
            old_val = self.config["game_rules"][key]
            if value in ["TMUF-X", "TMNF-X"] and old_val not in [
                "TMUF-X",
                "TMNF-X",
            ]:
                # different tags
                self.tag.setCurrentText("Any")
                self.tag.clear()
                self.tag.addItem("Any")
                self.tag.addActions(sites[key]["tags"])
                self.tag.setCurrentText("Any")
                self.track_rule_changed("tag", "Any")

        else:
            self.config["game_rules"][key] = value

    def track_rule_changed(self, key, value):
        track_rule = self.config["track_rules"][key]
        if key in ["authortimemin", "authortimemax"]:
            track_rule = value.msecsSinceStartOfDay()
        elif key in ["uploadedafter", "uploadedbefore"]:
            track_rule = datetime.fromtimestamp(value.toSecsSinceEpoch())
        elif key == "tag":
            if value == "Any":
                track_rule = None
            else:
                track_rule = sites[self.site.currentText()]["tags"].index(value)

        self.config["track_rules"][key] = track_rule
        print(f"{key} changed to {track_rule}")

    def save_config(self):
        with open("config.bin", "wb") as file:
            pickle.dump(self.config, file)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    app.exec()
