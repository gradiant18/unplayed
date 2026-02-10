import watchdog.events
import watchdog.observers
from time import sleep
from queue import Queue
from pygbx import Gbx, GbxType
import os
import re
import requests


class Handler(watchdog.events.PatternMatchingEventHandler):
    global current_queue, autosave_queue, current_dir, autosave_dir

    def __init__(self):
        # only watch for .gbx files
        watchdog.events.PatternMatchingEventHandler.__init__(
            self, patterns=["*.gbx"], ignore_directories=True, case_sensitive=False
        )

    def on_created(self, event):
        if os.path.split(event.src_path)[0] == autosave_dir:
            autosave_queue.put(event.src_path)

    def on_deleted(self, event):
        if os.path.split(event.src_path)[0] == current_dir:
            current_queue.put(event.src_path)


def app():
    global current_queue, autosave_queue, next_queue
    if not autosave_queue.empty():
        current = scan_dir(current_dir)
        replay = autosave_queue.get()
        if get_track_name(current[0]) == get_replay_track_name(replay):
            filename = os.path.split(current[0])[1]
            new_path = os.path.join(finished_dir, filename)
            os.rename(current[0], new_path)
            print(f"{filename} was just finished")

    if not current_queue.empty():
        current_queue.get()
        # move track from next_queue to current
        next_track = next_queue.get()
        filename = os.path.split(next_track)[1]
        new_path = os.path.join(current_dir, filename)
        os.rename(next_track, new_path)
        print(f"added {filename} to current")

        # add new track to next_queue
        while next_queue.empty():
            track = unplayed.pop()
            if has_record(get_track_id(track)):
                continue
            next_queue.put(track)


def get_replay_track_name(path):
    try:
        g = Gbx(path)
        replay = g.get_class_by_id(GbxType.REPLAY_RECORD)
        if not replay or not replay.track:
            g.f.close()
            raise RuntimeError

        challenge = replay.track.get_class_by_id(GbxType.CHALLENGE)

        if not challenge:
            return None
        g.f.close()
        return challenge.map_name
    except RuntimeError:
        return get_replay_track_name_backup(path)


def get_replay_track_name_backup(path):
    filename = os.path.split(path)[1]
    clean_string = r"[^a-zA-Z0-9\"\'\\[\]\$\(\)\.\ \-]"
    track_name = re.sub(clean_string, "", filename)
    track_name = re.sub(r"^steamuser", "", track_name)
    track_name = re.sub(r"\.Replay\.gbx$", "", track_name)

    return track_name


def get_track_name(path):
    try:
        g = Gbx(path)
        challenge = g.get_class_by_id(GbxType.CHALLENGE)
        if not challenge:
            return None
        g.f.close()
        return challenge.map_name
    except RuntimeError:
        return None
    except AttributeError:
        return None


def get_track_id(path):
    match = re.search(r"\/\d+\.", path)
    if not match:
        return None
    return match.group()[1:-1]


def has_record(track_id):
    url = "http://tmnf.exchange/api/tracks"
    params = {"fields": "TrackName", "id": track_id, "inhasrecord": 1}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return bool(response.json().get("Results"))
    except requests.RequestException as e:
        print(f"Request Error: {e}")
        return False


def scan_dir(path):
    tracks = []
    for entry in os.scandir(path):
        if entry.is_file():
            tracks.append(entry.path)
    return tracks


if __name__ == "__main__":
    autosave_dir = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Replays/Autosaves"
    current_dir = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Challenges/Current"
    unplayed_dir = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Challenges/Unplayed"
    finished_dir = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Challenges/Finished"

    current_queue = Queue()
    autosave_queue = Queue()
    next_queue = Queue()
    event_handler = Handler()
    observer = watchdog.observers.Observer()
    observer.schedule(event_handler, path=current_dir, recursive=False)
    observer.schedule(event_handler, path=autosave_dir, recursive=False)
    observer.start()

    unplayed = scan_dir(unplayed_dir)
    current = scan_dir(current_dir)

    # check if track in current is finished
    if has_record(get_track_id(current[0])):
        filename = os.path.split(current[0])[1]
        new_path = os.path.join(finished_dir, filename)
        os.rename(current[0], new_path)
        current.pop()

    # place unplayed track in the next queue
    while next_queue.empty():
        track = unplayed.pop()
        if has_record(get_track_id(track)):
            continue
        next_queue.put(track)

    try:
        print("starting")
        while True:
            app()
            sleep(0.1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
