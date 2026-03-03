from datetime import datetime, timedelta
import json
from multiprocessing import Pool
import os
from pygbx2 import get_uid, get_replay_time, get_medal, get_medal_time
import time
from tmx import load_track_in_game, download_track, get_tracks


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
        self.current_uid = None
        self.next_track = None
        self.current_medal = "None"
        self.target_time = None
        self.start_time = datetime.now()
        self.stop_time = self._calculate_stop_time()
        self.track_limit = self.config["game_rules"].get("track_limit")
        self.track_name = None

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

    def _get_downloaded_track(self):
        while True:
            try:
                track_id, track_uid, self.track_name = self.unplayed_tracks.pop()
            except KeyError:
                return 0

            if track_uid in self.autosaves:
                continue

            track_path = download_track(self.config["track_dir"], self.site, track_id)
            if track_path is not None:
                return track_path

    def load_next(self):
        if not self.next_track:
            self.next_track = self._get_downloaded_track()

        start = time.perf_counter()
        load_track_in_game(self.config["exe_path"], self.next_track)
        print(f"\nTook {time.perf_counter() - start}s to load_track_in_game")

        start = time.perf_counter()
        self.current_track = self.next_track
        self.current_medal = "None"
        self.current_uid = get_uid(self.current_track)
        self.next_track = self._get_downloaded_track()
        self.target_time = get_medal_time(self.current_track, self.mode)
        print(f"\nTook {time.perf_counter() - start}s to set vars")

    def record_autosave(self, replay_path):
        print("\nran record_autosave")
        replay_uid = get_uid(replay_path)
        if self.current_uid != replay_uid:
            return

        self.current_medal = get_medal(replay_path, self.current_track)
        if self.mode != "finished":
            replay_time = get_replay_time(replay_path)
            if not replay_time:
                print("\nCouldn't get replay_time")
                raise SystemExit
            if replay_time > self.target_time:
                return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.finished.append([self.current_medal, replay_uid, timestamp])
        self.load_next()
        self.autosaves.add(replay_uid)
        self.save()

    def skip_track(self):
        # increase skipped track count?
        # add to skipped track list?
        self.load_next()

    def reload_track(self):
        time.sleep(0.1)
        load_track_in_game(self.config["exe_path"], self.current_track)

    def save(self):
        if len(self.finished) == 0:
            return
        timestamp = self.start_time.strftime("%Y-%m-%d_%H-%M-%S")
        with open(f"sessions/{timestamp}.json", "w") as file:
            json.dump(self.finished, file, indent=2)

    def status(self):
        time_left = ""
        if self.stop_time:
            time_left = self._format_timedelta(self.stop_time - datetime.now())
            time_left = f"Time Left: {time_left} |"

        tracks_left = ""
        if self.track_limit:
            tracks_left = self.track_limit - len(self.finished)
            tracks_left = f"Tracks Left: {tracks_left} |"

        # Not working
        if not self.current_medal:
            self.current_medal = "None"

        print(
            f"Tracks Played: {len(self.finished)} |",
            tracks_left,
            time_left,
            f"Current Medal: {self.current_medal.capitalize()} |",
            f"Current Track: {self.track_name}",
            end="\r",
        )

    def __str__(self):
        return str(
            [
                os.path.split(str(self.current_track))[1],
                self.current_medal,
                self.current_uid,
                os.path.split(str(self.next_track))[1],
                self.target_time,
            ]
        )
