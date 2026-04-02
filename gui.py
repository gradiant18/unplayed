import copy
import pickle
import os
import sys
import time
from banned_tracks import BannedTracksTab
from datetime import datetime, timedelta
from exchange import values
from game import Game
from helper import log
from settings import SettingsTab
from PyQt6.QtCore import QDateTime, QTime, QTimer
from PyQt6.QtWidgets import (
    QCheckBox,
    QDateTimeEdit,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QProgressBar,
    QTabWidget,
)


class MainWindow(QMainWindow):
    def __init__(self, data) -> None:
        super().__init__()
        self.setWindowTitle("Randomizer")
        self.data = data
        self.site_tabs = {}

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.make_config_widget()
        self.make_game_widget()

        if self.data["force_window_size"]:
            self.setMinimumSize(self.minimumSizeHint())
            self.setMaximumSize(self.minimumSizeHint())

        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self.update_progress)

    def make_config_widget(self):
        config_widget = QWidget()
        layout = QVBoxLayout(config_widget)

        options_tab = self.make_options_tab()
        banned_tracks_tab = BannedTracksTab(self.data)
        settings_tab = SettingsTab(self.data)

        self.tabs = QTabWidget()
        self.tabs.addTab(options_tab, "Options")
        self.tabs.addTab(banned_tracks_tab, "Banned Tracks")
        self.tabs.addTab(settings_tab, "Settings")
        layout.addWidget(self.tabs)
        self.stacked_widget.addWidget(config_widget)

    def make_game_widget(self):
        game_widget = QWidget()
        layout = QVBoxLayout(game_widget)
        game_tab = self.make_game_tab()
        layout.addWidget(game_tab)
        self.stacked_widget.addWidget(game_widget)

    def make_options_tab(self) -> QWidget:
        # next_mode
        self.mode_label = QLabel(text="Next Mode")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(values["all"]["mode"])
        self.mode_combo.setCurrentText(
            self.data["game_rules"]["next_mode"].capitalize()
        )
        self.mode_combo.currentTextChanged.connect(
            lambda val: self.game_rule_changed("next_mode", val.lower())
        )
        mode = QVBoxLayout()
        mode.addWidget(self.mode_label)
        mode.addWidget(self.mode_combo)

        # track_limit
        self.track_limit = QSpinBox()
        self.track_limit.setMinimum(0)
        self.track_limit.setMaximum(1000)
        self.track_limit.setValue(self.data["game_rules"]["track_limit"]["value"])
        self.track_limit.valueChanged.connect(
            lambda val: self.game_rule_changed("track_limit", val)
        )
        self.track_box = self.make_checkbox("Track Limit", "track_limit")
        track = QVBoxLayout()
        track.addWidget(self.track_box)
        track.addWidget(self.track_limit)

        # time_limit
        self.time_limit = QTimeEdit()
        self.time_limit.setDisplayFormat("HH:mm:ss")
        limit = int(self.data["game_rules"]["time_limit"]["value"].total_seconds())
        self.time_limit.setTime(QTime(0, 0, 0).addSecs(limit))
        self.time_limit.timeChanged.connect(
            lambda val: self.game_rule_changed("time_limit", val)
        )
        self.time_box = self.make_checkbox("Time Limit", "time_limit")
        tme = QVBoxLayout()
        tme.addWidget(self.time_box)
        tme.addWidget(self.time_limit)

        # site
        self.site_label = QLabel(text="Site")
        self.site = QComboBox()
        self.site.addItems(values["all"]["site"])
        self.site.setCurrentText(self.data["game_rules"]["site"])
        self.site.currentTextChanged.connect(
            lambda val: self.game_rule_changed("site", val)
        )
        site = QVBoxLayout()
        site.addWidget(self.site_label)
        site.addWidget(self.site)

        # uploadedafter
        self.uploadedafter = QDateTimeEdit()
        self.uploadedafter.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        seconds = int(self.data["track_rules"]["uploadedafter"]["value"].timestamp())
        self.uploadedafter.setDateTime(QDateTime().fromSecsSinceEpoch(seconds))
        self.uploadedafter.dateTimeChanged.connect(
            lambda val: self.track_rule_changed("uploadedafter", val)
        )
        self.after_box = self.make_checkbox("Uploaded After", "uploadedafter")
        after = QVBoxLayout()
        after.addWidget(self.after_box)
        after.addWidget(self.uploadedafter)

        # uploadedbefore
        self.uploadedbefore = QDateTimeEdit()
        self.uploadedbefore.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        seconds = int(self.data["track_rules"]["uploadedbefore"]["value"].timestamp())
        self.uploadedbefore.setDateTime(QDateTime().fromSecsSinceEpoch(seconds))
        self.uploadedbefore.dateTimeChanged.connect(
            lambda val: self.track_rule_changed("uploadedbefore", val)
        )
        self.before_box = self.make_checkbox("Uploaded Before", "uploadedbefore")
        before = QVBoxLayout()
        before.addWidget(self.before_box)
        before.addWidget(self.uploadedbefore)

        # authortimemin
        self.authortimemin = QTimeEdit()
        self.authortimemin.setDisplayFormat("HH:mm:ss")
        min = self.data["track_rules"]["authortimemin"]["value"]
        self.authortimemin.setTime(QTime(0, 0, 0).fromMSecsSinceStartOfDay(min))
        self.authortimemin.timeChanged.connect(
            lambda val: self.track_rule_changed("authortimemin", val)
        )
        self.authortimemin_check = self.make_checkbox("Min AT", "authortimemin")
        at_min = QVBoxLayout()
        at_min.addWidget(self.authortimemin_check)
        at_min.addWidget(self.authortimemin)

        # authortimemax
        self.authortimemax = QTimeEdit()
        self.authortimemax.setDisplayFormat("HH:mm:ss")
        max = self.data["track_rules"]["authortimemax"]["value"]
        self.authortimemax.setTime(QTime(0, 0, 0).fromMSecsSinceStartOfDay(max))
        self.authortimemax.timeChanged.connect(
            lambda val: self.track_rule_changed("authortimemax", val)
        )
        self.authortimemax_check = self.make_checkbox("Max AT", "authortimemax")
        at_max = QVBoxLayout()
        at_max.addWidget(self.authortimemax_check)
        at_max.addWidget(self.authortimemax)

        # tag
        self.tag = self.make_combobox("tag", self.site.currentText())
        self.tag_check = self.make_checkbox("Tag", "tag")
        tag = QVBoxLayout()
        tag.addWidget(self.tag_check)
        tag.addWidget(self.tag)

        # primarytype
        self.primarytype = self.make_combobox("primarytype")
        self.primarytype_check = self.make_checkbox("Style", "primarytype")
        primarytype = QVBoxLayout()
        primarytype.addWidget(self.primarytype_check)
        primarytype.addWidget(self.primarytype)

        # environment
        self.environment = self.make_combobox("environment", self.site.currentText())
        self.environment_check = self.make_checkbox("Environment", "environment")
        environment = QVBoxLayout()
        environment.addWidget(self.environment_check)
        environment.addWidget(self.environment)

        # mood
        self.mood = self.make_combobox("mood")
        self.mood_check = self.make_checkbox("Mood", "mood")
        mood = QVBoxLayout()
        mood.addWidget(self.mood_check)
        mood.addWidget(self.mood)

        # difficulty
        self.difficulty = self.make_combobox("difficulty")
        self.difficulty_check = self.make_checkbox("Difficulty", "difficulty")
        difficulty = QVBoxLayout()
        difficulty.addWidget(self.difficulty_check)
        difficulty.addWidget(self.difficulty)

        # inhasrecord
        self.inhasrecord = self.make_combobox("inhasrecord")
        self.inhasrecord_check = self.make_checkbox("Records", "inhasrecord")
        inhasrecord = QVBoxLayout()
        inhasrecord.addWidget(self.inhasrecord_check)
        inhasrecord.addWidget(self.inhasrecord)

        # inunlimiter
        self.unlimiterver = self.make_combobox("unlimiterver")
        self.inunlimeter_check = self.make_checkbox("Unlimiter", "unlimiterver")
        if self.inunlimeter_check.checkState().value == 2:
            self.data["track_rules"]["inunlimiter"]["state"] = 2
            self.data["track_rules"]["inunlimiter"]["value"] = 1
        else:
            self.data["track_rules"]["inunlimiter"]["state"] = 0
            self.data["track_rules"]["inunlimiter"]["value"] = 0
        if self.data["track_rules"]["unlimiterver"]["text"] == "Any":
            self.data["track_rules"]["unlimiterver"]["state"] = 0
        else:
            self.data["track_rules"]["unlimiterver"]["state"] = 2

        unlimiter = QVBoxLayout()
        unlimiter.addWidget(self.inunlimeter_check)
        unlimiter.addWidget(self.unlimiterver)

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

        main4 = QHBoxLayout()
        main4.addLayout(primarytype)
        main4.addLayout(environment)
        main4.addLayout(mood)

        main5 = QHBoxLayout()
        main5.addLayout(difficulty)
        main5.addLayout(inhasrecord)
        main5.addLayout(unlimiter)

        layout = QVBoxLayout()
        layout.addLayout(main)
        layout.addLayout(main2)
        layout.addLayout(main3)
        layout.addLayout(main4)
        layout.addLayout(main5)
        layout.addWidget(self.start_button)
        layout.addWidget(self.save_button)
        tab = QWidget()
        tab.setLayout(layout)
        return tab

    def make_game_tab(self) -> QWidget:
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

        layout = QVBoxLayout()
        layout.addLayout(bars)
        layout.addLayout(buttons)
        tab = QWidget()
        tab.setLayout(layout)
        return tab

    def make_checkbox(self, text, label) -> QCheckBox:
        checkbox = QCheckBox(text)
        if self.data["track_rules"].get(label):
            state = self.data["track_rules"][label]["state"]
        else:
            state = self.data["game_rules"][label]["state"]
        checkbox.setChecked(state)
        checkbox.stateChanged.connect(lambda state: self.check_changed(label, state))
        param = getattr(self, label, None)
        if param is not None:
            param.setEnabled(checkbox.isChecked())
        return checkbox

    def make_combobox(self, label, site="all") -> QComboBox:
        combo = QComboBox()
        site_items = values[site].get(label)
        if not site_items:
            return combo
        items = [item for item in site_items if item != ""]
        combo.addItems(items)

        text = self.data["track_rules"][label]["text"]
        if text in items:
            combo.setCurrentText(text)
            self.data["track_rules"][label]["value"] = site_items.index(text)
        else:
            combo.setCurrentText(items[0])
            self.data["track_rules"][label]["value"] = site_items.index(items[0])
            self.data["track_rules"][label]["text"] = items[0]
        combo.currentTextChanged.connect(
            lambda val: self.track_rule_changed(label, val, site)
        )
        return combo

    def update_combobox(self, label, site="all") -> None:
        combo = getattr(self, label, None)
        site_items = values[site].get(label)
        if combo is None or not site_items:
            return
        combo.currentTextChanged.disconnect()
        items = [item for item in site_items if item != ""]
        combo.clear()
        combo.addItems(items)

        text = self.data["track_rules"][label]["text"]
        if text in items:
            # keep same choice
            combo.setCurrentText(text)
            self.data["track_rules"][label]["value"] = site_items.index(text)
        else:
            # set to default choice
            combo.setCurrentText(items[0])
            self.data["track_rules"][label]["value"] = site_items.index(items[0])
            self.data["track_rules"][label]["text"] = items[0]
        combo.currentTextChanged.connect(
            lambda val: self.track_rule_changed(label, val, site)
        )

    def check_changed(self, key, state) -> None:
        param = getattr(self, key, None)
        if param is not None:
            param.setEnabled(state == 2)
        if key == "unlimiterver":
            log(f"check_changed, {state = }")
            if state == 2:
                self.data["track_rules"]["inunlimiter"]["state"] = 2
                self.data["track_rules"]["inunlimiter"]["value"] = 1
            else:
                self.data["track_rules"]["inunlimiter"]["state"] = 0
                self.data["track_rules"]["inunlimiter"]["value"] = 0
            if self.data["track_rules"][key]["text"] == "Any":
                self.data["track_rules"][key]["state"] = 0
                return
        if self.data["track_rules"].get(key):
            self.data["track_rules"][key]["state"] = state
        else:
            self.data["game_rules"][key]["state"] = state

    def create_config(self) -> dict:
        if not os.path.exists(self.data["exe_path"]):
            # TODO: pop up stopping session
            pass
        if not os.path.exists(self.data["track_dir"]):
            # TODO: pop up stopping session
            pass
        config = copy.deepcopy(self.data)
        if self.data["game_rules"]["track_limit"]["state"]:
            limit = self.data["game_rules"]["track_limit"]["value"]
            config["game_rules"]["track_limit"] = limit
        else:
            config["game_rules"]["track_limit"] = -1

        if self.data["game_rules"]["time_limit"]["state"]:
            limit = self.data["game_rules"]["time_limit"]["value"]
            config["game_rules"]["time_limit"] = limit
        else:
            config["game_rules"]["time_limit"] = timedelta()

        for rule in self.data["track_rules"]:
            if self.data["track_rules"][rule]["state"]:
                config["track_rules"][rule] = self.data["track_rules"][rule]["value"]
            else:
                config["track_rules"][rule] = None
        return config

    def start(self) -> None:
        self.setWindowTitle("Randomizer")
        self.stop_button.setStyleSheet("background-color: red")
        self.start_button.setStyleSheet("background-color: grey")
        self.stop_button.setEnabled(True)
        self.start_button.setEnabled(False)

        self.data["debug"] = len(sys.argv) == 2

        self.session = Game(self.create_config())
        self.progress_timer.start(100)
        self.session.start()

        self.stacked_widget.setCurrentIndex(1)

    def skip(self) -> None:
        self.session.skip()

    def reload(self) -> None:
        self.session.reload()

    def stop(self) -> None:
        self.session.stop()
        self.save_config()

        if reason := self.session.stop_reason:
            self.setWindowTitle(f"Randomizer | {reason}")

        self.stop_button.setStyleSheet("background-color: grey")
        self.start_button.setStyleSheet("background-color: green")
        self.stop_button.setEnabled(False)
        self.start_button.setEnabled(True)
        self.stacked_widget.setCurrentIndex(0)

    def update_progress(self) -> None:
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
                max = int(stop_time.timestamp() - start_time.timestamp())
                self.time_progress.setMaximum(max)

                progress = max - (stop_time.timestamp() - time.time())
                self.time_progress.setValue(int(progress))
                self.times.setText(f"{self.session.get_time_left():^10}")
        else:
            self.times.setText("          ")

        try:
            track = self.session.current.track_id
            target = self.session.current.medals.get(self.session.mode)
            if not target:
                self.setWindowTitle(f"Randomizer | {track}")
            else:
                self.setWindowTitle(f"Randomizer | {track} | {target}")
        except AttributeError:
            # current wasn't initialized yet
            pass

    def game_rule_changed(self, key, value) -> None:
        if key == "time_limit":
            self.data["game_rules"][key] = timedelta(
                hours=value.hour(), minutes=value.minute(), seconds=value.second()
            )
        elif key == "site":
            self.data["game_rules"][key] = value
            for param in ["tag", "primarytype", "environment"]:
                self.update_combobox(param, self.site.currentText())
        else:
            self.data["game_rules"][key] = value

    def track_rule_changed(self, key, value, site="all") -> None:
        track_rule = self.data["track_rules"][key]["value"]
        if key in ["authortimemin", "authortimemax"]:
            track_rule = value.msecsSinceStartOfDay()
        elif key in ["uploadedafter", "uploadedbefore"]:
            track_rule = datetime.fromtimestamp(value.toSecsSinceEpoch())
        elif key == "unlimiterver":
            track_rule = values[site][key].index(value)
            self.data["track_rules"]["unlimiterver"]["text"] = value
            if value == "Any":
                self.data["track_rules"]["unlimiterver"]["state"] = 0
            else:
                self.data["track_rules"]["unlimiterver"]["state"] = 2
        elif key in [
            "difficulty",
            "environment",
            "inhasrecord",
            "mood",
            "primarytype",
            "tag",
        ]:
            track_rule = values[site][key].index(value)
            self.data["track_rules"][key]["text"] = values[site][key][track_rule]

        self.data["track_rules"][key]["value"] = track_rule
        log(f"{key} changed to {track_rule}")

    def save_config(self) -> None:
        with open("data.bin", "wb") as file:
            pickle.dump(self.data, file)
