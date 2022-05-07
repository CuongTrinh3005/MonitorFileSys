import json
import pyperclip
from config import USE_TEMPLATES
from templates import data


def read_file(path):
    with open(path) as file:
        return str(file.read())


def dump_to_json(path):
    file_content = read_file(path)
    data = {'code': file_content}
    return json.dumps(data)


def send_content_to_clipboard(content):
    if not USE_TEMPLATES:
        payload = content[1:len(content)-1]
    else:
        payload_str = json.dumps(data)
        payload_dict = json.loads(payload_str)
        content_dict = json.loads(content)
        payload_dict['smart_contracts'][0]['code'] = content_dict['code']
        payload = json.dumps(payload_dict)
    pyperclip.copy(payload)
