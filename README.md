# Overview

Unplayed is a simple utility to play random tracks for TMNF/TMUF  
![game screen](/assets/game.png)

## Requirements

- TMNF/TMUF installed with Steam
- [protontricks](https://github.com/Matoking/protontricks) (if on Linux)

## Options

![options screen](/assets/options.png)

| Name            | Description                                                |
| --------------- | ---------------------------------------------------------- |
| Next Mode       | When to go to the next track (eg. Finished)                |
| Track Limit     | How many tracks to complete before stopping                |
| Time Limit      | How long to play before stopping                           |
| Site            | Which site to get tracks from (eg. TMNF)                   |
| Uploaded After  | Only play tracks uploaded after this date                  |
| Uploaded Before | Only play tracks uploaded before this date                 |
| Min AT          | Only play tracks with author time longer than this time    |
| Max AT          | Only play tracks with author time shorter than this time   |
| Mood            | Only play tracks from this mood (eg. Day)                  |
| Tag             | Only play tracks that has this tag (eg. FullSpeed)         |
| Style           | Only play tracks that are this style (eg. Race)            |
| Difficulty      | Only play tracks with this difficulty (eg. Beginner)       |
| Environment     | Only play tracks from this environment (eg. Stadium)       |
| Records         | Only play tracks with or without records                   |
| Author Time     | Only play tracks with or without a beaten author time      |
| Sort Order      | Play tracks in this order (eg. Track Length (Shortest))    |
| Unlimiter       | Only play tracks with specific unlimiter version (eg. 2.0) |

## Banned tracks

Will not play any tracks with track ID as specified in each site tab.
![banned tracks screen](/assets/banned_tracks.png)

| Name   | Description                                                                                                                                                         |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Save   | Saves ID's to file                                                                                                                                                  |
| Clear  | Clears all banned tracks from all sites                                                                                                                             |
| Update | Sets all banned tracks to the same as from the [Cheated Map List](https://docs.google.com/spreadsheets/d/1fqmzFGPIFBlJuxlwnPJSh1nCTTxqWXtHtvP5OUxE4Ow/) spreadsheet |

## Settings

![settings screen](/assets/settings.png)

| Name                      | Description                                            |
| ------------------------- | ------------------------------------------------------ |
| Force Window Size         | Forces the window size so it can't be resized          |
| Auto Update Banned Tracks | At startup, update banned tracks from Cheated Map List |
| Don't Play Skipped Tracks | Saves skipped tracks to file and won't play them again |
| Theme                     | Select window theme                                    |
| Rescan Autosaves          | Rescans autosaves                                      |
| Reset To Defaults         | Resets all settings and options to their defaults      |
