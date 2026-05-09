import re

from PyQt6.QtCore import QDateTime, Qt, QTime, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from common import values


class FindPath(QDialog):
    def __init__(self, path_type: str, paths: dict):
        super().__init__()
        self.path_type = path_type
        self.paths = paths
        self.path = None
        self.main_layout = QVBoxLayout()

        if path_type == "exe_path":
            self.setWindowTitle("Select an Exe")
        elif path_type == "track_dir":
            self.setWindowTitle("Select a Tracks Directory")

        self._display_paths()
        self.setLayout(self.main_layout)

    def _display_paths(self):
        """Display all found paths to select from"""
        grid_layout = QGridLayout()
        for i, (path, name) in enumerate(self.paths.items()):
            label = QLabel(path)
            button = QPushButton(name)
            button.clicked.connect(lambda _, p=path: self._return_path(p))
            grid_layout.addWidget(label, i, 0)
            grid_layout.addWidget(button, i, 1)
        self.main_layout.addLayout(grid_layout)

        other_button = QPushButton("Other Path")
        other_button.clicked.connect(self._open_file_dialog)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self._return_path)

        row = QHBoxLayout()
        row.addWidget(other_button)
        row.addWidget(cancel_button)
        self.main_layout.addLayout(row)

    def _open_file_dialog(self):
        """Opens file dialog"""
        if self.path_type == "exe_path":
            path = Dialogs.ask_for_exe(self)
        elif self.path_type == "track_dir":
            path = Dialogs.ask_for_track_dir(self)
        else:
            return

        if path:
            self._return_path(path)

    def _return_path(self, path=None):
        """Sets self.path and closes self"""
        self.path = path
        self.accept()


class SettingsTab(QWidget):
    settings_changed = pyqtSignal(dict)
    delete_data_requested = pyqtSignal()
    rescan_autosaves = pyqtSignal()
    save_requested = pyqtSignal()
    find_exe = pyqtSignal()
    find_track = pyqtSignal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        self.forced_window = QCheckBox("Force Window Size (Requires Restart)")
        self.auto_update = QCheckBox("Auto Update Banned Tracks")
        self.skip_skipped = QCheckBox("Don't Play Skipped Tracks")

        self.checkboxes = [self.forced_window, self.auto_update, self.skip_skipped]

        for checkbox in self.checkboxes:
            checkbox.stateChanged.connect(self._emit_settings)
            layout.addWidget(checkbox)

        # Exe path
        paths_layout = QGridLayout()
        self.exe_edit = QLineEdit()
        self.exe_edit.textEdited.connect(self._emit_settings)
        btn_exe = QPushButton("Find")
        btn_exe.clicked.connect(self.find_exe.emit)
        paths_layout.addWidget(QLabel("Exe Path:"), 0, 0)
        paths_layout.addWidget(self.exe_edit, 0, 1)
        paths_layout.addWidget(btn_exe, 0, 2)

        # Track dir
        self.dir_edit = QLineEdit()
        self.dir_edit.textEdited.connect(self._emit_settings)
        btn_dir = QPushButton("Find")
        btn_dir.clicked.connect(self.find_track.emit)
        paths_layout.addWidget(QLabel("Track Dir:"), 1, 0)
        paths_layout.addWidget(self.dir_edit, 1, 1)
        paths_layout.addWidget(btn_dir, 1, 2)

        btn_scan = QPushButton("Rescan autosaves")
        btn_scan.clicked.connect(self.rescan_autosaves.emit)
        layout.addWidget(btn_scan)

        btn_delete = QPushButton("Delete all data")
        btn_delete.clicked.connect(self.delete_data_requested.emit)
        layout.addWidget(btn_delete)

        # NOTE: get rid of this button? have other functions auto save
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.save_requested.emit)
        layout.addWidget(btn_save)

        self.setLayout(layout)

    def populate(self, config_data: dict):
        """Populates checkboxes and text exits from config_data"""
        for checkbox in self.checkboxes:
            checkbox.blockSignals(True)
        self.exe_edit.blockSignals(True)
        self.dir_edit.blockSignals(True)

        self.forced_window.setChecked(config_data.get("force_window_size", True))
        self.auto_update.setChecked(config_data.get("auto_update", False))
        self.skip_skipped.setChecked(config_data.get("skip_skipped", True))
        self.exe_edit.setText(config_data.get("exe_path", "bad"))
        self.dir_edit.setText(config_data.get("track_dir", "bad"))

        for checkbox in self.checkboxes:
            checkbox.blockSignals(False)
        self.exe_edit.blockSignals(False)
        self.dir_edit.blockSignals(False)

    def _emit_settings(self):
        """Emits checkbox states and text edit text"""
        self.settings_changed.emit(
            {
                "force_window_size": self.forced_window.isChecked(),
                "auto_update": self.auto_update.isChecked(),
                "skip_skipped": self.skip_skipped.isChecked(),
                "exe_path": self.exe_edit.text(),
                "track_dir": self.dir_edit.text(),
            }
        )


