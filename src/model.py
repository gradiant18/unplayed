import copy
import csv
import json
import os
import platform
import random
import re
import subprocess
import threading
import time
import tomlkit
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from io import StringIO
from queue import Empty, Full, Queue

import requests
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

from common import (
    default_data,
    values,
    get_uid,
    log,
    AUTOSAVE_FILE,
    CONFIG_FILE,
    DATA_FILE,
    DOWNLOAD_DIR,
    LOG_FILE,
    PRESETS_DIR,
)


class ConfigModel:
    def __init__(self, no_launch: bool):
        open(LOG_FILE, "w").close()

        self.config = self.load_config()
        self.config["no_launch"] = no_launch
        self.data = self.load_data()
        self.update_autosave_data()

    def load_config(self) -> dict:
        """Loads config from file"""
        try:
            with open(CONFIG_FILE) as file:
                config = tomlkit.load(file)
        except Exception as e:
            log(f"Error loading {CONFIG_FILE}: {e}")
            config = tomlkit.loads(default_data)

        # TODO: verify config, load from default if wrong/missing

        return self._str_to_date(config)

    def save_config(self):
        """Saves config to file"""
        config = self._date_to_str(copy.deepcopy(self.config))
        if config.get("default_data"):
            del config["default_data"]

        try:
            with open(CONFIG_FILE, "w") as file:
                tomlkit.dump(config, file)
        except Exception as e:
            log(f"Error saving {CONFIG_FILE}: {e}")

    def load_data(self) -> dict:
        try:
            with open(DATA_FILE) as file:
                data = json.load(file)
        except Exception as e:
            log(f"Error loading {DATA_FILE}: {e}")
            data = {}
            for site in values["all"]["site"]:
                data[site] = {"skipped": [], "banned": []}
        return data

    def save_data(self):
        data = copy.deepcopy(self.data)
        for site in data:
            data[site]["skipped"] = list(set(data[site]["skipped"]))
            data[site]["banned"] = list(set(data[site]["banned"]))
        try:
            with open(DATA_FILE, "w") as file:
                json.dump(data, file, indent=2)
        except AttributeError as e:
            log(f"Error saving {DATA_FILE}: {e}")

    def get_presets(self) -> list[str]:
        # NOTE: verify presets?
        if not os.path.exists(PRESETS_DIR):
            return []
        entries = [entry for entry in os.scandir(PRESETS_DIR) if entry.is_file()]
        return [
            os.path.basename(file)[:-5]
            for file in entries
            if os.path.splitext(file)[1] == ".toml"
        ]

    def load_preset(self, name: str):
        """Loads preset from file"""
        try:
            with open(os.path.join(PRESETS_DIR, f"{name}.toml")) as file:
                config = tomlkit.load(file)
        except Exception as e:
            log(f"Error loading {os.path.join(PRESETS_DIR, f'{name}.toml')}: {e}")
            return

        # TODO: verify config, load from default if wrong/missing
        return self._str_to_date(config)

    def save_preset(self, name: str, preset: dict):
        """Saves preset to file"""
        preset = self._date_to_str(preset)
        try:
            os.makedirs(PRESETS_DIR, exist_ok=True)
            with open(os.path.join(PRESETS_DIR, f"{name}.toml"), "w") as file:
                tomlkit.dump(preset, file)
        except Exception as e:
            log(f"Error saving {os.path.join(PRESETS_DIR, f'{name}.toml')}: {e}")

    def delete_preset(self, name: str):
        try:
            os.remove(os.path.join(PRESETS_DIR, f"{name}.toml"))
        except Exception as e:
            log(f"Error deleting preset {name}: {e}")

    def _load_autosave_data(self) -> dict:
        """Loads autosave data from file"""
        autosave_data = {"oldest": 0, "autosaves": set()}
        if os.path.exists(AUTOSAVE_FILE):
            with open(AUTOSAVE_FILE) as file:
                data = file.read().splitlines()

            if len(data) < 2:
                return autosave_data

            try:
                oldest = float(data[0])
            except Exception:
                return autosave_data

            autosave_data["oldest"] = oldest
            autosave_data["autosaves"] = set(data[1:])
        return autosave_data

    def rescan_autosaves(self):
        autosave_data = self.update_autosave_data({"oldest": 0, "autosaves": set()})
        return len(autosave_data["autosaves"])

    def update_autosave_data(self, autosave_data=None) -> dict:
        """Returns updated autosave data"""
        if not autosave_data:
            autosave_data = self._load_autosave_data()
        autosave_dir = os.path.join(self.config["track_dir"], "Replays", "Autosaves")
        if not os.path.exists(autosave_dir):
            return autosave_data

        files = []
        oldest = autosave_data.get("oldest", 0)
        new_oldest = oldest

        for entry in os.scandir(autosave_dir):
            if not entry.is_file():
                continue
            old = os.path.getmtime(entry)
            if old > oldest:
                files.append(entry.path)
                if old > new_oldest:
                    new_oldest = old

        autosave_data["oldest"] = new_oldest
        with ThreadPoolExecutor(max_workers=10) as exe:
            new_uids = set(exe.map(get_uid, files))
        new_uids.discard(None)

        autosave_data["autosaves"].update(new_uids)
        return autosave_data

    def save_autosaves(self):
        """Saves autosave data to file"""
        autosave_data = self.update_autosave_data()
        try:
            with open(AUTOSAVE_FILE, "w") as file:
                file.write(f"{str(autosave_data['oldest'])}\n")
                file.write("\n".join(autosave_data["autosaves"]))
        except Exception as e:
            log(f"Error saving to {AUTOSAVE_FILE}: {e}")

    def delete_files(self):
        files = [
            "config.toml",
            "data.json",
            "autosaves.txt",
            "log.log",
        ]
        for file in files:
            if os.path.exists(file):
                os.remove(file)
        if os.path.exists(PRESETS_DIR):
            for file in os.listdir(PRESETS_DIR):
                os.remove(os.path.join(PRESETS_DIR, file))
            os.rmdir(PRESETS_DIR)

    def _date_to_str(self, config: dict) -> dict:
        gr = config["game_rules"]
        tr = config["track_rules"]
        time_limit = datetime.strftime(gr["time_limit"]["value"], "%H:%M:%S")
        at_min = datetime.strftime(tr["authortimemin"]["value"], "%H:%M:%S")
        at_max = datetime.strftime(tr["authortimemax"]["value"], "%H:%M:%S")
        after = datetime.strftime(tr["uploadedafter"]["value"], "%Y-%m-%dT%H:%M:%S")
        befo = datetime.strftime(tr["uploadedbefore"]["value"], "%Y-%m-%dT%H:%M:%S")

        gr["time_limit"]["value"] = time_limit
        tr["authortimemin"]["value"] = at_min
        tr["authortimemax"]["value"] = at_max
        tr["uploadedafter"]["value"] = after
        tr["uploadedbefore"]["value"] = befo
        return config

    def _str_to_date(self, config: dict) -> dict:
        gr = config["game_rules"]
        tr = config["track_rules"]
        time_limit = datetime.strptime(gr["time_limit"]["value"], "%H:%M:%S")
        at_min = datetime.strptime(tr["authortimemin"]["value"], "%H:%M:%S")
        at_max = datetime.strptime(tr["authortimemax"]["value"], "%H:%M:%S")
        after = datetime.strptime(tr["uploadedafter"]["value"], "%Y-%m-%dT%H:%M:%S")
        befo = datetime.strptime(tr["uploadedbefore"]["value"], "%Y-%m-%dT%H:%M:%S")

        gr["time_limit"]["value"] = time_limit
        tr["authortimemin"]["value"] = at_min
        tr["authortimemax"]["value"] = at_max
        tr["uploadedafter"]["value"] = after
        tr["uploadedbefore"]["value"] = befo
        return config


