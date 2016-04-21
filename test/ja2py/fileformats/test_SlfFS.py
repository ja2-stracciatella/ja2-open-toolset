import unittest

from io import BytesIO
from time import strptime
from fs.errors import CreateFailedError, UnsupportedError, ResourceNotFoundError, ResourceInvalidError
from ja2py.fileformats import SlfEntry, SlfHeader, SlfFS, BufferedSlfFS

class TestSlfFSEntry(unittest.TestCase):
    def test_size(self):
        self.assertEqual(SlfEntry.get_size(), 280)

    def test_read_from_bytes(self):
        test_bytes = (b'1234567890' + (246 * b'\x00') + b'\x01\x00\x00\x00' + b'\x02\x00\x00\x00' + b'\x03' +
                      b'\x00\x00\x00' + b'\x00\xa2\xe3\x18\xbc\x86\xd1\x01' + b'\x00\x00\x00\x00')

        header = SlfEntry.from_bytes(test_bytes)
        expected_time = strptime('20160325T173100UTC', "%Y%m%dT%H%M%S%Z")

        self.assertEqual(header['file_name'], '1234567890')
        self.assertEqual(header['offset'], 1)
        self.assertEqual(header['length'], 2)
        self.assertEqual(header['state'], 3)
        self.assertEqual(header['time'], expected_time)

    def test_write_to_bytes(self):
        time = strptime('19900101T010000UTC', "%Y%m%dT%H%M%S%Z")
        header = SlfEntry(file_name='TestPadded', offset=4, length=3, state=2, time=time)
        expected = (b'TestPadded' + (246 * b'\x00') + b'\x04\x00\x00\x00' + b'\x03\x00\x00\x00' + b'\x02' +
                    b'\x00\x00\x00' + b'\x00\xa8\x9az2\x1e\xb4\x01' + b'\x00\x00\x00\x00')

        self.assertEqual(bytes(header), expected)

    def test_idempotency(self):
        time = strptime('20200325T183100UTC', "%Y%m%dT%H%M%S%Z")
        header = SlfEntry(file_name='Some Filename', offset=123581, length=4567, state=125, time=time)

        regenerated_header = SlfEntry.from_bytes(bytes(header))

        self.assertEqual(regenerated_header['file_name'], 'Some Filename')
        self.assertEqual(regenerated_header['offset'], 123581)
        self.assertEqual(regenerated_header['length'], 4567)
        self.assertEqual(regenerated_header['state'], 125)
        self.assertEqual(header['time'], time)


class TestSlfFSHeader(unittest.TestCase):
    def test_size(self):
        self.assertEqual(SlfHeader.get_size(), 532)

    def test_read_from_bytes(self):
        test_bytes = (b'Filename' + (248 * b'\x00') + b'LibraryName' + (245 * b'\x00') + b'\x01\x00\x00\x00' +
                      b'\x02\x00\x00\x00' + b'\x03\x00' + b'\x04\x00' + b'\x05\x00\x00\x00' + b'\x00\x00\x00\x00')

        header = SlfHeader.from_bytes(test_bytes)

        self.assertEqual(header['library_name'], 'Filename')
        self.assertEqual(header['library_path'], 'LibraryName')
        self.assertEqual(header['number_of_entries'], 1)
        self.assertEqual(header['used'], 2)
        self.assertEqual(header['sort'], 3)
        self.assertEqual(header['version'], 4)
        self.assertEqual(header['contains_subdirectories'], 5)

    def test_write_to_bytes(self):
        header = SlfHeader(
            library_name='SomeFilename',
            library_path='SomeLibPath',
            number_of_entries=5,
            used=4,
            sort=6,
            version=2,
            contains_subdirectories=1
        )
        expected_bytes = (b'SomeFilename' + (244 * b'\x00') + b'SomeLibPath' + (245 * b'\x00') + b'\x05\x00\x00\x00' +
                          b'\x04\x00\x00\x00' + b'\x06\x00' + b'\x02\x00' + b'\x01\x00\x00\x00' + b'\x00\x00\x00\x00')

        self.assertEqual(bytes(header), expected_bytes)

    def test_idempotency(self):
        header = SlfHeader(
            library_name='Some Very Complicated Filename',
            library_path='Secret Lib Path',
            number_of_entries=50001,
            used=2500,
            sort=500,
            version=501,
            contains_subdirectories=12
        )

        regenerated_header = SlfHeader.from_bytes(bytes(header))

        self.assertEqual(regenerated_header['library_name'], 'Some Very Complicated Filename')
        self.assertEqual(regenerated_header['library_path'], 'Secret Lib Path')
        self.assertEqual(regenerated_header['number_of_entries'], 50001)
        self.assertEqual(regenerated_header['used'], 2500)
        self.assertEqual(regenerated_header['sort'], 500)
        self.assertEqual(regenerated_header['version'], 501)
        self.assertEqual(regenerated_header['contains_subdirectories'], 12)