class BannedTracksTab(QWidget):
    save_requested = pyqtSignal()
    import_requested = pyqtSignal(str)
    export_requested = pyqtSignal(str)
    clear_requested = pyqtSignal()
    update_requested = pyqtSignal()
    tracks_modified = pyqtSignal(str, set)

    def __init__(self):
        super().__init__()
        self.site_tabs = {}

        main_layout = QHBoxLayout()
        self.tab_widget = QTabWidget()
        for site in ["TMUF-X", "TMNF-X", "TMO-X", "TMS-X", "TMN-X"]:
            text = QTextEdit()
            text.textChanged.connect(lambda s=site, t=text: self._on_text_changed(s, t))
            self.site_tabs[site] = text
            self.tab_widget.addTab(text, site)

        main_layout.addWidget(self.tab_widget)

        btn_layout = QVBoxLayout()
        btns = {
            "Save": self.save_requested,
            "Import": self._trigger_import,
            "Export": self._trigger_export,
            "Clear": self.clear_requested,
            "Update": self.update_requested,
        }
        for name, signal in btns.items():
            btn = QPushButton(name)
            if callable(signal):
                btn.clicked.connect(signal)
            else:
                btn.clicked.connect(signal.emit)
            btn_layout.addWidget(btn)

        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)

    def populate(self, banned_tracks):
        """Populates each site tabs text with banned_tracks"""
        for site, ids in banned_tracks.items():
            if site in self.site_tabs:
                te = self.site_tabs[site]
                te.blockSignals(True)
                te.setText("\n".join(map(str, ids)))
                te.blockSignals(False)

    def _on_text_changed(self, site, text):
        ids = {int(id) for id in re.findall(r"\d+", text.toPlainText())}
        self.tracks_modified.emit(site, ids)

    def _trigger_import(self):
        path = QFileDialog.getOpenFileName(self, "Open File")[0]
        if path:
            self.import_requested.emit(path)

    def _trigger_export(self):
        path = QFileDialog.getSaveFileName(
            self, "Export File", filter="*.yaml *.yml *.txt"
        )[0]
        if path:
            self.export_requested.emit(path)


