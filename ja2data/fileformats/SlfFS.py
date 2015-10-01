##############################################################################
#
# This file is part of JA2 Open Toolset
#
# JA2 Open Toolset is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# JA2 Open Toolset is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with JA2 Open Toolset.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import os
import struct
import re
import io
from time import localtime, mktime
from functools import partial
from fs.base import FS
from fs.errors import CreateFailedError, UnsupportedError, ResourceNotFoundError, ResourceInvalidError
from fs.memoryfs import MemoryFS
from fs.multifs import MultiFS

from .common import decode_ja2_string, encode_ja2_string

DIRECTORY_CONFLICT_SUFFIX = '_DIRECTORY_CONFLICT'
WRITING_NOT_SUPPORTED_ERROR = 'Writing to an SLF is not yet supported. Operation. {}'


class SlfEntry:
    """
    Class Representation of a SlfEntry that represents a single file inside a slf file
    """
    format_in_file = '<256sIIBB2xqh2x'
    field_names = [
        'file_name',
        'offset',
        'length',
        'state',
        'reserved',
        'time',
        'reserved2'
    ]

    def __init__(self, data=None):
        if data:
            attributes = dict(zip(SlfEntry.field_names, struct.unpack(SlfEntry.format_in_file, data)))
            attributes["file_name"] = '/' + re.sub(r'[\\]+', '/', decode_ja2_string(attributes["file_name"]))
            attributes["time"] = localtime(attributes["time"] / 10000000 - 11644473600)
        else:
            attributes = {
                'file_name': 'Some File',
                'offset': 0,
                'length': 0,
                'state': 0,
                'reserved': 0,
                'time': localtime(),
                'reserved2': 0
            }

        for key in attributes:
            setattr(self, key, attributes[key])

    def to_bytes(self):
        attributes = dict(zip(SlfEntry.field_names, map(partial(getattr, self), SlfEntry.field_names)))
        attributes["file_name"] = encode_ja2_string(attributes["file_name"][1:].replace('/', '\\'), pad=256)
        attributes["time"] = int((mktime(attributes["time"]) + 11644473600) * 10000000)
        return struct.pack(SlfEntry.format_in_file, *list(map(attributes.get, SlfEntry.field_names)))

    def __str__(self):
        return '<SlfEntry: {0}>'.format(list(map(lambda f: getattr(self, f), self.field_names)))

class SlfHeader:
    """
    Class Representation of the SLFHeader that is at the top of every SLF File
    """
    format_in_file = '<256s256siiHHii'
    field_names = [
        'library_name',
        'library_path',
        'number_of_entries',
        'used',
        'sort',
        'version',
        'contains_subdirectories',
        'reserved'
    ]

    def __init__(self, data=None):
        if data:
            attributes = dict(zip(SlfHeader.field_names, struct.unpack(SlfHeader.format_in_file, data)))
            attributes['library_name'] = decode_ja2_string(attributes["library_name"])
            attributes['library_path'] = decode_ja2_string(attributes["library_path"])
        else:
            attributes = {
                'library_name': 'Custom',
                'library_path': 'Custom.slf',
                'number_of_entries': 0,
                'used': 0,
                'sort': 65535,
                'version': 512,
                'contains_subdirectories': 1,
                'reserved': 0,
            }

        for key in attributes:
            setattr(self, key, attributes[key])

    def to_bytes(self):
        attributes = dict(zip(SlfHeader.field_names, map(partial(getattr, self), SlfHeader.field_names)))
        attributes['library_name'] = encode_ja2_string(attributes["library_name"], pad=256)
        attributes['library_path'] = encode_ja2_string(attributes["library_path"], pad=256)
        return struct.pack(SlfHeader.format_in_file, *list(map(attributes.get, SlfHeader.field_names)))

    def __str__(self):
        return '<SlfHeader: {0}>'.format(list(map(lambda f: getattr(self, f), self.field_names)))


