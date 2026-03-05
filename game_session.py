from datetime import datetime, timedelta
import json
from multiprocessing import Pool
import os
from pygbx2 import get_uid, get_replay_time
import time
from tmx import load_track_in_game, get_tracks


class GameSession:
    def __init__(self, config):
        self.config = config

        self.mode = config.get("next_mode", "author")
        self.site = config.get("site", "TMNF-X")
        self.site_url = self._get_site_url()

        self.finished = []
        self.autosave_dir = f"{self.config['track_dir']}/Replays/Autosaves"
        self.autosaves = self._get_autosaves()
        self.tracks = get_tracks(
            self.site_url,
            config["track_rules"],
            set(config["banned_tracks"][self.site]),
            self.autosaves,
        )

        self.start_time = datetime.now()
        self.stop_time = self._calculate_stop_time()
        self.track_limit = config.get("track_limit")
        self.stop = False

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

    def _calculate_stop_time(self):
        limit = self.config.get("time_limit")
        if not limit:
            return None

        if isinstance(limit, int):
            return datetime.now() + timedelta(seconds=limit)
        dt = timedelta(
            hours=int(limit[:2]), minutes=int(limit[3:5]), seconds=int(limit[6:])
        )
        return datetime.now() + dt

    def _format_timedelta(self, td):
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        seconds += td.microseconds / 1e6
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d}"

    def get_next(self):
        while True:
            try:
                self.next = self.tracks.pop()
            except KeyError:
                print("No more tracks")
                return

            self.next.download(self.config["track_dir"], self.site, self.site_url)
            if self.next.path is not None:
                return

    def start(self):
        if len(self.tracks) == 0:
            print("No tracks")
            raise SystemExit
        self.next = self.tracks.pop()
        self.load_next()

    def load_next(self):
        if not self.next.path:
            self.get_next()

        load_track_in_game(self.config["exe_path"], self.next.path)

        self.current = self.next
        self.get_next()

    def update_session(self, replay_path):
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
        self.save()
        if (
            len(self.tracks) == 0
            and self.track_limit
            and len(self.finished) >= self.track_limit
        ):
            print("\nshould stop soon")
            self.stop = True
            return
        self.load_next()

    def skip_track(self):
        # increase skipped track count?
        # add to skipped track list?
        self.load_next()

    def reload_track(self):
        time.sleep(0.1)
        load_track_in_game(self.config["exe_path"], self.current.path)

    def save(self):
        if len(self.finished) == 0 and not self.config["save_empty"]:
            return
        timestamp = self.start_time.strftime("%Y-%m-%d_%H-%M-%S")
        with open(f"sessions/{timestamp}.json", "w") as file:
            json.dump(self.finished, file, indent=2)

    def status(self):
        tracks_played = f"Tracks Played: {len(self.finished)} | "

        tracks_left = ""
        if self.track_limit:
            tracks_left = self.track_limit - len(self.finished)
            tracks_left = f"Tracks Left: {tracks_left} | "

        time_left = ""
        if self.stop_time:
            time_left = self._format_timedelta(self.stop_time - datetime.now())
            time_left = f"Time Left: {time_left} | "

        current_medal = ""
        if self.mode != "finished" or "bronze":
            medal = "None"
            if self.current.medal:
                medal = self.current.medal.capitalize()
            current_medal = f"Current Medal: {medal} | "

        current_track = f"Current Track: {self.current.name}"
        print(
            f"{tracks_played}{tracks_left}{time_left}{current_medal}{current_track}",
            end="\r",
        )

    def __str__(self):
        return str([self.current, self.next])
