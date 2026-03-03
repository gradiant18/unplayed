import datetime
import json
from multiprocessing import Pool
import os
from requests import session
from pygbx2 import get_uid, get_replay_time, get_medal, get_medal_time
from tmx import load_track_in_game, download_track, get_tracks
import time
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer
import yaml


class GameSession:
    def __init__(self, config):
        self.config = config
        self.mode = self.config["game_rules"].get("next_mode")
        self.finished = []
        self.autosave_dir = f"{self.config['track_dir']}/Replays/Autosaves"
        self.autosaves = self._get_autosaves()
        self.site = self._get_site()
        self.unplayed_tracks = get_tracks(
            self.config["track_rules"],
            self.site,
            self.config["track_rules"].get("banned_tracks"),
        )

        self.current_track = None
        self.next_track = None
        self.current_medal = "None"
        self.start_time = datetime.datetime.now()
        self.stop_time = self._calculate_stop_time()
        self.track_limit = self.config["game_rules"].get("track_limit")

    def _get_site(self):
        sites = {
            "TMUF-X": "tmuf.exchange",
            "TMNF-X": "tmnf.exchange",
            "TMO-X": "original.tm-exchange.com",
            "TMS-X": "sunrise.tm-exchange.com",
            "TMN-X": "nations.tm-exchange.com",
        }
        return sites.get(self.config["game_rules"].get("site"))

    def _get_autosaves(self):
        files = []
        for entry in os.scandir(self.autosave_dir):
            if entry.is_file():
                files.append(entry.path)
        with Pool(16) as pool:
            autosaves = set(pool.imap_unordered(get_uid, files))
        return autosaves

    def _calculate_stop_time(self):
        limit = self.config["game_rules"].get("time_limit")
        if not limit:
            return None

        if isinstance(limit, int):
            return datetime.datetime.now() + datetime.timedelta(seconds=limit)
        dt = datetime.timedelta(
            hours=int(limit[:2]), minutes=int(limit[3:5]), seconds=int(limit[6:])
        )
        return datetime.datetime.now() + dt

    def _format_timedelta(self, td):
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        seconds += td.microseconds / 1e6
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d}"

    def status(self):
        track_name = (
            os.path.split(self.current_track)[1][:-14] if self.current_track else "None"
        )
        stat_time_left = ""
        if self.stop_time:
            time_left = self._format_timedelta(self.stop_time - datetime.datetime.now())
            stat_time_left = f"Time Left: {time_left} | "

        stat_tracks_left = ""
        if self.track_limit:
            tracks_left = self.track_limit - len(self.finished)
            stat_tracks_left = f"Tracks Left: {tracks_left} | "

        if not self.current_medal:
            self.current_medal = "None"

        print(
            f"Tracks Played: {len(self.finished)} | {stat_tracks_left}{stat_time_left}Current Medal: {self.current_medal.capitalize()} | Current Track: {track_name}",
            end="\r",
        )

    def _get_downloaded_track(self):
        while True:
            try:
                track_id, track_uid, track_name = self.unplayed_tracks.pop()
            except KeyError:
                print("\nNo tracks remaining")
                raise SystemExit

            if track_uid in self.autosaves:
                continue

            filename = os.path.join(
                self.config["track_dir"],
                "Challenges/Randomizer",
                f"{track_name}.Challenge.Gbx",
            )
            track_path = download_track(self.site, track_id, filename)
            if track_path is not None:
                return track_path

    def load_next(self):
        if not self.next_track:
            self.next_track = self._get_downloaded_track()

        load_track_in_game(self.config["exe_path"], self.next_track)
        self.current_track = self.next_track
        self.current_medal = "None"
        self.next_track = self._get_downloaded_track()

    def record_autosave(self, replay_path):
        replay_uid = get_uid(replay_path)
        if get_uid(self.current_track) != replay_uid:
            return

        self.current_medal = get_medal(replay_path, self.current_track)
        if self.mode != "finished":
            replay_time = get_replay_time(replay_path)
            target_time = get_medal_time(self.current_track, self.mode)
            if not replay_time or not target_time:
                print("\nCouldn't get replay_time or current_track")
                raise SystemExit
            if replay_time > target_time:
                return

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.finished.append([self.current_medal, replay_uid, timestamp])
        self.load_next()
        self.autosaves.add(replay_uid)
        self.save()

    def skip_track(self):
        self.load_next()

    def reload_track(self):
        load_track_in_game(self.config["exe_path"], self.current_track)

    def save(self):
        timestamp = self.start_time.strftime("%Y-%m-%d_%H-%M-%S")
        with open(f"sessions/{timestamp}.json", "w") as file:
            json.dump(self.finished, file, indent=2)


class Handler(PatternMatchingEventHandler):
    def __init__(self, session):
        super().__init__(patterns=["*.gbx"], ignore_directories=True)
        self.session = session

    def on_modified(self, event):
        self.session.record_autosave(event.src_path)


def load_config(path):
    with open(path) as file:
        config = yaml.safe_load(file)
    return config


if __name__ == "__main__":
    config = load_config("config.yaml")

    session = GameSession(config)

    observer = Observer()
    observer.schedule(Handler(session), path=session.autosave_dir, recursive=False)
    observer.start()

    session.load_next()

    while True:
        try:
            if session.track_limit and len(session.finished) >= session.track_limit:
                break
            if session.stop_time and datetime.datetime.now() >= session.stop_time:
                break

            session.status()
            time.sleep(0.1)
        except KeyboardInterrupt:
            choice = input("\na) Skip b) Reload c) Quit >> ")
            if choice == "a":
                session.skip_track()
            elif choice == "b":
                session.reload_track()
            elif choice == "c":
                session.save()
                break

    observer.stop()
    observer.join()
