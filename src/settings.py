import shutil
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QMessageBoxو
)


class SettingsTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.parent_window = main_window
        self.data = self.parent_window.data

        # force window size true/false
        self.forced_window = QCheckBox("Force Window Size (Requires Restart)")
        self.forced_window.setChecked(self.data["force_window_size"])
        self.forced_window.stateChanged.connect(lambda state: self.change_window(state))

        # auto update banned tracks
        self.auto_update = QCheckBox("Auto Update Banned Tracks")
        self.auto_update.setChecked(self.data["auto_update"])
        self.auto_update.stateChanged.connect(lambda state: self.change_update(state))

        # don't play skipped tracks
        self.skip_skipped = QCheckBox("Don't Play Skipped Tracks")
        self.skip_skipped.setChecked(self.data.get("skip_skipped", False))
        self.skip_skipped.stateChanged.connect(lambda state: self.change_skip(state))

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

        # delete data
        delete_button = QPushButton("Delete all data")
        delete_button.clicked.connect(self.delete_data)

        # save
        save = QPushButton("Save")
        save.clicked.connect(self.parent_window.save_config)

        layout = QVBoxLayout()
        layout.addWidget(self.forced_window)
        layout.addWidget(self.auto_update)
        layout.addWidget(self.skip_skipped)
        layout.addLayout(exe)
        layout.addWidget(delete_button)
        layout.addWidget(save)
        self.setLayout(layout)

    def change_window(self, state):
        self.data["force_window_size"] = state == 2

    def change_update(self, state):
        self.data["auto_update"] = state == 2

    def change_skip(self, state):
        self.data["skip_skipped"] = state == 2

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

    def path_changed(self):
        self.data["exe_path"] = self.filename_edit.text()
        self.data["track_dir"] = self.dir_name_edit.text()

    def update_paths(self):
        self.filename_edit.setText(self.data["exe_path"])
        self.dir_name_edit.setText(self.data["track_dir"])
    
    def delete_data(self):
        # إضافة رسالة تأكيد لتوحيد نمط الكود في المشروع (Consistency)
        reply = QMessageBox.question(
            self,
            "Delete All Data",
            "Are you sure you want to delete all data? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        # لا يتم المسح إلا إذا ضغط المستخدم على Yes
        if reply == QMessageBox.StandardButton.Yes:
            data_path = self.data["app_dir"]
            shutil.rmtree(data_path)
