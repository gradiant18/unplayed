import os
from multiprocessing import Pool
from pygbx2 import get_uid
from datetime import datetime, timedelta


def _get_autosaves(self):
    files = []
    for entry in os.scandir(self.autosave_dir):
        if entry.is_file():
            files.append(entry.path)
    with Pool(16) as pool:
        autosaves = set(pool.imap_unordered(get_uid, files))
    return autosaves


def _get_site_url(self):
    sites = {
        "TMUF-X": "tmuf.exchange",
        "TMNF-X": "tmnf.exchange",
        "TMO-X": "original.tm-exchange.com",
        "TMS-X": "sunrise.tm-exchange.com",
        "TMN-X": "nations.tm-exchange.com",
    }
    return sites[self.site]


def _calculate_stop_time(self):
    limit = self.time_limit
    if not limit:
        return None

    if isinstance(limit, int):
        return datetime.now() + timedelta(seconds=limit)
    dt = timedelta(
        hours=int(limit[:2]), minutes=int(limit[3:5]), seconds=int(limit[6:])
    )
    return datetime.now() + dt


def _format_timedelta(self, td):
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    seconds += td.microseconds / 1e6
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d}"
