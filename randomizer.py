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

    start = time.perf_counter()
    session = GameSession(config)
    print(f"\nTook {time.perf_counter() - start}s to create GameSession")

    observer = Observer()
    observer.schedule(Handler(session), path=session.autosave_dir, recursive=False)
    observer.start()

    start = time.perf_counter()
    session.load_next()
    print(f"\nTook {time.perf_counter() - start}s to load next")

    not_working = []
    while True:
        try:
            if session.track_limit and len(session.finished) >= session.track_limit:
                break
            if session.stop_time and datetime.datetime.now() >= session.stop_time:
                break

            print(session, end="\r")
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
            elif choice == "d":
                not_working.append((session.current_track, session.current_uid))

    observer.stop()
    observer.join()
    print("\n", not_working)