def create_test_slf_fs():
    time = strptime('19900101T010000UTC', "%Y%m%dT%H%M%S%Z")
    header = SlfHeader(
        library_name='SomeFile',
        library_path='SomePath',
        number_of_entries=4,
        used=4,
        sort=1,
        version=1,
        contains_subdirectories=1
    )
    data_offset = SlfHeader.get_size()
    first_entry = SlfEntry(file_name='foo\\bar.baz', offset=data_offset, length=5, state=1, time=time)
    second_entry = SlfEntry(file_name='spam\\ham\\parrot.txt', offset=data_offset+5, length=6, state=1, time=time)
    third_entry = SlfEntry(file_name='spam\\parrot.txt', offset=data_offset+11, length=5, state=1, time=time)
    fourth_entry = SlfEntry(file_name='carrot', offset=data_offset+16, length=6, state=1, time=time)

    first_data = b'First'
    second_data = b'Second'
    third_data = b'Third'
    fourth_data = b'Fourth'

    return BytesIO(bytes(header) + first_data + second_data + third_data + fourth_data +
                   bytes(first_entry) + bytes(second_entry) + bytes(third_entry) + bytes(fourth_entry))


def create_slf_fs_with_directory_conflict(reversed=False):
    time = strptime('19900101T010000UTC', "%Y%m%dT%H%M%S%Z")
    header = SlfHeader(
        library_name='SomeFile',
        library_path='SomePath',
        number_of_entries=2,
        used=2,
        sort=1,
        version=1,
        contains_subdirectories=1
    )
    data_offset = SlfHeader.get_size()
    first_entry = SlfEntry(file_name='foo\\bar', offset=data_offset, length=5, state=1, time=time)
    second_entry = SlfEntry(file_name='foo', offset=data_offset+5, length=6, state=1, time=time)

    first_data = b'First'
    second_data = b'Second'

    entries = [bytes(first_entry), bytes(second_entry)]
    if reversed:
        entries.reverse()

    return BytesIO(bytes(header) + first_data + second_data + b''.join(entries))


class TestSlfFS(unittest.TestCase):
    def test_reading_directory_structure(self):
        slf_file = SlfFS(create_test_slf_fs())

        self.assertTrue(slf_file.isdir('/foo'))
        self.assertFalse(slf_file.isfile('/foo'))
        self.assertTrue(slf_file.isdir('/spam'))
        self.assertFalse(slf_file.isfile('/spam'))
        self.assertTrue(slf_file.isdir('/spam/ham'))
        self.assertFalse(slf_file.isfile('/spam/ham'))
        self.assertTrue(slf_file.isdir('/'))
        self.assertFalse(slf_file.isfile('/'))

        self.assertTrue(slf_file.isfile('/foo/bar.baz'))
        self.assertFalse(slf_file.isdir('/foo/bar.baz'))
        self.assertTrue(slf_file.isfile('/spam/ham/parrot.txt'))
        self.assertFalse(slf_file.isdir('/spam/ham/parrot.txt'))
        self.assertTrue(slf_file.isfile('/spam/parrot.txt'))
        self.assertFalse(slf_file.isdir('/spam/parrot.txt'))
        self.assertTrue(slf_file.isfile('/carrot'))
        self.assertFalse(slf_file.isdir('/carrot'))

    def test_directory_conflict(self):
        slf_file = SlfFS(create_slf_fs_with_directory_conflict())

        self.assertTrue(slf_file.isdir('/foo'))
        self.assertTrue(slf_file.isfile('/foo_DIRECTORY_CONFLICT'))
        with slf_file.open('/foo_DIRECTORY_CONFLICT', 'rb') as f:
            self.assertEqual(f.read(), b'Second')

        slf_file = SlfFS(create_slf_fs_with_directory_conflict(reversed=True))

        self.assertTrue(slf_file.isdir('/foo'))
        self.assertTrue(slf_file.isfile('/foo_DIRECTORY_CONFLICT'))
        with slf_file.open('/foo_DIRECTORY_CONFLICT', 'rb') as f:
            self.assertEqual(f.read(), b'Second')

    def test_listing_directory(self):
        slf_file = SlfFS(create_test_slf_fs())

        self.assertEqual(set(slf_file.listdir('/')), {'spam', 'carrot', 'foo'})
        self.assertEqual(set(slf_file.listdir('/foo')), {'bar.baz'})
        self.assertEqual(set(slf_file.listdir('/spam')), {'parrot.txt', 'ham'})
        self.assertEqual(set(slf_file.listdir('/spam/ham')), {'parrot.txt'})

    def test_file_info(self):
        time = strptime('19900101T010000UTC', "%Y%m%dT%H%M%S%Z")
        slf_file = SlfFS(create_test_slf_fs())

        self.assertEqual(slf_file.getinfo('/foo'), {'size': 0})
        self.assertEqual(slf_file.getinfo('/foo/bar.baz'), {'size': 5, 'modified_time': time})
        self.assertEqual(slf_file.getinfo('/spam/parrot.txt'), {'size': 5, 'modified_time': time})
        self.assertEqual(slf_file.getinfo('/spam/ham/parrot.txt'), {'size': 6, 'modified_time': time})
        self.assertEqual(slf_file.getinfo('/carrot'), {'size': 6, 'modified_time': time})

    def test_file_info_on_missing_file(self):
        slf_file = SlfFS(create_test_slf_fs())

        with self.assertRaises(ResourceNotFoundError):
            slf_file.getinfo('/foo/missing')

    def test_file_open(self):
        slf_file = SlfFS(create_test_slf_fs())

        self.assertEqual(slf_file.open('/foo/bar.baz', 'rb').read(), b'First')
        self.assertEqual(slf_file.open('/spam/ham/parrot.txt', 'rb').read(), b'Second')
        self.assertEqual(slf_file.open('/spam/parrot.txt', 'rb').read(), b'Third')
        self.assertEqual(slf_file.open('/carrot', 'r').read(), 'Fourth')

    def test_open_directory(self):
        slf_file = SlfFS(create_test_slf_fs())

        with self.assertRaises(ResourceInvalidError):
            slf_file.open('/foo', 'r')

    def test_open_missing_file(self):
        slf_file = SlfFS(create_test_slf_fs())

        with self.assertRaises(ResourceNotFoundError):
            slf_file.open('/foo/missing', 'r')

    def test_writing_not_supported(self):
        slf_file = SlfFS(create_test_slf_fs())

        with self.assertRaises(UnsupportedError):
            slf_file.open('/foo', 'w')

        with self.assertRaises(UnsupportedError):
            slf_file.makedir('/foo')

        with self.assertRaises(UnsupportedError):
            slf_file.removedir('/foo')

        with self.assertRaises(UnsupportedError):
            slf_file.remove('/foo/bar.baz')

        with self.assertRaises(UnsupportedError):
            slf_file.rename('/carrot', '/parrot')


