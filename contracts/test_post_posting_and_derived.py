display_name = 'Exersice for smart contract assessment'
api = '3.8.0'
version = '0.0.1'
summary = 'Smart Contract APIs Exercise for applying interest'
description = 'This is the test for beginners in the learning Smart Contract career path'
tside = Tside.LIABILITY

# Parameters
parameters = [
    Parameter(
        name='accrue_digits',
        shape=NumberShape(
            kind=NumberKind.PLAIN,
            min_value=1,
            max_value=5,
            step=1
        ),
        level=Level.TEMPLATE,
        description='Constraint of floating-point amount of money to accrue',
        display_name='Constraint of floating-point amount of money to accrue',
    ),
    Parameter(
        name='apply_digits',
        shape=NumberShape(
            kind=NumberKind.PLAIN,
            min_value=1,
            max_value=3,
            step=1
        ),
        level=Level.TEMPLATE,
        description='Constraint of floating-point amount of money to apply interest',
        display_name='Constraint of floating-point amount of money to apply interest',
    ),
    Parameter(
        name='denomination',
        shape=DenominationShape,
        level=Level.TEMPLATE,
        description='Default denomination',
        display_name='Test denomination parameter'
    ),
    Parameter(
        name='interest_rate',
        shape=NumberShape(
            kind=NumberKind.PERCENTAGE, min_value=0, max_value=1, step=0.01),
        level=Level.TEMPLATE,
        description='Interest Rate',
        display_name='Rate paid on positive balances'
    ),
    Parameter(
        name='internal_account_1',
        description='Internal Account used for recording the postings',
        display_name='Current Account Overdraft Fee Account',
        level=Level.TEMPLATE,
        shape=AccountIdShape
    ),
    Parameter(
        name='internal_account_2',
        description='Internal Account used for recording the postings',
        display_name='Current Account Interest Account',
        level=Level.TEMPLATE,
        shape=AccountIdShape
    ),
    Parameter(
        name='internal_account_3',
        description='Internal Account used for officially paying interest amount for customer',
        display_name='Current Account Interest Account',
        level=Level.TEMPLATE,
        shape=AccountIdShape
    ),
    Parameter(
        name='total_days',
        level=Level.TEMPLATE,
        description="Which day of the month would you like to receive interest?",
        display_name='Elected day of month to apply interest',
        shape=NumberShape(
            min_value=364,
            max_value=366,
            step=1,
        )
    ),
    Parameter(
        name="last_month_amount",
        description="The latest-one-month posting amount",
        display_name="The amount in the latest one month postings",
        level=Level.INSTANCE,
        shape=OptionalShape(NumberShape(min_value=0, max_value=100000000, step=0.000000000001)),
        derived=True,
    ),
]

_DEFAULT_DENOMINATION = ['GBP', 'HKD']
_DEFAULT_INTEREST_RATE = 0.0
_DEFAULT_TOTAL_DAYS = 365
_DEFAULT_ACCRUE_DIGITS = 5
_DEFAULT_APPLY_DIGITS = 2


def execution_schedules():
    return [
        (
            'ACCRUE_INTEREST', {
                'hour': '00',
                'minute': '00',
                'second': '00'
            }
        ),
        (
            'APPLY_ACCRUED_INTEREST', {
                'hour': '00',
                'minute': '10',
                'second': '00'
            }
        )
    ]


@requires(parameters=True)
def pre_posting_code(postings, effective_date):
    denomination_list = _get_list_denominations(vault)
    if any(posting.denomination not in denomination_list for posting in postings):
        raise Rejected(
            'Cannot make transactions in given denomination; '
            'transactions must be in {}'.format(denomination_list),
            reason_code=RejectedReason.WRONG_DENOMINATION,
        )


@requires(event_type='ACCRUE_INTEREST', parameters=True, balances='1 day')
@requires(event_type='APPLY_ACCRUED_INTEREST', parameters=True, balances='1 day')
def scheduled_code(event_type, effective_date):
    if event_type == 'ACCRUE_INTEREST':
        _accrue_interest(vault, effective_date)
    elif event_type == 'APPLY_ACCRUED_INTEREST':
        _apply_accrued_interest(vault, effective_date)


@requires(parameters=True, postings="1 month")
def derived_parameters(effective_date):
    return {
        "last_month_amount": OptionalValue(_get_total_amount_of_last_month_posting(vault))
    }


@requires(parameters=True, postings="1 month")
def post_posting_code(postings: PostingInstructionBatch, effective_date: datetime):
    """
    Get all posting over the period of latest one month.
    :param postings:
    :param effective_date:
    :return: None
    """
    instructions = []
    _get_postings_within_month(vault, instructions)

    vault.instruct_posting_batch(
        posting_instructions=instructions,
        effective_date=effective_date,
        client_batch_id=f"BATCH_APPLIED_TESTING_GET_POSTINGS",
    )
    last_month_amount = _get_total_amount_of_last_month_posting(vault)


