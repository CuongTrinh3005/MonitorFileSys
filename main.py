from configuration.config import USE_FILE_TRACKER, FILE_TO_READ
from helpers.file_processing import dump_to_json, send_content_to_clipboard, simulate_contract
from helpers.watch_dog import OnMyWatch


if __name__ == '__main__':
    if USE_FILE_TRACKER:
        watch = OnMyWatch()
        watch.run()
    else:
        file_content = dump_to_json(FILE_TO_READ)
        # send_content_to_clipboard(file_content)
        simulate_contract(file_content, verbose=False, state_persisted=True)