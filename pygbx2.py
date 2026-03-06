from pygbx import Gbx, GbxType
from re import search


def get_replay_time(path):
    if not (ghost := Gbx(path).get_class_by_id(GbxType.CTN_GHOST)):
        return None
    return ghost.race_time


def get_uid(path):
    with open(path, "rb") as file:
        data = str(file.read())
    if not (match := search(r'uid="\w*"', data)):
        return None
    return match.group()[5:-1]
