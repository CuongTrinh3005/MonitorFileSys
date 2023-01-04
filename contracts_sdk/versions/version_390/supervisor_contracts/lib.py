from . import types as supervisor_contract_types
from ...version_380.supervisor_contracts import lib as v380_lib
from ..common import lib as common_lib


types_registry = supervisor_contract_types.types_registry

WHITELISTED_BUILTINS = common_lib.WHITELISTED_BUILTINS


class VaultFunctionsABC(v380_lib.VaultFunctionsABC):
    pass
