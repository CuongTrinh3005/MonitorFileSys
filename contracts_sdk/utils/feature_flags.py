from functools import wraps
import unittest

from . import feature_flags_config

# A list of feature flags used in the Contracts Language library.
CALENDAR_SUPPORT = 'KERN_447_CALENDAR_SUPPORT_IN_CONTRACTS'
TRANSACTION_CODE_FFLAG = 'PYMT_247_CONTRACTS_LANGUAGE_TRANSACTION_CODE'
PERMITTED_DENOMINATIONS_NEW_HOOKS = 'KERN_508_PERMITTED_DENOMINATIONS_NEW_HOOKS'
CONTRACT_MODULE_SUPPORT = 'TMV_237_CONTRACT_MODULE_SUPPORT'
HOOK_DIRECTIVES_AND_DATA_SCOPE_POST_POSTING_HOOK = (
    'KERN_540_HOOK_DIRECTIVES_AND_DATA_SCOPE_POST_POSTING_HOOK'
)

CONTRACT_LANGUAGE_FFLAGS = [
    CALENDAR_SUPPORT,
    TRANSACTION_CODE_FFLAG,
    PERMITTED_DENOMINATIONS_NEW_HOOKS,
    CONTRACT_MODULE_SUPPORT,
    HOOK_DIRECTIVES_AND_DATA_SCOPE_POST_POSTING_HOOK,
]


def is_fflag_enabled(feature_flag: str) -> bool:
    """
    Checks if a feature flag is enabled within the CONTRACT_FFLAGS_CONFIG.
    Returns a boolean to indicate if the checked flag is enabled.
    """
    return feature_flags_config.CONTRACT_FFLAGS_CONFIG.get(feature_flag, False)


def skip_if_not_enabled(feature_flag: str):
    """
    Decorator that skips a given test if the passed feature flag is not enabled
    within the CONTRACT_FFLAGS_CONFIG.
    """
    def skip_wrapper(test):
        @wraps(test)
        def wrapped_test(test_instance, *args, **kwargs):
            if not is_fflag_enabled(feature_flag):
                raise unittest.SkipTest(f"Feature flag {feature_flag} not enabled in environment.")
            else:
                return test(test_instance, *args, **kwargs)
        return wrapped_test
    return skip_wrapper
