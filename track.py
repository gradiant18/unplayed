import os
import platform
from pygbx import Gbx, GbxType
import requests
import subprocess
import time


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

    def update_medal(self, replay_path):
        if not (ghost := Gbx(replay_path).get_class_by_id(GbxType.CTN_GHOST)):
            return None

        medal = "None"
        for medal in self.medals:
            if ghost.race_time <= self.medals[medal]:
                self.medal = medal
                break
        return ghost.race_time

    # TODO: make not os/program dependent
    def load(self, exe_path, debug):
        if platform.system() == "Windows":
            command = [
                exe_path,
                "/singleinst",
                f"/file={self.path}",
            ]
        else:
            command = [
                "protontricks-launch",
                "--appid",
                "7200",
                exe_path,
                "/singleinst",
                f"/file={self.path}",
            ]

        if not debug:
            subprocess.run(command)

    def download(self, track_dir, site):
        # check dir path
        dir_path = os.path.join(track_dir, "Challenges/Randomizer", site)
        if not os.path.exists(dir_path):
            os.mkdir(dir_path)

        # check file path
        self.path = os.path.join(dir_path, f"{self.track_id}.Challenge.gbx")
        if os.path.exists(self.path):
            return

        # get download url
        sites = {
            "TMUF-X": "tmuf.exchange",
            "TMNF-X": "tmnf.exchange",
            "TMO-X": "original.tm-exchange.com",
            "TMS-X": "sunrise.tm-exchange.com",
            "TMN-X": "nations.tm-exchange.com",
        }
        download_url = f"https://{sites[site]}/trackgbx/{self.track_id}"

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
            except requests.RequestException as e:
                print(f"Retry {retries + 1}/3 failed: {e}")
                retries += 1
                time.sleep(1)
        return

    def __str__(self):
        return str(self.__dict__)
