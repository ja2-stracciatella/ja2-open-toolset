import unittest
from ja2py.fileformats import etrle_compress, etrle_decompress, EtrleException

COMPRESSED_FLAG = 0x80
MAX_COMPR_BYTES = 127


class TestEtrleDecompress(unittest.TestCase):
    def test_zeros(self):
        self.assertEqual(etrle_decompress(bytes([COMPRESSED_FLAG | 0x02])), 2 * b'\x00')
        self.assertEqual(etrle_decompress(bytes([COMPRESSED_FLAG | 0x02, COMPRESSED_FLAG | 0x02])), 4 * b'\x00')

        self.assertEqual(etrle_decompress(bytes([COMPRESSED_FLAG | 0x0F])), 15 * b'\x00')
        self.assertEqual(etrle_decompress(bytes([COMPRESSED_FLAG | 0x0F, COMPRESSED_FLAG | 0x0F])), 30 * b'\x00')

        max_byte = COMPRESSED_FLAG | MAX_COMPR_BYTES
        self.assertEqual(etrle_decompress(bytes([max_byte])), MAX_COMPR_BYTES * b'\x00')
        self.assertEqual(etrle_decompress(bytes([max_byte, max_byte])), 2 * MAX_COMPR_BYTES * b'\x00')

    def test_data(self):
        self.assertEqual(etrle_decompress(bytes([0x02, 0x02, 0x03])),  b'\x02\x03')
        self.assertEqual(etrle_decompress(bytes([0x05, 0x02, 0x03, 0x04, 0x05, 0x06])),  b'\x02\x03\x04\x05\x06')

        self.assertEqual(etrle_decompress(bytes([0x02, 0x02, 0x03, 0x02, 0x02, 0x03])),  b'\x02\x03\x02\x03')
        self.assertEqual(etrle_decompress(bytes([0x02, 0x02, 0x03, 0x03, 0x04, 0x05, 0x06])),  b'\x02\x03\x04\x05\x06')

    def test_mixed(self):
        two_zero_bytes = COMPRESSED_FLAG | 0x02

        self.assertEqual(etrle_decompress(bytes([0x02, 0x02, 0x03, two_zero_bytes])),  b'\x02\x03\x00\x00')
        self.assertEqual(etrle_decompress(bytes([two_zero_bytes, 0x02, 0x02, 0x03])),  b'\x00\x00\x02\x03')

        self.assertEqual(
            etrle_decompress(bytes([two_zero_bytes, 0x02, 0x02, 0x03, two_zero_bytes])),
            b'\x00\x00\x02\x03\x00\x00'
        )
        self.assertEqual(
            etrle_decompress(bytes([0x02, 0x02, 0x03, two_zero_bytes, 0x02, 0x02, 0x03])),
            b'\x02\x03\x00\x00\x02\x03'
        )

    def test_not_enough_data(self):
        with self.assertRaises(EtrleException):
            etrle_decompress(bytes([0x02, 0x02]))


class TestEtrleCompress(unittest.TestCase):
    def test_zeros(self):
        self.assertEqual(etrle_compress(3 * b'\x00'), bytes([COMPRESSED_FLAG | 3]))
        self.assertEqual(etrle_compress(12 * b'\x00'), bytes([COMPRESSED_FLAG | 12]))
        self.assertEqual(etrle_compress(MAX_COMPR_BYTES * b'\x00'), bytes([COMPRESSED_FLAG | MAX_COMPR_BYTES]))
        self.assertEqual(
            etrle_compress(2 * MAX_COMPR_BYTES * b'\x00'),
            bytes([COMPRESSED_FLAG | MAX_COMPR_BYTES, COMPRESSED_FLAG | MAX_COMPR_BYTES])
        )

    def test_data(self):
        self.assertEqual(etrle_compress(b'\x01\x02\x03'), b'\x03\x01\x02\x03')
        self.assertEqual(etrle_compress(b'\x01\x02'), b'\x02\x01\x02')
        self.assertEqual(
            etrle_compress(2 * MAX_COMPR_BYTES * b'\x01'),
            b'\x7f' + MAX_COMPR_BYTES * b'\x01' + b'\x7f' + MAX_COMPR_BYTES * b'\x01'
        )

    def test_mixed(self):
        self.assertEqual(etrle_compress(b'\x01\x02\x03\x00'), b'\x03\x01\x02\x03\x81')
        self.assertEqual(etrle_compress(b'\x01\x02\x03\x00\x00\x00'), b'\x03\x01\x02\x03\x83')
        self.assertEqual(etrle_compress(b'\x00\x00\x00\x01\x02\x03'), b'\x83\x03\x01\x02\x03')
        self.assertEqual(etrle_compress(b'\x00\x01\x02\x00\x00'), b'\x81\x02\x01\x02\x82')


class TestEtrleRoundTrip(unittest.TestCase):
    def test_decompress_compress(self):
        self.assertEqual(etrle_decompress(etrle_compress(b'\x01\x02\x03\x00')), b'\x01\x02\x03\x00')
        self.assertEqual(etrle_decompress(etrle_compress(b'\x01\x02\x00\x00\x00\x03')), b'\x01\x02\x00\x00\x00\x03')

    def test_compress_decompress(self):
        self.assertEqual(etrle_compress(etrle_decompress(b'\x8f\x02\x02\x03')), b'\x8f\x02\x02\x03')
        self.assertEqual(etrle_compress(etrle_decompress(b'\x01\x02\x8f\x02\x03\x04')), b'\x01\x02\x8f\x02\x03\x04')