def _get_postings_within_month(vault, instructions):
    last_month_postings = vault.get_postings(include_proposed=True)

    denomination_list = _get_list_denominations(vault)
    num = 0
    for denomination in denomination_list:
        for posting in last_month_postings:
            hook_execution_id = vault.get_hook_execution_id()
            instructions.extend(vault.make_internal_transfer_instructions(
                amount=posting.amount,
                denomination=denomination,
                from_account_id=vault.account_id,
                from_account_address=DEFAULT_ADDRESS,
                to_account_id=vault.account_id,
                to_account_address="TESTING_GET_POSTING",
                asset=DEFAULT_ASSET,
                client_transaction_id=f"TESTING_GET_POSTING{hook_execution_id}_{num}",
                instruction_details={
                    "description": f"Get postings testing, amount: {posting.amount} {denomination}",
                },
            ))
            num += 1


def _get_total_amount_of_last_month_posting(vault):
    last_month_postings = vault.get_postings(include_proposed=True)
    total_amount = 0
    for posting in last_month_postings:
        total_amount += posting.amount

    return total_amount


def _accrue_interest(vault, time_effective):
    denomination_list = _get_list_denominations(vault)
    # Get the balance at the end of the previous day
    balances = vault.get_balance_timeseries().at(timestamp=time_effective)
    for denomination in denomination_list:
        effective_balance = balances[(DEFAULT_ADDRESS, DEFAULT_ASSET, denomination, Phase.COMMITTED)].net
        if effective_balance > 0:
            try:
                interest_rate = vault.get_parameter_timeseries(
                    name='interest_rate'
                ).latest()
                _validate_interest(interest_rate)
            except:
                interest_rate = _DEFAULT_INTEREST_RATE

            try:
                total_days = vault.get_parameter_timeseries(name='total_days').latest()
                if total_days <= 0:
                    raise ValueError("Total days of year must be larger than 0")
                _validate_positive_int(total_days, min_val=1, max_val=366)
            except:
                total_days = _DEFAULT_TOTAL_DAYS

            daily_rate = interest_rate / total_days
            daily_rate_percent = daily_rate * 100
            amount_to_accrue = _precision_accrual(vault, effective_balance * daily_rate)

            if amount_to_accrue > 0:
                # Credit ACCRUED_INCOMING_ADDRESS - debit INTERNAL of CASA
                posting_ins = vault.make_internal_transfer_instructions(
                    amount=amount_to_accrue,
                    denomination=denomination,
                    client_transaction_id='CALCULATE_{}_ACCRUED_INTEREST_{}'.format(
                        vault.get_hook_execution_id(), denomination),
                    from_account_id=vault.account_id,
                    from_account_address='INTERNAL',
                    to_account_id=vault.account_id,
                    to_account_address='ACCRUED_INCOMING_ADDRESS',
                    instruction_details={
                        'description': 'Daily interest accrued at %0.5f%% on balance of %0.2f' %
                                       (daily_rate_percent, effective_balance)
                    },
                    asset=DEFAULT_ASSET
                )

                # Credit Internal account 1111 - debit internal account 2222
                internal_account_1 = vault.get_parameter_timeseries(name='internal_account_1').latest()
                internal_account_2 = vault.get_parameter_timeseries(name='internal_account_2').latest()

                posting_ins.extend(
                    vault.make_internal_transfer_instructions(
                        amount=amount_to_accrue,
                        denomination=denomination,
                        from_account_id=internal_account_2,
                        from_account_address=DEFAULT_ADDRESS,
                        to_account_id=internal_account_1,
                        to_account_address=DEFAULT_ADDRESS,
                        asset=DEFAULT_ASSET,
                        client_transaction_id='RECORD_ACCRUED_INTEREST_BANK_{}_{}'.format(
                            vault.get_hook_execution_id(), denomination
                        ),
                        instruction_details={
                            'description': 'Interest Applied',
                            'event': 'RECORD_ACCRUED_INTEREST_INTERNAL'
                        }
                    )
                )

                vault.instruct_posting_batch(
                    posting_instructions=posting_ins,
                    effective_date=time_effective,
                    client_batch_id='BATCH_ACCRUED_INTEREST_{}_{}'.format(
                        vault.get_hook_execution_id(), denomination
                    )
                )


