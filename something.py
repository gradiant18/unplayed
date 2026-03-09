import threading
import json
import random
import time
import requests
from queue import Queue
import yaml
from pygbx2 import get_uid, get_replay_time
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from tmx import Track
from datetime import datetime
from helper import (
    _get_autosaves,
    _get_site_url,
    _calculate_stop_time,
    _format_timedelta,
)


class Handler(PatternMatchingEventHandler):
    def __init__(self, session):
        super().__init__(patterns=["*.gbx"], ignore_directories=True)
        self.session = session

    def on_modified(self, event):
        self.session.update_session(event.src_path)


class Game:
    def __init__(self, config):
        self.config = config
        self.exe = config["exe_path"]
        self.track_dir = config["track_dir"]
        self.autosave_dir = f"{self.track_dir}/Replays/Autosaves"

        self.time_limit = config.get("time_limit")
        self.track_limit = None
        self.mode = config.get("next_mode", "author")
        self.site = config.get("site", "TMNF-X")
        self.save_empty = config.get("save_empty")

        self.track_rules = config.get("track_rules")
        self.banned_tracks = (
            config["banned_tracks"][self.site]
            if config.get("banned_tracks") and config["banned_tracks"].get(self.site)
            else []
        )

        self.tracks = []
        self.finished = []
        self.autosaves = set()
        self.next = Queue(maxsize=1)
        self.observer = None

        self.go_next = False
        self.fetching_done = False
        self.stop_session = False

    def start(self):
        self.autosaves = _get_autosaves(self)
        self.start_time = datetime.now()
        self.stop_time = _calculate_stop_time(self)

        threading.Thread(target=self._get_tracks, daemon=True).start()
        threading.Thread(target=self._limits, daemon=True).start()

        # print("Waiting for first batch of tracks...")
        while not self.tracks and not self.fetching_done:
            time.sleep(0.1)

        if not self.tracks:
            print("No tracks found matching your parameters!")
            self.stop_session = True
            return

        if self.config.get("track_limit") == "all":
            self.track_limit = len(self.tracks)
        else:
            self.track_limit = config.get("track_limit")

        threading.Thread(target=self._downloader, daemon=True).start()

        self.go_next = True
        self.observer = Observer()
        self.observer.schedule(Handler(self), path=self.autosave_dir, recursive=False)
        self.observer.start()
        threading.Thread(target=self._main, daemon=True).start()

    def stop(self):
        self.stop_session = True

    def skip(self):
        session.go_next = True

    def reload(self):
        time.sleep(0.5)
        session.current.load(self.config["exe_path"])

    # TODO: clean up function
    def _limits(self):
        while True:
            if self.stop_session:
                if self.observer:
                    self.observer.stop()
                    self.observer.join()
                return

            if (
                self.track_limit
                and len(self.finished) >= 1
                and len(self.finished) >= self.track_limit
            ):
                print("\nTrack limit reached")
                self.stop_session = True
                continue
            if self.stop_time and datetime.now() > self.stop_time:
                print("\nTime limit reached")
                self.stop_session = True
                continue

            time.sleep(0.1)

    def _main(self):
        while not self.stop_session:
            if self.go_next:
                self.current = self.next.get()
                self.current.load(self.config["exe_path"])
                self.go_next = False
            time.sleep(0.1)

    def _get_tracks(self):
        api_url = f"https://{_get_site_url(self)}/api/tracks?"
        params = {
            "fields": "TrackId,TrackName,UId,AuthorTime,GoldTarget,SilverTarget,BronzeTarget",
            "count": 1000,
        }
        for param, value in self.config["track_rules"].items():
            if value is not None:
                params[param] = value

        current_last = 0
        while not self.stop_session:
            try:
                params["after"] = current_last
                response = requests.get(api_url, params=params, timeout=10)
                data = response.json()
                results = data.get("Results", [])

                if not results:
                    break

                for track in results:
                    if track["UId"] in self.autosaves:
                        continue
                    if track["TrackId"] in self.banned_tracks:
                        continue
                    self.tracks.append(Track(track))
                current_last = results[-1]["TrackId"]

                if not data.get("More", False):
                    break

            except requests.exceptions.RequestException as e:
                print(e)
                time.sleep(1)
                continue

        self.fetching_done = True
        if self.config.get("track_limit") == "all":
            self.track_limit = len(self.tracks)
        print(f"\nFound a total of {len(self.tracks)} tracks.")

    def _downloader(self):
        while len(self.tracks) > 0 and not self.stop_session:
            track = random.choice(self.tracks)
            self.tracks.remove(track)

            track.download(self.track_dir, self.site)
            self.next.put(track)
            time.sleep(0.5)

    def update_session(self, replay_path):
        replay_uid = get_uid(replay_path)
        if self.current.uid != replay_uid:
            return

        self.current.update_medal(replay_path)

        if self.mode != "finished":
            replay_time = get_replay_time(replay_path)
            if not replay_time:
                raise AttributeError("Couldn't get replay_time")
            if replay_time > self.current.medals[self.mode]:
                return

        self.autosaves.add(replay_uid)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.current.time = timestamp

        if len(self.finished) == 0:
            self.finished.append(self.current.__dict__)
        else:
            added = False
            for track in self.finished:
                if self.current.uid == track["uid"]:
                    added = True
                    break
            if not added:
                self.finished.append(self.current.__dict__)

        self.save()
        if len(self.tracks) >= 0 and not self.stop_session:
            self.go_next = True

    def save(self):
        if len(self.finished) == 0 and not self.config.get("save_empty"):
            return
        timestamp = self.start_time.strftime("%Y-%m-%d_%H-%M-%S")
        with open(f"sessions/{timestamp}.json", "w") as file:
            json.dump(self.finished, file, indent=2)

    def get_tracks_left(self):
        if self.track_limit:
            return self.track_limit - len(self.finished)
        return None

    def get_time_left(self):
        if self.stop_time:
            return _format_timedelta(self, self.stop_time - datetime.now())
        return None

    def get_current(self):
        try:
            return self.current
        except AttributeError:
            return None

    def __str__(self):
        if not self.get_current():
            return ""

        tracks_played = f"Tracks Played: {len(self.finished)} | "

        tracks_left = ""
        if self.track_limit:
            tracks_left = f"Tracks Left: {self.get_tracks_left()} | "

        time_left = ""
        if self.stop_time:
            time_left = f"Time Left: {self.get_time_left()} | "

        current_medal = ""
        if self.mode != "finished" or "bronze":
            medal = "None"
            if self.current.medal:
                medal = self.current.medal.capitalize()
            current_medal = f"Current Medal: {medal} | "

        current_track = f"Current Track: {self.current.name}"
        return f"{tracks_played}{tracks_left}{time_left}{current_medal}{current_track}"


if __name__ == "__main__":
    with open("config.yaml") as file:
        config = yaml.safe_load(file)
    session = Game(config)
    session.start()
    while not session.stop_session:
        try:
            print(session, end="\r")
            time.sleep(0.1)
        except KeyboardInterrupt:
            choice = input("\na) Skip b) Reload c) Quit >> ")
            if choice == "a":
                session.skip()
            elif choice == "b":
                session.reload()
            elif choice == "c":
                session.stop()
    print("session stopped")
