from datetime import datetime, timedelta
import json
from multiprocessing import Pool
import os
from pygbx2 import get_uid, get_replay_time, get_medal_times
import time
from tmx import load_track_in_game, download_track, get_tracks


class Track:
    def __init__(self):
        self.path = ""
        self.uid = None
        self.name = None
        self.medal = None
        self.medals = None

    def update_medal(self, replay_path):
        replay_time = get_replay_time(replay_path)

        if not self.medals:
            self.medals = get_medal_times(self.path)

        for medal in self.medals:
            if replay_time <= self.medals[medal]:
                self.medal = medal
                return

    def update_medals(self):
        self.medals = get_medal_times(self.path)

    def __str__(self):
        return f"{self.name = }, {self.path = }, {self.uid = }, {self.medal = }, {self.medals = }"


class GameSession:
    def __init__(self, config):
        self.config = config

        self.mode = config["game_rules"].get("next_mode", "author")
        self.site = config["game_rules"].get("site", "TMNF-X")
        self.site_url = self._get_site_url()

        self.finished = []
        self.autosave_dir = f"{self.config['track_dir']}/Replays/Autosaves"
        self.autosaves = self._get_autosaves()
        self.unplayed_tracks = get_tracks(
            config["track_rules"],
            self.site_url,
            set(config["banned_tracks"][self.site]),
        )

        self.next = Track()

        self.start_time = datetime.now()
        self.stop_time = self._calculate_stop_time()
        self.track_limit = config["game_rules"].get("track_limit")

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
                track_id, self.next.uid, self.next.name = self.unplayed_tracks.pop()
            except KeyError:
                print("No more tracks")
                self.next.path = "Stop"
                return

            if self.next.uid in self.autosaves:
                continue

            track_path = download_track(
                self.config["track_dir"], self.site_url, track_id
            )
            if track_path is not None:
                self.next.path = track_path
                return

    def load_next(self):
        if not self.next.path:
            self._get_downloaded_track()
        if self.next.path == "Stop":
            self.stop_time = datetime.now()
            return

        load_track_in_game(self.config["exe_path"], self.next.path)

        self.current = self.next
        self.current.update_medals()
        self.next = Track()
        self._get_downloaded_track()

    def record_autosave(self, replay_path):
        replay_uid = get_uid(replay_path)
        if self.current.uid != replay_uid:
            return

        self.current.update_medal(replay_path)

        if self.mode != "finished":
            replay_time = get_replay_time(replay_path)
            if not replay_time:
                print("\nCouldn't get replay_time")
                raise SystemExit
            if self.current.medals and replay_time > self.current.medals[self.mode]:
                return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.finished.append([self.current.medal, replay_uid, timestamp])
        self.load_next()
        self.autosaves.add(replay_uid)
        self.save()

    def skip_track(self):
        # increase skipped track count?
        # add to skipped track list?
        self.load_next()

    def reload_track(self):
        time.sleep(0.1)
        load_track_in_game(self.config["exe_path"], self.current.path)

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

        current_medal = ""
        if self.mode != "finished":
            medal = "None"
            if self.current.medal:
                medal = self.current.medal.capitalize()
            current_medal = f"Current Medal: {medal} |"

        print(
            f"Tracks Played: {len(self.finished)} |",
            tracks_left,
            time_left,
            current_medal,
            f"Current Track: {self.current.name}",
            end="\r",
        )

    def __str__(self):
        return str([self.current, self.next])
