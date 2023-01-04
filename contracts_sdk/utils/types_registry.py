import builtins
from datetime import datetime
from decimal import Decimal
import typing

from .exceptions import InvalidSmartContractError, StrongTypingError
from .types_utils import ClassSpec, EnumSpec, FixedValueSpec, NativeObjectSpec, ValueSpec


def _check_class_spec(results, registry, prebuilt_instances, class_spec):
    if class_spec.name not in prebuilt_instances and not class_spec.constructor:
        # If the ClassSpec doesn't have a constructor, ignore it.
        # There are some types where the class itself may be used
        # as opposed to constructing an instance, e.g. Parameter types.
        results.classes_without_constructor_specs.add(class_spec.name)
        return

    try:
        instance = _try_to_construct(registry, prebuilt_instances, class_spec.name)
    except (TypeError, StrongTypingError) as e:
        # The arguments within the constructor were of the wrong types
        # with respect to the specification.
        results.invalid_methods.add((('%s.__init__' % class_spec.name), e))
        return
    except:  # noqa: E722
        return

    # Check that all the public attributes match the Class specification.
    for attr_spec in class_spec.public_attributes.values():
        try:
            attr = getattr(instance, attr_spec.name)
        except AttributeError:
            results.missing_attributes.add('%s.%s' % (class_spec.name, attr_spec.name))
            continue
        except Exception:
            # The attribute exists, but there was a different problem:
            # potentially, one of the attributes was a property whose method threw an exception.
            continue
        try:
            registry.assert_type_name(attr_spec.type, attr, '')
        except StrongTypingError:
            results.invalid_attributes.add(
                ('%s.%s' % (class_spec.name, attr_spec.name), attr_spec.type, type(attr))
            )

    # Check all the public methods match the specification.
    for method_spec in class_spec.public_methods.values():
        identifier = '%s.%s' % (class_spec.name, method_spec.name)
        try:
            method = getattr(instance, method_spec.name)
        except:  # noqa: E722
            results.missing_methods.add(identifier)
            return
        _check_method_spec(
            results, registry, prebuilt_instances, identifier, method, method_spec
        )


def _check_method_spec(results, registry, prebuilt_instances, identifier, method, method_spec):
    args = {
        name: _try_to_construct(registry, prebuilt_instances, spec_of_arg.type)
        for name, spec_of_arg in method_spec.args.items()
    }

    try:
        return_value = method(**args)
    except (TypeError, StrongTypingError) as e:  # TypeError: invalid argument count.
        results.invalid_methods.add((identifier, e))
        return
    except:  # noqa: E722
        return

    # Check the return value.
    if method_spec.return_value:
        try:
            registry.assert_type_name(method_spec.return_value.type, return_value, '')
        except StrongTypingError:
            results.invalid_method_return_values.add(
                (identifier, method_spec.type, type(return_value))
            )


def _try_to_construct(registry, prebuilt_instances, type_str):
    prebuilt_instance = prebuilt_instances.get(type_str)
    if prebuilt_instance is not None:
        return prebuilt_instance

    type_obj = eval(type_str, registry._check_dict, registry._check_dict)  # noqa: SLF001
    spec = registry._specs.get(type_str)  # noqa: SLF001

    if spec:
        if isinstance(spec, ClassSpec):
            return type_obj(**{
                name: _try_to_construct(registry, prebuilt_instances, spec_of_arg.type)
                for name, spec_of_arg in spec.constructor.args.items()
            })
        elif isinstance(spec, ValueSpec):
            return _try_to_construct(registry, prebuilt_instances, spec.type)
        elif isinstance(spec, NativeObjectSpec):
            if type_obj == Decimal:
                return Decimal(123)
            elif type_obj == datetime:
                return datetime(2019, 1, 1)
            else:
                raise ValueError('Dont know how to construct NativeObject of type %s' % type_obj)
        elif isinstance(spec, EnumSpec):
            return spec.members[0]['value']
        else:
            raise ValueError('Cant construct specification of type %s' % spec.__class__)
    else:
        if type_obj == str:
            return 'Hello'
        elif type_obj.__bases__ == (_TypeCheckingOptional, ):
            return None
        elif type_obj.__bases__ == (_TypeCheckingList, ):
            return []
        elif type_obj.__bases__ == (_TypeCheckingDict, ):
            return {}
        instance = type_obj()
        return instance


