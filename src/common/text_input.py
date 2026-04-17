from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton, QInputDialog


class TextInput(QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.btn = QPushButton("Get Text", self)
        self.btn.clicked.connect(self.getText)
        layout.addWidget(self.btn)

        self.text_edit = QLineEdit(self)
        layout.addWidget(self.text_edit)

        self.setLayout(layout)

    def getText(self):
        text, okPressed = QInputDialog.getText(
            self, "New Preset", "Name your new preset:"
        )
        if okPressed and text != "":
            return text
