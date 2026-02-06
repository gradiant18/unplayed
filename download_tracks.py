import os
import requests
import random
import time
from datetime import datetime
from multiprocessing import Pool


# Function to gather all track IDs from the TMNF Exchange API
def gather_all_track_ids():
    api_url = "https://tmnf.exchange/api/tracks?fields=TrackId&count=1000&inhasrecord=0&after="
    all_track_ids = []  # List to store all Track IDs
    current_last = 0  # Initialize the last track ID for pagination

    while True:
        # Fetch tracks using the 'after' parameter for pagination
        url = api_url + str(current_last)
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # Raise error for bad HTTP status codes (4xx, 5xx)

            tracks_results = response.json().get("Results", [])
            if not tracks_results:
                print("No more tracks available.")
                break

            all_track_ids.extend([track["TrackId"] for track in tracks_results])
            current_last = tracks_results[-1]["TrackId"]
            print(f"Fetched {len(tracks_results)} tracks. Total: {len(all_track_ids)}")

            # If less than 1000 tracks were returned, we've reached the last page
            if len(tracks_results) < 1000:
                print("Finished gathering all tracks.")
                break

        except requests.RequestException as e:
            print(f"Error fetching track list: {e}. Retrying...")

    return all_track_ids


# Function to download a specified number of random maps
def download_random_maps(no_of_maps_to_download=50, save_folder="TMNF_Maps"):
    folder_path = f"/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Challenges/Downloaded/{datetime.now().strftime("%Y-%m-%d")}"
    folder_path = f"/home/russell/.local/share/Steam/steamapps/compatdata/7200/pfx/drive_c/users/steamuser/Documents/TrackMania/Tracks/Challenges/Unplayed"

    # Create the save folder if it doesn't exist
    if not os.path.exists(folder_path):
        try:
            os.makedirs(
                folder_path, exist_ok=True
            )  # Create the folder if it doesn't exist
            print(f"Folder created: {folder_path}")
        except Exception as e:
            print(f"Error creating folder: {e}")
            return

    print(f"Maps will be saved to: {folder_path}")

    # Gather all track IDs from the TMNF Exchange API
    track_ids = gather_all_track_ids()

    # Track download count
    downloaded_count = 0
    max_retries = 3  # Number of retries if request fails

    # Shuffle track IDs to download random maps
    random.shuffle(track_ids)

    # Download the specified number of random maps
    while downloaded_count < no_of_maps_to_download and track_ids:
        track_id = track_ids.pop()  # Pop a random track ID from the list
        download_url = f"https://tmnf.exchange/trackgbx/{track_id}"

        # Define a simple file name using TrackId
        file_name = f"{track_id}.Challenge.Gbx"
        file_path = os.path.join(folder_path, file_name)

        # Check if the map file already exists
        if os.path.exists(file_path):
            print(f"Map {file_name} already exists. Skipping download.")
            continue  # Skip the download if the file already exists

        # Attempt download with retry mechanism
        retries = 0
        while retries < max_retries:
            try:
                map_response = requests.get(download_url, timeout=10)
                if map_response.status_code == 200:
                    with open(file_path, "wb") as file:
                        file.write(map_response.content)
                    downloaded_count += 1
                    print(
                        f"Downloaded: {file_name:<22}{downloaded_count:>5}/{no_of_maps_to_download}"
                    )
                    break
                else:
                    print(
                        f"Failed to download map ID {track_id}, status code: {map_response.status_code}"
                    )
                retries += 1
                time.sleep(1)
            except requests.RequestException as e:
                print(
                    f"Retry {retries + 1}/{max_retries} failed for map ID {track_id}: {e}"
                )
                retries += 1
                time.sleep(1)

    print(f"Total maps downloaded: {downloaded_count}")


# Call the function to download maps
download_random_maps(1000)
