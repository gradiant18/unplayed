import json
import random
import threading
import time
from datetime import datetime
from queue import Queue
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from helper import (
    get_autosaves,
    format_timedelta,
    get_tracks,
    get_uid,
    save_autosaves,
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

        self.start_time = datetime.now()
        self.stop_time = None
        self.time_limit = config["game_rules"].get("time_limit")  # timedelta
        self.track_limit = config["game_rules"].get("track_limit")
        self.mode = config["game_rules"].get("next_mode", "author")
        self.site = config["game_rules"].get("site", "TMNF-X")
        self.save_empty = config["game_rules"].get("save_empty")

        self.track_rules = config.get("track_rules")
        self.banned_tracks = (
            config["banned_tracks"][self.site]
            if config.get("banned_tracks") and config["banned_tracks"].get(self.site)
            else []
        )

        self.tracks = []
        self.finished = []
        self.data = get_autosaves(self)
        self.autosaves = self.data["autosaves"]

        self.next = Queue(maxsize=1)
        self.observer = None

        self.go_next = False
        self.fetching_done = False
        self.stop_session = False
        self.stopped = False

    def start(self):
        self.start_time = datetime.now()
        if self.time_limit.total_seconds() > 0:
            self.stop_time = self.start_time + self.time_limit

        threading.Thread(target=get_tracks(self), daemon=True).start()
        threading.Thread(target=self.main, daemon=True).start()

        while not self.tracks and not self.fetching_done:
            time.sleep(0.1)

        if not self.tracks:
            print("no tracks found matching your parameters")
            self.stop_session = True
            return

        if self.track_limit == 0:
            self.track_limit = len(self.tracks)

        threading.Thread(target=self.downloader, daemon=True).start()

        self.go_next = True
        self.observer = Observer()
        self.observer.schedule(Handler(self), path=self.autosave_dir, recursive=False)
        self.observer.start()

    def main(self):
        while not self.stop_session:
            if self.go_next:
                self.current = self.next.get()
                self.current.load(self.config["exe_path"])
                self.go_next = False
            time.sleep(0.1)

            if (
                self.track_limit
                and len(self.finished) >= 1
                and len(self.finished) >= self.track_limit
            ):
                print("\nTrack limit reached")
                self.stop_session = True
            if self.stop_time and datetime.now() > self.stop_time:
                print("\nTime limit reached")
                self.stop_session = True

            time.sleep(0.1)
        self.stop()

    def stop(self):
        print("\nstop just got called")
        self.stop_session = True
        if self.observer:
            self.observer.stop()
            self.observer.join()
        self.save()
        self.data["autosaves"] = self.autosaves
        save_autosaves(self.data)
        self.stopped = True

    def skip(self):
        self.go_next = True

    def reload(self):
        time.sleep(0.5)
        self.current.load(self.config["exe_path"])

    def downloader(self):
        while len(self.tracks) > 0 and not self.stop_session:
            track = random.choice(self.tracks)
            self.tracks.remove(track)

            if track.uid in self.autosaves:
                continue

            track.download(self.track_dir, self.site)
            self.next.put(track)

    def update_session(self, replay_path):
        replay_uid = get_uid(replay_path)
        if self.current.uid != replay_uid:
            return

        replay_time = self.current.update_medal(replay_path)
        if self.mode != "finished":
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
        self.data["autosaves"] = self.autosaves
        save_autosaves(self.data)
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
            return format_timedelta(self.stop_time - datetime.now())
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
