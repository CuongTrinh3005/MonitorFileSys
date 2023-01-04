PRINCIPAL_OUTSTANDING = "principal_outstanding"
INTERNAL_CONTRA = "internal_contra"
LOAN_BALANCE = "loan_balance"
AGGREGATE_BALANCE_DEFINITIONS = "aggregate_balance_definitions"
BALANCES = "balances"
OFFSET = "offset"

amount = 10.0

AGGREGATE_BALANCE_DEFINITIONS = {
    LOAN_BALANCE: {
        BALANCES: {
            PRINCIPAL_OUTSTANDING,
            # INTERNAL_CONTRA
        },
        OFFSET: False
    },
}

fund_movements = [(PRINCIPAL_OUTSTANDING, INTERNAL_CONTRA, amount)]
aggregates_by_address = {address: 0.0 for address in AGGREGATE_BALANCE_DEFINITIONS}

for from_address, to_address, amount in fund_movements:
    for aggregate_address, item in AGGREGATE_BALANCE_DEFINITIONS.items():
        delta = 0.0
        if to_address in item[BALANCES]:
            delta += amount if item[OFFSET] else -amount
        if from_address in item[BALANCES]:
            delta += -amount if item[OFFSET] else amount
        aggregates_by_address[aggregate_address] += delta

print("Aggregating by addresses: ", aggregates_by_address)
