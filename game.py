import os
import pickle
import random
import re
import requests
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from exchange import values
from queue import Queue, Empty, Full
from track import Track
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler


class Handler(PatternMatchingEventHandler):
    def __init__(self, session):
        super().__init__(patterns=["*.gbx"], ignore_directories=True)
        self.session = session

    def on_modified(self, event) -> None:
        self.session.update_session(event.src_path)


class Game:
    def __init__(self, parent_window, config):
        self.update_config(config)
        self.parent_window = parent_window

        self.autosave_data = self.update_autosaves()
        self.autosaves = self.autosave_data["autosaves"]
        self.next = Queue(maxsize=1)
        self.observer = None

        self.tracks = []
        self.finished = {}

        self.go_next = False
        self.fetching_done = False
        self.stop_session = False
        self.stopped = False
        self.stop_time = None
        self.stop_reason = None

    def update_config(self, config) -> None:
        self.config = config
        self.set_dirs()

    def set_dirs(self) -> None:
        self.exe = self.config["exe_path"]
        self.track_dir = self.config["track_dir"]
        self.autosave_dir = os.path.join(
            self.config["track_dir"], "Replays", "Autosaves"
        )

    def start(self) -> None:
        self.next = Queue(maxsize=1)
        self.tracks = []
        self.finished = {}

        self.go_next = False
        self.fetching_done = False
        self.stop_session = False
        self.stopped = False
        self.stop_time = None
        self.stop_reason = None

        # set options
        self.start_time = datetime.now()
        self.time_limit = self.config["game_rules"].get("time_limit")
        self.track_limit = self.config["game_rules"].get("track_limit")
        self.mode = self.config["game_rules"].get("next_mode", "author")
        self.site = self.config["game_rules"].get("site", "TMNF-X")
        self.track_rules = self.config.get("track_rules")
        self.banned_tracks = (
            self.config["banned_tracks"][self.site]
            if self.config.get("banned_tracks")
            and self.config["banned_tracks"].get(self.site)
            else []
        )
        if self.time_limit.total_seconds() > 0:
            self.stop_time = self.start_time + self.time_limit

        threading.Thread(target=self.get_tracks, daemon=True).start()
        threading.Thread(target=self.main, daemon=True).start()

        while not self.tracks and not self.fetching_done:
            time.sleep(0.1)

        if not self.tracks:
            self.stop("No Tracks Found")
            return

        if self.track_limit == 0:
            self.track_limit = len(self.tracks)

        threading.Thread(target=self.downloader, daemon=True).start()

        self.go_next = True
        self.observer = Observer()
        self.observer.schedule(Handler(self), path=self.autosave_dir, recursive=False)
        self.observer.start()

    def main(self) -> None:
        while not self.stop_session:
            if (
                self.track_limit
                and len(self.finished) >= 1
                and len(self.finished) >= self.track_limit
            ):
                self.parent_window.log("[STOP] Track limit reached")
                self.stop("Track Limit Reached")
                break
            if self.stop_time and datetime.now() > self.stop_time:
                self.parent_window.log("[STOP] Time limit reached")
                self.stop("Time Limit Reached")
                break

            if self.go_next:
                try:
                    self.current = self.next.get(timeout=0.5)
                    if not self.config["no_launch"]:
                        self.current.load(self.config["exe_path"])
                    self.go_next = False
                except Empty:
                    pass
            time.sleep(0.01)

    def stop(self, reason="") -> None:
        self.stop_session = True
        if not self.stop_reason:
            self.stop_reason = reason
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None

        self.autosave_data["autosaves"] = self.autosaves
        self.parent_window.save_autosaves(self.autosave_data)
        self.stopped = True

    def skip(self) -> None:
        self.go_next = True

    def reload(self) -> None:
        time.sleep(0.5)
        self.current.load(self.config["exe_path"], self.config["debug"])

    def downloader(self) -> None:
        while len(self.tracks) > 0 and not self.stop_session:
            if self.config["sorted"] == 2:
                track = self.tracks.pop(0)
            else:
                track = random.choice(self.tracks)
                self.tracks.remove(track)

            if track.uid in self.autosaves:
                continue

            track.download(self.track_dir, self.site)
            while not self.stop_session:
                try:
                    self.next.put(track, timeout=0.5)
                    break
                except Full:
                    continue

    def get_uid(self, path):
        for _ in range(10):
            with open(path, "rb") as file:
                data = file.read(4096)
            if not data:
                time.sleep(0.001)
                continue
            if match := re.search(rb'uid="(\w*)"', data):
                return match.group(1).decode("utf-8")
            time.sleep(0.001)

    def update_session(self, replay_path) -> None:
        replay_uid = self.get_uid(replay_path)
        if not hasattr(self, "current") or self.current.uid != replay_uid:
            # different track played
            return
        if self.current.uid in self.autosaves:
            # already played (duplicate watchdog event probably)
            return

        replay_time = self.current.update_medal(replay_path)
        if self.mode != "finished":
            if self.mode == "wr":
                if self.current.wr and replay_time > self.current.wr:
                    return
            else:
                if replay_time > self.current.medals[self.mode]:
                    return

        self.autosaves.add(replay_uid)
        self.finished.update({self.current.uid: self.current.medal})
        self.parent_window.log(f"[FINISHED] {self.finished}")
        self.autosave_data["autosaves"] = self.autosaves
        self.parent_window.save_autosaves(self.autosave_data)
        if len(self.tracks) >= 0 and not self.stop_session:
            self.go_next = True

    def get_tracks_left(self) -> int | None:
        if self.track_limit:
            return self.track_limit - len(self.finished)
        return None

    def get_time_left(self) -> str | None:
        if self.stop_time:
            td = self.stop_time - datetime.now()
            hours, remainder = divmod(td.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            seconds += td.microseconds / 1e6
            return f"{hours:02d}:{minutes:02d}:{int(seconds):02d}"
        return None

    def get_current(self) -> Track | None:
        try:
            return self.current
        except AttributeError:
            return None

    def load_autosaves(self):
        path = os.path.join(self.config["app_dir"], "autosaves.bin")
        if not os.path.exists(path):
            return {"oldest": 0, "autosaves": None}
        with open(path, "rb") as file:
            data = pickle.load(file)
        if not data:
            data = {"oldest": 0, "autosaves": None}
        return data

    def update_autosaves(self):
        autosave_data = self.load_autosaves()
        files = []
        oldest = autosave_data.get("oldest", None)
        if not oldest:
            oldest = 0
            autosave_data["oldest"] = 0

        for entry in os.scandir(self.autosave_dir):
            if not entry.is_file():
                continue
            if (old := os.path.getmtime(entry)) <= autosave_data["oldest"]:
                continue

            files.append(entry.path)
            if old > oldest:
                oldest = old
        autosave_data["oldest"] = oldest

        with ThreadPoolExecutor(max_workers=10) as exe:
            autosaves = set(exe.map(self.get_uid, files))

        if not autosave_data.get("autosaves"):
            autosave_data["autosaves"] = autosaves
        else:
            autosave_data["autosaves"].update(autosaves)
        return autosave_data

    def get_tracks(self):
        api_url = f"https://{values[self.site]['url']}/api/tracks?"
        params = {
            "fields": "TrackId,TrackName,UId,AuthorTime,GoldTarget,SilverTarget,BronzeTarget,WRReplay.ReplayTime",
            "count": 1000,
        }

        for param, value in self.config.get("track_rules", {}).items():
            if value is not None:
                params[param] = value

        banned_set = set(self.banned_tracks)
        autosaves_set = self.autosaves
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

                    valid_tracks = [
                        Track(track)
                        for track in results
                        if track["UId"] not in autosaves_set
                        and track["TrackId"] not in banned_set
                    ]

                    if valid_tracks:
                        self.tracks.extend(valid_tracks)

                    current_last = results[-1]["TrackId"]

                    if not data.get("More", False):
                        break
                    self.parent_window.log(
                        f"[API] Getting more tracks, total so far = {len(self.tracks)}"
                    )

                except requests.exceptions.RequestException as e:
                    self.parent_window.log(f"[API] Error fetching tracks: {e}")
                    retries += 1
                    time.sleep(1)
                    continue

        self.fetching_done = True
        original_limit = self.config["game_rules"]["track_limit"]
        if not original_limit or self.track_limit > len(self.tracks):
            self.track_limit = len(self.tracks)
        self.detect_uid_clash()

    def detect_uid_clash(self):
        processed_uids = {}
        for track in self.tracks:
            if track.wr:
                processed_uids[track.uid] = track.track_id
                continue

            if track.uid in processed_uids:
                self.parent_window.log(
                    f"[UID] Clash for {track.track_id} and {processed_uids[track.uid]}"
                )
            else:
                processed_uids[track.uid] = track.track_id
        return processed_uids