class Track:
    def __init__(self, track_data: dict):
        self.name = track_data["TrackName"]
        self.uid = track_data["UId"]
        self.id = track_data["TrackId"]
        self.path = ""
        self.medals = {
            "author": track_data["AuthorTime"],
            "gold": track_data["GoldTarget"],
            "silver": track_data["SilverTarget"],
            "bronze": track_data["BronzeTarget"],
        }
        self.medal = None
        self.wr = None
        wr = track_data.get("WRReplay", {})
        if wr:
            self.wr = wr.get("ReplayTime")

    def update_medal(self, replay_path: str) -> int | None:
        """Updates medal and returns replay time based on replay time from replay_path"""
        with open(replay_path, "rb") as file:
            data = file.read(4096)
        if not data:
            return None
        search = re.compile(rb'times best="(\d*)"')
        match = search.search(data)
        if not match:
            return None
        replay_time = int(match.group(1).decode("utf-8"))

        for medal, target in self.medals.items():
            if replay_time <= target:
                self.medal = medal
                break
        return replay_time

    def load(self, exe_path: str, id: int):
        """Loads track in game"""
        cmd = [exe_path, "/singleinst", "/useexedir", f"/file={self.path}"]
        if platform.system() != "Windows":
            cmd = ["protontricks-launch", "--appid", id] + cmd
        subprocess.run(cmd)

    def download(self, track_dir: str, site: str):
        """Downloads track from site to track_dir"""
        unplayed_path = os.path.join(track_dir, "Challenges", DOWNLOAD_DIR, site)
        os.makedirs(unplayed_path, exist_ok=True)

        self.path = os.path.join(unplayed_path, f"{self.id}.Challenge.gbx")
        if os.path.exists(self.path):
            return

        url = f"https://{values[site]['url']}/trackgbx/{self.id}"
        for _ in range(3):
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    with open(self.path, "wb") as f:
                        f.write(resp.content)
                    return
            except requests.RequestException:
                time.sleep(1)