def _apply_accrued_interest(vault, time_effective):
    denomination_list = _get_list_denominations(vault)
    latest_bal_by_addr = vault.get_balance_timeseries().at(timestamp=time_effective)

    for denomination in denomination_list:
        incoming_accrued = latest_bal_by_addr[
            ('ACCRUED_INCOMING_ADDRESS', DEFAULT_ASSET, denomination, Phase.COMMITTED)
        ].net
        amount_to_be_paid = _precision_apply(vault, incoming_accrued)

        # Fulfil any incoming interest into the account
        if amount_to_be_paid > 0:
            internal_account_1 = vault.get_parameter_timeseries(name='internal_account_1').latest()
            internal_account_2 = vault.get_parameter_timeseries(name='internal_account_2').latest()
            internal_account_3 = vault.get_parameter_timeseries(name='internal_account_3').latest()

            posting_ins = vault.make_internal_transfer_instructions(
                amount=amount_to_be_paid,
                denomination=denomination,
                from_account_id=internal_account_3,
                from_account_address=DEFAULT_ADDRESS,
                to_account_id=vault.account_id,
                to_account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                client_transaction_id='OFFICIAL_APPLY_ACCRUED_INTEREST_CUSTOMER_{}_{}'.format(
                    vault.get_hook_execution_id(), denomination
                ),
                instruction_details={
                    'description': 'Interest Applied',
                    'event': 'APPLY_ACCRUED_INTEREST'
                }
            )

            posting_ins.extend(
                vault.make_internal_transfer_instructions(
                    amount=amount_to_be_paid,
                    denomination=denomination,
                    from_account_id=vault.account_id,
                    from_account_address='ACCRUED_INCOMING_ADDRESS',
                    to_account_id=vault.account_id,
                    to_account_address='INTERNAL',
                    asset=DEFAULT_ASSET,
                    client_transaction_id='RECORD_APPLY_ACCRUED_INTEREST_CUSTOMER_{}_{}'.format(
                        vault.get_hook_execution_id(), denomination
                    ),
                    instruction_details={
                        'description': 'Interest Applied',
                        'event': 'AFTER_APPLY_ACCRUED_INTEREST'
                    }
                )
            )

            posting_ins.extend(
                vault.make_internal_transfer_instructions(
                    amount=amount_to_be_paid,
                    denomination=denomination,
                    from_account_id=internal_account_1,
                    from_account_address=DEFAULT_ADDRESS,
                    to_account_id=internal_account_2,
                    to_account_address=DEFAULT_ADDRESS,
                    asset=DEFAULT_ASSET,
                    client_transaction_id='RECORD_APPLY_ACCRUED_INTEREST_BANK_{}_{}'.format(
                        vault.get_hook_execution_id(), denomination
                    ),
                    instruction_details={
                        'description': 'Interest Applied',
                        'event': 'APPLY_ACCRUED_INTEREST'
                    }
                )
            )

            # instructions to apply interest and optional reversal of remainder must be executed
            # in a batch to ensure the overall transaction is atomic
            vault.instruct_posting_batch(
                posting_instructions=posting_ins,
                effective_date=time_effective,
                client_batch_id='BATCH_APPLY_ACCRUED_INTEREST_{}_{}'.format(
                    vault.get_hook_execution_id(), denomination
                )
            )


def _truncate_decimal(value, num_digits):
    stepper = 10.0 ** num_digits
    return math.trunc(stepper * value) / stepper


def _precision_accrual(vault, amount):
    try:
        digits = vault.get_parameter_timeseries(name='accrue_digits').latest()
        _validate_positive_int(digits, min_val=0, max_val=7, name='Decimal for accrue')
    except:
        digits = _DEFAULT_ACCRUE_DIGITS

    return _truncate_decimal(value=amount, num_digits=digits)


def _precision_apply(vault, amount):
    try:
        digits = vault.get_parameter_timeseries(name='apply_digits').latest()
        _validate_positive_int(digits, min_val=0, max_val=4, name='Decimal for accrue')
    except:
        digits = _DEFAULT_APPLY_DIGITS

    return _truncate_decimal(value=amount, num_digits=digits)


def _get_list_denominations(vault):
    try:
        denomination_str = vault.get_parameter_timeseries(name='denomination').latest()
        only_chars = denomination_str.replace("[^\\p{IsAlphabetic}\\p{IsDigit}]", "")
        only_chars = only_chars[1:len(only_chars)]
        deno_split = only_chars.split(",")

        denomination_list = []
        for deno in deno_split:
            denomination_list.append(deno.replace("[", "").replace("]", "").replace('"', "").strip())
    except:
        denomination_list = _DEFAULT_DENOMINATION
    return denomination_list


def _validate_positive_int(value, min_val=0, max_val=0, name='Value '):
    is_positive_int = str(value).isdigit()
    if not is_positive_int:
        raise ValueError(f"{name} must be a positive number")
    if value < min_val or value > max_val:
        raise ValueError(f"{name} must be in range[{min_val}, {max_val}]")


def _validate_interest(value, min_val=0, max_val=1):
    if value < 0 or (value < min_val or value > max_val):
        raise ValueError("Interest rate must be in range [{min_val}, {max_val}]")
