import unittest
from io import BytesIO

from ja2py.fileformats.Gap import load_gap


class TestGap(unittest.TestCase):
    def test_load_gap(self):
        gap_file = BytesIO(b'\x01\x00\x00\x00\x02\x00\x00\x00' + b'\x03\x00\x00\x00\x04\x00\x00\x00')

        self.assertEqual(load_gap(gap_file), [
            (1, 2),
            (3, 4)
        ])

    def test_load_gap_with_error(self):
        gap_file = BytesIO(b'\x01\x00\x00\x00\x02\x00\x00\x00' + b'\x03')

        with self.assertRaises(ValueError):
            load_gap(gap_file)