def _builtin_not_supported(*args):
    raise InvalidSmartContractError("Unsupported builtin used")


def check_registry_specs_sanity(registry, prebuilt_instances):
    # Start with an empty results object.
    results = RegistrySpecsSanityCheckResults()

    # For each object in the registry with a spec, check that the specification is valid.
    for object_name, spec in registry._specs.items():  # noqa: SLF001
        if isinstance(spec, ClassSpec):
            _check_class_spec(results, registry, prebuilt_instances, spec)

    return results


class RegistrySpecsSanityCheckResults:
    def __init__(self):
        # Each item is a class name.
        self.classes_without_constructor_specs = set()

        # Each item is attr identifier.
        self.missing_attributes = set()

        # Each item is (attr identifier, expected type name, actual type obj).
        self.invalid_attributes = set()

        # Each item is a method identifier.
        self.missing_methods = set()

        # Each item is (method identifier, exception).
        self.invalid_methods = set()

        # Each item is (method identifier, expected type name, actual type obj).
        self.invalid_method_return_values = set()

    def __str__(self):
        lines = []
        if self.classes_without_constructor_specs:
            lines.append(
                'Classes without constructor specs: %s' % (
                    ', '.join(sorted(self.classes_without_constructor_specs))
                )
            )

        if self.missing_attributes:
            lines.append(
                'Missing attributes: %s' % (
                    ', '.join(sorted(self.missing_attributes))
                )
            )

        if self.invalid_attributes:
            lines.append('Invalid attributes:')
            lines.extend(
                ('%s expected %r but got %s' % item)
                for item in sorted(self.invalid_attributes)
            )

        if self.missing_methods:
            lines.append(
                'Missing methods: %s' % (
                    ', '.join(sorted(self.missing_methods))
                )
            )

        if self.invalid_methods:
            lines.append('Invalid methods:')
            lines.extend(
                ('%s raised %s' % item)
                for item in sorted(self.invalid_methods)
            )

        return '\n'.join(lines or ['All specs satisfied'])


def make_contract_version_sandbox(contract_lib: typing.Any) -> typing.Dict[str, typing.Any]:
    # The _builtin_not_supported method provides a more accurate error message when unsupported
    # builtin methods are used, e.g. if python has a C implementation which is calling a Python
    # function such as `__import__`.
    types_dict = TypeRegistry(
        builtins={
            k: v if k in contract_lib.WHITELISTED_BUILTINS else _builtin_not_supported
            for k, v in builtins.__dict__.items()
        },
        custom=list(contract_lib.types_registry().values())
    )
    return types_dict


class TypeRegistry(dict):
    """
    The TypeRegistry hold all types that a particular Smart Contract API defines.

    A TypeRegistry instance is itself usable as a dict, meaning that it can be used
    as a sandbox for contract execution via instructions like:
        exec(contract_code, type_registry, type_registry)

    It also contains the member _check_dict, which consists of the builtins, custom types,
    and the type annotation types that are needed to verify a type that any custom type
    or method may wish to assert.
    """

    def __init__(self, *, builtins, custom):
        if not isinstance(builtins, dict):
            raise ValueError('builtins must be a dict')
        if not isinstance(custom, list):
            raise ValueError('custom must be a list')

        self['__builtins__'] = builtins
        self._specs = {}

        for item in custom:
            if isinstance(item, NativeObjectSpec):
                name, object, spec = item.name, item.object, item
            elif isinstance(item, FixedValueSpec):
                name, object, spec = item.name, item.fixed_value, item
            elif hasattr(item, '_spec'):
                name, object, spec = item._spec().name, item, item._spec()  # noqa:SF01
            else:
                raise ValueError('Invalid item %s inserted into TypeRegistry' % item)

            if not isinstance(name, str):
                raise ValueError('TypeRegistry could not infer name for object %s' % repr(item))
            if name in self:
                raise ValueError('Name %r is multiply defined in TypeRegistry' % name)

            self[name] = object
            self._specs[name] = spec

        # Build the dictionary to check all the types used within Smart Contracts
        # that contain custom types and typing classes.
        self._check_dict = dict(self)
        self._check_dict['Any'] = TypeCheckingAny
        self._check_dict['Dict'] = _TypeCheckingDict()
        self._check_dict['List'] = _TypeCheckingList()
        self._check_dict['Optional'] = _TypeCheckingOptional()
        self._check_dict['Tuple'] = _TypeCheckingTupleCls()
        self._check_dict['Union'] = _TypeCheckingUnionCls()

        # Attach the type registry to every class in the check dict;
        # each class in there may need to check the registry for recursive types.
        for cls in self._check_dict.values():
            try:
                cls._registry = self  # noqa:SF01
            except (AttributeError, TypeError):
                pass

    def assert_type_name(self, type_name, obj, location):
        # Use the Python interpreter to parse the type_name string,
        # which may be arbitrarily nested, e.g. 'List[Dict[int, SomeType]].
        type_obj = eval(type_name, self._check_dict)
        if not self.is_valid_type(type_obj, obj):
            raise StrongTypingError('%s expected %s but got value %r' % (location, type_name, obj))

    @staticmethod
    def is_valid_type(type_obj, obj):
        if hasattr(type_obj, '_type_check'):
            return type_obj._type_check(obj)  # noqa:SF01
        else:
            return isinstance(obj, type_obj)


