import json
import requests
import pyperclip
from pprint import pprint
from configuration.config import USE_TEMPLATES
from configuration.templates import data


url = "https://core-api-demo.grasshopper.tmachine.io/v1/contracts:simulate"
headers = {
  'X-Auth-Token': 'A0003846294086802479307!UKizTC7qz5oAypR9nky/WQUtZ6L6dJPdIL6kOQNGWeW3KwLmhUdXIIYlwKFuj3uKGW38xbDyD5TKodX1xYeUQhSB/1Q=',
  'Content-Type': 'application/json'
}


def read_file(path):
    with open(path) as file:
        return str(file.read())


def dump_to_json(path):
    file_content = read_file(path)
    payload = {'code': file_content}
    return json.dumps(payload)


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


def simulate_contract(content, verbose=False, state_persisted=False):
    payload_str = json.dumps(data)
    payload_dict = json.loads(payload_str)
    content_dict = json.loads(content)
    payload_dict['smart_contracts'][0]['code'] = content_dict['code']
    payload = json.dumps(payload_dict)

    response = requests.request("POST", url, headers=headers, data=payload)
    results = response.text.strip().split("\n")

    if verbose:
        for result in results:
            pprint(json.loads(result))

    if state_persisted:
        list_of_dicts = [json.loads(result) for result in results]
        string_list_of_dicts = json.dumps(list_of_dicts, indent=4)

        with open("outputs/results.json", "w") as file:
            file.write(string_list_of_dicts)
