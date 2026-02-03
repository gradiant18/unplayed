import os
from pygbx import Gbx, GbxType
import random
import re
import requests
from time import sleep, time
from tqdm import tqdm

finished_dir = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Challenges/Finished"
current_dir = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Challenges/Current"
unplayed_dir = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Challenges/Unplayed"
autosaves_dir = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Replays/Autosaves"


def clean_autosave(path):
    directory, filename = os.path.split(path)
    clean_name = re.sub(r"[^a-zA-Z0-9_\\[\]\$\(\)\.\ -]", "", filename)
    clean_path = os.path.join(directory, clean_name)

    if path != clean_path:
        os.rename(path, clean_path)
    return clean_path


def get_medal(autosave, track_id):
    ghost = Gbx(autosave).get_class_by_id(GbxType.CTN_GHOST)
    if not ghost:
        return None

    url = "https://tmnf.exchange/api/tracks"
    params = {
        "fields": "AuthorTime,GoldTarget,SilverTarget,BronzeTarget",
        "id": track_id,
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        medals = response.json().get("Results")[0]
    except requests.RequestException as e:
        print(f"Request Error: {e}")
        return None

    if ghost.race_time <= medals["AuthorTime"]:
        return "author"
    elif ghost.race_time <= medals["GoldTarget"]:
        return "gold"
    elif ghost.race_time <= medals["SilverTarget"]:
        return "silver"
    elif ghost.race_time <= medals["BronzeTarget"]:
        return "bronze"
    else:
        return "none"


def get_track_name(path):
    g = Gbx(path)
    challenge = g.get_class_by_id(GbxType.CHALLENGE)
    if not challenge:
        return None

    clean_name = re.sub(r"\/", "_", challenge.map_name)
    clean_name = re.sub(r"[^a-zA-Z0-9_\\[\]\$\(\)\.\ -]", "", clean_name)
    g.f.close()
    return clean_name


def get_track_id(path):
    match = re.search(r"\/\d+\.", path)
    if not match:
        return None
    return match.group()[1:-1]


def has_record(track_id):
    url = "https://tmnf.exchange/api/tracks"
    params = {"fields": "TrackName", "id": track_id, "inhasrecord": 1}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return bool(response.json().get("Results"))
    except requests.RequestException as e:
        print(f"Request Error: {e}")
        return False


def scan_tracks(path):
    tracks = []
    for entry in os.scandir(path):
        if not entry.is_file():
            continue

        track_id = get_track_id(entry.path)
        track_name = get_track_name(entry.path)
        tracks.append({"path": entry, "id": track_id, "name": track_name})
    return tracks


def scan_replays(path):
    replays = []
    for entry in os.scandir(path):
        if not entry.is_file():
            continue
        entry = clean_autosave(entry.path)
        _, filename = os.path.split(entry)
        replays.append({"path": entry, "name": filename})
    return replays


medals_collected = {"author": 0, "gold": 0, "silver": 0, "bronze": 0, "none": 0}
unplayed = scan_tracks(unplayed_dir)
current = scan_tracks(current_dir)
for track in current:  # remove played maps from current
    if has_record(track["path"]):
        os.remove(track["path"])
        current.pop(track)

while True:
    current = scan_tracks(current_dir)
    autosaves = scan_replays(autosaves_dir)

    for track in current:
        for autosave in autosaves:
            if autosave["name"] == f"steamuser_{track["name"]}.Replay.gbx":
                print(f'{track["name"]} is finished')

                # get medal type
                medal = get_medal(autosave["path"], track["id"])
                medals_collected[medal] += 1
                print(medals_collected)

                # move track into finished directory
                _, file = os.path.split(track["path"])
                new_path = os.path.join(finished_dir, file)
                os.rename(track["path"], new_path)

                current.remove(track)  # update current

    while len(current) < 2:
        track = unplayed.pop()

        # don't add played maps to current
        if has_record(track["path"]):
            os.remove(track["path"])
            continue

        # move track into current list
        _, file = os.path.split(track["path"])
        new_path = os.path.join(current_dir, file)
        os.rename(track["path"], new_path)

        # update current
        track["path"] = new_path
        current.append(track)
        print(f"Added {track["name"]} to current")

    sleep(0.5)
