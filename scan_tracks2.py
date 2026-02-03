import os
from pygbx import Gbx, GbxType
import re
import requests

# remove 'bad' characters from filename
def clean_filename(file_path):
    if "Replay.gbx" in file_path:
        directory, filename = os.path.split(file_path)
        clean_name = re.sub(r"[^a-zA-Z0-9_\/\\[\]\$\(\)\.\ -]", "", filename)
        clean_full_path = os.path.join(directory, clean_name)

        if file_path != clean_full_path:
            print(f"Renaming: {filename} -> {clean_filename}")
            os.rename(file_path, clean_full_path)

        return clean_full_path
    return None

# get map name from challenge file
def get_map_name(gbx_file):
    g = Gbx(gbx_file)
    challenge = g.get_class_by_id(GbxType.CHALLENGE)
    if not challenge:
        return None
    return challenge.map_name

# get track id from downloaded challenge file
def get_track_id(challenge):
    match = re.search(r"\/\d+\.", challenge)
    if match:
        return match.group()[1:-1]
    else:
        return None

# find if track has a record uploaded
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

# find if autosave exists
def has_replay(challenge_file):
    track_name = get_map_name(challenge_file)
    if not track_name:
        print(f"Could not get map name from {challenge_file}")
        return None

    replay_name = clean_filename(track_name)

    if os.path.exists(f"{autosaves}/{replay_name}"):
        return True
    else:
        return False

# recursively make list of files and directories in path
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
finished = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Challenges/Finished"

# clean autosave file names
files, _ = scan_folder(autosaves)
for file_path in files:
    clean_filename(file_path)

# get list of files and directories
files, dirs = scan_folder(maps)

# find replay for every track
for file in files:
    track_id = get_track_id(file)

    if not track_id:
        print(f"Could not extract TrackId from {file}")
        continue

    if has_replay(file):
        print(f"{track_id} has a replay but not uploaded")
        os.rename(file, f"{finished}/{track_id}.Challenge.Gbx")
        continue

    if has_record(track_id):
        print(f"{track_id} has at least 1 record")
        os.rename(file, f"{finished}/{track_id}.Challenge.Gbx")
        continue

    print(f"{track_id} does not have a replay")

# remove empty folders
for folder in dirs[::-1]:
    files, folders = scan_folder(folder)
    if not files and not folders:
        os.rmdir(folder)
