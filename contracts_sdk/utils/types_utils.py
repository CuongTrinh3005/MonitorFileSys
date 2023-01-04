from abc import ABC
from collections.abc import Mapping
from functools import lru_cache
from textwrap import dedent
import inspect

from . import exceptions, symbols


class StrictInterface(ABC):
    """
    This class enforces the 'public' interface on derived classes, and is used to ensure the
    shared Vault interface used in tests matches the actual Vault interface.
    """

    def __new__(cls, *args, **kwargs):

        abstract_methods = set()
        allow_non_abstract = ['get_posting_batches']
        for base in inspect.getmro(cls):
            try:
                abstract_methods = abstract_methods.union(base.__abstractmethods__)
            except AttributeError:
                continue

        for name, _ in inspect.getmembers(cls, predicate=inspect.isfunction):
            if name.startswith('_'):
                continue
            if name in abstract_methods:
                continue
            if name in allow_non_abstract:
                continue
            raise TypeError(f"Method '{name}' missing from public abstract base class")
        return super().__new__(cls)


class TypeQualifier:
    def __init__(self, optional, repeated, deprecated, description):
        self._optional = optional
        self._repeated = repeated
        self._deprecated = deprecated
        self._description = description

    def _check(self, owner_str, value, names, expected_types):
        if value is None:
            if not self._optional:
                raise TypeError('%s is not optional' % owner_str)
            return

        if self._repeated:
            if not isinstance(value, (list, tuple)):
                raise TypeError(
                    '%s expects an iterable of %s, instead got non-iterable %s (%r)' % (
                        owner_str, ' or '.join(names), type(value).__name__, value
                    )
                )
            bad_values = [v for v in value if not self._is_valid(v, expected_types)]

            if bad_values:
                bad_types = set(type(v).__name__ for v in bad_values)
                raise TypeError(
                    '%s expects an iterable of %s, instead got iterable containing %s' % (
                        owner_str, ' or '.join(names), ' and '.join(bad_types)
                    )
                )

        elif not self._is_valid(value, expected_types):
            raise TypeError(
                '%s expects %s, instead got %s (%r)' % (
                    owner_str, ' or '.join(names), type(value).__name__, value
                )
            )

    def _make_type_docstring(self, names):
        if self._repeated:
            return make_docstring_seq(make_docstring(*names))
        else:
            return make_docstring(*names)

    def _make_docstring(self, key, names):
        return "{description: %r, name: %s, type: '%s'}" % (
            self._description or '', key, self._make_type_docstring(names)
        )

    @staticmethod
    def _is_valid(value, expected_types):
        # Return whether value is valid for at least one of the expected types
        return any(
            expected_type._is_valid_value(value)  # noqa:SF01
            if hasattr(expected_type, '_is_valid_value')
            else isinstance(value, expected_type)
            for expected_type in expected_types
        )

    def make_spec(self):
        return {
            'type': self.make_type_docstring(),
            'optional': self._optional,
            'repeated': self._repeated,
            'deprecated': self._deprecated,
            'description': dedent_and_strip(self._description or '')
        }


class TypeFixed(TypeQualifier):
    def __init__(
        self, name, *, optional=False, repeated=False, deprecated=False, description=None
    ):
        super().__init__(optional, repeated, deprecated, description)
        self._name = name

    def check(self, owner_str, type_registry, value):
        self._check(
            owner_str, value, (self._name, ),
            (type_registry.resolve(self._name), )
        )

    def make_docstring(self, key):
        return self._make_docstring(key, [self._name])

    def make_type_docstring(self):
        return self._make_type_docstring([self._name])


def TypedList(item_type):

    class _TypedList(list):

        def __init__(self, iterable=None, _from_proto=False):
            self._from_proto = _from_proto
            self.extend(iterable or ())
            self._from_proto = False

        def append(self, item):
            self._registry.assert_type_name(
                item_type, item, '%s item' % self.__class__.__name__)
            list.append(self, item)

        def extend(self, iterable):
            items = list(iterable)
            if not self._from_proto:
                for i, item in enumerate(items):
                    self._registry.assert_type_name(
                        item_type, item,
                        '%s item[%s]' % (self.__class__.__name__, i)
                    )
            list.extend(self, items)

        def __setitem__(self, key, value):
            if isinstance(key, int):
                if not self._from_proto:
                    self._registry.assert_type_name(
                        item_type, value,
                        '%s item' % self.__class__.__name__
                    )
            elif isinstance(key, slice):
                value = list(value)
                if not self._from_proto:
                    for v in value:
                        self._registry.assert_type_name(
                            item_type, v, '%s item' % self.__class__.__name__
                        )
            # else: Fall through and let list handle the key error
            list.__setitem__(self, key, value)

        def __add__(self, other):
            result = self.__class__(self)  # Copy self
            result.extend(other)
            return result

        def __iadd__(self, other):
            self.extend(other)
            return self

        @classmethod
        @lru_cache()
        def _spec(cls, language_code=symbols.Languages.ENGLISH):
            if language_code != symbols.Languages.ENGLISH:
                raise ValueError('Language not supported')

            return ClassSpec(
                name='TypedList',
                docstring='A list that enforces the type of members.',
                public_attributes=[],
                constructor=ConstructorSpec(
                    docstring='',
                    args=[
                        ValueSpec(
                            name='iterable',
                            type='Optional[List[%s]]' % item_type,
                            docstring='An optional iterable of initial items to be added.'
                        )
                    ]
                ),
                public_methods=[]
            )

    return _TypedList


