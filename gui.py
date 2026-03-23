import copy
import pickle
import re
import sys
import time
from datetime import datetime, timedelta
from exchange import sites
from game import Game
from PyQt6.QtCore import QDateTime, QTime, QTimer
from PyQt6.QtWidgets import (
    QCheckBox,
    QDateTimeEdit,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QProgressBar,
    QTabWidget,
)
from update_banned_tracks import get_cheated_ids


class MainWindow(QMainWindow):
    def __init__(self, data) -> None:
        super().__init__()
        self.setWindowTitle("Randomizer")
        self.data = data
        self.site_tabs = {}
        options_tab = self.make_options_tab()
        game_tab = self.make_game_tab()
        banned_tracks_tab = self.make_banned_tracks_tab()
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(options_tab, "Options")
        self.tab_widget.addTab(game_tab, "Game")
        self.tab_widget.addTab(banned_tracks_tab, "Banned Tracks")
        self.tab_widget.setTabEnabled(1, False)

        self.setCentralWidget(self.tab_widget)
        self.setMinimumSize(self.minimumSizeHint())
        self.setMaximumSize(self.minimumSizeHint())

        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self.update_progress)

    def make_options_tab(self) -> QWidget:
        # next_mode
        self.mode_label = QLabel(text="Next Mode")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Author", "Gold", "Silver", "Bronze", "Finished"])
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
        self.track_label = QLabel(text="Track Limit")
        self.track_spin = QSpinBox()
        self.track_spin.setMinimum(0)
        self.track_spin.setMaximum(1000)
        self.track_spin.setValue(self.data["game_rules"]["track_limit"])
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
        limit = int(self.data["game_rules"]["time_limit"].total_seconds())
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

    def make_settings_tab(self) -> QWidget:
        # force window size true/false
        # exe path
        # track dir
        tab = QWidget()
        return tab

    def banned_tracks_changed(self) -> None:
        for site in self.site_tabs:
            text = self.site_tabs[site].toPlainText()
            if not (matches := re.findall(r"\d+", text)):
                ids = {}
            else:
                ids = {int(x) for x in matches}
            self.data["banned_tracks"][site] = ids

    def make_site_tabs(self) -> QTabWidget:
        tab = QTabWidget()
        for site in sites:
            if site == "all":
                continue

            text_input = QTextEdit()
            site_ids = ""
            for track_id in self.data["banned_tracks"].get(site):
                site_ids += f"{track_id}\n"
            text_input.setText(site_ids)
            text_input.textChanged.connect(self.banned_tracks_changed)
            self.site_tabs.update({site: text_input})
            tab.addTab(text_input, site)

        return tab

    def make_banned_tracks_tab(self) -> QWidget:
        self.text_input = self.make_site_tabs()

        save = QPushButton("Save")
        save.clicked.connect(self.save_config)
        load = QPushButton("Load")
        load.clicked.connect(self.load_banned_tracks)
        export = QPushButton("Export")
        export.clicked.connect(self.export_banned_tracks)
        clear = QPushButton("Clear")
        clear.clicked.connect(self.clear_banned_tracks)
        update = QPushButton("Update")
        update.clicked.connect(self.update_banned_tracks)

        buttons = QVBoxLayout()
        for button in [save, load, export, clear, update]:
            buttons.addWidget(button)

        layout = QHBoxLayout()
        layout.addWidget(self.text_input)
        layout.addLayout(buttons)
        tab = QWidget()
        tab.setLayout(layout)
        return tab

    def get_ids_from_file(self, file_path) -> dict:
        with open(file_path, "r", encoding="utf-8") as file:
            data = file.read()

        pattern = re.compile(r"\b(TMUF|TMNF|TMO|TMS|TMN)(?:-X)?\b", re.IGNORECASE)
        matches = list(pattern.finditer(data))
        if not matches:
            return {}

        ids = {}

        for i, current_match in enumerate(matches):
            base_site = current_match.group(1).upper()
            site_key = f"{base_site}-X"

            start_idx = current_match.end()

            if i + 1 < len(matches):
                end_idx = matches[i + 1].start()
            else:
                end_idx = len(data)

            section_text = data[start_idx:end_idx]
            found_ids = {int(x) for x in re.findall(r"\d+", section_text)}
            if site_key not in ids:
                ids[site_key] = set()
            ids[site_key].update(found_ids)

        return ids

    def load_banned_tracks(self) -> None:
        # replace banned tracks from file
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Open File")
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setViewMode(QFileDialog.ViewMode.Detail)

        if file_dialog.exec():
            path = file_dialog.selectedFiles()[0]
            ids = self.get_ids_from_file(path)
            self.data["banned_tracks"].update(ids)
            for site in self.site_tabs:
                text = ""
                if not ids.get(site):
                    self.site_tabs[site].setText("")
                    continue
                for id in ids[site]:
                    text += f"{id}\n"
                self.site_tabs[site].setText(text)

    def export_banned_tracks(self) -> None:
        # save banned tracks to file
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Export File")
        if file_dialog.exec():
            ids = ""
            for site in self.data["banned_tracks"]:
                site_ids = f"{site}:"
                for track_id in self.data["banned_tracks"].get(site):
                    site_ids += f"\n - {track_id}"
                ids += f"{site_ids}\n"
            with open(file_dialog.selectedFiles()[0], "w") as file:
                file.write(ids)

    def clear_banned_tracks(self) -> None:
        # empty banned tracks
        self.data["banned_tracks"] = {
            "TMUF-X": [],
            "TMNF-X": [],
            "TMO-X": [],
            "TMS-X": [],
            "TMN-X": [],
        }
        for site in self.site_tabs:
            self.site_tabs[site].setText("")

    def update_banned_tracks(self) -> None:
        # update banned tracks from cheated track spread sheet
        self.data["banned_tracks"] = get_cheated_ids()
        for site in self.site_tabs:
            site_ids = ""
            for track_id in self.data["banned_tracks"].get(site):
                site_ids += f"{track_id}\n"
            self.site_tabs[site].textChanged.disconnect()
            self.site_tabs[site].setText(site_ids)
            self.site_tabs[site].textChanged.connect(self.banned_tracks_changed)

    def make_checkbox(self, text, label) -> QCheckBox:
        checkbox = QCheckBox(text)
        checkbox.setChecked(self.data["track_rules"][label]["state"])
        checkbox.stateChanged.connect(lambda state: self.check_changed(label, state))
        param = getattr(self, label, None)
        if param is not None:
            param.setEnabled(checkbox.isChecked())
        return checkbox

    def make_combobox(self, label, site="all") -> QComboBox:
        combo = QComboBox()
        site_items = sites[site].get(label)
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
        site_items = sites[site].get(label)
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
            print(f"check_changed, {state = }")
            if state == 2:
                self.data["track_rules"]["inunlimiter"]["state"] = 2
                self.data["track_rules"]["inunlimiter"]["value"] = 1
            else:
                self.data["track_rules"]["inunlimiter"]["state"] = 0
                self.data["track_rules"]["inunlimiter"]["value"] = 0
            if self.data["track_rules"][key]["text"] == "Any":
                self.data["track_rules"][key]["state"] = 0
                return

        self.data["track_rules"][key]["state"] = state

    def create_config(self) -> dict:
        config = copy.deepcopy(self.data)
        for rule in self.data["track_rules"]:
            if self.data["track_rules"][rule]["state"]:
                # if checked set
                config["track_rules"][rule] = self.data["track_rules"][rule]["value"]
            else:
                config["track_rules"][rule] = None
        # print(f"{config = }\n{self.data = }")
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

        self.tab_widget.setCurrentIndex(1)
        self.tab_widget.setTabEnabled(0, False)
        self.tab_widget.setTabEnabled(1, True)

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
        self.tab_widget.setCurrentIndex(0)
        self.tab_widget.setTabEnabled(0, True)
        self.tab_widget.setTabEnabled(1, False)

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
                max = stop_time.timestamp() - start_time.timestamp()
                self.time_progress.setMaximum(int(max))

                progress = int(max) - (stop_time.timestamp() - time.time())
                self.time_progress.setValue(int(progress))
                self.times.setText(f"{self.session.get_time_left():^10}")
        else:
            self.times.setText("          ")

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
            track_rule = sites[site][key].index(value)
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
            track_rule = sites[site][key].index(value)
            self.data["track_rules"][key]["text"] = sites[site][key][track_rule]

        self.data["track_rules"][key]["value"] = track_rule
        print(f"{key} changed to {track_rule}")

    def save_config(self) -> None:
        with open("data.bin", "wb") as file:
            pickle.dump(self.data, file)
