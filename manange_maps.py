import os
from pygbx import Gbx, GbxType
import re
import requests

def get_map_name(gbx_file):
    g = Gbx(gbx_file)
    challenge = g.get_class_by_id(GbxType.CHALLENGE)
    if not challenge:
        return None
    return challenge.map_name

def get_track_id(challenge):
    match = re.search(r"\/\d+\.", challenge)
    if match:
        return match.group()[1:-1]
    else:
        return None

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

def has_replay(challenge_file):
    track_name = get_map_name(challenge_file)
    if not track_name:
        print(f"Could not get map name from {challenge_file}")
        return None

    replay_name = f"steamuser_{track_name}.Replay.gbx"
    if os.path.exists(f"{autosaves}/{replay_name}"):
        return True
    else:
        return False

def scan_folder(path):
    files, dirs = [], []
    for entry in os.scandir(path):
        if entry.is_file():
            files.append(entry.path)
        elif entry.is_dir():
            dirs.append(entry.path)
            files_r, dirs_r = scan_folder(entry.path)
            for file in files_r:
                files.append(file)
            for dir_r in dirs_r:
                dirs.append(dir_r)
    return files, dirs
    
autosaves = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Replays/Autosaves"
maps = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Challenges/Downloaded"

files, dirs = scan_folder(maps)

for file in files:
    track_id = get_track_id(file)
    if not track_id:
        print(f"Could not extract TrackId from {file}")
        continue

    if has_record(track_id):
        print(f"{track_id} has at least 1 record")
        os.remove(file)
        continue

    if has_replay(file):
        print(f"{track_id} has a replay but not uploaded")
        os.remove(file)
        continue
