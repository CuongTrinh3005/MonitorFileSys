import builtins
from types import FunctionType

from .types import _ALL_TYPES, _WHITELISTED_BUILTINS


def run(contract_module_code: str, function_name: str, *args, **kwargs):
    """Runs function `function_name` that is defined in the `contract_module_code`.

    The function will run in a similar environment as when executed in Vault:
    - Only some builtins are available (see Vault Smart Contract documentation for full list).
    - Types (see Vault Smart Contract documentation for full list) are globally available.

    Args:
        contract_module_code: The source code of the Contract Module.
        function_name: The name of the function to run, this must be defined in the Contract Module
            code.
        *args: Additional arguments to call `function_name` with.
        **kwargs: Additional named arguments to call `function_name` with.
    """
    # The function we will execute will only have access to symbols defined in the sandbox and the
    # symbols defined by the Contract Module itself.
    sandbox = {
        '__builtins__': {name: getattr(builtins, name) for name in _WHITELISTED_BUILTINS},
        **_ALL_TYPES,
    }

    exec(contract_module_code, sandbox, sandbox)

    func = sandbox.get(function_name)
    if func is None:
        raise ValueError(
            f'Function "{function_name}" does not exist in provided Contract Module code'
        )

    function_globals = {**sandbox}

    func = FunctionType(
        func.__code__,
        function_globals,
        func.__name__,
        func.__defaults__,
        func.__closure__
    )

    return func(*args, **kwargs)
