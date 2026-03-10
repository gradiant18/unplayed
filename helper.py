import os
from datetime import datetime, timedelta
from track import Track
import requests
import time
import re
from concurrent.futures import ThreadPoolExecutor


def get_uid(path):
    with open(path, "rb") as file:
        data = str(file.read())
    if not (match := re.search(r'uid="\w*"', data)):
        return None
    return match.group()[5:-1]


def get_autosaves(self):
    files = []
    for entry in os.scandir(self.autosave_dir):
        if entry.is_file():
            files.append(entry.path)
    with ThreadPoolExecutor(max_workers=10) as exe:
        autosaves = set(exe.map(get_uid, files))
    return autosaves


def get_site_url(self):
    sites = {
        "TMUF-X": "tmuf.exchange",
        "TMNF-X": "tmnf.exchange",
        "TMO-X": "original.tm-exchange.com",
        "TMS-X": "sunrise.tm-exchange.com",
        "TMN-X": "nations.tm-exchange.com",
    }
    return sites[self.site]


def calculate_stop_time(self):
    limit = self.time_limit
    if not limit:
        return None

    if isinstance(limit, int):
        return datetime.now() + timedelta(seconds=limit)
    dt = timedelta(
        hours=int(limit[:2]), minutes=int(limit[3:5]), seconds=int(limit[6:])
    )
    return datetime.now() + dt


def format_timedelta(td):
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    seconds += td.microseconds / 1e6
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d}"


def get_tracks(self):
    api_url = f"https://{get_site_url(self)}/api/tracks?"
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
