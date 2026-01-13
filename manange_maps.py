import os
from pygbx import Gbx, GbxType
import re
import requests

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

    file_name = re.sub(r"\W+", "", track_name.replace(":", "_").strip())
    replay_name = f"steamuser_{file_name}.Replay.gbx"

    real_name = "steamuser_§TF§Left of the Moon§.Replay.gbx"
    fake_name = f"{autosaves}/{replay_name}"
    print(r'\x' + r'\x'.join(f'{b:02x}' for b in bytes(real_name, 'utf8')))
    print(r'\x' + r'\x'.join(f'{b:02x}' for b in bytes(replay_name, 'utf8')))

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
