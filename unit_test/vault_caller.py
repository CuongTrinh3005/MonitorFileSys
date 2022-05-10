import functools
import json
import requests
from collections import namedtuple


class VaultException(Exception):
    def __init__(self, vault_error_code, message):
        self.vault_error_code = vault_error_code
        self.message = message

    def __str__(self):
        return 'An exception was raised inside Vault:\nError Code: %s\nMessage:\n%s' % (
            self.vault_error_code, self.message
        )


def _auth_required(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        return func(self, *args, **kwargs)
    return wrapper


SimulationEvent = namedtuple('SimulationEvent', ['time', 'event'])
SimulateSmartContractResult = namedtuple('SimulateSmartContractResult', ['postings'])
Posting = namedtuple(
    'Posting', ['amount', 'request_details', 'value_timestamp', 'denomination', 'account_id']
)


class Client:
    def __init__(self, *, core_api_url, auth_token):
        self._core_api_url = core_api_url.rstrip('/')
        self._auth_token = auth_token

    @_auth_required
    def _api_post(self, url, payload, timeout):
        with requests.Session() as session:
            for prefix in ("http://", "https://"):
                session.get_adapter(prefix).init_poolmanager(
                    connections=requests.adapters.DEFAULT_POOLSIZE,
                    maxsize=requests.adapters.DEFAULT_POOLSIZE,
                    source_address=("10.200.248.194", 0)
                )
            response = session.post(
                self._core_api_url + url,
                headers={
                    'Content-Type': 'application/json',
                    'X-Auth-Token': self._auth_token,
                    'grpc-timeout': timeout,
                },
                json=payload
            )
        try:
            response.raise_for_status() # noqa: RFS001
        except requests.exceptions.HTTPError as e:
            return self._handle_error(response, e)
        return response.json()

    @staticmethod
    def _handle_error(response, e):
        try:
            content = json.loads(response.text)
        except json.decoder.JSONDecodeError as json_e:
            raise json_e from e
        if 'vault_error_code' in content and 'message' in content:
            raise VaultException(content['vault_error_code'], content['message']) from e
        if 'error' in content:
            raise ValueError(content['error']) from e
        raise e

    def simulate_smart_contract(
        self, *, contract_code, start_timestamp, end_timestamp,
        template_parameters, instance_parameters, return_event_log, events,
        timeout='10S'
    ):
        payload = self._api_post(
            '/v1/smart-contracts:simulate',
            {
                'contract_code': contract_code,
                'start_timestamp': _datetime_to_rfc_3339(start_timestamp),
                'end_timestamp': _datetime_to_rfc_3339(end_timestamp),
                'template_params': template_parameters,
                'instance_params': instance_parameters,
                'return_event_log': return_event_log,
                'events': [_event_to_json(event) for event in events]
            },
            timeout='10S'
        )
        return payload


def _datetime_to_rfc_3339(dt):
    timezone_aware = dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None
    if not timezone_aware:
        raise ValueError('The datetime object passed in is not timezone-aware')
    return dt.astimezone().isoformat()


def _event_to_json(event):
    return {'timestamp': _datetime_to_rfc_3339(event.time), **event.event}