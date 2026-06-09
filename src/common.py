import re
import time

AUTOSAVE_FILE = "autosaves.txt"
CONFIG_FILE = "config.toml"
DATA_FILE = "data.json"
DOWNLOAD_DIR = "Unplayed"
LOG_FILE = "log.log"
PRESETS_DIR = "presets"

values = {
    "all": {
        "mode": ["Author", "Gold", "Silver", "Bronze", "Finished", "WR"],
        "site": ["TMUF-X", "TMNF-X", "TMO-X", "TMN-X", "TMS-X"],
        "difficulty": ["Beginner", "Intermediate", "Expert", "Lunatic"],
        "inhasrecord": ["No Records", "Has Records"],
        "mood": ["Sunrise", "Day", "Sunset", "Night"],
        "primarytype": ["Race", "Puzzle", "Platform", "Stunts", "Shortcut", "Laps"],
        "unlimiterver": ["Any", "0.4", "0.6", "0.7", "1.1", "1.2", "1.3", "2.0"],
        "inauthortimebeaten": ["Not Beaten", "Beaten"],
        "order1": [
            "",
            "Uploaded (Oldest)",
            "Uploaded (Newest)",
            "Updated (Least recent)",
            "Updated (Most recent)",
            "Awards (Least)",
            "Awards (Most)",
            "Comments (Least)",
            "Comments (Most)",
            "Activity (Least recent)",
            "Activity (Most recent)",
            "Track name (A-Z)",
            "Track name (Z-A)",
            "Author name (A-Z)",
            "Author name (Z-A)",
            "Difficulty (Easiest)",
            "Difficulty (Hardest)",
            "Downloads (Least)",
            "Downloads (Most)",
            "Track value (Least)",
            "Track value (Most)",
            "Awards this week (Least)",
            "Awards this week (Most)",
            "Awards this month (Least)",
            "Awards this month (Most)",
            "Awarded (Least recent)",
            "Awarded (Most recent)",
            "World record set (Least recent)",
            "World record set (Most recent)",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "Track Length (Shortest)",
            "Track Length (Longest)",
            "World record time (Shortest)",
            "World record time (Longest)",
        ],
    },
    "TMUF-X": {
        "url": "tmuf.exchange",
        "tag": [
            "Race",
            "Stunt",
            "Maze",
            "Offroad",
            "Multilap",
            "FullSpeed",
            "LOL",
            "Tech",
            "SpeedTech",
            "RPG",
            "PressForward",
            "Trial",
            "Grass",
            "Story",
            "Nascar",
            "SpeedFun",
            "Endurance",
            "Altered Nadeo",
            "Transitional",
        ],
        "environment": [
            "",
            "Snow",
            "Desert",
            "Rally",
            "Island",
            "Coast",
            "Bay",
            "Stadium",
        ],
    },
    "TMNF-X": {
        "url": "tmnf.exchange",
        "tag": [
            "Race",
            "Stunt",
            "Maze",
            "Offroad",
            "Multilap",
            "FullSpeed",
            "LOL",
            "Tech",
            "SpeedTech",
            "RPG",
            "PressForward",
            "Trial",
            "Grass",
            "Story",
            "Nascar",
            "SpeedFun",
            "Endurance",
            "Altered Nadeo",
            "Transitional",
        ],
        "environment": ["", "", "", "", "", "", "", "Stadium"],
    },
    "TMO-X": {
        "url": "original.tm-exchange.com",
        "tag": [
            "Race",
            "Stunt",
            "Maze",
            "Offroad",
            "Multilap",
            "FullSpeed",
            "LOL",
            "Tech",
            "SpeedTech",
            "RPG",
            "PressForward",
            "Trial",
            "Grass",
        ],
        "environment": ["", "Snow", "Desert", "Rally"],
    },
    "TMS-X": {
        "url": "sunrise.tm-exchange.com",
        "tag": [
            "Race",
            "Stunt",
            "Maze",
            "Offroad",
            "Multilap",
            "FullSpeed",
            "LOL",
            "Tech",
            "SpeedTech",
            "RPG",
            "PressForward",
            "Trial",
            "Grass",
        ],
        "environment": ["", "", "", "", "Island", "Coast", "Bay"],
    },
    "TMN-X": {
        "url": "nations.tm-exchange.com",
        "tag": [
            "Race",
            "Stunt",
            "Maze",
            "Offroad",
            "Multilap",
            "FullSpeed",
            "LOL",
            "Tech",
            "SpeedTech",
            "RPG",
            "PressForward",
            "Trial",
            "Grass",
        ],
        "environment": ["", "", "", "", "", "", "", "Stadium"],
    },
}

default_data = """exe_path = ""
track_dir = ""
force_window_size = true
auto_update = false
skip_skipped = true
default_data = true

[game_rules]
next_mode = "finished"
site = "TMNF-X"
track_limit = {enabled = false, value = 15}
time_limit = {enabled = true, value = "00:20:00"}

[track_rules]
tag = {enabled = false, value = 0}
mood = {enabled = false, value = 1}
order1 = {enabled = true, value = 39}
difficulty = {enabled = false, value = 0}
inhasrecord = {enabled = true, value = 0}
primarytype = {enabled = false, value = 0}
environment = {enabled = false, value = 7}
inunlimiter = {enabled = false, value = 0}
unlimiterver = {enabled = false, value = 0}
authortimemin = {enabled = false, value = "00:00:00"}
authortimemax = {enabled = true, value = "00:03:00"}
uploadedafter = {enabled = true, value = "2010-01-01T00:00:00"}
uploadedbefore = {enabled = true, value = "2020-12-31T23:59:59"}
inauthortimebeaten = {enabled = false, value = 0}
"""


def get_uid(path: str) -> str | None:
    """Gets UID for path"""
    for _ in range(10):
        try:
            with open(path, "rb") as file:
                data = file.read(4096)
            if data and (match := re.search(rb'uid="(\w*)"', data)):
                return match.group(1).decode("utf-8")
        except Exception as e:
            log(f"Error getting UID: {e}")
        time.sleep(0.001)
    return None


def log(msg: str):
    """Saves msg to log file"""
    with open(LOG_FILE, "a") as file:
        file.write(f"[{time.time()}] {msg}\n")
