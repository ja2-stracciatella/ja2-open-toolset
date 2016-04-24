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
import io
from time import gmtime
from calendar import timegm
from datetime import datetime
from fs.base import FS
from fs.errors import CreateFailedError, UnsupportedError, ResourceNotFoundError, ResourceInvalidError
from fs.memoryfs import MemoryFS
from fs.multifs import MultiFS

from .common import decode_ja2_string, encode_ja2_string, Ja2FileHeader

DIRECTORY_CONFLICT_SUFFIX = '_DIRECTORY_CONFLICT'
WRITING_NOT_SUPPORTED_ERROR = 'Writing to an SLF is not yet supported. Operation. {}'


class SlfEntry(Ja2FileHeader):
    """
    Class Representation of a SlfEntry that represents a single file inside a slf file
    """
    fields = [
        ('file_name', '256s'),
        ('offset', 'I'),
        ('length', 'I'),
        ('state', 'B'),
        (None, '3x'),
        ('time', 'q'),
        (None, '4x'),
    ]

    @staticmethod
    def map_raw_to_attrs(raw):
        attrs = raw.copy()
        attrs['file_name'] = decode_ja2_string(raw['file_name'])
        attrs['time'] = gmtime(float(raw['time']) / 10000000.0 - 11644473600.0)
        return attrs

    @staticmethod
    def map_attrs_to_raw(attrs):
        raw = attrs.copy()
        raw['file_name'] = encode_ja2_string(attrs['file_name'], pad=256)
        raw['time'] = int((timegm(attrs['time']) + 11644473600.0) * 10000000.0)
        return raw


class SlfHeader(Ja2FileHeader):
    """
    Class Representation of a SlfHeader that is at the top of every slf file
    """
    fields = [
        ('library_name', '256s'),
        ('library_path', '256s'),
        ('number_of_entries', 'i'),
        ('used', 'i'),
        ('sort', 'H'),
        ('version', 'H'),
        ('contains_subdirectories', 'i'),
        (None, '4x')
    ]

    @staticmethod
    def map_raw_to_attrs(raw):
        attrs = raw.copy()
        attrs['library_name'] = decode_ja2_string(raw['library_name'])
        attrs['library_path'] = decode_ja2_string(raw['library_path'])
        return attrs

    @staticmethod
    def map_attrs_to_raw(attrs):
        raw = attrs.copy()
        raw['library_name'] = encode_ja2_string(attrs['library_name'], pad=256)
        raw['library_path'] = encode_ja2_string(attrs['library_path'], pad=256)
        return raw


def _get_normalized_filename(name_in_slf):
    return '/' + '/'.join(name_in_slf.split('\\'))