def TypedDefaultDict(dict_type):

    class _TypedDefaultDict(dict):

        def __init__(self, default_factory=None, mapping=None, _from_proto=False):
            self.default_factory = default_factory
            if mapping is not None and not isinstance(mapping, Mapping):
                raise TypeError('TypedDict init expects Mapping object')
            if mapping:
                if not _from_proto:
                    self._registry.assert_type_name(
                        dict_type, mapping, '%s key: value' % self.__class__.__name__
                    )
            else:
                mapping = {}
            super(_TypedDefaultDict, self).__init__(mapping)

        def __missing__(self, key):
            if self.default_factory is None:
                raise KeyError(key)
            value = self.default_factory(key)
            # Check dict type that we get from key and default_factory
            temp_dict = {key: value}
            self._registry.assert_type_name(
                dict_type, temp_dict, '%s key: value' % self.__class__.__name__
            )
            self[key] = value
            return value

        def __getitem__(self, key):
            try:
                return dict.__getitem__(self, key)
            except KeyError:
                return self.__missing__(key)

        def __setitem__(self, key, value):
            temp_dict = {key: value}
            self._registry.assert_type_name(
                dict_type, temp_dict, '%s key: value' % self.__class__.__name__
            )
            super(_TypedDefaultDict, self).__setitem__(key, value)

        def update(self, other_dict=None, **kwargs):
            if other_dict:
                self._registry.assert_type_name(
                    dict_type, other_dict, '%s key: value' % self.__class__.__name__
                )
            if kwargs:
                self._registry.assert_type_name(
                    dict_type, kwargs, '%s key: value' % self.__class__.__name__
                )
            super(_TypedDefaultDict, self).update(other_dict, **kwargs)

        def setdefault(self, key, default=None):
            if key in self:
                return self[key]
            temp_dict = {key: default}
            self._registry.assert_type_name(
                dict_type, temp_dict, '%s key: value' % self.__class__.__name__
            )
            super(_TypedDefaultDict, self).setdefault(key, default)

        def copy(self):
            return type(self)(self.default_factory, self)

    return _TypedDefaultDict


class NativeObjectSpec:
    """
    A NativeObjectSpec is an object that is defined by Python or an included third party library.
    If specified, the docs field links to the appropriate third party webpage, otherwise the link
    is inferred from the object and package.
    """
    def __init__(self, *, name, object, package=None, docs=None, description=''):
        self.name = name
        self.object = object
        self.package = package
        self.docs = docs
        self.description = description


class ValueSpec:
    """A Specification defining an exposed value."""

    def __init__(self, *, name, type, docstring):
        self.name = name
        self.docstring = docstring
        self.type = type


class FixedValueSpec:
    """A Specification defining a fixed value."""

    def __init__(self, *, name, type, fixed_value, docstring):
        self.name = name
        self.docstring = docstring
        self.fixed_value = fixed_value
        self.type = type


class ReturnValueSpec:
    """A Specification defining an exposed value."""

    def __init__(self, *, type, docstring):
        self.docstring = docstring
        self.type = type


class EnumSpec:
    """A Specification defining a custom enum."""

    def __init__(self, *, name, docstring, members, show_values=False):
        self.name = name
        self.docstring = docstring
        self.members = members
        self.show_values = show_values


class Example:
    def __init__(self, *, title, code):
        self.title = title
        self.code = code


class MethodSpec:
    """A Specification defining a custom method."""

    def __init__(self, *, name, docstring, args=[], return_value=None, examples=[]):
        self.name = name
        self.docstring = docstring
        self.args = {arg.name: arg for arg in args}
        self.return_value = return_value
        self.examples = examples

    def assert_args(self, type_registry, cls_name, args):
        for arg_name, arg_value in args.items():
            arg_spec = self.args.get(arg_name)
            if not arg_spec:
                raise ValueError(
                    'ArgSpec missing on class %s for method %r arg %r' % (
                        cls_name, self.name, arg_name
                    )
                )
            type_registry.assert_type_name(
                arg_spec.type, arg_value, '%s.%s arg %r' % (cls_name, self.name, arg_name)
            )

    def arg_names(self):
        return self.args.keys()


