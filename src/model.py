import copy
import csv
import os
import pickle
import platform
import random
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from io import StringIO
from queue import Empty, Full, Queue

import requests
import semver
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

from common import default_data, values


class ConfigModel:
    def __init__(self, version: str, save_here: str, no_launch: str):
        self.version = version
        self.no_launch = no_launch
        self.data = copy.deepcopy(default_data)

        if platform.system() == "Windows":
            self.app_dir = os.path.join(str(os.getenv("APPDATA")), "unplayed")
        elif platform.system() == "Linux":
            self.app_dir = os.path.expanduser("~/.unplayed")
        if save_here:
            self.app_dir = "unplayed"

        if not os.path.exists(self.app_dir):
            os.mkdir(self.app_dir)

        log_path = os.path.join(self.app_dir, "log.log")
        open(log_path, "w").close()

        # PERF: start up performance?
        # self.update_autosave_data()
        self.load_data()
        self.test_data()
        self.data["app_dir"] = self.app_dir
        self.data["no_launch"] = self.no_launch

    def load_skipped(self) -> set:
        """Loads skipped tracks from file"""
        site = self.data["game_rules"].get("site")
        path = os.path.join(self.app_dir, f"{site}_skipped.txt")
        if not os.path.exists(path):
            print(f"{path} doesn't exists, no skipped tracks")
            return set()
        with open(path) as file:
            data = file.read()
        return {int(x.group(0)) for x in re.finditer(r"\d+", data)}

    def save_skipped(self, site: str, skipped: set):
        """Saves skipped tracks to file"""
        path = os.path.join(self.app_dir, f"{site}_skipped.txt")
        with open(path, "w") as file:
            for track_id in skipped:
                file.write(f"https://{values[site]['url']}/trackshow/{track_id}\n")

    def _get_uid(self, path: str) -> str | None:
        """Gets UID for path"""
        for _ in range(10):
            try:
                with open(path, "rb") as file:
                    data = file.read(4096)
                if data and (match := re.search(rb'uid="(\w*)"', data)):
                    return match.group(1).decode("utf-8")
            except Exception:
                pass
            time.sleep(0.001)
        return None

    def _load_autosave_data(self) -> dict:
        """Loads autosave data from file"""
        autosave_data = {"oldest": 0, "autosaves": set()}
        path = os.path.join(self.app_dir, "autosaves.bin")
        if os.path.exists(path):
            with open(path, "rb") as file:
                data = pickle.load(file)
                if data:
                    autosave_data = data
        return autosave_data

    def rescan_autosaves(self):
        autosave_data = self.update_autosave_data({"oldest": 0, "autosaves": set()})
        return len(autosave_data["autosaves"])

    def update_autosave_data(self, autosave_data=None) -> dict:
        """Returns updated autosave data"""
        if not autosave_data:
            autosave_data = self._load_autosave_data()
        autosave_dir = os.path.join(self.data["track_dir"], "Replays", "Autosaves")
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
            new_uids = set(exe.map(self._get_uid, files))
        new_uids.discard(None)

        autosave_data["autosaves"].update(new_uids)
        return autosave_data

    def save_autosaves(self):
        """Saves autosave data to file"""
        path = os.path.join(self.app_dir, "autosaves.bin")
        autosave_data = self.update_autosave_data()
        with open(path, "wb") as file:
            pickle.dump(autosave_data, file)

    def load_data(self):
        """Loads data from file"""
        data_path = os.path.join(self.app_dir, "data.bin")
        if os.path.exists(data_path):
            try:
                with open(data_path, "rb") as file:
                    saved_data = pickle.load(file)
                if (
                    semver.Version.parse(self.version).major
                    > semver.Version.parse(saved_data.get("version", "1.2.0")).major
                ):
                    self.log("Version mismatch, falling back to default data")
                else:
                    self.data = saved_data
            except Exception as e:
                self.log(f"Error loading data: {e}")

    def save_data(self):
        """Saves data to file"""
        if not os.path.exists(self.app_dir):
            os.mkdir(self.app_dir)
        data_path = os.path.join(self.app_dir, "data.bin")
        with open(data_path, "wb") as file:
            pickle.dump(self.data, file)

    def test_data(self):
        """Verifies data paths"""
        # TODO: add tests to check file paths

        # exe_path

        # track_dir
        autosave_dir = os.path.join(self.data["track_dir"], "Replays", "Autosaves")
        if not os.path.exists(autosave_dir):
            return False

        # app_dir

    def log(self, msg: str):
        """Saves msg to log file"""
        log_path = os.path.join(self.app_dir, "log.log")
        with open(log_path, "a") as file:
            file.write(f"[{time.time()}] {msg}\n")


