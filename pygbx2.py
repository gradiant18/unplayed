from pygbx import Gbx, GbxType
from re import search


def get_replay_time(path):
    if not (ghost := Gbx(path).get_class_by_id(GbxType.CTN_GHOST)):
        return None
    return ghost.race_time


def get_medal_time(path, medal):
    with open(path, "rb") as file:
        data = str(file.read())

    regexes = {
        "author": r'ortime="\d+"',
        "gold": r'" gold="\d+"',
        "silver": r'silver="\d+"',
        "bronze": r'bronze="\d+"',
    }
    if not (match := search(regexes[medal], data)):
        return None
    return int(match.group()[8:-1])


def _get_all_medal_times(path):
    with open(path, "rb") as file:
        data = str(file.read())

    regexes = {
        "author": r'ortime="\d+"',
        "gold": r'" gold="\d+"',
        "silver": r'silver="\d+"',
        "bronze": r'bronze="\d+"',
    }
    medals = []
    for medal in regexes:
        if not (match := search(regexes[medal], data)):
            return None
        medals.append(int(match.group()[8:-1]))
    return {
        "author": medals[0],
        "gold": medals[1],
        "silver": medals[2],
        "bronze": medals[3],
    }


def get_medal(replay_path, track_path):
    race_time = get_replay_time(replay_path)
    medal_times = _get_all_medal_times(track_path)

    if not race_time or not medal_times:
        return None

    medal = ""
    for medal_type in medal_times:
        if race_time <= medal_times[medal_type]:
            medal = medal_type
            break

    return medal


def get_uid(path):
    with open(path, "rb") as file:
        data = str(file.read())
    if not (match := search(r'uid="\w*"', data)):
        return None
    return match.group()[5:-1]
