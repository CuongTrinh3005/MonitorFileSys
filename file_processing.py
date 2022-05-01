import json
import pyperclip


def read_file(path):
    with open(path) as file:
        return str(file.read())


def dump_to_json(path):
    file_content = read_file(path)
    data = {'code': file_content}
    return json.dumps(data)


def send_content_to_clipboard(content):
    pyperclip.copy(content[1:len(content)-1])