def _get_slf_filename(name_in_fs):
    return '\\'.join(name_in_fs.strip('/').split('/'))


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
        super(SlfFS, self).__init__()

        if isinstance(slf_filename, str):
            slf_filename = os.path.expanduser(os.path.expandvars(slf_filename))
            slf_filename = os.path.normpath(os.path.abspath(slf_filename))
            try:
                self.file_name = slf_filename
                self.file = open(slf_filename, 'rb')
            except FileNotFoundError as e:
                raise CreateFailedError(
                    'Slf file not found ({0})'.format(slf_filename),
                    details=e
                )
        else:
            self.file_name = 'file-like'
            self.file = slf_filename

        self.header = SlfHeader.from_bytes(self.file.read(SlfHeader.get_size()))
        self.entries = list(map(self._read_entry, range(self.header['number_of_entries'])))

        self.library_name = self.header['library_name']
        self.library_path = self.header['library_path']
        self.sort = self.header['sort']
        self.version = self.header['version']

        self._path_fs = MemoryFS()
        for e in self.entries:
            path = _get_normalized_filename(e['file_name']).split('/')
            directory = '/'.join(path[:-1]) if len(path) > 2 else '/'

            if self._path_fs.isfile(directory):
                # Sometimes there exists a file that has the same name as a directory
                # Solution: Rename it with a _DIRECTORY_CONFLICT suffix
                self._path_fs.move(directory, directory + DIRECTORY_CONFLICT_SUFFIX)

            if self._path_fs.isdir('/'.join(path)):
                self._path_fs.createfile('/'.join(path) + DIRECTORY_CONFLICT_SUFFIX)
            else:
                self._path_fs.makedir(directory, recursive=True, allow_recreate=True)
                self._path_fs.createfile('/'.join(path))

    def _read_entry(self, index):
        entry_size = SlfEntry.get_size()
        self.file.seek(-entry_size * (self.header['number_of_entries'] - index), os.SEEK_END)
        return SlfEntry.from_bytes(self.file.read(entry_size))

    def __str__(self):
        return '<SlfFS: {0}>'.format(self['library_name'])

    def isfile(self, path):
        return self._path_fs.isfile(path)

    def isdir(self, path):
        return self._path_fs.isdir(path)

    def listdir(self, path="/", wildcard=None, full=False, absolute=False, dirs_only=False, files_only=False):
        return self._path_fs.listdir(path, wildcard, full, absolute, dirs_only, files_only)

    def open(self, path, mode='r', buffering=-1, encoding='ascii', errors=None, newline=None, line_buffering=False, **kwargs):
        if mode != 'r' and mode != 'rb':
            raise UnsupportedError(WRITING_NOT_SUPPORTED_ERROR.format('open'))
        if not self.exists(path):
            raise ResourceNotFoundError(path)
        if self.isdir(path):
            raise ResourceInvalidError(path)
        slf_entry = self._get_slf_entry_for_path(path)

        self.file.seek(slf_entry['offset'], os.SEEK_SET)
        if mode == 'rb':
            return io.BytesIO(self.file.read(slf_entry['length']))
        return io.StringIO(self.file.read(slf_entry['length']).decode(encoding))

    def getinfo(self, path):
        if not self.exists(path):
            raise ResourceNotFoundError(path)
        if self.isdir(path):
            return {
                'size': 0
            }
        slf_entry = self._get_slf_entry_for_path(path)
        return {
            'size': slf_entry['length'],
            'modified_time': slf_entry['time']
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
        return next(e for e in self.entries if _get_normalized_filename(e['file_name']) == path)


class BufferedSlfFS(MultiFS):
    def __init__(self, slf_filename=None):
        super(BufferedSlfFS, self).__init__()

        if slf_filename is not None:
            self._file_fs = SlfFS(slf_filename)
            self.addfs('file', self._file_fs)
            self.library_name = self._file_fs.library_name
            self.library_path = self._file_fs.library_path
            self.version = self._file_fs.version
            self.sort = self._file_fs.sort
            self.contains_subdirectories = self._file_fs.header['contains_subdirectories']
        else:
            self.library_name = 'Custom'
            self.library_path = 'Custom.slf'
            self.version = 1
            self.used = 1
            self.sort = 1
            self.contains_subdirectories = 1

        self._memory_fs = MemoryFS()
        self.addfs('memory', self._memory_fs, write=True)

    def remove(self, path):
        if self._file_fs.exists(path):
            return self._file_fs._path_fs.remove(path)
        return super(BufferedSlfFS, self).remove(path)

    def removedir(self, path, recursive=False, force=False):
        if self._file_fs.exists(path):
            return self._file_fs._path_fs.removedir(path, recursive=recursive, force=force)
        return super(BufferedSlfFS, self).removedir(path, recursive=recursive, force=force)

    def save(self, to_file):
        header_size = SlfHeader.get_size()
        names = list(self.walkfiles('/'))

        offset_start = header_size
        sizes = list(self.getinfo(f)['size'] for f in names)
        times = list(self.getinfo(f)['modified_time'] for f in names)
        times = list(t.timetuple() if isinstance(t, datetime) else t for t in times)
        offsets = list(sum(sizes[:i]) + offset_start for i in range(len(sizes)))

        header = SlfHeader(
           library_name=self.library_name,
           library_path=self.library_path,
           number_of_entries=len(names),
           used=len(names),
           sort=self.sort,
           version=self.version,
           contains_subdirectories=self.contains_subdirectories
        )

        to_file.write(bytes(header))

        for name in names:
            with self.open(name, 'rb') as f:
                to_file.write(f.read())
        for name, modified_time, size, offset in zip(names, times, sizes, offsets):
            entry_header = SlfEntry(file_name=_get_slf_filename(name), offset=offset, length=size, time=modified_time, state=0)
            to_file.write(bytes(entry_header))


