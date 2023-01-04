# Contracts SDK

## Introduction
The Contracts SDK is a Python package that can be used to develop and unit test Smart and Supervisor
Contracts. It fully replaces the Contract Tester library as it offers the same unit testing
capabilities but provides more accurate typing, since it uses the actual Smart and Supervisor
Contract custom types rather than generating a testing-specific version of them. The Contracts SDK
comes with custom Smart and Supervisor Contract types, unit testing utilities and some example unit
tests.

> The Contract Tester library will continue to be supported for the current major Contracts API
> version (3.*), but new Contracts API major versions (4.0+) will only have Contracts SDK support.

## Installation
After downloading and unzipping the 'contracts_sdk' package into directory of your choice, you can
start using its custom types and unit test utilities in your python code by simply importing the
package modules.

## Directory Structure

### example_unit_tests
This directory contains example Smart and Supervisor Contracts with corresponding
unit tests designed using the Contracts SDK.

### utils
This directory contains a collection of utility functions that are used by the
SDK and provide functionality for local testing of sample Contracts.

### versions
This directory contains all of the Contract versions available in a particular
Vault release, with sub-directories separated into Common, Smart Contracts and
Supervisor Contracts. These contain the relevant Contract types and supported
library functions for specific versions of Vault.

Sub-directories separating out the components:
```
common
smart_contracts
supervisor_contracts
```

Vault functions can be found in:
```
lib.py
```

Available types can be found in:
```
types.py
```

## Tests
The Contracts SDK comes with unit test utilities; these are base classes that
should be used in Contract unit tests. There are separate base classes for
each Contracts API version and for Smart or Supervisor Contracts.

There are several types of tests:
- `contracts_sdk/example_unit_tests` contains some sample Contracts unit tests using the SDK.
These tests should be used as an example when writing Contract unit tests.
- `contracts_sdk/utils/tests` contains unit tests for the utilities used in the SDK. These are
tests of the internal SDK code.
- `contracts_sdk/versions/version_*/*/tests/test_lib.py` contains unit tests against the Vault
object. These are tests of the internal SDK code.
- `contracts_sdk/versions/version_*/*/tests/test_types.py` contains unit tests against the
Contract types. These are tests of the internal SDK code.

To run the tests:
```
cd <parent of the sdk directory>
python3 -m unittest
```
