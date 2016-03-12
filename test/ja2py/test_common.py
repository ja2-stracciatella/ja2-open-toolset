import unittest
from ja2py.fileformats import encode_ja2_string, decode_ja2_string

class TestJa2StringDecompress(unittest.TestCase):
    def test_encode(self):
        self.assertEqual(encode_ja2_string('spam'), b'spam\x00')
        self.assertEqual(encode_ja2_string('ham', pad=5), b'ham\x00\x00')
        self.assertEqual(encode_ja2_string('ham', pad=6), b'ham\x00\x00\x00')

    def test_decode(self):
        self.assertEqual(decode_ja2_string(b'spam\x00'), 'spam')
        self.assertEqual(decode_ja2_string(b'ham\x00\x00'), 'ham')
        self.assertEqual(decode_ja2_string(b'\x00\x00bar\x00\x00'), 'bar')

