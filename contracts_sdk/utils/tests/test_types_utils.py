from abc import abstractmethod
import builtins
from datetime import datetime
import unittest

from .. import exceptions, symbols, types_registry, types_utils


class ListOfInts(types_utils.TypedList('int')):
    @classmethod
    def _spec(cls, *_, **__):
        return types_utils.ClassSpec(name='ListOfInts', docstring='')


registry = types_registry.TypeRegistry(
    builtins={name: getattr(builtins, name) for name in dir(builtins)},
    custom=[ListOfInts]
)


class PublicTypesUtilsTest(unittest.TestCase):

    def test_hidden_keys_key_not_in_symbol(self):
        ContractParameterLevel = types_utils.transform_const_enum(
            name='Level',
            const_enum=symbols.ContractParameterLevel,
            docstring='Different levels of visibility for Parameter objects.',
            hide_keys=('SIMULATION')
        )
        self.assertRaises(AttributeError, getattr, ContractParameterLevel, 'SIMULATION')

    def test_hidden_keys_key_in_symbol(self):
        ContractParameterLevel = types_utils.transform_const_enum(
            name='Level',
            const_enum=symbols.ContractParameterLevel,
            docstring='Different levels of visibility for Parameter objects.',
            hide_keys=('INSTANCE')
        )
        self.assertRaises(AttributeError, getattr, ContractParameterLevel, 'INSTANCE')

    def test_typed_lists(self):

        x = ListOfInts()
        self.assertEqual(len(x), 0)
        self.assertTrue(not x)

        x = ListOfInts([1, 2, 3])
        self.assertEqual(len(x), 3)
        self.assertEqual(x, [1, 2, 3])
        self.assertNotEqual(x, [1, 2])

        def generator():
            yield 1
            yield 'hello'

        with self.assertRaisesRegex(
            exceptions.StrongTypingError,
            r"ListOfInts item\[1\] expected int but got value 'hello'"
        ):
            ListOfInts(generator())

        def generator():
            yield 1
            yield 2
            yield 3

        x = ListOfInts(generator())
        self.assertEqual(x, [1, 2, 3])
        x.extend((4, 5, 6))
        x.append(7)
        self.assertEqual(x, [1, 2, 3, 4, 5, 6, 7])

        self.assertEqual(x[2], 3)
        self.assertEqual(x[2:5], [3, 4, 5])
        self.assertEqual(x[4:], [5, 6, 7])
        self.assertEqual(x[:3], [1, 2, 3])

        with self.assertRaisesRegex(
            exceptions.StrongTypingError,
            r"ListOfInts item expected int but got value 'hello'"
        ):
            x.append('hello')

        with self.assertRaisesRegex(
            exceptions.StrongTypingError,
            r"ListOfInts item\[1\] expected int but got value 'world'"
        ):
            x.extend([8, 'world'])

        self.assertEqual(x, [1, 2, 3, 4, 5, 6, 7])

        x_plus_extras = x + [8]
        self.assertEqual(x, [1, 2, 3, 4, 5, 6, 7])
        self.assertIsInstance(x_plus_extras, ListOfInts)
        self.assertEqual(x_plus_extras, [1, 2, 3, 4, 5, 6, 7, 8])

        x_plus_extras += ListOfInts([9])
        self.assertEqual(x_plus_extras, [1, 2, 3, 4, 5, 6, 7, 8, 9])

        rhs_added = [1, 2] + ListOfInts([3, 4])
        self.assertIsInstance(rhs_added, list)
        self.assertNotIsInstance(rhs_added, ListOfInts)
        self.assertEqual(rhs_added, [1, 2, 3, 4])

        x[3] = 123
        self.assertEqual(x, [1, 2, 3, 123, 5, 6, 7])

        with self.assertRaisesRegex(
            exceptions.StrongTypingError,
            r"ListOfInts item expected int but got value '123'"
        ):
            x[3] = '123'

        x[3:5] = [123]
        self.assertEqual(x, [1, 2, 3, 123, 6, 7])

        with self.assertRaisesRegex(
            exceptions.StrongTypingError,
            r"ListOfInts item expected int but got value 'hmm'"
        ):
            x[3:5] = [55555, 0, -323, 'hmm', 7]

    def test_typed_list_type_check(self):
        list_of_ints = ListOfInts()
        with self.assertRaises(exceptions.StrongTypingError):
            list_of_ints.append('not_an_int')

    def test_typed_list_from_proto(self):
        data = [1, 2, 'not_an_int']
        list_bypass_type_check = ListOfInts(data, _from_proto=True)
        self.assertEqual(len(list_bypass_type_check), 3)

    def test_type_annotation_any(self):
        for obj in 123, None, 'hello', {(1, 2): ListOfInts([4, 5, 6])}:
            registry.assert_type_name('Any', obj, '')

    def test_type_annotation_dict(self):
        registry.assert_type_name(
            'Dict[int, ListOfInts]',
            {1: ListOfInts(), 2: ListOfInts([1, 2])},
            ''
        )
        registry.assert_type_name('Dict[int, ListOfInts]', {}, '')

        with self.assertRaisesRegex(
            exceptions.StrongTypingError,
            r"expected Dict\[int, ListOfInts\] but got value 'hello'"
        ):
            registry.assert_type_name('Dict[int, ListOfInts]', 'hello', '')

        with self.assertRaisesRegex(
            exceptions.StrongTypingError,
            r"expected Dict\[int, str\] but got value {'5': '5'}"
        ):
            registry.assert_type_name('Dict[int, str]', {'5': '5'}, '')

        with self.assertRaisesRegex(
            exceptions.StrongTypingError,
            r"expected Dict\[int, ListOfInts\] but got value {1: \[\], 2: \[1, 2\]}"
        ):
            registry.assert_type_name('Dict[int, ListOfInts]', {1: ListOfInts(), 2: [1, 2]}, '')

    def test_type_annotation_list(self):
        registry.assert_type_name('List[str]', [], '')
        registry.assert_type_name('List[str]', ['hello', 'world'], '')

        with self.assertRaisesRegex(
            exceptions.StrongTypingError,
            r"expected List\[str\] but got value 123"
        ):
            registry.assert_type_name('List[str]', 123, '')

        with self.assertRaisesRegex(
            exceptions.StrongTypingError,
            r"expected List\[str\] but got value \[123, '456'\]"
        ):
            registry.assert_type_name('List[str]', [123, '456'], '')

        registry.assert_type_name('List[int]', ListOfInts([123, 456]), '')

    def test_type_annotation_optional(self):
        registry.assert_type_name('Optional[int]', 123, '')
        registry.assert_type_name('Optional[int]', None, '')
        registry.assert_type_name('Optional[ListOfInts]', None, '')
        registry.assert_type_name('Optional[ListOfInts]', ListOfInts([1, 2, 3]), '')

        with self.assertRaisesRegex(
            exceptions.StrongTypingError,
            r"expected Optional\[int\] but got value 'some string'"
        ):
            registry.assert_type_name('Optional[int]', 'some string', '')

    def test_type_annotation_tuple(self):
        registry.assert_type_name('Tuple[int, str]', (123, '456'), '')
        registry.assert_type_name('Tuple[int, str, List[int]]', (123, '456', [789]), '')

        with self.assertRaisesRegex(
            exceptions.StrongTypingError,
            r"expected Tuple\[int, str\] but got value \[123, '456'\]"
        ):
            registry.assert_type_name('Tuple[int, str]', [123, '456'], '')

        with self.assertRaisesRegex(
            exceptions.StrongTypingError,
            r"expected Tuple\[int, str\] but got value 123"
        ):
            registry.assert_type_name('Tuple[int, str]', 123, '')

    def test_type_annotation_union(self):
        registry.assert_type_name('Union[int, str]', 123, '')
        registry.assert_type_name('Union[int, str]', '123', '')

        with self.assertRaisesRegex(
            exceptions.StrongTypingError,
            r"expected Union\[int, str\] but got value 1.23"
        ):
            registry.assert_type_name('Union[int, str]', 1.23, '')

    def test_timeseries_with_type_checking(self):
        StringTimeseries = types_utils.Timeseries('int', 'bunch of ints')
        builtins_ = {name: getattr(builtins, name) for name in dir(builtins)}
        builtins_['datetime'] = datetime
        types_registry.TypeRegistry(
            builtins=builtins_,
            custom=[StringTimeseries]
        )
        ts = StringTimeseries()
        ts.append((datetime(year=2020, month=10, day=1), 1))
        ts.append((datetime(year=2020, month=10, day=1), 2))
        with self.assertRaises(exceptions.StrongTypingError):
            ts.append((datetime(year=2020, month=10, day=3), 'Wrong type'))

    def test_timeseries_from_proto(self):
        StringTimeseries = types_utils.Timeseries('int', 'bunch of ints')
        proto_series = [
            (datetime(year=2020, month=10, day=1), 1),
            (datetime(year=2020, month=10, day=1), 2),
            (datetime(year=2020, month=10, day=3), 'No Type Checking'),
        ]
        ts = StringTimeseries(proto_series, _from_proto=True)
        self.assertEqual(len(ts.all()), 3)


