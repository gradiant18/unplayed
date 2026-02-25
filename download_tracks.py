import os
import requests
import time
from multiprocessing import Pool
from tqdm import tqdm


def get_ids_from_file():
    track_ids = []
    with open("ids.txt") as file:
        for line in file:
            track_ids.append(int(line))
    return track_ids


def download_track(track_id):
    download_url = f"https://tmnf.exchange/trackgbx/{track_id}"

    file_name = f"{track_id}.Challenge.Gbx"
    file_path = os.path.join(folder_path, file_name)

    if os.path.exists(file_path):
        print(f"Map {file_name} already exists. Skipping download.")
        return

    retries = 0
    while retries < 3:
        try:
            map_response = requests.get(download_url, timeout=10)
            if map_response.status_code == 200:
                with open(file_path, "wb") as file:
                    file.write(map_response.content)
                break
            else:
                print(
                    f"Failed to download map ID {track_id}, status code: {map_response.status_code}"
                )
            retries += 1
            time.sleep(1)
        except requests.RequestException as e:
            print(f"Retry {retries + 1}/3 failed for map ID {track_id}: {e}")
            retries += 1
            time.sleep(1)


folder_path = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Challenges/Unplayed"
track_ids = get_ids_from_file()
if __name__ == "__main__":
    with Pool(32) as pool:
        output = list(
            tqdm(pool.imap_unordered(download_track, track_ids), total=len(track_ids))
        )
