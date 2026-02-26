import json
from datetime import date


def get_todays_tracks(path):
    with open(path) as file:
        data = json.load(file)

    today = date.today()
    today = f"{today.year}-{today.month}-{today.day}"
    try:
        return data[today]
    except KeyError:
        return []


def save_todays_tracks(path, finished):
    with open(path) as file:
        data = json.load(file)

    today = date.today()
    today = f"{today.year}-{today.month}-{today.day}"
    data[today] = finished

    with open(path, "w") as file:
        json.dump(data, file, indent=2)
