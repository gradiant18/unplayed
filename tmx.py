import requests
import time
import subprocess
import os
from pygbx2 import get_replay_time


class Track:
    def __init__(self, track):
        self.path = ""
        self.name = track["TrackName"]
        self.track_id = track["TrackId"]
        self.uid = track["UId"]
        self.medal = None
        self.medals = {
            "author": track["AuthorTime"],
            "gold": track["GoldTarget"],
            "silver": track["SilverTarget"],
            "bronze": track["BronzeTarget"],
        }

    def update_medal(self, replay_path):
        replay_time = get_replay_time(replay_path)

        for medal in self.medals:
            if replay_time <= self.medals[medal]:
                self.medal = medal
                return

    def download(self, track_dir, site):
        self.path = download_track(track_dir, site, self.track_id)

    def __str__(self):
        return f"{self.name = }, {self.path = }, {self.uid = }, {self.medal = }, {self.medals = }"


def get_site_url(site):
    sites = {
        "TMUF-X": "tmuf.exchange",
        "TMNF-X": "tmnf.exchange",
        "TMO-X": "original.tm-exchange.com",
        "TMS-X": "sunrise.tm-exchange.com",
        "TMN-X": "nations.tm-exchange.com",
    }
    return sites[site]


def get_tracks(site, track_rules):
    api_url = f"https://{get_site_url(site)}/api/tracks?"
    params = {
        "fields": "TrackId,TrackName,UId,AuthorTime,GoldTarget,SilverTarget,BronzeTarget",
        "count": 1000,
    }
    for param in track_rules:
        value = track_rules.get(param)
        if value is not None:
            params[f"{param}"] = value

    tracks = []
    current_last = 0

    while True:
        try:
            params["after"] = current_last
            response = requests.get(api_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            results = data.get("Results", [])
            if not results:
                break

            for track in results:
                tracks.append(Track(track))

            if not data.get("More", False):
                break

            current_last = results[-1]["TrackId"]

        except requests.exceptions.RequestException as e:
            print(f"error: {e}")
            time.sleep(1)
            continue

    return tracks


def download_track(track_dir, site, track_id):
    # check dir path
    dir_path = os.path.join(track_dir, "Challenges/Randomizer", site)
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)

    # check file path
    file_path = os.path.join(dir_path, f"{track_id}.Challenge.gbx")
    if os.path.exists(file_path):
        return file_path

    download_url = f"https://{get_site_url(site)}/trackgbx/{track_id}"

    retries = 0
    while retries < 3:
        try:
            track_response = requests.get(download_url, timeout=10)
            if track_response.status_code == 200:
                with open(file_path, "wb") as file:
                    file.write(track_response.content)
                return file_path
            else:
                print(track_response.status_code)
            retries += 1
            time.sleep(1)
        except requests.RequestException as e:
            print(f"Retry {retries + 1}/3 failed: {e}")
            retries += 1
            time.sleep(1)
    return None


def load_track_in_game(exe_path, track_path):
    command = [
        "protontricks-launch",
        "--appid",
        "7200",
        exe_path,
        "/useexedir",
        "/singleinst",
        f"/file={track_path}",
    ]

    subprocess.run(command)
