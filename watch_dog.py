from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime

from config import FILE_TO_READ
from file_processing import dump_to_json, send_content_to_clipboard


class OnMyWatch:
    # Set the directory on watch
    watchDirectory = FILE_TO_READ

    def __init__(self):
        self.observer = Observer()

    def run(self):
        event_handler = Handler()
        self.observer.schedule(event_handler, self.watchDirectory, recursive=True)
        self.observer.start()
        try:
            while True:
                pass
        except:
            self.observer.stop()
            print("Observer Stopped")

        self.observer.join()


class Handler(FileSystemEventHandler):
    @staticmethod
    def on_any_event(event):
        if event.is_directory:
            return None

        elif event.event_type == 'created' or event.event_type == 'modified':
            # Event is created, you can process it now
            file_path = event.src_path
            print("Watchdog received created/ modified event - % s." % file_path)
            print("At timestamp: ", datetime.now())
            file_content = dump_to_json(file_path)
            send_content_to_clipboard(file_content)