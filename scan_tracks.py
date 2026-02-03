from multiprocessing import Pool
import os
from pygbx import Gbx, GbxType
import re
import requests
from tqdm import tqdm

# get track id from downloaded challenge file
def get_track_id(challenge):
    match = re.search(r"\/\d+\.", challenge)
    if match:
        return match.group()[1:-1]
    else:
        return None

# find if track has a record uploaded
def has_record(challenge):
    track_id = get_track_id(challenge)
    url = "https://tmnf.exchange/api/tracks"
    params = {"fields": "TrackName", "id": track_id, "inhasrecord": 1}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return (bool(response.json().get("Results")), challenge, track_id)
    except requests.RequestException as e:
        print(f"Request Error: {e}")
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
    
maps = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Challenges/Downloaded"
finished = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Challenges/Finished"

if __name__ == "__main__":
    # get list of files and directories
    files, dirs = scan_folder(maps)
    
    with Pool(16) as pool:
        output = list(tqdm(pool.imap_unordered(has_record, files), total=len(files)))

    for index, item in enumerate(output):
        if item[0]:
            print(f"{item[2]} does have a record")
            #print(item[1], f"{finished}/{item[2]}.Challenge.Gbx")
            os.rename(item[1], f"{finished}/{item[2]}.Challenge.Gbx")
    
    # remove empty folders
    for folder in dirs[::-1]:
        files, folders = scan_folder(folder)
        if not files and not folders:
            os.rmdir(folder)
