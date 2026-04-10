import os
import platform
import re
import requests
import subprocess
import time
from common.exchange import values


class Track:
    def __init__(self, track):
        self.name = track["TrackName"]
        self.path = ""
        self.uid = track["UId"]
        self.track_id = track["TrackId"]
        self.medals = {
            "author": track["AuthorTime"],
            "gold": track["GoldTarget"],
            "silver": track["SilverTarget"],
            "bronze": track["BronzeTarget"],
        }
        self.medal = None
        self.wr = None
        if track.get("WRReplay"):
            if track["WRReplay"].get("ReplayTime"):
                self.wr = track["WRReplay"]["ReplayTime"]

    def update_medal(self, replay_path) -> int | None:
        with open(replay_path, "rb") as file:
            data = file.read(4096)
        if not data:
            return None
        match = re.search(rb'times best="(\d*)"', data)
        if not match:
            return None
        replay_time = int(match.group(1).decode("utf-8"))

        medal = "None"
        for medal in self.medals:
            if replay_time <= self.medals[medal]:
                self.medal = medal
                break
        return replay_time

    def load(self, exe_path) -> None:
        if platform.system() == "Windows":
            command = [
                exe_path,
                "/singleinst",
                "/useexedir",
                f"/file={self.path}",
            ]
        else:
            command = [
                "protontricks-launch",
                "--appid",
                "7200",
                exe_path,
                "/singleinst",
                "/useexedir",
                f"/file={self.path}",
            ]
        subprocess.run(command)

    def download(self, track_dir, site):
        # check dir path
        unplayed_path = os.path.join(track_dir, "Challenges", "Unplayed")
        if not os.path.exists(unplayed_path):
            os.mkdir(unplayed_path)
        dir_path = os.path.join(unplayed_path, site)
        if not os.path.exists(dir_path):
            os.mkdir(dir_path)

        # check file path
        self.path = os.path.join(dir_path, f"{self.track_id}.Challenge.gbx")
        if os.path.exists(self.path):
            return

        download_url = f"https://{values[site]['url']}/trackgbx/{self.track_id}"

        retries = 0
        while retries < 3:
            try:
                track_response = requests.get(download_url, timeout=10)
                if track_response.status_code == 200:
                    with open(self.path, "wb") as file:
                        file.write(track_response.content)
                    return
                else:
                    print(track_response.status_code)
                retries += 1
                time.sleep(1)
            except requests.RequestException:
                retries += 1
                time.sleep(1)
        return

    def __str__(self):
        return str(self.__dict__)
