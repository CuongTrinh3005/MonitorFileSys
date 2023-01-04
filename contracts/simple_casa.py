display_name = 'Exersice for smart contract assessment'
api = '3.8.0'
version = '0.0.1'
summary = 'Smart Contract APIs Exercise for applying interest'
description = 'This is the test for beginners in the learning Smart Contract career path'
tside = Tside.LIABILITY
supported_denominations = ['GBP', 'HKD']

# Params' names
# Template
ACCRUE_DIGITS = 'accrue_digits'
APPLY_DIGITS = 'apply_digits'
DENOMINATION = 'denomination'
INTEREST_RATE = 'interest_rate'
TOTAL_DAYS = 'total_days'

# Related to GLs
PARTNER_GL = 'partner_gl'
PARTNER_ACCRUED_INTEREST_GL = "partner_accrued_interest_gl"
PARTNER_INTEREST_INCOME_GL = "partner_interest_income_gl"

# Default values
DEFAULT_DENOMINATION = ['GBP', 'HKD']
DEFAULT_INTEREST_RATE = 0.0
DEFAULT_TOTAL_DAYS = 365
DEFAULT_ACCRUE_DIGITS = 5
DEFAULT_APPLY_DIGITS = 2

# Addresses
INTERNAL = 'INTERNAL'
ACCRUED_INCOMING_ADDRESS = 'ACCRUED_INCOMING_ADDRESS'

# Effect
CUSTOMER = 'CUSTOMER'
BANK = 'BANK'

# Events
ACCRUED_INTEREST = 'RECORD_ACCRUED_INTEREST'
APPLY_ACCRUED_INTEREST = 'APPLY_ACCRUED_INTEREST'
REBALANCING = 'RE-BALANCING'
ACCRUED_INTEREST_CUSTOMER = ACCRUED_INTEREST + "_" + CUSTOMER
ACCRUED_INTEREST_BANK = ACCRUED_INTEREST + "_" + BANK
APPLY_ACCRUED_INTEREST_REBALANCING = APPLY_ACCRUED_INTEREST + "_" + REBALANCING

# Parameters
parameters = [
    Parameter(
        name=ACCRUE_DIGITS,
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
        name=APPLY_DIGITS,
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
        name=DENOMINATION,
        shape=DenominationShape,
        level=Level.TEMPLATE,
        description='Default denomination',
        display_name='Test denomination parameter'
    ),
    Parameter(
        name=INTEREST_RATE,
        shape=NumberShape(
            kind=NumberKind.PERCENTAGE, min_value=0, max_value=1, step=0.01),
        level=Level.TEMPLATE,
        display_name='Interest Rate',
        description='Rate paid on positive balances'
    ),
    Parameter(
        name=PARTNER_INTEREST_INCOME_GL,
        description='Internal Account used for receiving the accrual interest',
        display_name='Partner Interest Income GL',
        level=Level.TEMPLATE,
        shape=AccountIdShape
    ),
    Parameter(
        name=PARTNER_ACCRUED_INTEREST_GL,
        description='Internal Account used for sending the accrual interest',
        display_name='Partner Accrued Interest GL',
        level=Level.TEMPLATE,
        shape=AccountIdShape
    ),
    Parameter(
        name=PARTNER_GL,
        description='Internal Account used for officially paying interest amount for customer',
        display_name='Partner GL',
        level=Level.TEMPLATE,
        shape=AccountIdShape
    ),
    Parameter(
        name=TOTAL_DAYS,
        level=Level.TEMPLATE,
        description="Total days in one year to calculate interest",
        display_name='Total days in one year',
        shape=NumberShape(
            min_value=364,
            max_value=366,
            step=1,
        )
    )
]


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
                'hour': '01',
                'minute': '00',
                'second': '00'
            }
        )
    ]


@requires(parameters=True)
def pre_posting_code(postings, effective_date):
    if any(posting.denomination not in DEFAULT_DENOMINATION for posting in postings):
        raise Rejected(
            'Cannot make transactions in given denomination; '
            'transactions must be in {}'.format(DEFAULT_DENOMINATION),
            reason_code=RejectedReason.WRONG_DENOMINATION,
        )