class TestBufferedSlfFS(unittest.TestCase):
    def test_reading_still_works(self):
        slf_file = BufferedSlfFS(create_test_slf_fs())

        self.assertTrue(slf_file.isdir('/foo'))
        self.assertTrue(slf_file.isfile('/foo/bar.baz'))
        self.assertEqual(slf_file.open('/foo/bar.baz', 'rb').read(), b'First')

    def test_writing_works(self):
        slf_file = BufferedSlfFS(create_test_slf_fs())
        with slf_file.open('/test', 'wb') as f:
            f.write(b'Test')
        with slf_file.open('/test', 'rb') as f:
            self.assertEqual(f.read(), b'Test')

    def test_removing_works(self):
        slf_file = BufferedSlfFS(create_test_slf_fs())

        slf_file.remove('/foo/bar.baz')

        self.assertFalse(slf_file.exists('/foo/bar.baz'))

    def test_removing_directory_works(self):
        slf_file = BufferedSlfFS(create_test_slf_fs())

        slf_file.removedir('/spam', recursive=True, force=True)

        self.assertFalse(slf_file.exists('/spam'))

    def test_writing_to_disk_works(self):
        time = strptime('20160325T183100UTC', "%Y%m%dT%H%M%S%Z")
        slf_file = BufferedSlfFS(create_test_slf_fs())
        expected_bytes = (b'SomeFile' + (248 * b'\x00') + b'SomePath' + (248 * b'\x00') + b'\x02\x00\x00\x00' +
                          b'\x02\x00\x00\x00' + b'\x01\x00' + b'\x01\x00' + b'\x01\x00\x00\x00' + b'\x00\x00\x00\x00' +
                          b'Fourth' + b'WrittenInMemory' +
                          b'carrot' + (250 * b'\x00') + b'\x14\x02\x00\x00' + b'\x06\x00\x00\x00' + b'\x00' +
                          b'\x00\x00\x00' + b'\x00\xa8\x9az2\x1e\xb4\x01' + b'\x00\x00\x00\x00' +
                          b'test\\a' + (250 * b'\x00') + b'\x1A\x02\x00\x00' + b'\x0F\x00\x00\x00' + b'\x00' +
                          b'\x00\x00\x00' + b'\x00\n\xa8z\xc4\x86\xd1\x01' + b'\x00\x00\x00\x00'
                         )

        slf_file.remove('/foo/bar.baz')
        slf_file.removedir('/spam', recursive=True, force=True)

        slf_file.makedir('/test')
        with slf_file.open('/test/a', 'wb') as f:
            f.write(b'WrittenInMemory')
        slf_file.settimes('/test/a', modified_time=time)

        with BytesIO() as output:
            slf_file.save(output)
            self.assertEqual(output.getvalue(), expected_bytes)
