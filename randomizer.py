import datetime
from game_session import GameSession
import os
import time
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer
import yaml


class Handler(PatternMatchingEventHandler):
    def __init__(self, session):
        super().__init__(patterns=["*.gbx"], ignore_directories=True)
        self.session = session

    def on_modified(self, event):
        self.session.update_session(event.src_path)


if __name__ == "__main__":
    if not os.path.exists("config.yaml"):
        raise FileNotFoundError("config.yaml does not exist")
    with open("config.yaml") as file:
        config = yaml.safe_load(file)
    if not config:
        raise ValueError("config.yaml is empty")

    # track_dir errors
    if not config.get("track_dir"):
        raise ValueError("track_dir is not defined")
    if os.path.exists(config["track_dir"]):
        if not os.path.isdir(config["track_dir"]):
            raise ValueError(f"{config['track_dir']} is not a directory")
    else:
        raise ValueError(f"{config['track_dir']} does not exist")

    # exe_path errors
    if not config.get("exe_path"):
        raise ValueError("exe_path is not defined")
    if os.path.exists(config["exe_path"]):
        if not os.path.isfile(config["exe_path"]):
            raise ValueError(f"{config['exe_path']} is not a file")
    else:
        raise ValueError(f"{config['exe_path']} does not exist")

    # track_rules errors
    if not config.get("track_rules"):
        raise ValueError("track_rules is not defined")
    track_rules = [
        "name",
        "author",
        "packid",
        "awardedby",
        "commentedby",
        "replaysby",
        "tag",
        "etag",
        "primarytype",
        "uploadedafter",
        "uploadedbefore",
        "authortimemin",
        "authortimemax",
        "environment",
        "mood",
        "difficulty",
        "inlatestauthor",
        "inlatestawardedauthor",
        "insupporter",
        "inreplays",
        "inhasrecord",
        "enenvmix",
        "inunlimiter",
        "unlimitedver",
        "inauthortimebeaten",
    ]
    for param in config["track_rules"]:
        if param not in track_rules:
            raise ValueError(f'"{param}" is not an accepted track rule')

    session = GameSession(config)

    observer = Observer()
    observer.schedule(Handler(session), path=session.autosave_dir, recursive=False)
    observer.start()

    session.start()

    while True:
        try:
            if session.stop_time and datetime.datetime.now() >= session.stop_time:
                break
            if session.stop:
                break

            session.status()
            time.sleep(0.1)
        except KeyboardInterrupt:
            choice = input("\na) Skip b) Reload c) Quit >> ")
            if choice == "a":
                session.skip_track()
            elif choice == "b":
                session.reload_track()
            elif choice == "c":
                session.save()
                break

    observer.stop()
    observer.join()
