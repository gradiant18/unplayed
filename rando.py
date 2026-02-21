import requests


def get_new_track():
    response = requests.get("https://tmnf.exchange/trackrandom?inhasrecord=0").url
    track_id = response[32:]
    print(response, track_id)

    download_url = f"https://tmnf.exchange/trackgbx/{track_id}"
    file_name = f"{track_id}.Challenge.Gbx"

    map_response = requests.get(download_url)
    if map_response.status_code == 200:
        with open(file_name, "wb") as file:
            file.write(map_response.content)


get_new_track()
