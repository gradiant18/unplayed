import os
from pygbx import Gbx, GbxType
import re
import requests
from time import sleep, time
import logging


class ErrorInterceptor(logging.Handler):
    def emit(self, record):
        if "Failed to read string" in record.getMessage():
            raise RuntimeError()


logger = logging.getLogger()
logger.addHandler(ErrorInterceptor())
finished_dir = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Challenges/Finished"
current_dir = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Challenges/Current"
unplayed_dir = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Challenges/Unplayed"
autosaves_dir = "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Replays/Autosaves"
clean_string = r"[^a-zA-Z0-9\"\'\\[\]\$\(\)\.\ \-]"


# TODO: combine with has_record to avoid multiple api calls
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
    _, filename = os.path.split(path)
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
        print(path)
        return None


def get_track_id(path):
    match = re.search(r"\/\d+\.", path)
    if not match:
        return None
    return match.group()[1:-1]


def has_record(track_id):
    url = "https://tmnf.exchange/api/tracks"
    params = {"fields": "TrackName", "id": track_id, "inhasrecord": 1}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return bool(response.json().get("Results"))
    except requests.RequestException as e:
        print(f"Request Error: {e}")
        return False


def scan_tracks(path):
    tracks = []
    for entry in os.scandir(path):
        if not entry.is_file():
            continue

        track_id = get_track_id(entry.path)
        track_name = get_track_name(entry.path)
        tracks.append({"path": entry, "id": track_id, "name": track_name})
    return tracks


def scan_replays(path):
    replays = []
    for entry in os.scandir(path):
        if not entry.is_file():
            continue
        name = get_replay_track_name(entry.path)
        replays.append({"path": entry, "name": name})
    return replays


def main(medals_collected):
    current = scan_tracks(current_dir)
    autosaves = scan_replays(autosaves_dir)

    for track in current:
        for autosave in autosaves:
            if autosave["name"] == track["name"]:
                print(f"{track['name']} is finished")

                # get medal type
                medal = get_medal(autosave["path"].path, track["id"])
                medals_collected[medal] += 1

                # move track into finished directory
                _, file = os.path.split(track["path"])
                new_path = os.path.join(finished_dir, file)
                os.rename(track["path"], new_path)

                current.remove(track)  # update current

    while len(current) < 2:
        track = unplayed.pop()

        # don't add played maps to current
        if has_record(track["path"]):
            os.remove(track["path"])
            continue

        # move track into current list
        _, file = os.path.split(track["path"])
        new_path = os.path.join(current_dir, file)
        os.rename(track["path"], new_path)

        # update current
        track["path"] = new_path
        current.append(track)
        print(f"Added {track['name']} to current")

    return medals_collected


mode = "free"
timer = 7 * 60
target = 2
medals_collected = {"author": 0, "gold": 0, "silver": 0, "bronze": 0, "none": 0}
unplayed = scan_tracks(unplayed_dir)
current = scan_tracks(current_dir)
for track in current:  # remove played maps from current
    if has_record(track["path"]):
        os.remove(track["path"])
        current.pop(track)


match mode:
    case "free":
        while True:
            tracks_done = main(medals_collected)
            print(tracks_done, end="\r")
            sleep(0.5)
    case "timed":
        end_time = time() + timer
        while time() < end_time:
            tracks_done = main(medals_collected)
            t = end_time - time()
            print(f"{tracks_done}, {t = :.0f}", end="\r")
            sleep(0.5)
    case "target":
        total = 0
        while total < target - 1:
            tracks_done = main(medals_collected)
            for medal_type in tracks_done:
                total += tracks_done[medal_type]
            print(f"{tracks_done}, {total = }", end="\r")
            sleep(0.5)
