import unittest

from mock import MagicMock as Mock
from collections import OrderedDict

from ja2py.fileformats import encode_ja2_string, decode_ja2_string, Ja2FileHeader

class TestJa2StringDecompress(unittest.TestCase):
    def test_encode(self):
        self.assertEqual(encode_ja2_string('spam'), b'spam\x00')
        self.assertEqual(encode_ja2_string('ham', pad=5), b'ham\x00\x00')
        self.assertEqual(encode_ja2_string('ham', pad=6), b'ham\x00\x00\x00')

    def test_decode(self):
        self.assertEqual(decode_ja2_string(b'spam\x00'), 'spam')
        self.assertEqual(decode_ja2_string(b'ham\x00\x00'), 'ham')
        self.assertEqual(decode_ja2_string(b'\x00\x00bar\x00\x00'), 'bar')


class TestHeader(Ja2FileHeader):
    fields = [
        ('item1', 'B'),
        ('item2', 'B'),
        ('item3', 'H'),
        (None, '2x'),
        ('item4', '4s'),
        (None, '2x')
    ]


class TestJa2FileHeader(unittest.TestCase):
    def test_attribute(self):
        test_header = TestHeader()
        test_header['item1'] = 1
        self.assertEqual(test_header['item1'], 1)

    def test_attribute_through_constructor(self):
        test_header = TestHeader(item1=1)
        self.assertEqual(test_header['item1'], 1)

    def test_setting_non_existing_field_throws(self):
        test_header = TestHeader()

        with self.assertRaises(KeyError):
            test_header['non_existing'] = 1

    def test_setting_none_field_throws(self):
        test_header = TestHeader()

        with self.assertRaises(KeyError):
            test_header[None] = 1

    def test_setting_non_existing_field_through_constructor_throws(self):
        with self.assertRaises(KeyError):
            TestHeader(non_existing=1)

    def test_getting_non_existing_field_throws(self):
        test_header = TestHeader()

        with self.assertRaises(KeyError):
            _ = test_header['non_existing']

    def test_string(self):
        self.assertEqual(str(TestHeader()), '<TestHeader object>')
        self.assertEqual(str(TestHeader(item1=1, item3=3)), '<TestHeader object item1=1 item3=3>')

    def test_keys(self):
        self.assertEqual(TestHeader.keys(), ['item1', 'item2', 'item3', 'item4'])

    def test_struct_size(self):
        self.assertEqual(TestHeader.get_size(), 12)

    def test_reading_from_bytes_without_mapping(self):
        test_header = TestHeader.from_bytes(b'\x01\x02\x00\x03\x00\x001234\x00\x00')

        self.assertEqual(test_header['item1'], 1)
        self.assertEqual(test_header['item2'], 2)
        self.assertEqual(test_header['item3'], 768)
        self.assertEqual(test_header['item4'], b'1234')

    def test_reading_from_bytes_with_mapping_function(self):
        mock = Mock(return_value={'item1': 1, 'item2': 2, 'item3': 3, 'item4': 4})

        class TestHeaderWithMapping(TestHeader):
            @staticmethod
            def map_raw_to_attrs(*args, **kwargs):
                return mock(*args, **kwargs)

        test_header = TestHeaderWithMapping.from_bytes(b'\x01\x02\x00\x03\x00\x001234\x00\x00')

        self.assertEqual(mock.call_count, 1)
        self.assertEqual(mock.call_args[0], ({'item1': 1, 'item2': 2, 'item3': 768, 'item4': b'1234'}, ))
        self.assertEqual(test_header['item1'], 1)
        self.assertEqual(test_header['item2'], 2)
        self.assertEqual(test_header['item3'], 3)
        self.assertEqual(test_header['item4'], 4)

    def throws_when_converting_to_bytes_with_not_all_fields_set(self):
        test_header = TestHeader(item1=2, item2=3)
        with self.assertRaises(KeyError):
            bytes(test_header)

    def test_writing_to_bytes_without_mapping(self):
        test_header = TestHeader(item1=2, item2=3, item3=1024, item4=b'4321')
        self.assertEqual(bytes(test_header), b'\x02\x03\x00\x04\x00\x004321\x00\x00')

    def test_writing_to_bytes_with_mapping_function(self):
        mock = Mock(return_value={'item1': 3, 'item2': 2, 'item3': 1, 'item4': b'1234'})

        class TestHeaderWithMapping(TestHeader):
            @staticmethod
            def map_attrs_to_raw(*args, **kwargs):
                return mock(*args, **kwargs)

        test_header_bytes = bytes(TestHeaderWithMapping(item1=4, item2=5, item3=6, item4=b'4321'))

        self.assertEqual(mock.call_count, 1)
        self.assertEqual(mock.call_args[0], ({'item1': 4, 'item2': 5, 'item3': 6, 'item4': b'4321'}, ))
        self.assertEqual(test_header_bytes, b'\x03\x02\x01\x00\x00\x001234\x00\x00')

    def test_getting_non_existing_flags(self):
        test_header = TestHeader(item3=1)
        with self.assertRaises(KeyError):
            test_header.get_flag('item3', 'flag1')

    def test_getting_flags_without_value(self):
        class TestHeaderWithFlags(TestHeader):
            flags = {'item3': {'flag1': 0}}

        test_header = TestHeaderWithFlags()
        with self.assertRaises(KeyError):
            test_header.get_flag('item3', 'flag1')

    def test_getting_flags(self):
        class TestHeaderWithFlags(TestHeader):
            flags = {'item3': {'flag1': 0, 'flag2': 1}}

        test_header = TestHeaderWithFlags(item3=1)
        self.assertEqual(test_header.get_flag('item3', 'flag1'), True)
        self.assertEqual(test_header.get_flag('item3', 'flag2'), False)

    def test_setting_non_existant_flag(self):
        test_header = TestHeader(item3=1)
        with self.assertRaises(KeyError):
            test_header.set_flag('item3', 'flag1', True)

    def test_setting_flag(self):
        class TestHeaderWithFlags(TestHeader):
            flags = {'item3': {'flag1': 0, 'flag2': 1}}

        test_header = TestHeaderWithFlags(item3=1)

        test_header.set_flag('item3', 'flag1', False)
        test_header.set_flag('item3', 'flag2', True)

        self.assertEqual(test_header['item3'], 2)



