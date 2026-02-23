import os
from pygbx import Gbx, GbxType
from queue import Queue
import re
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
    random_url = """
        https://tmnf.exchange/trackrandom?inhasrecord=0&uploadedbefore=2010-02-28&uploadedafter=2010-02-01&authortimemax=30999
    """

    track_id = requests.get(random_url).url[32:]
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
        finished_queue.put((finished_replay, finished_track))
        print(f"finished {finished_replay}")

        # move next track and download new one
        current.append(move_track(next[0], current_dir))
        next.pop(0)
        next.append(get_new_track(next_dir))

    # only if user deletes track in game
    if not current_queue.empty():
        current_queue.get()
        if not os.listdir(current_dir):
            current.pop(0)
            current.append(move_track(next[0], current_dir))
            next.pop(0)
            next.append(get_new_track(next_dir))

    if not finished_queue.empty():
        replay, track = finished_queue.get()
        medal = medal_detector(replay, track)
        if medal:
            print(f"You got the {medal} medal!")
            finished.append(medal)
        else:
            print("You didn't get any medal :(")
            finished.append("none")


autosave_dir = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Replays/Autosaves"
current_dir = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Challenges/Current"
finished_dir = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Challenges/Finished"
next_dir = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Challenges/Next"
autosave_queue, current_queue, finished_queue = Queue(), Queue(), Queue()
current, next, finished = [], [], []

event_handler = Handler()
observer = watchdog.observers.Observer()
observer.schedule(event_handler, path=current_dir, recursive=False)
observer.schedule(event_handler, path=autosave_dir, recursive=False)
observer.start()

st = time.time()
start_up()
print(f"finished start_up in {time.time() - st}s")
try:
    while True:
        main()
        time.sleep(0.1)
except KeyboardInterrupt:
    print(finished)
