from multiprocessing import Pool
import os
from pygbx2 import get_uid, get_medal
from queue import Queue
import requests
from sessions import get_todays_tracks, save_todays_tracks
import subprocess
from sys import argv
from time import sleep
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer


class Handler(PatternMatchingEventHandler):
    def __init__(self):
        # only watch for .gbx files
        PatternMatchingEventHandler.__init__(
            self, patterns=["*.gbx"], ignore_directories=True, case_sensitive=False
        )

    def on_created(self, event):
        if os.path.split(event.src_path)[0] == autosave_dir:
            autosave_queue.put(event.src_path)

    def on_modified(self, event):
        if os.path.split(event.src_path)[0] == autosave_dir:
            autosave_queue.put(event.src_path)

    def on_deleted(self, event):
        if os.path.split(event.src_path)[0] == randomizer_dir:
            current_queue.put(event.src_path)


def get_ids(max_time):
    start_date = "2010-02-01T00:00:00"
    end_date = "2010-02-28T23:59:59"

    api_url = (
        f"https://tmnf.exchange/api/tracks?"
        f"uploadedafter={start_date}&"
        f"uploadedbefore={end_date}&"
        f"inhasrecord=0&"
        f"fields=TrackId,UId&"
        f"authortimemax={max_time * 1000}&"
        f"count=1000"
    )

    ids = set()
    current_last = 0

    while True:
        paginated_url = f"{api_url}&after={current_last}"
        try:
            response = requests.get(paginated_url, timeout=10)
            response.raise_for_status()
            data = response.json()

            results = data.get("Results", [])
            if not results:
                break

            for track in results:
                tid = track["TrackId"]
                uid = track["UId"]
                ids.add((tid, uid))

            if not data.get("More", False):
                break

            current_last = results[-1]["TrackId"]
            sleep(0.1)

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
        "/home/russell/.steam/steam/steamapps/common/TrackMania United/TmForever.exe",
        "/useexedir",
        "/singleinst",
        f"/file={track_path}",
    ]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error launching game: {e}")


def download_track(track_id):
    download_url = f"https://tmnf.exchange/trackgbx/{track_id}"

    file_name = f"{track_id}.Challenge.Gbx"
    file_path = os.path.join(randomizer_dir, file_name)

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


def add_to_next_queue():
    global unplayed, max_time
    while next_queue.empty():
        try:
            track_id, track_uid = unplayed.pop()
        except IndexError:
            max_time += 5
            unplayed = get_ids(max_time)
            print(f"max_time increased to {max_time}")
            continue

        if track_uid in autosaves:
            print(f"{track_id} has an autosave")
            continue

        track_path = download_track(track_id)
        next_queue.put(track_path)
        print(f"added {track_id} to next_queue")


def main():
    global current_track
    if not autosave_queue.empty():
        replay = autosave_queue.get()
        if get_uid(current_track) == get_uid(replay):
            if get_medal(replay, current_track) != "author":
                return
            replay_queue.put((replay, current_track))
            current_queue.put("")

            print(f"{os.path.split(current_track)[1]} was just finished")

    if not current_queue.empty():
        current_queue.get()
        if len(scan_dir(current_dir)) == 0:
            current_track = next_queue.get()
            print(f"Playing {os.path.split(current_track)[1]}")
            load_track(current_track)
            add_to_next_queue()

    if not replay_queue.empty():
        replay, track = replay_queue.get()
        medal = get_medal(replay, track)
        if medal:
            print(f"You got the {medal} medal!")
        else:
            print("You didn't get any medal :(")
        finished.append(medal)
        print(f"You've completed {len(finished)} tracks so far.")


def move_file(file_path, dir_path):
    filename = os.path.split(file_path)[1]
    new_path = os.path.join(dir_path, filename)
    os.rename(file_path, new_path)
    return new_path


def scan_dir(path):
    tracks = []
    for entry in os.scandir(path):
        if entry.is_file():
            tracks.append(entry.path)
    return tracks


if __name__ == "__main__":
    max_time = 50
    if len(argv) == 2:
        target_tracks = int(argv[1])
    else:
        target_tracks = 50

    tracks = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks"
    autosave_dir = f"{tracks}/Replays/Autosaves"
    current_dir = f"{tracks}/Challenges/Current"
    unplayed_dir = f"{tracks}/Challenges/Unplayed"
    finished_dir = f"{tracks}/Challenges/Finished"
    randomizer_dir = f"{tracks}/Challenges/Randomizer"
    sessions_path = "sessions.json"

    current_queue = Queue()
    autosave_queue = Queue()
    next_queue = Queue()
    replay_queue = Queue()
    event_handler = Handler()
    observer = Observer()
    observer.schedule(event_handler, path=current_dir, recursive=False)
    observer.schedule(event_handler, path=autosave_dir, recursive=False)
    observer.start()

    # get list of uid's for autosaves
    files = [entry.path for entry in os.scandir(autosave_dir) if entry.is_file()]
    with Pool(16) as pool:
        autosaves = set(pool.imap(get_uid, files))

    while not (unplayed := get_ids(max_time)):
        max_time += 5

    current_track = ""
    current_queue.put("")
    finished = get_todays_tracks(sessions_path)
    add_to_next_queue()

    try:
        while len(finished) < target_tracks:
            main()
            sleep(0.1)
    except KeyboardInterrupt:
        pass

    print(finished)
    save_todays_tracks(sessions_path, finished)
    observer.stop()
    observer.join()
