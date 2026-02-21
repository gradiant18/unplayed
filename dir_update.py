import watchdog.events
from multiprocessing import Pool
import watchdog.observers
from time import sleep, time
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


def add_to_next_queue():
    global next_queue, unplayed
    while next_queue.empty():
        track = unplayed.pop()
        if has_autosave(track):
            print(f"{track} does have an autosave")
            move_file(track, finished_dir)
            continue
        if has_record(get_track_id(track)):
            print(f"{track} does have a record")
            move_file(track, finished_dir)
            continue
        next_queue.put(track)
        print(f"added {os.path.split(track)[1]} to next_queue")


def move_file(file_path, dir_path):
    filename = os.path.split(file_path)[1]
    new_path = os.path.join(dir_path, filename)
    os.rename(file_path, new_path)
    return new_path


def app():
    global current_queue, autosave_queue, next_queue, replay_queue
    if not autosave_queue.empty():
        current = scan_dir(current_dir)
        replay = autosave_queue.get()
        if get_track_name(current[0]) == get_replay_track_name(replay):
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
        medal = get_medal(replay, get_track_id(track))
        print(medal)


def get_medal(autosave, track_id):
    ghost = Gbx(autosave).get_class_by_id(GbxType.CTN_GHOST)
    if not ghost:
        return None

    url = "https://tmnf.exchange/api/tracks"
    params = {
        "fields": "AuthorTime,GoldTarget,SilverTarget,BronzeTarget",
        "id": track_id,
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        medals = response.json().get("Results")[0]
    except requests.RequestException as e:
        print(f"Request Error: {e}")
        return None

    for medal in medals:
        if ghost.race_time <= medals[medal]:
            return re.sub(r"T.+", "", medal).lower()

    return "none"


def get_replay_track_name(path):
    g = Gbx(path)
    replay = g.get_class_by_id(GbxType.REPLAY_RECORD)
    if not replay or not replay.track:
        g.f.close()
        print("not replay")
        return

    challenge = replay.track.get_class_by_id(GbxType.CHALLENGE)

    if not challenge:
        return None
    g.f.close()
    return challenge.map_name


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


def has_autosave(path):
    global autosaves
    name = get_track_name(path)
    if name in autosaves:
        return True
    filename = os.path.split(path)[1]
    clean_string = r"[^a-zA-Z0-9\"\'\\[\]\$\(\)\.\ \-]"
    name = re.sub(clean_string, "", filename)
    if name in autosaves:
        return True

    return False


def scan_dir(path):
    tracks = []
    for entry in os.scandir(path):
        if entry.is_file():
            tracks.append(entry.path)
    return tracks


if __name__ == "__main__":
    full_start = time()
    autosave_dir = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Replays/Autosaves"
    current_dir = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Challenges/Current"
    unplayed_dir = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Challenges/Unplayed"
    finished_dir = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Challenges/Finished"

    current_queue = Queue()
    autosave_queue = Queue()
    next_queue = Queue()
    replay_queue = Queue()
    event_handler = Handler()
    observer = watchdog.observers.Observer()
    observer.schedule(event_handler, path=current_dir, recursive=False)
    observer.schedule(event_handler, path=autosave_dir, recursive=False)
    observer.start()

    start = time()
    files = [entry.path for entry in os.scandir(autosave_dir) if entry.is_file()]
    with Pool(16) as pool:
        autosaves = set(pool.imap(get_replay_track_name, files))
    print(f"took {time() - start}s to scan autosaves")

    start = time()
    unplayed = scan_dir(unplayed_dir)
    current = scan_dir(current_dir)
    print(f"took {time() - start}s to scan unplayed and current")

    if len(current) == 0:
        current_queue.put("lol")

    for track in current:
        move_file(track, unplayed_dir)
    current.clear()
    add_to_next_queue()

    try:
        print(f"starting took {time() - full_start}s")
        while True:
            app()
            sleep(0.1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
