import copy
import os
import re
import shutil
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

        if self.model.data.get("default_data"):
            self.model.data["default_data"] = False
            self.handle_preset_changed("Default")
            self.save_model()

        if self.model.data.get("auto_update"):
            self.handle_banned_update()

        self.connect_signals()
        self.refresh_ui_from_model()

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
        self.view.banned_tab.export_requested.connect(self.handle_banned_export)
        self.view.banned_tab.import_requested.connect(self.handle_banned_import)

        self.view.options_tab.save_requested.connect(self.save_model)
        self.view.options_tab.start_requested.connect(self.handle_start_game)
        self.view.options_tab.preset_changed.connect(self.handle_preset_changed)
        self.view.options_tab.save_preset_requested.connect(self.handle_save_preset)
        self.view.options_tab.new_preset_requested.connect(self.handle_new_preset)
        self.view.options_tab.delete_preset_requested.connect(self.handle_delete_preset)
        self.view.options_tab.game_rule_changed.connect(self.handle_game_rule_changed)
        self.view.options_tab.track_rule_changed.connect(self.handle_track_rule_changed)

        self.view.game_tab.skip_requested.connect(lambda: self.session.skip())
        self.view.game_tab.reload_requested.connect(lambda: self.session.reload())
        self.view.game_tab.stop_requested.connect(lambda: self.session.stop())

    def refresh_ui_from_model(self):
        # NOTE: on startup, if options are different than last loaded preset,
        # maybe set preset text to ---
        if self.model.data["force_window_size"]:
            self.view.setMinimumSize(self.view.minimumSizeHint())
            self.view.setMaximumSize(self.view.minimumSizeHint())

        self.view.settings_tab.populate(self.model.data)
        self.view.banned_tab.populate(self.model.data.get("banned_tracks", {}))

        self.view.options_tab.populate_presets(
            list(self.model.data["presets"].keys()), self.model.data["preset"]
        )

        site = self.model.data["game_rules"]["site"]
        self.view.options_tab.update_comboboxes(site)
        self.view.options_tab.populate_rules(
            self.model.data["game_rules"], self.model.data["track_rules"]
        )

    def save_model(self):
        self.view.set_status("Saving...")
        self.model.save_data()
        self.model.save_autosaves()
        self.view.set_status("Saved!", 3000)

    # TODO: change window size, so no restart required
    def handle_settings_changed(self, new_settings):
        self.model.data.update(new_settings)

    def handle_rescan_autosaves(self):
        self.view.set_status("Scanning...")
        total = self.model.rescan_autosaves()
        self.view.set_status(f"Found {total} replays!", 3000)

    def handle_delete_data(self):
        if self.model.app_dir:
            shutil.rmtree(self.model.app_dir, ignore_errors=True)
            self.view.show_info(
                "Deleted", "Data directory removed. Restart application."
            )

    def handle_banned_clear(self):
        # NOTE: maybe have popup with warning?
        self.model.data["banned_tracks"] = {
            site: set() for site in values["all"]["site"]
        }
        self.view.banned_tab.populate(self.model.data["banned_tracks"])

    def handle_banned_update(self):
        self.view.set_status("Updating...")

        self.banned_worker = BannedTracksWorker()
        self.banned_worker.finished_fetch.connect(self._on_banned_update_success)
        self.banned_worker.error_fetch.connect(self._on_banned_update_error)
        self.banned_worker.start()

    def _on_banned_update_success(self, data: dict):
        self.model.data["banned_tracks"] = {
            site: set(ids) for site, ids in data.items()
        }
        self.view.banned_tab.populate(self.model.data["banned_tracks"])
        self.save_model()
        self.view.set_status("Updated!", 3000)

    def _on_banned_update_error(self, err_msg: str):
        self.view.set_status("Update Failed!", 3000)
        self.view.show_error(
            "Network Error", f"Failed to fetch banned tracks:\n{err_msg}"
        )

    def handle_banned_modified(self, site: str, ids: set):
        self.model.data["banned_tracks"][site] = ids

    def handle_banned_export(self, path: str):
        pattern = re.compile(r"\.(txt|ya?ml)$", re.IGNORECASE)
        match = re.match(pattern, path)
        if not match:
            path += ".yml"

        with open(path, "w") as file:
            for site, ids in self.model.data["banned_tracks"].items():
                file.write(f"{site}:\n")
                for id in ids:
                    file.write(f" - {id}\n")

    def handle_banned_import(self, path: str):
        with open(path, "r") as f:
            data = f.read()
        pattern = re.compile(r"\b(TMUF|TMNF|TMO|TMS|TMN)(?:-X)?\b", re.IGNORECASE)
        matches = list(pattern.finditer(data))
        total = 0
        for i, match in enumerate(matches):
            site = f"{match.group(1).upper()}-X"
            end = matches[i + 1].start() if i + 1 < len(matches) else len(data)
            ids = {int(id) for id in re.findall(r"\d+", data[match.end() : end])}
            total += len(ids)
            self.model.data["banned_tracks"][site].update(ids)
        self.view.banned_tab.populate(self.model.data["banned_tracks"])
        self.view.set_status(f"Imported {total} ids!", 5000)

    def handle_preset_changed(self, name: str):
        if name and name in self.model.data["presets"]:
            self.model.data["preset"] = name
            preset = self.model.data["presets"][name]
            self.model.data["game_rules"] = copy.deepcopy(preset["game_rules"])
            self.model.data["track_rules"] = copy.deepcopy(preset["track_rules"])
            self.refresh_ui_from_model()

    def handle_save_preset(self):
        name = self.model.data["preset"]
        self.model.data["presets"][name]["game_rules"] = copy.deepcopy(
            self.model.data["game_rules"]
        )
        self.model.data["presets"][name]["track_rules"] = copy.deepcopy(
            self.model.data["track_rules"]
        )
        self.save_model()

    def handle_new_preset(self, name: str):
        if name in self.model.data["presets"]:
            rename = Dialogs.ask_for_rename(self.view, name)
            if not rename:
                return
        self.model.data["presets"][name] = {
            "game_rules": copy.deepcopy(self.model.data["game_rules"]),
            "track_rules": copy.deepcopy(self.model.data["track_rules"]),
        }
        self.model.data["preset"] = name
        self.view.options_tab.populate_presets(
            list(self.model.data["presets"].keys()), name
        )
        self.save_model()

    # NOTE: change to first preset or keep options?
    # doesn't preserve current options right now
    def handle_delete_preset(self):
        name = self.model.data["preset"]
        if len(self.model.data["presets"]) <= 1:
            return
        del self.model.data["presets"][name]
        new_name = list(self.model.data["presets"].keys())[0]
        self.handle_preset_changed(new_name)
        self.save_model()

    def handle_game_rule_changed(self, key, val):
        gr = self.model.data["game_rules"]
        if key == "next_mode":
            gr["next_mode"] = val
        elif key == "site":
            gr["site"] = val
            self.view.options_tab.update_comboboxes(val)
        elif key == "track_limit_state":
            gr["track_limit"]["state"] = 2 if val else 0
        elif key == "track_limit_val":
            gr["track_limit"]["value"] = val
        elif key == "time_limit_state":
            gr["time_limit"]["state"] = 2 if val else 0
        elif key == "time_limit_val":
            gr["time_limit"]["value"] = timedelta(
                hours=val.hour(), minutes=val.minute(), seconds=val.second()
            )

    def handle_track_rule_changed(self, key, val):
        track_rule = self.model.data["track_rules"]
        base_key = key.replace("_state", "").replace("_val", "")
        if base_key not in track_rule:
            return

        if key.endswith("_state"):
            track_rule[base_key]["state"] = 2 if val else 0
        else:
            if "time" in base_key:
                track_rule[base_key]["value"] = val.msecsSinceStartOfDay()
            elif "uploaded" in base_key:
                track_rule[base_key]["value"] = datetime.fromtimestamp(
                    val.toSecsSinceEpoch()
                )
            else:
                site = self.model.data["game_rules"]["site"]
                opts = values.get(site, values["all"]).get(
                    base_key, values["all"].get(base_key, [])
                )
                opts = [x for x in opts if x != ""]
                track_rule[base_key]["text"] = val
                track_rule[base_key]["value"] = opts.index(val) if val in opts else 0

    def handle_find_exe(self):
        exe_paths = self._find_executables()
        if not exe_paths:
            path = Dialogs.ask_for_exe(self.view)
        else:
            dialog = FindPath("exe_path", exe_paths)
            if not dialog.exec():
                return False  # window closed
            if not dialog.path:
                return False  # cancel
            path = dialog.path
        self.model.data["exe_path"] = path
        self.view.settings_tab.populate(self.model.data)
        return True

    def handle_find_track(self):
        track_paths = self._find_track_folders()
        if not track_paths:
            path = Dialogs.ask_for_track_dir(self.view)
        else:
            dialog = FindPath("track_dir", track_paths)
            if not dialog.exec():
                return False
            if not dialog.path:
                return False
            path = dialog.path
        self.model.data["track_dir"] = path
        self.view.settings_tab.populate(self.model.data)
        return True

    def _find_executables(self):
        steam = os.path.join("Steam", "steamapps", "common")
        tmuf = "TrackMania United"
        tmnf = "TrackMania Nations Forever"
        exe = "TmForever.exe"

        steam_paths = {
            os.path.join(str(os.getenv("ProgramFiles")), steam, tmuf, exe): "TMUF",
            os.path.join(str(os.getenv("ProgramFiles")), steam, tmnf, exe): "TMNF",
            os.path.join(str(os.getenv("ProgramFiles(x86)")), steam, tmuf, exe): "TMUF",
            os.path.join(str(os.getenv("ProgramFiles(x86)")), steam, tmnf, exe): "TMNF",
            os.path.join(str(os.getenv("ProgramFiles(x86)")), steam, tmuf, exe): "TMUF",
            os.path.expanduser(
                f"~/.local/share/Steam/steamapps/common/{tmuf}/{exe}"
            ): "TMUF",
            os.path.expanduser(
                f"~/.local/share/Steam/steamapps/common/{tmnf}/{exe}"
            ): "TMNF",
        }

        paths = {}
        for path, name in steam_paths.items():
            if os.path.exists(path):
                paths.update({path: name})
        return paths

    def _find_track_folders(self):
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

        paths = {}
        for path, name in dir_paths.items():
            if os.path.exists(path):
                paths.update({path: name})
        return paths

    def generate_session_config(self):
        if not os.path.exists(self.model.data.get("exe_path", "")):
            if not self.handle_find_exe():
                return None

        while not os.path.exists(self.model.data.get("track_dir", "")):
            if not self.handle_find_track():
                return None

        config = copy.deepcopy(self.model.data)
        game_rule = config["game_rules"]
        game_rule["track_limit"] = (
            game_rule["track_limit"]["value"]
            if game_rule["track_limit"]["state"]
            else None
        )
        game_rule["time_limit"] = (
            game_rule["time_limit"]["value"]
            if game_rule["time_limit"]["state"]
            else None
        )

        for rule, rule_dict in config["track_rules"].items():
            config["track_rules"][rule] = (
                rule_dict["value"] if rule_dict["state"] else None
            )

        config["sorted"] = self.model.data["track_rules"]["order1"]["state"]
        autosave_data = self.model.update_autosave_data()
        config["autosaves"] = autosave_data.get("autosaves", set())
        config["skipped"] = self.model.load_skipped()
        return config

    def handle_start_game(self):
        session_config = self.generate_session_config()
        if not session_config:
            self.view.set_status("Canceled", 3000)
            return

        self.view.game_tab.set_time_visible(
            bool(session_config["game_rules"]["time_limit"])
        )

        self.session.start(session_config)
        self.progress_timer.start(100)
        self.view.show_game()
        if self.model.data["force_window_size"]:
            self.view.setMinimumHeight(220)
            self.view.setMaximumHeight(220)

    def handle_stop(self):
        self.progress_timer.stop()
        self.save_model()
        self.model.save_skipped(self.session.site, self.session.skipped)
        if self.session.stop_reason:
            self.view.set_status(self.session.stop_reason, 5000)
        self.view.show_config()
        if self.model.data["force_window_size"]:
            self.view.setMinimumSize(self.view.minimumSizeHint())
            self.view.setMaximumSize(self.view.minimumSizeHint())

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
            info = f"{current.name} | {current.track_id}" + (
                f" | {targ / 1000}s" if targ else ""
            )
            self.view.game_tab.set_info(info)