class OptionsTab(QWidget):
    preset_changed = pyqtSignal(str)
    save_preset_requested = pyqtSignal()
    new_preset_requested = pyqtSignal(str)
    delete_preset_requested = pyqtSignal()

    game_rule_changed = pyqtSignal(str, object)
    track_rule_changed = pyqtSignal(str, object)

    start_requested = pyqtSignal()
    save_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.widgets = {}
        layout = QVBoxLayout()

        # Presets
        preset_layout = QHBoxLayout()
        self.preset_combo = QComboBox()
        self.preset_combo.currentTextChanged.connect(self.preset_changed.emit)
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.save_preset_requested.emit)
        btn_new = QPushButton("Save As")
        btn_new.clicked.connect(self._trigger_new_preset)
        btn_del = QPushButton("Delete")
        btn_del.clicked.connect(self.delete_preset_requested.emit)
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addWidget(btn_save)
        preset_layout.addWidget(btn_new)
        preset_layout.addWidget(btn_del)
        layout.addLayout(preset_layout)

        # Game Rules
        gr_layout = QHBoxLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(values["all"]["mode"])
        self.mode_combo.currentTextChanged.connect(
            lambda value: self.game_rule_changed.emit("next_mode", value.lower())
        )
        mode_layout = QVBoxLayout()
        mode_layout.addWidget(QLabel("Next Mode"))
        mode_layout.addWidget(self.mode_combo)
        gr_layout.addLayout(mode_layout)

        self.track_limit_chk = QCheckBox("Track Limit")
        self.track_limit_spn = QSpinBox()
        self.track_limit_spn.setMinimum(1)
        self.track_limit_spn.setMaximum(1000)
        self.track_limit_chk.stateChanged.connect(
            lambda s: self._emit_state("track_limit", s, self.track_limit_spn, True)
        )
        self.track_limit_spn.valueChanged.connect(
            lambda v: self.game_rule_changed.emit("track_limit_val", v)
        )
        track_layout = QVBoxLayout()
        track_layout.addWidget(self.track_limit_chk)
        track_layout.addWidget(self.track_limit_spn)
        gr_layout.addLayout(track_layout)

        self.time_limit_chk = QCheckBox("Time Limit")
        self.time_limit_edit = QTimeEdit()
        self.time_limit_edit.setDisplayFormat("HH:mm:ss")
        self.time_limit_chk.stateChanged.connect(
            lambda state: self._emit_state(
                "time_limit", state, self.time_limit_edit, True
            )
        )
        self.time_limit_edit.timeChanged.connect(
            lambda value: self.game_rule_changed.emit("time_limit_val", value)
        )
        time_layout = QVBoxLayout()
        time_layout.addWidget(self.time_limit_chk)
        time_layout.addWidget(self.time_limit_edit)
        gr_layout.addLayout(time_layout)
        layout.addLayout(gr_layout)

        # Site & Basic Rules
        row2 = QHBoxLayout()
        self.site_combo = QComboBox()
        self.site_combo.addItems(values["all"]["site"])
        self.site_combo.currentTextChanged.connect(
            lambda v: self.game_rule_changed.emit("site", v)
        )
        site_layout = QVBoxLayout()
        site_layout.addWidget(QLabel("Site"))
        site_layout.addWidget(self.site_combo)
        row2.addLayout(site_layout)

        self.up_after_chk, self.up_after_edit = self._make_date(
            "Uploaded After", "uploadedafter"
        )
        self.up_bef_chk, self.up_bef_edit = self._make_date(
            "Uploaded Before", "uploadedbefore"
        )
        after_layout = QVBoxLayout()
        after_layout.addWidget(self.up_after_chk)
        after_layout.addWidget(self.up_after_edit)
        row2.addLayout(after_layout)
        before_layout = QVBoxLayout()
        before_layout.addWidget(self.up_bef_chk)
        before_layout.addWidget(self.up_bef_edit)
        row2.addLayout(before_layout)
        layout.addLayout(row2)

        # Other fields rows
        rows = [
            [
                ("Min AT", "authortimemin", "time"),
                ("Max AT", "authortimemax", "time"),
                ("Mood", "mood"),
            ],
            [
                ("Tag", "tag"),
                ("Style", "primarytype"),
                ("Difficulty", "difficulty"),
            ],
            [
                ("Environment", "environment"),
                ("Records", "inhasrecord"),
                ("Author Time", "inauthortimebeaten"),
            ],
            [
                ("Sort Order", "order1"),
                ("Unlimiter", "unlimiterver"),
            ],
        ]

        for row in rows:
            row_layout = QHBoxLayout()
            for item in row:
                checkbox = QCheckBox(item[0])
                if len(item) == 3 and item[2] == "time":
                    widget = QTimeEdit()
                    widget.setDisplayFormat("HH:mm:ss")
                    widget.timeChanged.connect(
                        lambda v, k=item[1]: self.track_rule_changed.emit(f"{k}_val", v)
                    )
                else:
                    widget = QComboBox()
                    widget.currentTextChanged.connect(
                        lambda v, k=item[1]: self.track_rule_changed.emit(f"{k}_val", v)
                    )
                    self.widgets[item[1]] = widget

                checkbox.stateChanged.connect(
                    lambda s, k=item[1], w=widget: self._emit_state(k, s, w, False)
                )
                self.widgets[f"{item[1]}_chk"] = checkbox
                self.widgets[f"{item[1]}_wdg"] = widget

                item_layout = QVBoxLayout()
                item_layout.addWidget(checkbox)
                item_layout.addWidget(widget)
                row_layout.addLayout(item_layout)
            layout.addLayout(row_layout)

        # Bottom buttons
        btn_start = QPushButton("Start")
        btn_start.setStyleSheet("background-color: green")
        btn_start.clicked.connect(self.start_requested.emit)

        btn_save_main = QPushButton("Save")
        btn_save_main.clicked.connect(self.save_requested.emit)

        layout.addWidget(btn_start)
        layout.addWidget(btn_save_main)
        self.setLayout(layout)

    def _make_date(self, label, key):
        checkbox = QCheckBox(label)
        date = QDateTimeEdit()
        date.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        checkbox.stateChanged.connect(
            lambda state: self._emit_state(key, state, date, False)
        )
        date.dateTimeChanged.connect(
            lambda value: self.track_rule_changed.emit(f"{key}_val", value)
        )
        self.widgets[f"{key}_chk"] = checkbox
        self.widgets[f"{key}_wdg"] = date
        return checkbox, date

    def _emit_state(self, key, state, widget, is_game):
        widget.setEnabled(state == 2)
        if is_game:
            self.game_rule_changed.emit(f"{key}_state", state == 2)
        else:
            self.track_rule_changed.emit(f"{key}_state", state == 2)

    def _trigger_new_preset(self):
        text, ok = QInputDialog.getText(self, "New Preset", "Name:")
        if ok and text:
            self.new_preset_requested.emit(text)

    def populate_presets(self, presets: list, current: str):
        """Populates list of presets"""
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItems(presets)
        self.preset_combo.setCurrentText(current)
        self.preset_combo.blockSignals(False)

    def update_comboboxes(self, site: str):
        """Update site specific comboboxes"""
        for key in [
            "tag",
            "primarytype",
            "environment",
            "car",
            "mood",
            "difficulty",
            "inhasrecord",
            "unlimiterver",
            "inauthortimebeaten",
            "order1",
        ]:
            if key in self.widgets and isinstance(self.widgets[key], QComboBox):
                combo = self.widgets[key]
                items = [
                    i
                    for i in values.get(site, values["all"]).get(
                        key, values["all"].get(key, [])
                    )
                    if i != ""
                ]
                combo.blockSignals(True)
                current_item = combo.currentText()
                combo.clear()
                combo.addItems(items)
                if current_item in items:
                    combo.setCurrentText(current_item)
                combo.blockSignals(False)

    def populate_rules(self, game_rules: dict, track_rules: dict):
        """Populates all options from game_rules and track_rules"""
        self.mode_combo.setCurrentText(
            "WR"
            if game_rules["next_mode"] == "wr"
            else game_rules["next_mode"].capitalize()
        )
        self.site_combo.setCurrentText(game_rules["site"])

        self.track_limit_chk.setChecked(game_rules["track_limit"]["state"])
        self.track_limit_spn.setValue(game_rules["track_limit"]["value"])
        self.track_limit_spn.setEnabled(game_rules["track_limit"]["state"])

        self.time_limit_chk.setChecked(game_rules["time_limit"]["state"])
        self.time_limit_edit.setTime(
            QTime(0, 0).addSecs(int(game_rules["time_limit"]["value"].total_seconds()))
        )
        self.time_limit_edit.setEnabled(game_rules["time_limit"]["state"])

        # Generic setter for track rules
        for key, config in track_rules.items():
            chk = self.widgets.get(f"{key}_chk")
            wdg = self.widgets.get(f"{key}_wdg")
            if not chk or not wdg:
                continue

            chk.blockSignals(True)
            wdg.blockSignals(True)

            chk.setChecked(config["state"])
            wdg.setEnabled(config["state"])

            if "authortime" in key and "min" in key or "max" in key:
                wdg.setTime(QTime(0, 0).fromMSecsSinceStartOfDay(config["value"]))
            elif "uploaded" in key:
                wdg.setDateTime(
                    QDateTime().fromSecsSinceEpoch(int(config["value"].timestamp()))
                )
            elif isinstance(wdg, QComboBox):
                possible_text = values[game_rules["site"]].get(
                    key, values["all"].get(key)
                )
                text = possible_text[0]
                if len(possible_text) > config["value"]:
                    text = possible_text[config["value"]]
                wdg.setCurrentText(text)

            chk.blockSignals(False)
            wdg.blockSignals(False)