class ExceptionSpec:
    """A Specification defining a custom Exception"""

    def __init__(self, name, docstring, constructor_args=[]):
        self.name = name
        self.docstring = docstring
        self.constructor_args = constructor_args


class ConstructorSpec(MethodSpec):
    """A Specification defining a constructor"""

    def __init__(self, docstring, args):
        self.docstring = docstring
        self.args = {arg.name: arg for arg in args}

    def assert_args(self, type_registry, cls_name, args):
        for arg_name, arg_value in args.items():
            arg_spec = self.args.get(arg_name)
            if not arg_spec:
                raise ValueError(
                    'ArgSpec missing on class %s for constructor arg %r' % (cls_name, arg_name)
                )
            type_registry.assert_type_name(
                arg_spec.type, arg_value, '%s.__init__ arg %r' % (cls_name, arg_name)
            )


class ClassSpec:
    """A Specification defined a custom defined class."""

    def __init__(
        self, *, name, docstring, public_attributes=[], constructor=None, public_methods=[]
    ):
        self.name = name
        self.docstring = docstring
        self.public_attributes = {
            public_attribute.name: public_attribute
            for public_attribute in public_attributes
        }
        self.constructor = constructor
        self.public_methods = {
            public_method.name: public_method
            for public_method in public_methods
        }

    def assert_constructor_args(self, type_registry, method_args):
        if not self.constructor:
            raise ValueError('ConstructorSpec missing on class %s' % self.name)
        self.constructor.assert_args(type_registry, self.name, method_args)

    def assert_method_args(self, type_registry, method_name, method_args):
        method_spec = self.public_methods.get(method_name)
        if not method_spec:
            raise ValueError(
                'MethodSpec missing on class %s for method %r' % (self.name, method_name)
            )
        method_spec.assert_args(type_registry, self.name, method_args)

    def assert_attribute_value(self, type_registry, name, value):
        attribute_spec = self.public_attributes.get(name)
        if not attribute_spec:
            raise exceptions.StrongTypingError(
                'ValueSpec missing on class %s for attribute %s' % (self.name, name)
            )
        type_registry.assert_type_name(
            attribute_spec.type, value, '%s.%s' % (self.name, name)
        )


class _IntWithValueProperty(int):
    @property
    def value(self):
        return self


class _StrWithValueProperty(str):
    @property
    def value(self):
        return self


_WITH_VALUE_PROPERTY_CLASSES = {
    int: _IntWithValueProperty,
    str: _StrWithValueProperty
}


def Enum(*, name, key_value_dict, docstring=None, show_values=False):

    valid_values = set(v for v in key_value_dict.values())

    def _type_check(value):
        return value in valid_values

    key_value_dict = {
        key: _WITH_VALUE_PROPERTY_CLASSES[type(value)](value)
        for key, value in key_value_dict.items()
    }
    for k, v in key_value_dict.items():
        v.name = k

    @lru_cache()
    def _spec():
        return EnumSpec(
            name=name,
            docstring=docstring or '',
            members=[
                {'name': name, 'value': value}
                for name, value in sorted(key_value_dict.items())
                if 'UNKNOWN' not in name
            ],
            show_values=show_values
        )

    members = dict(key_value_dict)
    members['_spec'] = _spec
    members['_type_check'] = _type_check

    return type(name, (), members)


