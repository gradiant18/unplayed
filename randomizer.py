import os
import time
import yaml
from game import Game


if __name__ == "__main__":
    # config file
    if not os.path.exists("config.yaml"):
        raise FileNotFoundError("config.yaml does not exist")
    with open("config.yaml") as file:
        config = yaml.safe_load(file)
    if not config:
        raise ValueError("config.yaml is empty")

    # exe_path errors
    if not config.get("exe_path"):
        raise ValueError("exe_path is not defined")
    if os.path.exists(config["exe_path"]):
        if not os.path.isfile(config["exe_path"]):
            raise ValueError(f"{config['exe_path']} is not a file")
    else:
        raise ValueError(f"{config['exe_path']} does not exist")

    # track_dir errors
    if not config.get("track_dir"):
        raise ValueError("track_dir is not defined")
    if os.path.exists(config["track_dir"]):
        if not os.path.isdir(config["track_dir"]):
            raise ValueError(f"{config['track_dir']} is not a directory")
    else:
        raise ValueError(f"{config['track_dir']} does not exist")

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
        "inenvmix",
        "inunlimiter",
        "unlimiterver",
        "inauthortimebeaten",
    ]
    for param in config["track_rules"]:
        if param not in track_rules:
            raise AttributeError(f'"{param}" is not an accepted track rule')

    session = Game(config)
    session.start()

    while not session.stopped:
        try:
            print(session, end="\r")
            time.sleep(0.1)
        except KeyboardInterrupt:
            choice = input("\na) Skip b) Reload c) Quit >> ")
            if choice == "a":
                session.skip()
            elif choice == "b":
                session.reload()
            elif choice == "c":
                session.stop()
    print("session ended")