class GameTab(QWidget):
    skip_requested = pyqtSignal()
    reload_requested = pyqtSignal()
    stop_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        self.track_lbl = QLabel()
        self.track_bar = QProgressBar()
        frame = QFrame()
        l1 = QHBoxLayout(frame)
        l1.addWidget(self.track_lbl)
        l1.addWidget(self.track_bar)

        self.time_lbl = QLabel()
        self.time_bar = QProgressBar()
        self.time_frame = QFrame()
        l2 = QHBoxLayout(self.time_frame)
        l2.addWidget(self.time_lbl)
        l2.addWidget(self.time_bar)

        self.track_info = QLabel()
        self.track_info.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_layout = QHBoxLayout()
        btn_rel = QPushButton("Reload")
        btn_rel.setStyleSheet("background-color: yellow")
        btn_rel.clicked.connect(self.reload_requested.emit)
        btn_skip = QPushButton("Skip")
        btn_skip.setStyleSheet("background-color: orange")
        btn_skip.clicked.connect(self.skip_requested.emit)
        btn_stop = QPushButton("Stop")
        btn_stop.setStyleSheet("background-color: red")
        btn_stop.clicked.connect(self.stop_requested.emit)
        btn_layout.addWidget(btn_rel)
        btn_layout.addWidget(btn_skip)
        btn_layout.addWidget(btn_stop)

        layout.addWidget(frame)
        layout.addWidget(self.time_frame)
        layout.addWidget(self.track_info)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def set_time_visible(self, visible: bool):
        """Show time progress bar in game screen"""
        self.time_frame.setVisible(visible)

    def update_track_progress(self, current: int, total: int):
        if total:
            self.track_bar.setMaximum(total)
            self.track_bar.setValue(current)
            string = f"{current}/{total}"
            self.track_lbl.setText(f"{string:^9}")

    def update_time_progress(self, text: str, current_sec: int, max_sec: int):
        if max_sec:
            self.time_bar.setMaximum(max_sec)
            self.time_bar.setValue(current_sec)
            self.time_lbl.setText(f"{text:^9}")

    def set_info(self, text: str):
        self.track_info.setText(text)


