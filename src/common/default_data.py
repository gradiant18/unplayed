import datetime

today = datetime.datetime.today()

default_data = {
    "version": "2.0.0",
    "exe_path": "",
    "track_dir": "",
    "app_dir": "",
    "force_window_size": True,
    "auto_update": False,
    "skip_skipped": True,
    "default_data": True,
    "game_rules": {
        "next_mode": "finished",
        "track_limit": {"state": 0, "value": 0},
        "time_limit": {"state": 2, "value": datetime.timedelta(minutes=15)},
        "site": "TMNF-X",
    },
    "track_rules": {
        "uploadedafter": {
            "state": 0,
            "value": datetime.datetime(2008, 4, 3, 0, 0, 0),
        },
        "uploadedbefore": {
            "state": 0,
            "value": datetime.datetime(today.year, today.month, today.day, 23, 59, 59),
        },
        "authortimemin": {
            "state": 0,
            "value": 0,
        },
        "authortimemax": {
            "state": 0,
            "value": 0,
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
        "order1": {"state": 2, "value": 39, "text": "Track Length (Shortest)"},
    },
    "preset": "Default",
    "presets": {
        "Default": {
            "game_rules": {
                "next_mode": "finished",
                "track_limit": {"state": 0, "value": 1},
                "time_limit": {"state": 2, "value": datetime.timedelta(minutes=15)},
                "site": "TMNF-X",
            },
            "track_rules": {
                "uploadedafter": {
                    "state": 0,
                    "value": datetime.datetime(2008, 4, 3, 0, 0, 0),
                },
                "uploadedbefore": {
                    "state": 0,
                    "value": datetime.datetime(
                        today.year, today.month, today.day, 23, 59, 59
                    ),
                },
                "authortimemin": {
                    "state": 0,
                    "value": 0,
                },
                "authortimemax": {
                    "state": 0,
                    "value": 0,
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
                "order1": {"state": 2, "value": 39, "text": "Track Length (Shortest)"},
            },
        },
        "RMC": {
            "game_rules": {
                "next_mode": "author",
                "track_limit": {"state": 0, "value": 1},
                "time_limit": {"state": 2, "value": datetime.timedelta(hours=1)},
                "site": "TMNF-X",
            },
            "track_rules": {
                "uploadedafter": {
                    "state": 0,
                    "value": datetime.datetime(2010, 3, 1, 0, 0, 0),
                },
                "uploadedbefore": {
                    "state": 0,
                    "value": datetime.datetime(2010, 3, 31, 23, 59, 59),
                },
                "authortimemin": {
                    "state": 0,
                    "value": 0,
                },
                "authortimemax": {
                    "state": 2,
                    "value": 180000,
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
                "inhasrecord": {"state": 0, "value": 0, "text": "No Records"},
                "inauthortimebeaten": {"state": 0, "value": 0, "text": "Not Beaten"},
                "order1": {"state": 0, "value": 1, "text": "Uploaded (Oldest)"},
            },
        },
    },
    "banned_tracks": {
        "TMUF-X": set(),
        "TMNF-X": set(),
        "TMO-X": set(),
        "TMS-X": set(),
        "TMN-X": set(),
    },
}
