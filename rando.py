import os
from queue import Queue
import requests
import time
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
            print("new autosave")
            autosave_queue.put(event.src_path)

    def on_deleted(self, event):
        if os.path.split(event.src_path)[0] == current_dir:
            print("file deleted")
            current_queue.put(event.src_path)


def get_new_track(dir_path):
    track_id = requests.get("https://tmnf.exchange/trackrandom?inhasrecord=0").url[32:]
    download_url = f"https://tmnf.exchange/trackgbx/{track_id}"
    file_name = f"{track_id}.Challenge.Gbx"
    download_path = os.path.join(dir_path, file_name)
    print(f"downloading track {track_id}")

    map_response = requests.get(download_url)
    if map_response.status_code == 200:
        with open(download_path, "wb") as file:
            file.write(map_response.content)
        return download_path
    return False


def move_track(old_path, dir_path):
    filename = os.path.split(old_path)[1]
    new_path = os.path.join(dir_path, filename)
    os.rename(old_path, new_path)
    return new_path


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


def main():
    # new autosave was created
    if not autosave_queue.empty():
        # move finished track to finished_dir
        finished_track = move_track(current[0], finished_dir)
        current.pop(0)
        finished_replay = autosave_queue.get()
        finished.append((finished_track, finished_replay))
        print(f"finished {finished_replay}")

        current.append(move_track(next[0], current_dir))
        next.pop(0)
        next.append(get_new_track(next_dir))

    # only if user deletes track in game
    if not current_queue.empty():
        if not os.listdir(current_dir):
            current.pop(0)
            current.append(move_track(next[0], current_dir))
            next.pop(0)
            next.append(get_new_track(next_dir))


autosave_dir = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Replays/Autosaves"
current_dir = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Challenges/Current"
finished_dir = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Challenges/Finished"
next_dir = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Challenges/Next"
autosave_queue, current_queue = Queue(), Queue()
current, next, finished = [], [], []

event_handler = Handler()
observer = watchdog.observers.Observer()
observer.schedule(event_handler, path=current_dir, recursive=False)
observer.schedule(event_handler, path=autosave_dir, recursive=False)
observer.start()


start_up()
print("finished start_up")
try:
    while True:
        main()
        time.sleep(0.1)
except KeyboardInterrupt:
    pass