class TestStrictInterface(unittest.TestCase):

    def test_can_instantiate_class_with_all_abstract_methods(self):

        class BaseClass(types_utils.StrictInterface):
            @abstractmethod
            def base_method_one(self):
                pass

        class DerivedClass(BaseClass):
            def base_method_one(self):
                pass

        instance = DerivedClass()
        self.assertIsNotNone(instance)

    def test_can_instantiate_class_with_all_abstract_methods_multiple_inheritance(self):

        class BaseClass(types_utils.StrictInterface):
            @abstractmethod
            def base_method_one(self):
                pass

        class IntermediateClass(BaseClass):
            @abstractmethod
            def base_method_two(self):
                pass

        class DerivedClass(IntermediateClass):
            def base_method_one(self):
                pass

            def base_method_two(self):
                pass

        instance = DerivedClass()
        self.assertIsNotNone(instance)

    def test_cannot_instantiate_class_unless_all_abstract_methods_implemented(self):

        class BaseClass(types_utils.StrictInterface):
            @abstractmethod
            def base_method_one(self):
                pass

        class DerivedClass(BaseClass):
            pass

        with self.assertRaises(TypeError):
            DerivedClass()

    def test_cannot_instantiate_derived_class_unless_all_abstract_methods_implemented(self):

        class BaseClass(types_utils.StrictInterface):
            @abstractmethod
            def base_method_one(self):
                pass

        class IntermediateClass(BaseClass):
            @abstractmethod
            def base_method_two(self):
                pass

        class DerivedClass(IntermediateClass):
            def base_method_two(self):
                pass

        with self.assertRaises(TypeError):
            DerivedClass()

    def test_cannot_instantiate_class_if_method_not_in_base_class(self):

        class BaseClass(types_utils.StrictInterface):
            @abstractmethod
            def base_method_one(self):
                pass

        class DerivedClass(BaseClass):
            def base_method_one(self):
                pass

            def missing_method(self):
                pass

        with self.assertRaises(TypeError):
            DerivedClass()

    def test_private_methods_allowed(self):

        class BaseClass(types_utils.StrictInterface):
            @abstractmethod
            def base_method_one(self):
                pass

        class IntermediateClass(BaseClass):
            @abstractmethod
            def base_method_two(self):
                pass

        class DerivedClass(IntermediateClass):

            def _private_method(self):
                pass

            def base_method_one(self):
                pass

            def base_method_two(self):
                pass

        instance = DerivedClass()
        self.assertIsNotNone(instance)
