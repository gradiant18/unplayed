import requests
import time
import subprocess
import os


def get_tracks(track_rules, site, banned_tracks):
    api_url = f"https://{site}/api/tracks?"
    params = {"fields": "TrackId,UId,TrackName", "count": 1000}
    for param in track_rules:
        value = track_rules.get(param)
        if value is not None:
            params[f"{param}"] = value

    if not banned_tracks:
        banned_tracks = set()

    ids = set()
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
                if track["TrackId"] in banned_tracks:
                    continue
                ids.add((track["TrackId"], track["UId"], track["TrackName"]))

            if not data.get("More", False):
                break

            current_last = results[-1]["TrackId"]

        except requests.exceptions.RequestException as e:
            print(f"error: {e}")
            time.sleep(1)
            continue

    return ids


def download_track(site, track_id, file_path):
    if os.path.exists(file_path):
        return file_path

    download_url = f"https://{site}/trackgbx/{track_id}"

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
        os.path.abspath(exe_path),
        "/useexedir",
        "/singleinst",
        f"/file={os.path.abspath(track_path)}",
    ]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error launching game: {e}")