def Timeseries(_item_type, _item_desc, _return_on_empty=None):

    base_class = TypedList('Tuple[datetime, %s]' % _item_type)

    class _Timeseries(base_class):
        item_type = _item_type
        item_desc = _item_desc
        return_on_empty = _return_on_empty

        def __init__(self, *args, **kwargs):
            self._from_proto = kwargs.get('_from_proto', False)
            super().__init__(*args, **kwargs)
            self._from_proto = False

        @staticmethod
        def _select_timestamp_or_date(timestamp, date):
            if timestamp and not date:
                return timestamp
            elif date and not timestamp:
                return date
            else:
                raise exceptions.StrongTypingError('Specify date or timestamp, not both')

        def at(self, *, timestamp=None, date=None, inclusive=True):
            real_timestamp = self._select_timestamp_or_date(timestamp, date)
            self._spec().assert_method_args(
                self._registry, 'at',
                {'timestamp': real_timestamp}
            )
            for entry in reversed(self):
                if entry[0] <= real_timestamp:
                    if inclusive or entry[0] < real_timestamp:
                        return entry[1]
            if self.return_on_empty is not None:
                return self.return_on_empty()
            raise exceptions.StrongTypingError(
                'No values provided as of date %s' % real_timestamp
            )

        def before(self, *, timestamp=None, date=None):
            real_timestamp = self._select_timestamp_or_date(timestamp, date)
            self._spec().assert_method_args(
                self._registry, 'before',
                {'timestamp': real_timestamp}
            )
            return self.at(date=real_timestamp, inclusive=False)

        def latest(self):
            if not self:
                if self.return_on_empty is not None:
                    return self.return_on_empty()
                raise exceptions.StrongTypingError('No values provided')
            return self[-1][1]

        def all(self):
            return [item for item in self]

        @classmethod
        @lru_cache()
        def _spec(cls, language_code=symbols.Languages.ENGLISH):
            if language_code != symbols.Languages.ENGLISH:
                raise ValueError('Language not supported')

            item_desc = cls.item_desc
            return merge_class_specs(
                derived_spec=ClassSpec(
                    name='Timeseries',
                    docstring='A generic timeseries.',
                    public_attributes=[],
                    public_methods=[
                        MethodSpec(
                            name='at',
                            docstring=(
                                f' Returns the latest available {item_desc} as of the given '
                                'timestamp.'
                            ),
                            args=[
                                ValueSpec(
                                    name='timestamp',
                                    type='datetime',
                                    docstring=(
                                        'The timestamp as of which to fetch the '
                                        f'latest {item_desc}.'
                                    )
                                ),
                            ],
                            return_value=ReturnValueSpec(
                                type=cls.item_type,
                                docstring=(
                                    f'The latest {item_desc} as of the timestamp provided.'
                                )
                            )
                        ),
                        MethodSpec(
                            name='before',
                            docstring=(
                                f'Returns the latest available {item_desc} as of just before the '
                                'given timestamp.'
                            ),
                            args=[
                                ValueSpec(
                                    name='timestamp',
                                    type='datetime',
                                    docstring=(
                                        'The timestamp just before which to fetch the '
                                        f'latest {item_desc}.'
                                    )
                                ),
                            ],
                            return_value=ReturnValueSpec(
                                type=cls.item_type,
                                docstring=(
                                    f'The latest {item_desc} as of just before the timestamp '
                                    'provided.'
                                )
                            )
                        ),
                        MethodSpec(
                            name='latest',
                            docstring=f'Returns the latest available {item_desc}.',
                            args=[],
                            return_value=ValueSpec(
                                name=None,
                                type=cls.item_type,
                                docstring=f'The latest available {item_desc}.'
                            )
                        ),
                        MethodSpec(
                            name='all',
                            docstring=(
                                f'Returns a list of all available {item_desc} values across time.'
                            ),
                            args=[],
                            return_value=ValueSpec(
                                name=None,
                                type=f'List[Tuple[datetime, {cls.item_type}]]',
                                docstring=f'All available {item_desc} values and their timestamps.'
                            )
                        ),
                    ]
                ),
                base_spec=base_class._spec(language_code)  # noqa: SLF001
            )

    return _Timeseries


def merge_class_specs(*, derived_spec, base_spec):
    """
    Generates a new ClassSpec object by overriding base_spec values with derived_spec
    values where appropriate.
    """
    return ClassSpec(
        name=derived_spec.name,
        docstring=derived_spec.docstring or base_spec.docstring,
        public_attributes=dict(
            base_spec.public_attributes, **derived_spec.public_attributes
        ).values(),
        constructor=derived_spec.constructor or base_spec.constructor,
        public_methods=dict(base_spec.public_methods, **derived_spec.public_methods).values(),
    )


def transform_const_enum(*, name, const_enum, docstring=None, show_values=False, hide_keys=()):
    """
    Factory creating Enum representation of public.utils.symbols classes that shadow proto enums
    :param const_enum: The class from public.utils.symbols
    """
    key_value_dict = {
        key: value for key, value in const_enum.__dict__.items()
        if not key.startswith('__') and key not in hide_keys
    }
    return Enum(
        name=name,
        key_value_dict=key_value_dict,
        docstring=docstring,
        show_values=show_values
    )


def make_docstring(*names):
    if len(names) == 1:
        return names[0]
    elif len(names) > 1:
        return 'Union[%s]' % ', '.join(names)
    else:
        raise ValueError('len(names) must be >= 1')


def make_docstring_seq(name):
    return 'Sequence[%s]' % name


def dedent_and_strip(string):
    return dedent(string).strip()
