from multiprocessing import Pool
import os
from pygbx2 import get_uid, get_medal, get_medal_times
from queue import Queue
from random import shuffle
from re import search
import requests
from sessions import get_todays_tracks, save_todays_tracks
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

    def on_deleted(self, event):
        if os.path.split(event.src_path)[0] == current_dir:
            current_queue.put(event.src_path)


def add_to_next_queue():
    def __filter(track, max_time):
        medal_times = get_medal_times(track)
        if not medal_times:
            return False
        if medal_times["gold"] < max_time * 1000:
            return True
        return False

    def __has_record(path):
        match = search(r"\/\d+\.", path)
        if not match:
            return None
        track_id = match.group()[1:-1]
        url = "http://tmnf.exchange/api/tracks"
        params = {"fields": "TrackName", "id": track_id, "inhasrecord": 1}

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return bool(response.json().get("Results"))
        except requests.RequestException as e:
            print(f"Request Error: {e}")
            return False

    global max_time
    shuffle(unplayed)
    while next_queue.empty():
        try:
            track = unplayed.pop()
        except IndexError:
            unplayed.extend(scan_dir(unplayed_dir))
            shuffle(unplayed)
            max_time += 5
            print(f"max_time increased to {max_time}")
            continue

        if not __filter(track, max_time):
            continue
        if get_uid(track) in autosaves:
            print(f"{track} has an autosave")
            move_file(track, finished_dir)
            continue
        if __has_record(track):
            print(f"{track} has a record")
            move_file(track, finished_dir)
            continue
        next_queue.put(track)
        print(f"added {os.path.split(track)[1]} to next_queue")


def main():
    if not autosave_queue.empty():
        current = scan_dir(current_dir)
        replay = autosave_queue.get()
        if get_uid(current[0]) == get_uid(replay):
            new_path = move_file(current[0], finished_dir)
            current_queue.put("stinky")
            replay_queue.put((replay, new_path))

            print(f"{os.path.split(new_path)[1]} was just finished")

    if not current_queue.empty():
        current_queue.get()
        if len(scan_dir(current_dir)) == 0:
            path = move_file(next_queue.get(), current_dir)
            print(f"added {os.path.split(path)[1]} to current")
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
    max_time = 30
    if len(argv) == 2:
        target_tracks = int(argv[1])
    else:
        target_tracks = 50

    tracks = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks"
    autosave_dir = f"{tracks}/Replays/Autosaves"
    current_dir = f"{tracks}/Challenges/Current"
    unplayed_dir = f"{tracks}/Challenges/Unplayed"
    finished_dir = f"{tracks}/Challenges/Finished"
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

    files = [entry.path for entry in os.scandir(autosave_dir) if entry.is_file()]
    with Pool(16) as pool:
        autosaves = set(pool.imap(get_uid, files))

    if not (entries := list(os.scandir(current_dir))):
        current_queue.put("")
    for entry in entries:
        move_file(entry.path, unplayed_dir)

    current = []
    unplayed = scan_dir(unplayed_dir)
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
