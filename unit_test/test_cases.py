import vault_caller
from datetime import datetime, timezone
import os
import unittest

from helpers.figure_processing import truncate

core_api_url = 'https://core-api-demo.grasshopper.tmachine.io'
auth_token = 'A0003846294086802479307!UKizTC7qz5oAypR9nky/WQUtZ6L6dJPdIL6kOQNGWeW3KwLmhUdXIIYlwKFuj3uKGW38xbDyD5TKodX1xYeUQhSB/1Q='
CONTRACT_FILE = '/Users/cgth/PycharmProjects/SmartContractAssignment/contracts/exercise_contract.py'


class TutorialTest(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        contract = os.path.join(os.path.dirname(__file__), CONTRACT_FILE)
        if not core_api_url or not auth_token:
            raise ValueError("Please provide values for core_api_url and auth_token, these should "
                             "be provided by your system administrator.")
        with open(contract) as smart_contract_file:
            self.smart_contract_contents = smart_contract_file.read()
        self.client = vault_caller.Client(
            core_api_url=core_api_url,
            auth_token=auth_token
        )
        self.template_params = {
            "denomination": "[\"GBP\", \"HKD\"]",
            "interest_rate": "0.05",
            "internal_account_1": "1111",
            "internal_account_2": "2222",
            "internal_account_3": "3333",
            "total_days": "365",
            "accrue_digits": "5",
            "apply_digits": "2"
        }

    def test_accrue_success(self):
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2019, month=1, day=2, tzinfo=timezone.utc)
        template_params = self.template_params
        instance_params = {}
        deposit_event = {
            "posting_instruction_batch": {
                "client_id": "Visa",
                "client_batch_id": "123",
                "posting_instructions": [{
                    "inbound_hard_settlement": {"amount": "1000", "denomination": "GBP",
                                                "target_account_id": "Main account"}, "internal_account_id": "3333",
                    "client_transaction_id": "123456",
                    "pics": ["FEES"],
                    "instruction_details": {"description": "happy case"},
                }],
                "batch_details": {"description": "test"},
                "value_timestamp": "2019-01-01T01:00:00+00:00"
            }
        }
        events = [vault_caller.SimulationEvent(start, deposit_event)]
        res = self.client.simulate_smart_contract(contract_code=self.smart_contract_contents,
                                                  start_timestamp=start, end_timestamp=end,
                                                  template_parameters=template_params,
                                                  instance_parameters=instance_params,
                                                  return_event_log=True,
                                                  events=events)

        # Check the events schedules
        self.assertEqual(res['scheduled_events'][0]['event_type'], 'ACCRUE_INTEREST')
        self.assertEqual(res['scheduled_events'][1]['event_type'], 'APPLY_ACCRUED_INTEREST')
        self.assertEqual(res['v3_balance_timeseries'][1]['value_timestamp'], '2019-01-02T00:00:00Z')

        # Check the money movement when being accrued
        expect_accrued_amount = \
            float(deposit_event['posting_instruction_batch']['posting_instructions'][0]['inbound_hard_settlement'][
                      'amount']) * \
            float(self.template_params['interest_rate']) / int(self.template_params['total_days'])
        self.assertEqual(res['v3_balance_timeseries'][1]['amount'], str(truncate(0 - expect_accrued_amount, 5)))
        self.assertEqual(res['v3_balance_timeseries'][1]['account_address'], 'INTERNAL')
        self.assertEqual(res['v3_balance_timeseries'][2]['amount'], str(truncate(expect_accrued_amount, 5)))
        self.assertEqual(res['v3_balance_timeseries'][2]['account_address'], 'ACCRUED_INCOMING_ADDRESS')

    def test_balance_negative(self):
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2019, month=1, day=2, tzinfo=timezone.utc)
        template_params = self.template_params
        instance_params = {}
        deposit_event = {
            "posting_instruction_batch": {
                "client_id": "Visa",
                "client_batch_id": "123",
                "posting_instructions": [{
                    "inbound_hard_settlement": {"amount": "1000", "denomination": "GBP",
                                                "target_account_id": "Main account"}, "internal_account_id": "3333",
                    "client_transaction_id": "123456",
                    "pics": ["FEES"],
                    "instruction_details": {"description": "balance negative case"}},
                    {
                        "outbound_hard_settlement": {"amount": "1200", "denomination": "GBP",
                                                    "target_account_id": "Main account"}, "internal_account_id": "3333",
                        "client_transaction_id": "123452",
                        "pics": ["FEES"],
                        "instruction_details": {"description": "balance negative case"}}
                ],
                "batch_details": {"description": "test"},
                "value_timestamp": "2019-01-01T01:00:00+00:00"
            }
        }
        events = [vault_caller.SimulationEvent(start, deposit_event)]
        res = self.client.simulate_smart_contract(contract_code=self.smart_contract_contents,
                                                  start_timestamp=start, end_timestamp=end,
                                                  template_parameters=template_params,
                                                  instance_parameters=instance_params,
                                                  return_event_log=True,
                                                  events=events)

        # Check the events schedules
        self.assertEqual(res['scheduled_events'][0]['event_type'], 'ACCRUE_INTEREST')
        self.assertEqual(res['scheduled_events'][1]['event_type'], 'APPLY_ACCRUED_INTEREST')

        # No accrue postings
        no_accrue = False
        if all(time_series['account_address'] == 'DEFAULT' for time_series in res['v3_balance_timeseries']):
            no_accrue = True

        self.assertTrue(no_accrue)


if __name__ == '__main__':
    unittest.main()
