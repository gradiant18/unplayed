import datetime
from multiprocessing import Pool
import os
from pygbx2 import get_uid, get_replay_time, get_medal, get_medal_time
import requests
from sessions import get_todays_tracks, save_todays_tracks
import subprocess
from time import sleep
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer
import yaml


class Handler(PatternMatchingEventHandler):
    def __init__(self):
        # only watch for .gbx files
        PatternMatchingEventHandler.__init__(
            self, patterns=["*.gbx"], ignore_directories=True, case_sensitive=False
        )

    def on_modified(self, event):
        new_autosave(event.src_path)


def load_config(path):
    with open(path) as file:
        config = yaml.safe_load(file)
    return config


def get_ids():
    api_url = "https://tmnf.exchange/api/tracks?"
    params = {"fields": "TrackId,UId,TrackName", "count": 1000}
    for param in config["track_rules"]:
        value = config["track_rules"][f"{param}"]
        if value is not None:
            params[f"{param}"] = value

    ids = set()
    banned_ids = set(config["banned_tracks"])
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
                if track["TrackId"] not in banned_ids:
                    ids.add((track["TrackId"], track["UId"], track["TrackName"]))

            if not data.get("More", False):
                break

            current_last = results[-1]["TrackId"]

        except requests.exceptions.RequestException as e:
            print(f"error: {e}")
            sleep(1)
            continue

    return ids


def load_track(track_path):
    command = [
        "protontricks-launch",
        "--appid",
        "7200",
        config["exe_dir"],
        "/useexedir",
        "/singleinst",
        f"/file={track_path}",
    ]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error launching game: {e}")


def download_track(track_id, track_name):
    download_url = f"https://tmnf.exchange/trackgbx/{track_id}"

    file_name = f"{track_name}.Challenge.Gbx"
    file_path = os.path.join(randomizer_dir, file_name)

    if os.path.exists(file_path):
        return file_path

    retries = 0
    while retries < 3:
        try:
            map_response = requests.get(download_url, timeout=10)
            if map_response.status_code == 200:
                with open(file_path, "wb") as file:
                    file.write(map_response.content)
                return file_path
            else:
                print(
                    f"Failed to download map ID {track_id}, status code: {map_response.status_code}"
                )
            retries += 1
            sleep(1)
        except requests.RequestException as e:
            print(f"Retry {retries + 1}/3 failed for map ID {track_id}: {e}")
            retries += 1
            sleep(1)
    return None


def add_to_next():
    while len(next) == 0:
        try:
            track_id, track_uid, track_name = unplayed.pop()
        except KeyError:
            print("No tracks remaining")
            quit()

        if track_uid in autosaves:
            continue

        track_path = download_track(track_id, track_name)
        if track_path is not None:
            next.append(track_path)


def new_autosave(replay):
    global current_track
    replay_uid = get_uid(replay)

    if get_uid(current_track) != replay_uid:
        return

    replay_time = get_replay_time(replay)
    target_time = get_medal_time(current_track, config["game_rules"]["next_mode"])
    if not replay_time or not target_time:
        print("couldn't get replay_time or target_time")
        return
    if replay_time > target_time:
        return

    finished.append(get_medal(replay, current_track))
    next_track()
    autosaves.add(replay_uid)


# Source - https://stackoverflow.com/a/68238146
def format_timedelta(td):
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    seconds += td.microseconds / 1e6
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d}"


def status():
    track = os.path.split(current_track)[1][:-14]
    tracks_played = len(finished)
    tracks_left = track_limit - tracks_played
    time_left = format_timedelta(stop_time - datetime.datetime.now())
    print(
        f"Playing {track} | Tracks Played: {tracks_played} | Tracks Left: {tracks_left} | Time Left: {time_left}",
        end="\r",
    )


def next_track():
    global current_track
    current_track = next.pop(0)
    load_track(current_track)
    add_to_next()


if __name__ == "__main__":
    config = load_config("config.yaml")

    track_dir = config["track_dir"]
    autosave_dir = f"{track_dir}/Replays/Autosaves"
    randomizer_dir = f"{track_dir}/Challenges/{config['download_track_dir']}"
    sessions_path = "sessions.json"

    next = []
    event_handler = Handler()
    observer = Observer()
    observer.schedule(event_handler, path=autosave_dir, recursive=False)
    observer.start()

    finished = get_todays_tracks(sessions_path)
    if len(finished) >= config["game_rules"]["track_limit"]:
        print("Already achieved track limit")
        quit()

    # get set of uid's for autosaves
    files = [entry.path for entry in os.scandir(autosave_dir) if entry.is_file()]
    with Pool(16) as pool:
        autosaves = set(pool.imap(get_uid, files))

    # get set of available track ids
    unplayed = get_ids()
    if not unplayed:
        print("No tracks found")

    # start playing first track
    add_to_next()
    next_track()

    # set up for time limit
    now = datetime.datetime.now()
    time_limit = config["game_rules"]["time_limit"]
    delta = datetime.timedelta(
        hours=int(time_limit[:2]),
        minutes=int(time_limit[3:5]),
        seconds=int(time_limit[6:]),
    )
    stop_time = now + delta

    track_limit = int(config["game_rules"]["track_limit"])

    while True:
        try:
            status()
            enough_tracks = len(finished) >= track_limit
            enough_time = datetime.datetime.now() >= stop_time
            if enough_tracks or enough_time:
                break
            sleep(0.1)
        except KeyboardInterrupt:
            choice = input("\na) Skip b) Reload c) Quit >> ")
            if choice == "a":
                next_track()
            elif choice == "b":
                load_track(current_track)
            elif choice == "c":
                break

    save_todays_tracks(sessions_path, finished)
    observer.stop()
    observer.join()
    print()
