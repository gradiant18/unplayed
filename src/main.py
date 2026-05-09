import argparse
import sys

from PyQt6.QtWidgets import QApplication

from model import ConfigModel
from presenter import AppPresenter
from view import MainWindow

VERSION = "2.0.0"


def main():
    parser = argparse.ArgumentParser(description="Play random tracks in TMNF/TMUF")
    parser.add_argument(
        "-n", "--nolaunch", action="store_true", help="Don't launch tracks in game"
    )
    args = parser.parse_args()

    app = QApplication(sys.argv)
    model = ConfigModel(VERSION, args.nolaunch)
    view = MainWindow()
    presenter = AppPresenter(model, view)
    view.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
