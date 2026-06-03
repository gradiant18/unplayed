import copy
import os
from datetime import datetime, timedelta

from PyQt6.QtCore import QThread, QTimer, pyqtSignal

from common import values
from model import BannedTracksFetcher, ConfigModel, GameSession
from view import Dialogs, FindPath


class BannedTracksWorker(QThread):
    finished_fetch = pyqtSignal(dict)
    error_fetch = pyqtSignal(str)

    def run(self):
        try:
            data = BannedTracksFetcher.get_cheated_ids()
            self.finished_fetch.emit(data)
        except Exception as e:
            self.error_fetch.emit(str(e))


class AppPresenter:
    def __init__(self, model: ConfigModel, view):
        self.model = model
        self.view = view
        self.session = GameSession(model)

        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.update_game_ui)

        if self.model.config.get("auto_update"):
            self.handle_banned_update()

        self.connect_signals()
        self.refresh_ui_from_model()

        if "default_data" in self.model.config.keys():
            del self.model.config["default_data"]
            self.save_model(silent=True)

    def connect_signals(self):
        self.view.settings_tab.settings_changed.connect(self.handle_settings_changed)
        self.view.settings_tab.find_exe.connect(self.handle_find_exe)
        self.view.settings_tab.find_track.connect(self.handle_find_track)
        self.view.settings_tab.rescan_autosaves.connect(self.handle_rescan_autosaves)
        self.view.settings_tab.save_requested.connect(self.save_model)
        self.view.settings_tab.delete_data_requested.connect(self.handle_delete_data)

        self.view.banned_tab.save_requested.connect(self.save_model)
        self.view.banned_tab.clear_requested.connect(self.handle_banned_clear)
        self.view.banned_tab.update_requested.connect(self.handle_banned_update)
        self.view.banned_tab.tracks_modified.connect(self.handle_banned_modified)

        self.view.options_tab.preset_loaded.connect(self.handle_preset_changed)
        self.view.options_tab.save_preset_requested.connect(self.handle_save_preset)
        self.view.options_tab.delete_preset_requested.connect(self.handle_delete_preset)
        self.view.options_tab.game_rule_changed.connect(self.handle_game_rule_changed)
        self.view.options_tab.track_rule_changed.connect(self.handle_track_rule_changed)
        self.view.options_tab.start_requested.connect(self.handle_start_game)
        self.view.options_tab.save_requested.connect(self.save_model)

        self.view.game_tab.skip_requested.connect(lambda: self.session.skip())
        self.view.game_tab.reload_requested.connect(lambda: self.session.reload())
        self.view.game_tab.stop_requested.connect(lambda: self.session.stop())

    def refresh_ui_from_model(self):
        if self.model.config["force_window_size"]:
            self.view.setMinimumSize(self.view.minimumSizeHint())
            self.view.setMaximumSize(self.view.minimumSizeHint())

        self.view.settings_tab.populate(self.model.config)
        self.view.banned_tab.populate(self.model.data)

        self.view.options_tab.populate_presets(self.model.get_presets())

        game_rules = self.model.config["game_rules"]
        track_rules = self.model.config["track_rules"]
        self.view.options_tab.update_comboboxes(game_rules["site"])
        self.view.options_tab.populate_rules(game_rules, track_rules)

    def save_model(self, silent=False):
        if not silent:
            self.view.set_status("Saving...")
        self.model.save_config()
        self.model.save_data()
        self.model.save_autosaves()
        if not silent:
            self.view.set_status("Saved!", 3000)

    def handle_settings_changed(self, new_settings):
        self.model.config.update(new_settings)
        if self.model.config["force_window_size"]:
            hint = self.view.minimumSizeHint()
            self.view.setFixedSize(hint)
        else:
            self.view.setMinimumSize(0, 0)
            self.view.setMaximumSize(16777215, 16777215)
            self.view.hide()
            self.view.show()

    def handle_find_exe(self):
        steam = os.path.join("Steam", "steamapps", "common")
        tmuf = "TrackMania United"
        tmnf = "TrackMania Nations Forever"
        exe = "TmForever.exe"

        steam_paths = {
            os.path.join(str(os.getenv("ProgramFiles")), steam, tmuf, exe): "TMUF",
            os.path.join(str(os.getenv("ProgramFiles")), steam, tmnf, exe): "TMNF",
            os.path.join(str(os.getenv("ProgramFiles(x86)")), steam, tmuf, exe): "TMUF",
            os.path.join(str(os.getenv("ProgramFiles(x86)")), steam, tmnf, exe): "TMNF",
            os.path.expanduser(
                f"~/.local/share/Steam/steamapps/common/{tmuf}/{exe}"
            ): "TMUF",
            os.path.expanduser(
                f"~/.local/share/Steam/steamapps/common/{tmnf}/{exe}"
            ): "TMNF",
        }

        exe_paths = {}
        for path, name in steam_paths.items():
            if os.path.exists(path):
                exe_paths.update({path: name})

        while True:
            if not exe_paths:
                path = Dialogs.ask_for_exe(self.view)
            else:
                dialog = FindPath("exe_path", exe_paths)
                if not dialog.exec():
                    return False  # window closed
                path = dialog.path
            if not path:
                return False

            if (
                not os.path.isfile(path)
                or not os.access(path, os.X_OK)
                or os.path.splitext(path)[1] != ".exe"
            ):
                self.view.show_error(
                    "Invalid File", f"The file {path} is not an executable"
                )
            else:
                break
        self.model.config["exe_path"] = path
        self.view.settings_tab.populate(self.model.config)
        return True

    def handle_find_track(self):
        dir_paths = {
            os.path.join(
                str(os.getenv("HOMEPATH")), "Documents", "TrackMania", "Tracks"
            ): "Select",
            os.path.join(
                str(os.getenv("HOMEPATH")),
                "OneDrive",
                "Documents",
                "TrackMania",
                "Tracks",
            ): "Select",
            os.path.expanduser(
                "~/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks"
            ): "TMUF",
            os.path.expanduser(
                "~/.local/share/Steam/steamapps/compatdata/11020/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks"
            ): "TMNF",
        }

        track_paths = {}
        for path, name in dir_paths.items():
            if os.path.exists(path):
                track_paths.update({path: name})

        while True:
            if not track_paths:
                path = Dialogs.ask_for_track_dir(self.view)
            else:
                dialog = FindPath("track_dir", track_paths)
                if not dialog.exec():
                    return False
                path = dialog.path
            if not path:
                return False

            autosave_dir = os.path.join(path, "Replays", "Autosaves")
            if not os.path.exists(autosave_dir):
                self.view.show_error(
                    "Invalid Path",
                    f"The path {path} does not contain Replays/Autosaves",
                )
            else:
                break

        self.model.config["track_dir"] = path
        self.view.settings_tab.populate(self.model.config)
        return True

    def handle_rescan_autosaves(self):
        self.view.set_status("Scanning...")
        total = self.model.rescan_autosaves()
        self.view.set_status(f"Found {total} replays!", 3000)

    def handle_delete_data(self):
        reply = Dialogs.question(
            self.view, "Delete Data", "Are you sure you want to delete all data?"
        )
        if not reply:
            self.view.set_status("Canceled.", 3000)
            return

        self.model.delete_files()
        self.model.config = self.model.load_config()
        self.model.data = self.model.load_data()
        self.save_model(silent=True)
        self.refresh_ui_from_model()
        self.view.set_status("Deleted.", 3000)

    def handle_banned_clear(self):
        reply = Dialogs.question(
            self.view,
            "Clear Banned Tracks",
            "Are you sure you want to clear all banned tracks?",
        )
        if not reply:
            self.view.set_status("Canceled.", 3000)
            return

        for site in values["all"]["site"]:
            self.model.data[site]["banned"] = []
        self.view.banned_tab.populate(self.model.data)
        self.view.set_status("Cleared.", 3000)

    def handle_banned_update(self):
        self.view.set_status("Updating...")

        self.banned_worker = BannedTracksWorker()
        self.banned_worker.finished_fetch.connect(self._on_banned_update_success)
        self.banned_worker.error_fetch.connect(self._on_banned_update_error)
        self.banned_worker.start()

    def _on_banned_update_success(self, data: dict):
        for site, ids in data.items():
            self.model.data[site]["banned"] = set(ids)
        self.view.banned_tab.populate(self.model.data)
        self.save_model()
        self.view.set_status("Updated!", 3000)

    def _on_banned_update_error(self, err_msg: str):
        self.view.set_status("Update Failed!", 3000)
        self.view.show_error(
            "Network Error", f"Failed to fetch banned tracks:\n{err_msg}"
        )

    def handle_banned_modified(self, site: str, ids: set):
        self.model.data[site]["banned"] = ids

    def handle_preset_changed(self, name: str):
        if not name or name not in self.model.get_presets():
            return
        preset = self.model.load_preset(name)
        if not preset:
            return
        self.model.config["game_rules"] = preset["game_rules"]
        self.model.config["track_rules"] = preset["track_rules"]
        self.refresh_ui_from_model()

    def handle_save_preset(self, name: str):
        if name == "New...":
            new_name = Dialogs.new_preset_name(self.view, self.model.get_presets())
            if not new_name:
                self.view.options_tab.populate_presets(self.model.get_presets())
                return
            else:
                name = new_name

        preset = {}
        preset.update(copy.deepcopy({"game_rules": self.model.config["game_rules"]}))
        preset.update(copy.deepcopy({"track_rules": self.model.config["track_rules"]}))
        self.model.save_preset(name, preset)
        presets = self.model.get_presets()
        self.view.options_tab.populate_presets(presets)
        self.view.set_status(f"{name} saved!", 3000)

    def handle_delete_preset(self, name: str):
        self.view.options_tab.reset_presets()
        if len(self.model.get_presets()) < 1:
            return
        reply = Dialogs.question(
            self.view,
            "Delete Preset",
            f"Are you sure you want to delete preset {name}?",
        )
        if not reply:
            return

        self.model.delete_preset(name)
        self.view.set_status(f"{name} deleted.", 3000)
        presets = self.model.get_presets()
        self.view.options_tab.populate_presets(presets)

    def handle_game_rule_changed(self, key, val):
        gr = self.model.config["game_rules"]
        if key == "next_mode":
            gr["next_mode"] = val
        elif key == "site":
            gr["site"] = val
            self.view.options_tab.update_comboboxes(val)
        elif key == "track_limit_enabled":
            gr["track_limit"]["enabled"] = True if val else False
        elif key == "track_limit_val":
            gr["track_limit"]["value"] = val
        elif key == "time_limit_enabled":
            gr["time_limit"]["enabled"] = True if val else False
        elif key == "time_limit_val":
            gr["time_limit"]["value"] = datetime(
                1900, 1, 1, val.hour(), val.minute(), val.second()
            )

    def handle_track_rule_changed(self, key, val):
        track_rule = self.model.config["track_rules"]
        base_key = key.replace("_enabled", "").replace("_val", "")
        if base_key not in track_rule:
            return

        if key.endswith("_enabled"):
            track_rule[base_key]["enabled"] = True if val else False
        else:
            if base_key in ["authortimemin", "authortimemax"]:
                track_rule[base_key]["value"] = datetime(
                    1900, 1, 1, val.hour(), val.minute(), val.second()
                )
            elif "uploaded" in base_key:
                track_rule[base_key]["value"] = datetime.fromtimestamp(
                    val.toSecsSinceEpoch()
                )
            else:
                site = self.model.config["game_rules"]["site"]
                opts = values.get(site, values["all"]).get(
                    base_key, values["all"].get(base_key, [])
                )
                opts = [x for x in opts if x != ""]
                track_rule[base_key]["value"] = opts.index(val) if val in opts else 0

    def handle_start_game(self):
        session_config = self.generate_session_config()
        if not session_config:
            self.view.set_status("Canceled.", 3000)
            return

        self.view.game_tab.set_time_visible(
            bool(session_config["game_rules"]["time_limit"])
        )

        started = self.session.start(session_config)
        self.progress_timer.start(100)
        if started:
            self.view.game_tab.set_info("")
            self.view.show_game(self.model.config["force_window_size"])

    def handle_stop(self):
        self.progress_timer.stop()
        self.model.data[self.session.site]["skipped"].extend(list(self.session.skipped))

        self.save_model()
        if self.session.stop_reason:
            self.view.set_status(self.session.stop_reason, 5000)
        self.view.show_config(self.model.config["force_window_size"])

    def generate_session_config(self):
        if not os.path.exists(self.model.config.get("exe_path", "")):
            if not self.handle_find_exe():
                return None

        while not os.path.exists(self.model.config.get("track_dir", "")):
            if not self.handle_find_track():
                return None

        config = copy.deepcopy(self.model.config.unwrap())
        game_rule = config["game_rules"]
        game_rule["track_limit"] = (
            game_rule["track_limit"]["value"]
            if game_rule["track_limit"]["enabled"]
            else None
        )
        tl = game_rule["time_limit"]["value"]
        game_rule["time_limit"] = (
            timedelta(hours=tl.hour, minutes=tl.minute, seconds=tl.second)
            if game_rule["time_limit"]["enabled"]
            else None
        )

        for rule, rule_dict in config["track_rules"].items():
            if rule in ["authortimemin", "authortimemax"]:
                value = rule_dict["value"]
                msecs = (
                    (value.hour * 3600) + (value.minute * 60) + value.second
                ) * 1000
                rule_dict["value"] = msecs
            elif rule in ["uploadedafter", "uploadedbefore"]:
                value = rule_dict["value"].timestamp()
                rule_dict["value"] = datetime.fromtimestamp(value)
            if rule == "inunlimiter":
                continue
            if rule == "unlimiterver":
                if rule_dict["value"] == 0 and rule_dict["enabled"]:
                    rule_dict["enabled"] = False
                    config["track_rules"]["inunlimiter"] = 1

            config["track_rules"][rule] = (
                rule_dict["value"] if rule_dict["enabled"] else None
            )

        config["sorted"] = self.model.config["track_rules"]["order1"]["enabled"]
        autosave_data = self.model.update_autosave_data()
        config["autosaves"] = autosave_data.get("autosaves", set())

        site_data = copy.deepcopy(self.model.data[game_rule["site"]])
        config["skipped"] = set(site_data["skipped"])
        config["banned_tracks"] = set(site_data["banned"])
        # config["uids"] = site_data["clashes"]

        return config

    def update_game_ui(self):
        if self.session.stopped:
            self.handle_stop()
            return

        if self.session.track_limit:
            self.view.game_tab.update_track_progress(
                len(self.session.finished), self.session.track_limit
            )

        if self.session.stop_time:
            max_sec = int(
                (self.session.stop_time - self.session.start_time).total_seconds()
            )
            remaining = (self.session.stop_time - datetime.now()).total_seconds()
            curr_sec = int(max_sec - remaining)

            td = max(timedelta(0), self.session.stop_time - datetime.now())
            h, rem = divmod(td.seconds, 3600)
            m, s = divmod(rem, 60)
            txt = f"{h:02d}:{m:02d}:{s:02d}"
            self.view.game_tab.update_time_progress(txt, curr_sec, max_sec)

        if self.session.current:
            current = self.session.current
            targ = (
                current.wr
                if self.session.mode == "wr"
                else current.medals.get(self.session.mode)
            )
            info = f"{current.name} | {current.id}" + (
                f" | {targ / 1000}s" if targ else ""
            )
            self.view.game_tab.set_info(info)

        if self.model.config["force_window_size"]:
            self.view.setMinimumHeight(220)
            self.view.setMaximumHeight(220)