class Dialogs:
    @staticmethod
    def ask_for_exe(parent):
        path = QFileDialog.getOpenFileName(parent, "Select TmForever.exe")[0]
        return path

    @staticmethod
    def ask_for_track_dir(parent):
        path = QFileDialog.getExistingDirectory(parent, "Select Tracks Folder")
        return path

    @staticmethod
    def question(parent, title, question):
        reply = QMessageBox.question(parent, title, question)
        if reply == QMessageBox.StandardButton.Yes:
            return True


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Unplayed")
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self.stacked = QStackedWidget()
        self.setCentralWidget(self.stacked)

        # NOTE: advanced options tab?
        # search author/track/trackpack by name
        # move some other settings here?

        self.tabs = QTabWidget()
        self.options_tab = OptionsTab()
        self.banned_tab = BannedTracksTab()
        self.settings_tab = SettingsTab()
        self.tabs.addTab(self.options_tab, "Options")
        self.tabs.addTab(self.banned_tab, "Banned Tracks")
        self.tabs.addTab(self.settings_tab, "Settings")
        self.stacked.addWidget(self.tabs)

        self.game_tab = GameTab()
        self.stacked.addWidget(self.game_tab)

    def set_status(self, msg, timeout=0):
        self.status.showMessage(msg, timeout)

    def show_error(self, title, msg):
        QMessageBox.warning(self, title, msg)

    def show_info(self, title, msg):
        QMessageBox.information(self, title, msg)

    def show_game(self):
        """Switch to game screen"""
        self.stacked.setCurrentIndex(1)

    def show_config(self):
        """Switch to config screen"""
        self.stacked.setCurrentIndex(0)
