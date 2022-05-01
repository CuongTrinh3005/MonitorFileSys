display_name = 'My custom smart contract'
api = '3.8.0'  # This is a V3 Smart Contract
version = '0.0.1'  # Use semantic versioning, this is explained in the overview document
summary = 'Enter one line summary of contract here'
tside = Tside.LIABILITY


parameters = [
    Parameter(
        name='overdraft_fee_account',
        description='Internal Account used for receiving overdraft fees',
        display_name='Current Account Overdraft Fee Account',
        level=Level.TEMPLATE,
        shape=AccountIdShape
    )
]


@requires(parameters=True)
def execution_schedules():
    return [
        (
        'APPLY_OVERDRAFT_FEES', {
            'day': '11',
            'hour': '23',
            'minute': '59',
            'second': '59'
            }
        ),
    ]


@requires(event_type='APPLY_OVERDRAFT_FEES', parameters=True, balances='latest')
def scheduled_code(event_type, effective_date):
    if event_type == 'APPLY_OVERDRAFT_FEES':
        instructions = []
        internal_fee_account = vault.get_parameter_timeseries(
            name='overdraft_fee_account'
        ).at(timestamp=effective_date)

        client_transaction_id = 'APPLY_OVERDRAFT_FEES_{}_CUSTOMER'.format(
            vault.get_hook_execution_id()
        )

        instructions.extend(
            _charge_fee(
                vault, 'GBP', 100.00, {
                    'description': 'Overdraft Fee.'
                }, client_transaction_id, internal_fee_account
            )
        )

        vault.instruct_posting_batch(
            posting_instructions=instructions,
            effective_date=effective_date
        )


def _charge_fee(vault, denomination, amount, instruction_details, client_transaction_id,
                fee_internal_account):
    """
    Charge fees
    """
    ins = []
    if abs(amount) > 0:
        ins.extend(vault.make_internal_transfer_instructions(
            amount=abs(amount), denomination=denomination,
            from_account_id=vault.account_id, from_account_address=DEFAULT_ADDRESS,
            to_account_id=fee_internal_account, to_account_address=DEFAULT_ADDRESS,
            asset=DEFAULT_ASSET, client_transaction_id=client_transaction_id,
            instruction_details=instruction_details,
            pics=['FEES_CHARGED']
        ))
    return ins