class Track:
    def __init__(self, track_data: dict):
        self.name = track_data["TrackName"]
        self.uid = track_data["UId"]
        self.track_id = track_data["TrackId"]
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
        """Updates and returns medal based on replay time from replay_path"""
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
        print(
            exe_path,
            id,
            self.path,
        )
        cmd = [exe_path, "/singleinst", "/useexedir", f"/file={self.path}"]
        if platform.system() != "Windows":
            cmd = ["protontricks-launch", "--appid", id] + cmd
        subprocess.run(cmd)

    def download(self, track_dir: str, site: str):
        """Downloads track from site to track_dir"""
        unplayed_path = os.path.join(track_dir, "Challenges", "Unplayed", site)
        os.makedirs(unplayed_path, exist_ok=True)

        self.path = os.path.join(unplayed_path, f"{self.track_id}.Challenge.gbx")
        if os.path.exists(self.path):
            return

        url = f"https://{values[site]['url']}/trackgbx/{self.track_id}"
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
        self.fetching_done = False
        self.stop_session = False
        self.stopped = False
        self.stop_time = None
        self.stop_reason = None

        self.id = 0

    def start(self, session_config: dict):
        """Starts game session"""
        self.session_config = session_config
        self.autosaves = self.session_config["autosaves"]
        self.next = Queue(maxsize=1)
        self.tracks = []
        self.finished = {}
        self.skipped = self.session_config["skipped"]

        self.go_next = False
        self.fetching_done = False
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
        banned = self.session_config.get("banned_tracks", {}).get(self.site, [])
        self.banned_tracks = set(banned)

        if self.time_limit and self.time_limit.total_seconds() > 0:
            self.stop_time = self.start_time + self.time_limit

        threading.Thread(target=self._daemon_main, daemon=True).start()
        threading.Thread(target=self._daemon_get_tracks, daemon=True).start()

        # Wait for tracks
        while not self.tracks and not self.fetching_done:
            time.sleep(0.1)

        if not self.tracks:
            self.stop("No Tracks Found")
            return

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
            self.skipped.add(self.current.track_id)
        self.go_next = True

    def reload(self):
        """Reloads current track"""
        time.sleep(0.5)
        if self.current:
            self.current.load(self.session_config["exe_path"], self.id)

    def new_autosave(self, replay_path: str):
        """Determines if replay is the right track and fast enough"""
        replay_uid = self._get_uid(replay_path)
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
        self.config_model.log(f"[FINISHED] {self.finished}")

        if not self.stop_session:
            self.go_next = True

    def _daemon_main(self):
        """Loads tracks and checks for stops"""
        while not self.stop_session:
            if self.track_limit and len(self.finished) >= self.track_limit:
                self.config_model.log("[STOP] Track limit reached")
                self.stop("Track Limit Reached")
                break
            if self.stop_time and datetime.now() > self.stop_time:
                self.config_model.log("[STOP] Time limit reached")
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
                    self.config_model.log(f"[API] Tracks so far: {len(self.tracks)}")

                except requests.exceptions.RequestException as e:
                    self.config_model.log(f"[API] Error: {e}")
                    retries += 1
                    time.sleep(1)

        self.fetching_done = True

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
            while not self.stop_session:
                try:
                    self.next.put(track, timeout=0.5)
                    break
                except Full:
                    pass

    def _get_uid(self, path: str) -> str | None:
        """Gets UID for path"""
        for _ in range(10):
            try:
                with open(path, "rb") as file:
                    data = file.read(4096)
                if data and (match := re.search(rb'uid="(\w*)"', data)):
                    return match.group(1).decode("utf-8")
            except Exception:
                pass
            time.sleep(0.001)
        return None


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
                if len(row) > 1 and row[1].strip() and row[1].strip() != "TrackID":
                    try:
                        ids.append(int(row[1].strip()))
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
