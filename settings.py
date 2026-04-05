from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
    QPushButton,
)
import pickle


class SettingsTab(QWidget):
    def __init__(self, data):
        super().__init__()
        self.data = data
        # force window size true/false
        self.forced_window = QCheckBox("Force Window Size")
        self.forced_window.setChecked(self.data["force_window_size"])
        self.forced_window.stateChanged.connect(lambda state: self.change_window(state))

        # exe path
        file_browse = QPushButton("Browse")
        file_browse.clicked.connect(self.open_file_dialog)
        self.filename_edit = QLineEdit()
        self.filename_edit.setText(self.data["exe_path"])
        self.filename_edit.textEdited.connect(self.path_changed)
        exe = QGridLayout()
        exe.addWidget(QLabel("Exe Path:"), 0, 0)
        exe.addWidget(self.filename_edit, 0, 1)
        exe.addWidget(file_browse, 0, 2)

        # track dir
        dir_browse = QPushButton("Browse")
        dir_browse.clicked.connect(self.open_dir_dialog)
        self.dir_name_edit = QLineEdit()
        self.dir_name_edit.setText(self.data["track_dir"])
        self.dir_name_edit.textEdited.connect(self.path_changed)
        exe.addWidget(QLabel("Track Dir:"), 1, 0)
        exe.addWidget(self.dir_name_edit, 1, 1)
        exe.addWidget(dir_browse, 1, 2)

        # save
        save = QPushButton("Save")
        save.clicked.connect(self.save_config)

        layout = QVBoxLayout()
        layout.addWidget(self.forced_window)
        layout.addLayout(exe)
        layout.addWidget(save)
        self.setLayout(layout)

    def path_changed(self):
        self.data["exe_path"] = self.filename_edit.text()
        self.data["track_dir"] = self.dir_name_edit.text()

    def update_paths(self):
        self.filename_edit.setText(self.data["exe_path"])
        self.dir_name_edit.setText(self.data["track_dir"])

    def change_window(self, state):
        self.data["force_window_size"] = state == 2

    def open_file_dialog(self):
        filename = QFileDialog.getOpenFileName(self, "Select TMUF/TMNF Exe")[0]
        if filename:
            self.filename_edit.setText(filename)
            self.data["exe_path"] = filename

    def open_dir_dialog(self):
        dir_name = QFileDialog.getExistingDirectory(self, "Select Track Directory")
        if dir_name:
            self.dir_name_edit.setText(dir_name)
            self.data["track_dir"] = dir_name

    def save_config(self) -> None:
        with open("data.bin", "wb") as file:
            pickle.dump(self.data, file)
