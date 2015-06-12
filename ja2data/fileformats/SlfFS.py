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
from time import ctime
from fs.base import FS
from fs.errors import CreateFailedError, UnsupportedError, ResourceNotFoundError, ResourceInvalidError
from fs.filelike import FileLikeBase
from fs.memoryfs import MemoryFS

from .common import decode_ja2_string


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

    def __init__(self, data):
        data = dict(zip(SlfEntry.field_names, struct.unpack(SlfEntry.format_in_file, data)))
        data["file_name"] = '/' + re.sub(r'[\\]+', '/', decode_ja2_string(data["file_name"]))
        data["time"] = ctime(data["time"] / 10000000 - 11644473600)
        for key in data:
            setattr(self, key, data[key])

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

    def __init__(self, data):
        data = dict(zip(SlfHeader.field_names, struct.unpack(SlfHeader.format_in_file, data)))
        data['library_name'] = decode_ja2_string(data["library_name"])
        data['library_path'] = decode_ja2_string(data["library_path"])
        for key in data:
            setattr(self, key, data[key])

class PartialFile(FileLikeBase):
    """
    This implements a file inside a SLF archive with offset {offset} and length {size}
    """
    def __init__(self, slf_file, offset, size):
        super(PartialFile, self).__init__()
        self.file = slf_file
        self.min = offset
        self.max = offset + size

        self.file.seek(self.min, os.SEEK_SET)

    def _read(self, sizehint=-1):
        current = self.file.tell()
        is_not_over_max = sizehint != -1 and current + sizehint <= self.max
        sizehint = sizehint if is_not_over_max else self.max - current
        return self.file.read(sizehint) if sizehint != 0 else None

    def _seek(self, offset, whence):
        if whence == os.SEEK_CUR:
            pos = self.file.tell() + offset
        elif whence == os.SEEK_SET:
            pos = self.min + offset
        elif whence == os.SEEK_END:
            pos = self.max + offset
        else:
            raise NotImplementedError('Unsupported Seek Type')
        pos = pos if pos >= self.min else self.min
        pos = pos if pos <= self.max else self.max

        return self.file.seek(pos, os.SEEK_CUR)

    def _tell(self):
        return self.file.tell() - self.offset


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
                self._path_fs.createfile(directory[:-1] + '_DIRECTORY_CONFLICT')
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
        return PartialFile(self.file, slf_entry.offset, slf_entry.length)

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
        return next(e for e in self.entries if e.file_name == path)