class ReplayHandler(PatternMatchingEventHandler):
    def __init__(self, session):
        super().__init__(patterns=["*.gbx"], ignore_directories=True)
        self.session = session

    def on_modified(self, event):
        self.session.new_autosave(str(event.src_path))


class GameSession:
    def __init__(self, config_model: ConfigModel):
        self.config_model = config_model
        self.next = Queue(maxsize=1)
        self.observer = None
        self.skipped = set()
        self.tracks = []
        self.finished = {}

        self.current = None
        self.go_next = False
        self.fetched = False
        self.stop_session = False
        self.stopped = False
        self.stop_time = None
        self.stop_reason = None

        self.id = 0

    def start(self, session_config: dict):
        """Starts game session"""
        self.session_config = session_config
        self.autosaves = self.session_config["autosaves"]
        self.current = None
        self.next = Queue(maxsize=1)
        self.tracks = []
        self.finished = {}

        self.go_next = False
        self.fetched = False
        self.stop_session = False
        self.stopped = False
        self.stop_reason = None
        self.start_time = datetime.now()

        search = re.compile(r"\d+")
        id = search.findall(self.session_config["track_dir"])
        if id:
            self.id = id[-1]

        self.time_limit = self.session_config["game_rules"].get("time_limit")
        self.track_limit = self.session_config["game_rules"].get("track_limit", 0)
        self.mode = self.session_config["game_rules"].get("next_mode", "author")
        self.site = self.session_config["game_rules"].get("site", "TMNF-X")

        self.skipped = self.session_config["skipped"]
        self.banned_tracks = self.session_config["banned_tracks"]

        if self.time_limit and self.time_limit.total_seconds() > 0:
            self.stop_time = self.start_time + self.time_limit

        threading.Thread(target=self._daemon_main, daemon=True).start()
        threading.Thread(target=self._daemon_get_tracks, daemon=True).start()

        # Wait for tracks
        while (not self.fetched) and (not self.tracks):
            time.sleep(0.1)

        if not self.tracks:
            self.stop("No Tracks Found")
            return False

        if not self.track_limit:
            self.track_limit = len(self.tracks)

        threading.Thread(target=self._daemon_downloader, daemon=True).start()

        self.go_next = True
        self.observer = Observer()
        autosave_dir = os.path.join(
            self.session_config["track_dir"], "Replays", "Autosaves"
        )
        self.observer.schedule(ReplayHandler(self), path=autosave_dir, recursive=False)
        self.observer.start()
        return True

    def stop(self, reason=""):
        """Stops game session"""
        self.stop_session = True
        self.stop_reason = reason
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None

        self.stopped = True

    def skip(self):
        """Skips current track and goes to the next track"""
        if self.session_config.get("skip_skipped") and self.current:
            self.skipped.add(self.current.id)
        if self.track_limit == self.fetched:
            self.track_limit -= 1
            self.fetched -= 1
            if self.track_limit <= 0:
                self.stop("No Tracks Left")
        self.go_next = True

    def reload(self):
        """Reloads current track"""
        time.sleep(0.5)
        if self.current and not self.session_config.get("no_launch"):
            self.current.load(self.session_config["exe_path"], self.id)

    def new_autosave(self, replay_path: str):
        """Determines if replay is the right track and fast enough"""
        replay_uid = get_uid(replay_path)
        if not self.current or self.current.uid != replay_uid:
            return
        if self.current.uid in self.autosaves:
            return

        replay_time = self.current.update_medal(replay_path)
        if not replay_time:
            return

        if self.mode != "finished":
            if self.mode == "wr":
                if self.current.wr and replay_time > self.current.wr:
                    return
            else:
                if replay_time > self.current.medals.get(self.mode, 0):
                    return

        self.autosaves.add(replay_uid)
        self.finished[self.current.uid] = self.current.medal
        log(f"[FINISHED] {self.finished}")

        if not self.stop_session:
            self.go_next = True

    def _daemon_main(self):
        """Loads tracks and checks for stops"""
        while not self.stop_session:
            if self.track_limit and len(self.finished) >= self.track_limit:
                log("[STOP] Track limit reached")
                self.stop("Track Limit Reached")
                break
            if self.stop_time and datetime.now() > self.stop_time:
                log("[STOP] Time limit reached")
                self.stop("Time Limit Reached")
                break

            if self.go_next:
                try:
                    self.current = self.next.get(timeout=0.5)
                    if not self.session_config.get("no_launch"):
                        self.current.load(self.session_config["exe_path"], self.id)
                    self.go_next = False
                except Empty:
                    pass
            time.sleep(0.01)

    def _daemon_get_tracks(self):
        """Gets list of tracks that match track paramaters"""
        api_url = f"https://{values[self.site]['url']}/api/tracks?"
        params = {
            "fields": "TrackId,TrackName,UId,AuthorTime,GoldTarget,SilverTarget,BronzeTarget,WRReplay.ReplayTime",
            "count": 1000,
        }

        for param, value in self.session_config.get("track_rules", {}).items():
            if value is not None:
                params[param] = value

        current_last = 0
        with requests.Session() as http:
            retries = 0
            while not self.stop_session and retries < 5:
                try:
                    params["after"] = current_last
                    response = http.get(api_url, params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    results = data.get("Results", [])
                    if not results:
                        break

                    valid_tracks = []
                    for t in results:
                        if (
                            t["UId"] in self.autosaves
                            or t["TrackId"] in self.banned_tracks
                        ):
                            continue
                        if (
                            self.session_config.get("skip_skipped")
                            and t["TrackId"] in self.skipped
                        ):
                            continue
                        valid_tracks.append(Track(t))

                    if valid_tracks:
                        self.tracks.extend(valid_tracks)

                    current_last = results[-1]["TrackId"]
                    if not data.get("More", False):
                        break
                    log(f"[API] Tracks so far: {len(self.tracks)}")
                    time.sleep(3)

                except requests.exceptions.RequestException as e:
                    log(f"[API] Error: {e}")
                    retries += 1
                    time.sleep(1)

        self.fetched = len(self.tracks) if self.tracks else True

    def _daemon_downloader(self):
        """Gets and downloads tracks for playing queue"""
        while len(self.tracks) > 0 and not self.stop_session:
            track = (
                self.tracks.pop(0)
                if self.session_config.get("sorted")
                else self.tracks.pop(random.randrange(len(self.tracks)))
            )
            if track.uid in self.autosaves:
                continue
            track.download(self.session_config["track_dir"], self.site)
            try:
                self.next.put(track, timeout=0.5)
            except Full:
                pass


class BannedTracksFetcher:
    @staticmethod
    def get_cheated_ids() -> dict:
        """Returns dict of cheated track ids from spreadsheet"""
        sheet_id = "1fqmzFGPIFBlJuxlwnPJSh1nCTTxqWXtHtvP5OUxE4Ow"
        page_ids = {
            "TMUF-X": 2132753700,
            "TMNF-X": 605781157,
            "TMO-X": 1739598690,
            "TMS-X": 1438334892,
            "TMN-X": 38022687,
        }
        cheated_ids = {}

        def fetch_sheet(session, name, gid):
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&tq&gid={gid}"
            resp = session.get(url)
            resp.raise_for_status()
            ids = []
            for row in csv.reader(StringIO(resp.text)):
                val = row[1].strip() if len(row) > 1 else ""
                if val and val != "TrackID":
                    try:
                        ids.append(int(val))
                    except ValueError:
                        pass
            return name, ids

        with requests.Session() as session:
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(fetch_sheet, session, name, gid)
                    for name, gid in page_ids.items()
                ]
                for future in as_completed(futures):
                    page_name, ids = future.result()
                    cheated_ids[page_name] = ids
        return cheated_ids
