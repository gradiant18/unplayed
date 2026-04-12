# Overview

unplayed is a simple utility to play random tracks for TMNF/TMUF  
![game screen](/assets/game.png)

## Requirements

- TMNF/TMUF installed with Steam
- [protontricks](https://github.com/Matoking/protontricks) (if on Linux)

## Setup

The first time the program is run, there will be 2 pop-ups.  
First, location of the trackmania exe.  
![find exe screen](/assets/find_exe.png)

Then, location where the tracks are stored.
![find tracks screen](/assets/find_tracks.png)

## Options

![options screen](/assets/options.png)

| Name            | Description                                                |
| --------------- | ---------------------------------------------------------- |
| Next Mode       | When to go to the next track (eg. Finished)                |
| Track Limit     | How many tracks to play before stopping                    |
| Time Limit      | How long to play before stopping                           |
| Site            | Which site to get tracks from (eg. TMNF)                   |
| Uploaded After  | Only play tracks uploaded after this date                  |
| Uploaded Before | Only play tracks uploaded before this date                 |
| Tag             | Only play tracks that has this tag (eg. FullSpeed)         |
| Min AT          | Only play tracks with author time longer than this time    |
| Max AT          | Only play tracks with author time shorter than this time   |
| Style           | Only play tracks that are this style (eg. Race)            |
| Environment     | Only play tracks from this environment (eg. Stadium)       |
| Mood            | Only play tracks from this mood (eg. Day)                  |
| Difficulty      | Only play tracks with this difficulty (eg. Beginner)       |
| Records         | Only play tracks with or without records                   |
| Unlimiter       | Only play tracks with specific unlimiter version (eg. 2.0) |
| Sort Order      | Play tracks in this order (eg. Track Length (Shortest))    |

## Banned tracks

![banned tracks screen](/assets/banned_tracks.png)

Will not play any tracks with track id as specified in each site tab.

| Name   | Description                                                                                                                                                         |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Import | Import tracks from a file and appends to current banned tracks                                                                                                      |
| Export | Export banned tracks to a file, yaml format                                                                                                                         |
| Clear  | Clears all banned tracks from all sites                                                                                                                             |
| Update | Sets all banned tracks to the same as from the [Cheated Map List](https://docs.google.com/spreadsheets/d/1fqmzFGPIFBlJuxlwnPJSh1nCTTxqWXtHtvP5OUxE4Ow/) spreadsheet |

## Settings

![settings screen](/assets/settings.png)

| Name                      | Description                                            |
| ------------------------- | ------------------------------------------------------ |
| Force Window Size         | Forces the window size so it can't be resized          |
| Auto Update Banned Tracks | At startup, update banned tracks from Cheated Map List |
| Don't Play Skipped Tracks | Saves skipped tracks to file and won't play them again |
| Delete all data           | Deletes all saved data (Doesn't change UI)             |
