# Define your templates here

data = {
    "start_timestamp": "2018-04-09T20:14:37.808587Z",
    "end_timestamp": "2018-05-09T20:14:37.808587Z",
    "smart_contracts": [
        {
            "smart_contract_version_id": "1000",
            "smart_contract_param_vals": {
                "denomination": "[\"GBP\", \"HKD\"]",
                "interest_rate": "0.05",
                "internal_account_1": "1111",
                "internal_account_2": "2222",
                "internal_account_3": "3333",
                "total_days": "365",
                "accrue_digits": "5",
                "apply_digits": "2"
            },
            "code": "api = '3.8.0'\nversion = '0.0.1'\ntside = Tside.LIABILITY"
        },
        {
            "code": "api = '3.8.0'\nversion = '0.0.1'\ntside = Tside.LIABILITY",
            "smart_contract_version_id": "1001"
        }
    ],
    "instructions": [
        {
            "timestamp": "2018-04-10T20:14:37.808587Z",
            "create_account": {
                "id": "Main",
                "product_version_id": "1000"
            }
        },
        {
            "timestamp": "2018-04-10T20:14:37.808587Z",
            "create_account": {
                "id": "1111",
                "product_version_id": "1001"
            }
        },
        {
            "timestamp": "2018-04-10T20:14:37.808587Z",
            "create_account": {
                "id": "2222",
                "product_version_id": "1001"
            }
        },
        {
            "timestamp": "2018-04-10T20:14:37.808587Z",
            "create_account": {
                "id": "3333",
                "product_version_id": "1001"
            }
        },
        {
            "timestamp": "2018-04-11T20:14:37.808587Z",
            "create_posting_instruction_batch": {
                "client_id": "1",
                "client_batch_id": "1",
                "posting_instructions": [
                    {
                        "client_transaction_id": "22",
                        "inbound_hard_settlement": {
                            "amount": "10000",
                            "denomination": "GBP",
                            "target_account": {
                                "account_id": "Main"
                            },
                            "internal_account_id": "3333"
                        }
                    },
                    {
                        "client_transaction_id": "122",
                        "inbound_hard_settlement": {
                            "amount": "1500",
                            "denomination": "HKD",
                            "target_account": {
                                "account_id": "Main"
                            },
                            "internal_account_id": "3333"
                        }
                    }
                ],
                "batch_details": {}
            }
        }
    ]
}