DictKeyType = typing.TypeVar('DictKeyType')
DictValueType = typing.TypeVar('DictValueType')
ListItemType = typing.TypeVar('ListItemType')
OptionalItemType = typing.TypeVar('OptionalItemType')


class TypeCheckingAny:
    """
    A type that matches the signature of typing.Any but
    implements the _type_check method.
    """
    @classmethod
    def _type_check(cls, obj):
        return True


class _TypeCheckingDict:
    def __getitem__(self, types):
        class TypeCheckingDict(typing.Generic[DictKeyType, DictValueType]):
            """
            A type that matches the signature of typing.Dict but
            implements the _type_check method.
            """
            @staticmethod
            def _type_check(obj):
                return isinstance(obj, dict) and all(
                    self._registry.is_valid_type(types[0], key) and  # noqa: SLF001
                    self._registry.is_valid_type(types[1], value)  # noqa: SLF001
                    for key, value in obj.items()
                )

        return TypeCheckingDict


class _TypeCheckingList:
    def __getitem__(self, type):
        class TypeCheckingList(typing.Generic[ListItemType]):
            """
            A type that matches the signature of typing.List but
            implements the _type_check method.
            """
            @staticmethod
            def _type_check(obj):
                return isinstance(obj, list) and all(
                    self._registry.is_valid_type(type, item)  # noqa: SLF001
                    for item in obj
                )

        return TypeCheckingList


class _TypeCheckingOptional:
    def __getitem__(self, type):
        class TypeCheckingOptional(typing.Generic[OptionalItemType]):
            """
            A type that matches the signature of typing.Optional but
            implements the _type_check method.
            """
            @staticmethod
            def _type_check(obj):
                return obj is None or self._registry.is_valid_type(type, obj)

        return TypeCheckingOptional


class _TypeCheckingTupleCls:
    """
    The pattern of inheriting from typing.Generic does not work
    for tuples, because typing.Generic will not accept an Ellipsis.
    """
    def __getitem__(self, types):
        class TypeCheckingTupleWithArgs:
            @staticmethod
            def _type_check(obj):
                return (
                    isinstance(obj, tuple) and
                    len(obj) == len(types) and
                    all(
                        self._registry.is_valid_type(_type, item)
                        for _type, item in zip(types, obj)
                    )
                )

        return TypeCheckingTupleWithArgs


class _TypeCheckingUnionCls:
    """
    The pattern of inheriting from typing.Generic does not work
    for unions, because typing.Generic will not accept an Ellipsis.
    """
    def __getitem__(self, types):
        class TypeCheckingUnionWithArgs:
            @staticmethod
            def _type_check(obj):
                return any(
                    self._registry.is_valid_type(_type, obj)
                    for _type in types
                )
        return TypeCheckingUnionWithArgs
