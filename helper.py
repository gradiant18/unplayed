import os
from track import Track
import requests
import time
import re
from concurrent.futures import ThreadPoolExecutor
from itertools import repeat
import pickle
from test import timer
import track


def get_uid(path):
    for _ in range(10):
        with open(path, "rb") as file:
            data = file.read(4096)
        if not data:
            time.sleep(0.001)
            continue
        if match := re.search(rb'uid="(\w*)"', data):
            return match.group(1).decode("utf-8")
        time.sleep(0.001)


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


def get_autosaves(session):
    data = load()
    files = []
    oldest = data["oldest"]

    for entry in os.scandir(session.autosave_dir):
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


def get_session_url(session):
    sites = {
        "TMUF-X": "tmuf.exchange",
        "TMNF-X": "tmnf.exchange",
        "TMO-X": "original.tm-exchange.com",
        "TMS-X": "sunrise.tm-exchange.com",
        "TMN-X": "nations.tm-exchange.com",
    }
    return sites[session.site]


def get_tracks(session):
    api_url = f"https://{get_session_url(session)}/api/tracks?"
    params = {
        "fields": "TrackId,TrackName,UId,AuthorTime,GoldTarget,SilverTarget,BronzeTarget",
        "count": 1000,
    }

    for param, value in session.config.get("track_rules", {}).items():
        if value is not None:
            params[param] = value

    banned_set = set(session.banned_tracks)
    autosaves_set = session.autosaves
    current_last = 0

    with requests.Session() as http:
        while not session.stop_session:
            try:
                params["after"] = current_last
                response = http.get(api_url, params=params, timeout=10)

                response.raise_for_status()

                data = response.json()
                results = data.get("Results", [])

                if not results:
                    break

                valid_tracks = [
                    Track(track)
                    for track in results
                    if track["UId"] not in autosaves_set
                    and track["TrackId"] not in banned_set
                ]

                if valid_tracks:
                    session.tracks.extend(valid_tracks)

                current_last = results[-1]["TrackId"]

                if not data.get("More", False):
                    break

            except requests.exceptions.RequestException as e:
                print(f"API Error fetching tracks: {e}")
                time.sleep(1)
                continue

    session.fetching_done = True
    original_limit = session.config["game_rules"].get("track_limit")
    if session.track_limit != original_limit:
        session.track_limit = len(session.tracks)
