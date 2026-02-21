import os
import requests
import watchdog.events
import watchdog.observers
from queue import Queue


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


def get_new_track(dir_path):
    track_id = requests.get("https://tmnf.exchange/trackrandom?inhasrecord=0").url[32:]
    download_url = f"https://tmnf.exchange/trackgbx/{track_id}"
    file_name = f"{track_id}.Challenge.Gbx"
    download_path = os.path.join(dir_path, file_name)

    map_response = requests.get(download_url)
    if map_response.status_code == 200:
        with open(download_path, "wb") as file:
            file.write(map_response.content)
        return download_path
    return False


def start_up():
    # remove files in current_dir and next_dir
    for entry in os.scandir(current_dir):
        os.remove(entry)
    for entry in os.scandir(next_dir):
        os.remove(entry)

    # download track into current_dir and next_dir
    while len(current) == 0:
        current.append(get_new_track(current_dir))
    while len(next) == 0:
        next.append(get_new_track(next_dir))


autosave_dir = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Replays/Autosaves"
current_dir = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Challenges/Current"
next_dir = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Challenges/Next"
current, next = [], []

event_handler = Handler()
autosave_queue, current_queue = Queue(), Queue()
observer = watchdog.observers.Observer()
observer.schedule(event_handler, path=current_dir, recursive=False)
observer.schedule(event_handler, path=autosave_dir, recursive=False)


start_up()