@requires(event_type='ACCRUE_INTEREST', parameters=True, balances='1 day')
@requires(event_type='APPLY_ACCRUED_INTEREST', parameters=True, balances='1 day')
def scheduled_code(event_type, effective_date):
    if event_type == 'ACCRUE_INTEREST':
        _accrue_interest(vault, effective_date)
    elif event_type == 'APPLY_ACCRUED_INTEREST':
        _apply_accrued_interest(vault, effective_date)


# Helper functions


def _accrue_interest(vault, time_effective):
    for denomination in supported_denominations:
        # Get the balance at the end of the previous day
        balances = vault.get_balance_timeseries().at(timestamp=time_effective)
        effective_balance = balances[(DEFAULT_ADDRESS, DEFAULT_ASSET, denomination, Phase.COMMITTED)].net
        if effective_balance > 0:
            try:
                interest_rate = vault.get_parameter_timeseries(
                    name=INTEREST_RATE
                ).latest()
                _validate_interest(interest_rate)
            except:
                interest_rate = DEFAULT_INTEREST_RATE

            try:
                total_days = vault.get_parameter_timeseries(name=TOTAL_DAYS).latest()
                if total_days <= 0:
                    raise ValueError("Total days of year must be larger than 0")
                _validate_positive_int(total_days, min_val=1, max_val=366)
            except:
                total_days = DEFAULT_TOTAL_DAYS

            daily_rate = interest_rate / total_days
            daily_rate_percent = daily_rate * 100
            amount_to_accrue = _precision_accrual(vault, effective_balance * daily_rate)

            # Add note here for troubleshooting in need.
            notes = f"Accrual Data - Balance: {effective_balance} {denomination}- yearly interest rate: {interest_rate}" \
                    f" - daily interest rate: {daily_rate} - accrued amount: {amount_to_accrue} - at: {time_effective}."

            vault.add_account_note(
                body=notes,
                note_type=NoteType.RAW_TEXT,
                is_visible_to_customer=True,
                date=time_effective
            )

            if amount_to_accrue > 0:
                # Credit ACCRUED_INCOMING_ADDRESS - debit INTERNAL of CASA
                posting_ins = vault.make_internal_transfer_instructions(
                    amount=amount_to_accrue,
                    denomination=denomination,
                    client_transaction_id='CALCULATE_{}_ACCRUED_INTEREST_{}'.format(
                        vault.get_hook_execution_id(), denomination),
                    from_account_id=vault.account_id,
                    from_account_address=INTERNAL,
                    to_account_id=vault.account_id,
                    to_account_address=ACCRUED_INCOMING_ADDRESS,
                    instruction_details={
                        'description': 'Daily interest accrued at %0.5f%% on balance of %0.2f' %
                                       (daily_rate_percent, effective_balance),
                        'event': ACCRUED_INTEREST_CUSTOMER
                    },
                    asset=DEFAULT_ASSET
                )

                # Credit partner interest income GL - debit partner accrued interest GL
                partner_interest_income_gl = vault.get_parameter_timeseries(name=PARTNER_INTEREST_INCOME_GL).latest()
                partner_accrued_interest_gl = vault.get_parameter_timeseries(name=PARTNER_ACCRUED_INTEREST_GL).latest()

                posting_ins.extend(
                    vault.make_internal_transfer_instructions(
                        amount=amount_to_accrue,
                        denomination=denomination,
                        from_account_id=partner_accrued_interest_gl,
                        from_account_address=DEFAULT_ADDRESS,
                        to_account_id=partner_interest_income_gl,
                        to_account_address=DEFAULT_ADDRESS,
                        asset=DEFAULT_ASSET,
                        client_transaction_id='RECORD_ACCRUED_INTEREST_BANK_{}_{}'.format(
                            vault.get_hook_execution_id(), denomination
                        ),
                        instruction_details={
                            'description': 'Interest Accrued',
                            'event': ACCRUED_INTEREST_BANK
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
    latest_bal_by_addr = vault.get_balance_timeseries().at(timestamp=time_effective)
    for denomination in supported_denominations:
        incoming_accrued = latest_bal_by_addr[
            (ACCRUED_INCOMING_ADDRESS, DEFAULT_ASSET, denomination, Phase.COMMITTED)
        ].net
        amount_to_be_paid = _precision_apply(vault, incoming_accrued)

        # Fulfil any incoming interest into the account
        if amount_to_be_paid > 0:
            partner_interest_income_gl = vault.get_parameter_timeseries(name=PARTNER_INTEREST_INCOME_GL).latest()
            partner_accrued_interest_gl = vault.get_parameter_timeseries(name=PARTNER_ACCRUED_INTEREST_GL).latest()
            partner_gl = vault.get_parameter_timeseries(name=PARTNER_GL).latest()

            notes = f"Apply interest - amount: {amount_to_be_paid} {denomination} - Partner GL ID: {partner_gl} - Partner Interest Income GL " \
                    f"ID: {partner_interest_income_gl} - Partner Accrued Interest GL ID: {partner_accrued_interest_gl}"

            vault.add_account_note(
                body=notes,
                note_type=NoteType.RAW_TEXT,
                is_visible_to_customer=True,
                date=time_effective
            )

            posting_ins = vault.make_internal_transfer_instructions(
                amount=amount_to_be_paid,
                denomination=denomination,
                from_account_id=partner_gl,
                from_account_address=DEFAULT_ADDRESS,
                to_account_id=vault.account_id,
                to_account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                client_transaction_id='OFFICIAL_APPLY_ACCRUED_INTEREST_CUSTOMER_{}_{}'.format(
                    vault.get_hook_execution_id(), denomination
                ),
                instruction_details={
                    'description': 'Interest Applied',
                    'event': APPLY_ACCRUED_INTEREST
                }
            )

            posting_ins.extend(
                vault.make_internal_transfer_instructions(
                    amount=amount_to_be_paid,
                    denomination=denomination,
                    from_account_id=vault.account_id,
                    from_account_address=ACCRUED_INCOMING_ADDRESS,
                    to_account_id=vault.account_id,
                    to_account_address=INTERNAL,
                    asset=DEFAULT_ASSET,
                    client_transaction_id='RECORD_APPLY_ACCRUED_INTEREST_CUSTOMER_{}_{}'.format(
                        vault.get_hook_execution_id(), denomination
                    ),
                    instruction_details={
                        'description': 'Re-balancing Interest Applied',
                        'event': APPLY_ACCRUED_INTEREST_REBALANCING
                    }
                )
            )

            posting_ins.extend(
                vault.make_internal_transfer_instructions(
                    amount=amount_to_be_paid,
                    denomination=denomination,
                    from_account_id=partner_interest_income_gl,
                    from_account_address=DEFAULT_ADDRESS,
                    to_account_id=partner_accrued_interest_gl,
                    to_account_address=DEFAULT_ADDRESS,
                    asset=DEFAULT_ASSET,
                    client_transaction_id='RECORD_APPLY_ACCRUED_INTEREST_BANK_{}_{}'.format(
                        vault.get_hook_execution_id(), denomination
                    ),
                    instruction_details={
                        'description': 'Interest Applied',
                        'event': APPLY_ACCRUED_INTEREST
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
        digits = vault.get_parameter_timeseries(name=ACCRUE_DIGITS).latest()
        _validate_positive_int(digits, min_val=0, max_val=7, name='Decimal for accrue')
    except:
        digits = DEFAULT_ACCRUE_DIGITS

    return _truncate_decimal(value=amount, num_digits=digits)


def _precision_apply(vault, amount):
    try:
        digits = vault.get_parameter_timeseries(name=APPLY_DIGITS).latest()
        _validate_positive_int(digits, min_val=0, max_val=4, name='Decimal for accrue')
    except:
        digits = DEFAULT_APPLY_DIGITS

    return _truncate_decimal(value=amount, num_digits=digits)


def _validate_positive_int(value, min_val=0, max_val=0, name='Value '):
    is_positive_int = str(value).isdigit()
    if not is_positive_int:
        raise ValueError(f"{name} must be a positive number")
    if value < min_val or value > max_val:
        raise ValueError(f"{name} must be in range[{min_val}, {max_val}]")


def _validate_interest(value, min_val=0, max_val=1):
    if value < 0 or (value < min_val or value > max_val):
        raise ValueError("Interest rate must be in range [{min_val}, {max_val}]")
