from datetime import date
import json
from multiprocessing import Pool
import os
from pygbx import Gbx, GbxType
from queue import Queue
from random import shuffle
import re
import requests
import sys
from time import sleep
import watchdog.events
import watchdog.observers


class Handler(watchdog.events.PatternMatchingEventHandler):
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


def filter(track, max_time):
    medal_times = get_medal_times(track)
    if not medal_times:
        return False
    if medal_times["gold"] < max_time * 1000:
        return True
    return False


def add_to_next_queue():
    max_time = 30
    shuffle(unplayed)
    while next_queue.empty():
        try:
            track = unplayed.pop()
        except IndexError:
            unplayed.extend(scan_dir(unplayed_dir))
            max_time += 5
            print(f"max_time increased to {max_time}")
            continue

        if not filter(track, max_time):
            continue
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
        medal = medal_detector(replay, track)
        if medal:
            print(f"You got the {medal} medal!")
        else:
            print("You didn't get any medal :(")
        finished.append(medal)
        print(f"You've completed {len(finished)} tracks so far.")


def get_replay_time(path):
    ghost = Gbx(path).get_class_by_id(GbxType.CTN_GHOST)
    if not ghost:
        return None

    return ghost.race_time


def get_medal_times(path):
    with open(path, "rb") as file:
        data = str(file.read())

    medal_times = []
    regexes = [r'ortime="\d+"', r'" gold="\d+"', r'silver="\d+"', r'bronze="\d+"']
    for regex in regexes:
        if match := re.search(regex, data):
            medal_times.append(int(match.group()[8:-1]))
        else:
            return None

    return {
        "author": medal_times[0],
        "gold": medal_times[1],
        "silver": medal_times[2],
        "bronze": medal_times[3],
    }


def medal_detector(replay_path, track_path):
    race_time = get_replay_time(replay_path)
    medal_times = get_medal_times(track_path)

    if not race_time or not medal_times:
        return None

    medal = ""
    for medal_type in medal_times:
        if race_time <= medal_times[medal_type]:
            medal = medal_type
            break

    return medal


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


def get_todays_tracks():
    with open("sessions.json") as file:
        data = json.load(file)

    today = date.today()
    today = f"{today.year}-{today.month}-{today.day}"
    try:
        return data[today]
    except KeyError:
        return None


def save_todays_tracks():
    with open("sessions.json") as file:
        data = json.load(file)

    today = date.today()
    today = f"{today.year}-{today.month}-{today.day}"
    data[today] = finished

    with open("sessions.json", "w") as file:
        json.dump(data, file, indent=2)


def tracks_played_today():
    medals = get_todays_tracks()
    if not medals:
        return []
    else:
        return medals


if __name__ == "__main__":
    if len(sys.argv) == 2:
        target_tracks = int(sys.argv[1])
    else:
        target_tracks = 50

    tracks = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/"
    autosave_dir = f"{tracks}/Replays/Autosaves"
    current_dir = f"{tracks}/Challenges/Current"
    unplayed_dir = f"{tracks}/Challenges/Unplayed"
    finished_dir = f"{tracks}/Challenges/Finished"

    current_queue = Queue()
    autosave_queue = Queue()
    next_queue = Queue()
    replay_queue = Queue()
    event_handler = Handler()
    observer = watchdog.observers.Observer()
    observer.schedule(event_handler, path=current_dir, recursive=False)
    observer.schedule(event_handler, path=autosave_dir, recursive=False)
    observer.start()

    files = [entry.path for entry in os.scandir(autosave_dir) if entry.is_file()]
    with Pool(16) as pool:
        autosaves = set(pool.imap(get_replay_track_name, files))

    if not (entries := list(os.scandir(current_dir))):
        current_queue.put("")
    for entry in entries:
        move_file(entry.path, unplayed_dir)

    current = []
    unplayed = scan_dir(unplayed_dir)
    add_to_next_queue()

    finished = tracks_played_today()
    try:
        while len(finished) < target_tracks:
            app()
            sleep(0.1)
    except KeyboardInterrupt:
        pass

    print(finished)
    print(len(finished))
    save_todays_tracks()
    observer.stop()
    observer.join()
