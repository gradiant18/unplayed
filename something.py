import threading
import random
import time
import requests
from queue import Queue
import os
from multiprocessing import Pool
import yaml
from pygbx2 import get_uid, get_replay_time
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from tmx import Track
from datetime import datetime, timedelta


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
        self.autosaves = self._get_autosaves()
        self.stop_time = self._calculate_stop_time()

        threading.Thread(target=self._get_tracks, daemon=True).start()
        threading.Thread(target=self._limits, daemon=True).start()

        print("Waiting for first batch of tracks...")
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
        self._main()

    def _limits(self):
        while True:
            if self.stop_session:
                print("should be stoppd")
                if self.observer:
                    self.observer.stop()
                    self.observer.join()
                return

            if (
                self.track_limit
                and len(self.finished) >= 1
                and len(self.finished) >= self.track_limit
            ):
                print("Track limit reached")
                self.stop_session = True
                continue
            if self.stop_time and datetime.now() > self.stop_time:
                print("Time limit reached")
                self.stop_session = True
                continue

            time.sleep(0.1)

    def _calculate_stop_time(self):
        limit = self.time_limit
        if not limit:
            return None

        if isinstance(limit, int):
            return datetime.now() + timedelta(seconds=limit)
        dt = timedelta(
            hours=int(limit[:2]), minutes=int(limit[3:5]), seconds=int(limit[6:])
        )
        return datetime.now() + dt

    def _main(self):
        while not self.stop_session:
            try:
                if self.go_next:
                    self.current = self.next.get()
                    print(f">>> [Player] Now Playing: {self.current.name}")
                    print(f"track limit: {self.track_limit}")
                    self.current.load(self.config["exe_path"])
                    self.go_next = False
                time.sleep(0.1)
            except KeyboardInterrupt:
                choice = input("a) Skip b) Reload c) Quit >> ")
                if choice == "a":
                    self.go_next = True
                elif choice == "b":
                    time.sleep(0.5)
                    self.current.load(self.config["exe_path"])
                elif choice == "c":
                    self.stop_session = True
                    break

    def _get_autosaves(self):
        files = []
        for entry in os.scandir(self.autosave_dir):
            if entry.is_file():
                files.append(entry.path)
        with Pool(16) as pool:
            autosaves = set(pool.imap_unordered(get_uid, files))
        return autosaves

    def _get_site_url(self):
        sites = {
            "TMUF-X": "tmuf.exchange",
            "TMNF-X": "tmnf.exchange",
            "TMO-X": "original.tm-exchange.com",
            "TMS-X": "sunrise.tm-exchange.com",
            "TMN-X": "nations.tm-exchange.com",
        }
        return sites[self.site]

    def _get_tracks(self):
        api_url = f"https://{self._get_site_url()}/api/tracks?"
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
        print(f"Found a total of {len(self.tracks)} tracks.")

    def _downloader(self):
        while len(self.tracks) > 0 and not self.stop_session:
            track = random.choice(self.tracks)
            self.tracks.remove(track)

            print(f"downloading {track.name}")
            track.download(self.track_dir, self.site)
            self.next.put(track)
            time.sleep(0.5)

    def update_session(self, replay_path):
        print("authosave time")
        replay_uid = get_uid(replay_path)
        if self.current.uid != replay_uid:
            return

        self.current.update_medal(replay_path)

        if self.mode != "finished":
            replay_time = get_replay_time(replay_path)
            if not replay_time:
                print("\nCouldn't get replay_time")
                raise SystemExit
            if replay_time > self.current.medals[self.mode]:
                return

        self.autosaves.add(replay_uid)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        info = [self.current.medal, replay_uid, timestamp]
        if info not in self.finished:
            self.finished.append(info)
        if len(self.tracks) == 0 and self.next.qsize() == 0:  # no tracks left
            print(self.finished)
            self.stop_session = True

        self.go_next = True


if __name__ == "__main__":
    with open("config.yaml") as file:
        config = yaml.safe_load(file)
    session = Game(config)
    session.start()
    while not session.stop_session:
        print("session still going")
        time.sleep(0.1)
    print("session stopped")
