from PyQt6.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QTextEdit,
    QWidget,
    QTabWidget,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
)
import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed
from exchange import values
import csv
import re
import requests
from io import StringIO


class BannedTracksTab(QWidget):
    def __init__(self, data):
        super().__init__()
        self.site_tabs = {}
        self.data = data
        self.text_input = self.make_site_tabs()

        save = QPushButton("Save")
        save.clicked.connect(self.save_config)
        load = QPushButton("Import")
        load.clicked.connect(self.import_banned_tracks)
        export = QPushButton("Export")
        export.clicked.connect(self.export_banned_tracks)
        clear = QPushButton("Clear")
        clear.clicked.connect(self.clear_banned_tracks)
        update = QPushButton("Update")
        update.clicked.connect(self.update_banned_tracks)

        buttons = QVBoxLayout()
        for button in [save, load, export, clear, update]:
            buttons.addWidget(button)

        layout = QHBoxLayout()
        layout.addWidget(self.text_input)
        layout.addLayout(buttons)
        self.setLayout(layout)

        if self.data["auto_update"]:
            self.update_banned_tracks()

    def banned_tracks_changed(self) -> None:
        for site in self.site_tabs:
            text = self.site_tabs[site].toPlainText()
            if not (matches := re.findall(r"\d+", text)):
                ids = {}
            else:
                ids = {int(x) for x in matches}
            self.data["banned_tracks"][site] = ids

    def make_site_tabs(self) -> QTabWidget:
        tab = QTabWidget()
        for site in values:
            if site == "all":
                continue

            text_input = QTextEdit()
            site_ids = ""
            for track_id in self.data["banned_tracks"].get(site):
                site_ids += f"{track_id}\n"
            text_input.setText(site_ids)
            text_input.textChanged.connect(self.banned_tracks_changed)
            self.site_tabs.update({site: text_input})
            tab.addTab(text_input, site)

        return tab

    def get_ids_from_file(self, file_path) -> dict:
        with open(file_path, "r") as file:
            data = file.read()

        pattern = re.compile(r"\b(TMUF|TMNF|TMO|TMS|TMN)(?:-X)?\b", re.IGNORECASE)
        matches = list(pattern.finditer(data))
        if not matches:
            return {}

        ids = {}

        for i, current_match in enumerate(matches):
            base_site = current_match.group(1).upper()
            site_key = f"{base_site}-X"

            start_idx = current_match.end()

            if i + 1 < len(matches):
                end_idx = matches[i + 1].start()
            else:
                end_idx = len(data)

            section_text = data[start_idx:end_idx]
            found_ids = {int(x) for x in re.findall(r"\d+", section_text)}
            if site_key not in ids:
                ids[site_key] = set()
            ids[site_key].update(found_ids)

        return ids

    def import_banned_tracks(self) -> None:
        # import banned tracks from file
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Open File")
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setViewMode(QFileDialog.ViewMode.Detail)

        if file_dialog.exec():
            path = file_dialog.selectedFiles()[0]
            ids = self.get_ids_from_file(path)
            for site in ids:
                # update banned tracks
                current_ids = list(self.data["banned_tracks"][site])
                current_ids.extend(list(ids[site]))
                current_ids = set(current_ids)
                self.data["banned_tracks"][site] = current_ids

                # update tabs
                text = ""
                for id in current_ids:
                    text += f"{id}\n"
                self.site_tabs[site].setText(text)
                if site == "TMN-X":
                    print(self.data["banned_tracks"][site], current_ids, ids[site])

    def export_banned_tracks(self) -> None:
        # save banned tracks to file
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Export File")
        file_dialog.setNameFilter("*.yaml, *.yml, *.txt")
        if file_dialog.exec():
            ids = ""
            for site in self.data["banned_tracks"]:
                site_ids = f"{site}:"
                for track_id in self.data["banned_tracks"].get(site):
                    site_ids += f"\n - {track_id}"
                ids += f"{site_ids}\n"
            with open(file_dialog.selectedFiles()[0], "w") as file:
                file.write(ids)

    def clear_banned_tracks(self) -> None:
        # empty banned tracks
        reply = QMessageBox.question(
            self,
            "Clear Banned Tracks",
            "Are you sure you want to clear all banned tracks?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.data["banned_tracks"] = {
                "TMUF-X": [],
                "TMNF-X": [],
                "TMO-X": [],
                "TMS-X": [],
                "TMN-X": [],
            }
            for site in self.site_tabs:
                self.site_tabs[site].setText("")

    def update_banned_tracks(self) -> None:
        self.data["banned_tracks"] = self.get_cheated_ids()

        for site, tab in self.site_tabs.items():
            track_ids = self.data["banned_tracks"].get(site, [])
            site_ids = "\n".join(map(str, track_ids)) + ("\n" if track_ids else "")

            tab.textChanged.disconnect()
            tab.setText(site_ids)
            tab.textChanged.connect(self.banned_tracks_changed)

    def fetch_sheet_data(self, session, sheet_id, page_name, page_gid) -> tuple:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&tq&gid={page_gid}"
        response = session.get(url)
        response.raise_for_status()

        reader = csv.reader(StringIO(response.text))
        ids = []

        for row in reader:
            if len(row) > 1:
                val = row[1].strip()
                if val and val != "TrackID":
                    try:
                        ids.append(int(val))
                    except ValueError:
                        continue

        return page_name, ids

    def get_cheated_ids(self) -> dict:
        sheet_id = "1fqmzFGPIFBlJuxlwnPJSh1nCTTxqWXtHtvP5OUxE4Ow"
        page_ids = {
            "TMUF-X": 2132753700,
            "TMNF-X": 605781157,
            "TMO-X": 1739598690,
            "TMS-X": 1438334892,
            "TMN-X": 38022687,
        }

        cheated_ids = {}

        with requests.Session() as session:
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(self.fetch_sheet_data, session, sheet_id, name, gid)
                    for name, gid in page_ids.items()
                ]

                for future in as_completed(futures):
                    page_name, ids = future.result()
                    cheated_ids[page_name] = ids

        return cheated_ids

    def save_config(self) -> None:
        with open("data.bin", "wb") as file:
            pickle.dump(self.data, file)
