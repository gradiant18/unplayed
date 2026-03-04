import datetime
from game_session import GameSession
import time
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer
import yaml


class Handler(PatternMatchingEventHandler):
    def __init__(self, session):
        super().__init__(patterns=["*.gbx"], ignore_directories=True)
        self.session = session

    def on_modified(self, event):
        self.session.record_autosave(event.src_path)


if __name__ == "__main__":
    with open("config.yaml") as file:
        config = yaml.safe_load(file)

    session = GameSession(config)

    observer = Observer()
    observer.schedule(Handler(session), path=session.autosave_dir, recursive=False)
    observer.start()

    session.load_next()

    while True:
        try:
            if session.track_limit and len(session.finished) >= session.track_limit:
                break
            if session.stop_time and datetime.datetime.now() >= session.stop_time:
                break

            session.status()
            time.sleep(0.1)
        except KeyboardInterrupt:
            choice = input("\na) Skip b) Reload c) Quit >> ")
            if choice == "a":
                session.skip_track()
            elif choice == "b":
                session.reload_track()
            elif choice == "c":
                session.save()
                break

    observer.stop()
    observer.join()
