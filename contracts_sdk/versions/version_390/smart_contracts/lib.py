from functools import lru_cache

from . import types as smart_contract_types
from ...version_380.smart_contracts import lib as v380_lib
from ..common import lib as common_lib
from ....utils import symbols, types_utils, feature_flags


types_registry = smart_contract_types.types_registry

WHITELISTED_BUILTINS = common_lib.WHITELISTED_BUILTINS


class VaultFunctionsABC(v380_lib.VaultFunctionsABC):

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        spec = super()._spec(language_code)

        if feature_flags.is_fflag_enabled(feature_flags.CONTRACT_MODULE_SUPPORT):
            spec.public_attributes['modules'] = types_utils.ValueSpec(
                name='modules',
                type='Dict[str, Any]',
                docstring="""
                    A dictionary which maps `ContractModule` aliases to
                    [ContractModule](../types/#classes-ContractModule) objects, as defined in the
                    Contract [metadata](../metadata/#contract_module_imports). This object can be
                    used to call [SharedFunctions](../types/#classes-SharedFunction) that are
                    defined outside of the Contract. This attribute is not available on the
                    Supervisee Vault objects within a Supervisor Contract.
                """
            )

        return spec
