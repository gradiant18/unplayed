import datetime

default_data = {
    "exe_path": "/home/russell/.local/share/Steam/steamapps/common/TrackMania United/TmForever.exe",
    "track_dir": "/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks",
    "game_rules": {
        "next_mode": "finished",
        "track_limit": 0,
        "time_limit": datetime.timedelta(minutes=15),
        "site": "TMNF-X",
    },
    "track_rules": {
        "uploadedafter": {
            "state": 2,
            "value": datetime.datetime(2010, 2, 1, 0, 0, 0),
        },
        "uploadedbefore": {
            "state": 2,
            "value": datetime.datetime(2010, 2, 28, 23, 59, 59),
        },
        "authortimemin": {
            "state": 0,
            "value": 0,
        },
        "authortimemax": {
            "state": 2,
            "value": 105000,
        },
        "inunlimiter": {
            "state": 0,
            "value": 0,
        },
        "unlimiterver": {"state": 0, "value": 0, "text": "Any"},
        "tag": {"state": 0, "value": 0, "text": "Race"},
        "primarytype": {"state": 0, "value": 0, "text": "Race"},
        "environment": {"state": 0, "value": 7, "text": "Stadium"},
        "mood": {"state": 0, "value": 1, "text": "Day"},
        "difficulty": {"state": 0, "value": 0, "text": "Beginner"},
        "inhasrecord": {"state": 2, "value": 0, "text": "No Records"},
        "inauthortimebeaten": {"state": 0, "value": 0, "text": "Not Beaten"},
    },
}
