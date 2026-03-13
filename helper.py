import os
from track import Track
import requests
import time
import re
from concurrent.futures import ThreadPoolExecutor
from itertools import repeat
import pickle


def get_uid(path):
    data = "b''"
    while data == "b''":
        with open(path, "rb") as file:
            data = str(file.read())

    if not (match := re.search(r'uid="\w*"', data)):
        print("no  uid for:", path)
        print(data)
        return None
    return match.group()[5:-1]


def save_autosaves(data):
    with open("auto.bin", "wb") as file:
        pickle.dump(data, file)


def load():
    if not os.path.exists("auto.bin"):
        print("auto.bin doesn't exist")
        return {"oldest": 0, "autosaves": None}
    with open("auto.bin", "rb") as file:
        data = pickle.load(file)
    if not data:
        print("data isn't real")
        data = {"oldest": 0, "autosaves": None}
    return data


def get_autosaves(self):
    data = load()
    files = []
    oldest = data["oldest"]

    for entry in os.scandir(self.autosave_dir):
        if not entry.is_file():
            continue
        if (old := os.path.getmtime(entry)) <= data["oldest"]:
            continue

        files.append(entry.path)
        if old > oldest:
            oldest = old
    data["oldest"] = oldest

    with ThreadPoolExecutor(max_workers=10) as exe:
        autosaves = set(exe.map(get_uid, files))

    if not data.get("autosaves"):
        data["autosaves"] = autosaves
    else:
        data["autosaves"].update(autosaves)
    return data


def get_site_url(self):
    sites = {
        "TMUF-X": "tmuf.exchange",
        "TMNF-X": "tmnf.exchange",
        "TMO-X": "original.tm-exchange.com",
        "TMS-X": "sunrise.tm-exchange.com",
        "TMN-X": "nations.tm-exchange.com",
    }
    return sites[self.site]


def format_timedelta(td):
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    seconds += td.microseconds / 1e6
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d}"


def clean(self, track):
    if track["TrackId"] in self.autosaves:
        return
    if track["UId"] in self.banned_tracks:
        return
    self.tracks.append(Track(track))


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

            with ThreadPoolExecutor(max_workers=10) as exe:
                exe.map(clean, repeat(self), results)
            current_last = results[-1]["TrackId"]

            if not data.get("More", False):
                break

        except requests.exceptions.RequestException as e:
            print(e)
            time.sleep(1)
            continue

    self.fetching_done = True
    if self.track_limit != self.config["game_rules"]["track_limit"]:
        self.track_limit = len(self.tracks)
