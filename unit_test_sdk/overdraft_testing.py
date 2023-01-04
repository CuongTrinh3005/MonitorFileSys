from datetime import datetime
from decimal import Decimal

from contracts_sdk.utils.tools import SmartContracts380TestCase
from contracts_sdk.versions.version_380.smart_contracts import types


class SimpleTestCase(SmartContracts380TestCase):
    effective_date = datetime(year=2020, month=2, day=20)
    contract_code = """
def pre_posting_code(postings, effective_date):
    default_address_balance = vault.get_balance_timeseries().latest()[
        (DEFAULT_ADDRESS, DEFAULT_ASSET, 'GBP', Phase.COMMITTED)
    ].net
    # Check that PIB balances can be mocked
    new_postings_balance = postings.balances()[
        (DEFAULT_ADDRESS, DEFAULT_ASSET, 'GBP', Phase.COMMITTED)
    ].net
    if default_address_balance + new_postings_balance < 0:
        raise Rejected(
            message='Account Default address cannot go into overdraft',
            reason_code=RejectedReason.AGAINST_TNC
        )   
"""

    def test_pre_posting_code(self):
        def get_balance_timeseries_historical():
            balance_key_1 = (
                types.defaultAddress.fixed_value, types.defaultAsset.fixed_value, 'GBP',
                types.Phase.COMMITTED
            )
            balance_dict = types.BalanceDefaultDict()
            balance_dict[balance_key_1] = types.Balance(
                net=Decimal(20), credit=Decimal(20), debit=Decimal(0)
            )
            balance_timeseries = types.BalanceTimeseries([
                (self.effective_date, balance_dict),
            ])
            return balance_timeseries

        def get_balances_new_postings():
            balance_key_1 = (
                types.defaultAddress.fixed_value, types.defaultAsset.fixed_value, 'GBP',
                types.Phase.COMMITTED
            )
            balance_dict = types.BalanceDefaultDict()
            balance_dict[balance_key_1] = types.Balance(
                net=Decimal(-30), credit=Decimal(0), debit=Decimal(-30)
            )
            return balance_dict

        posting_instructions = [
            types.PostingInstruction(
                custom_instruction_grouping_key='some_key',
                client_transaction_id='id_12345',
                type=types.PostingInstructionType.CUSTOM_INSTRUCTION,
                pics=[],
                credit=True,
                amount=Decimal(10),
                denomination='GBP',
                account_id='customer_account',
                account_address=types.defaultAddress.fixed_value,
                asset=types.defaultAsset.fixed_value,
                phase=types.Phase.COMMITTED,
            )
        ]
        postings = types.PostingInstructionBatch(
            posting_instructions=posting_instructions,
            value_timestamp=self.effective_date,
            insertion_timestamp=self.effective_date,
            batch_details={},
            client_batch_id='123'
        )
        # Implement not implemented 'balances()' method.
        postings.balances = get_balances_new_postings
        # Mock historical balance timeseries data.
        self.vault.get_balance_timeseries.side_effect = get_balance_timeseries_historical
        with self.assertRaises(types.Rejected) as ex:
            self.run_contract_function(
                self.contract_code, 'pre_posting_code', postings, self.effective_date
            )
        self.assertEqual('Account Default address cannot go into overdraft', str(ex.exception))
