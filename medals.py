from pygbx import Gbx, GbxType
import re


def __get_replay_time(path):
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
    race_time = __get_replay_time(replay_path)
    medal_times = get_medal_times(track_path)

    if not race_time or not medal_times:
        return None

    medal = ""
    for medal_type in medal_times:
        if race_time <= medal_times[medal_type]:
            medal = medal_type
            break

    return medal