class SlfFS(FS):
    """
    Implements a read-only file system on top of a SLF-file
    """

    _meta = {
        'thread_safe': False,
        'virtual': False,
        'read_only': True,
        'unicode_paths': False,
        'case_insensitive_paths': False,
        'network': False,
        'atomic.setcontents': False
    }

    def __init__(self, slf_filename):
        header_size = struct.calcsize(SlfHeader.format_in_file)

        super(SlfFS, self).__init__()

        if isinstance(slf_filename, str):
            slf_filename = os.path.expanduser(os.path.expandvars(slf_filename))
            slf_filename = os.path.normpath(os.path.abspath(slf_filename))
            try:
                self.file_name = slf_filename
                self.file = open(slf_filename, 'rb')
            except FileNotFoundError as e:
                raise CreateFailedError(
                    'Zip file not found ({0})'.format(slf_filename),
                    details=e
                )
        else:
            self.file_name = 'file-like'
            self.file = slf_filename

        header_data = self.file.read(header_size)
        self.header = SlfHeader(header_data)
        self.entries = list(map(self._read_entry, range(self.header.number_of_entries)))

        self._path_fs = MemoryFS()
        for e in self.entries:
            path = e.file_name.split('/')
            directory = '/'.join(path[:-1]) + '/'

            if self._path_fs.isfile(directory):
                # Sometimes there exists a file that has the same name as a directory
                # Solution: Rename it with a _DIRECTORY_CONFLICT suffix
                self._path_fs.remove(directory[:-1])
                self._path_fs.createfile(directory[:-1] + DIRECTORY_CONFLICT_SUFFIX)
            self._path_fs.makedir(directory, recursive=True, allow_recreate=True)
            self._path_fs.createfile(e.file_name)

    def _read_entry(self, index):
        entry_size = struct.calcsize(SlfEntry.format_in_file)
        self.file.seek(-entry_size * (self.header.number_of_entries - index), os.SEEK_END)
        data = self.file.read(entry_size)
        return SlfEntry(data)

    def __str__(self):
        return '<SlfFS: {0}>'.format(self.file_name)

    def isfile(self, path):
        return self._path_fs.isfile(path)

    def isdir(self, path):
        return self._path_fs.isdir(path)

    def listdir(self, path="/", wildcard=None, full=False, absolute=False, dirs_only=False, files_only=False):
        return self._path_fs.listdir(path, wildcard, full, absolute, dirs_only, files_only)

    def open(self, path, mode='r', buffering=-1, encoding=None, errors=None, newline=None, line_buffering=False, **kwargs):
        if mode != 'r' and mode != 'rb':
            raise UnsupportedError(WRITING_NOT_SUPPORTED_ERROR.format('open'))
        if not self.exists(path):
            raise ResourceNotFoundError(path)
        if self.isdir(path):
            raise ResourceInvalidError(path)
        slf_entry = self._get_slf_entry_for_path(path)

        self.file.seek(slf_entry.offset, os.SEEK_SET)
        return io.BytesIO(self.file.read(slf_entry.length))

    def getinfo(self, path):
        if not self.exists(path):
            raise ResourceNotFoundError(path)
        if self.isdir(path):
            return {
                'size': 0
            }
        slf_entry = self._get_slf_entry_for_path(path)
        return {
            'size': slf_entry.length,
            'modified_time': slf_entry.time
        }

    def makedir(self, path, recursive=False, allow_recreate=False):
        raise UnsupportedError(WRITING_NOT_SUPPORTED_ERROR.format('makedir'))

    def remove(self, path):
        raise UnsupportedError(WRITING_NOT_SUPPORTED_ERROR.format('remove'))

    def removedir(self, path, recursive=False, force=False):
        raise UnsupportedError(WRITING_NOT_SUPPORTED_ERROR.format('removedir'))

    def rename(self, src, dst):
        raise UnsupportedError(WRITING_NOT_SUPPORTED_ERROR.format('rename'))

    def _get_slf_entry_for_path(self, path):
        if path.endswith(DIRECTORY_CONFLICT_SUFFIX):
            path = path[:-len(DIRECTORY_CONFLICT_SUFFIX)]
        return next(e for e in self.entries if e.file_name == path)

class BufferedSlfFS(MultiFS):
    def __init__(self, slf_filename=None):
        super(BufferedSlfFS, self).__init__()

        self.header = SlfHeader()
        if slf_filename is not None:
            self._file_fs = SlfFS(slf_filename)
            self.addfs('file', self._file_fs)
            self.header.library_name = self._file_fs.header.library_name
            self.header.library_path = self._file_fs.header.library_path

        self._memory_fs = MemoryFS()
        self.addfs('memory', self._memory_fs, write=True)

    def remove(self, path):
        if self._file_fs.exists(path):
            return self._file_fs._path_fs.remove(path)
        return super(BufferedSlfFS, self).remove(path)

    def save(self, to_file):
        with open(to_file, 'wb+') as file:
            header_size = struct.calcsize(SlfHeader.format_in_file)
            entry_size = struct.calcsize(SlfEntry.format_in_file)
            names = list(self.walkfiles('/'))

            offset_start = header_size
            sizes = list(map(lambda f: self.getinfo(f)['size'], names))
            times = list(map(lambda f: self.getinfo(f)['modified_time'], names))
            offsets = list(map(lambda i:  sum(sizes[:i]) + offset_start, range(len(sizes))))
            self.header.number_of_entries = len(names)
            self.header.used = len(names)

            file.write(self.header.to_bytes())

            for name in names:
                with self.open(name, 'rb') as f:
                    file.write(f.read())
            for name, modified_time, size, offset in zip(names, times, sizes, offsets):
                entry_header = SlfEntry()
                entry_header.file_name = name
                entry_header.offset = offset
                entry_header.length = size
                entry_header.modified_time = modified_time
                file.write(entry_header.to_bytes())


