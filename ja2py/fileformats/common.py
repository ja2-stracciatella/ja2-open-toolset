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

import struct


def decode_ja2_string(string):
    return string.decode("ascii").replace("\x00", "")


def encode_ja2_string(string, pad=None):
    encoded = (string + '\x00').encode("ascii")
    if pad is not None:
        return encoded.ljust(pad, b'\x00')
    return encoded


class Ja2FileHeader(object):
    fields = []
    flags = {}

    def __init__(self, **kwargs):
        self.field_values = dict()
        for key, value in kwargs.items():
            self[key] = value

    def __setitem__(self, key, value):
        if key not in self.keys() or key is None:
            raise KeyError()
        self.field_values[key] = value

    def __getitem__(self, key):
        return self.field_values[key]

    def __bytes__(self):
        raw_values = self.map_attrs_to_raw(self.field_values)
        ordered_raw_values = list(map(lambda k: raw_values[k], self.keys()))
        return struct.pack(self._get_struct_format(), *ordered_raw_values)

    def get_flag(self, attr, flag_name):
        return (self[attr] >> self.flags[attr][flag_name]) & 1 == 1

    def set_flag(self, attr, flag_name, value):
        if value:
            self[attr] |= 1 << self.flags[attr][flag_name]
        else:
            self[attr] &= ~(1 << self.flags[attr][flag_name])

    @staticmethod
    def map_raw_to_attrs(data):
        return data

    @staticmethod
    def map_attrs_to_raw(attrs):
        return attrs

    @classmethod
    def keys(cls):
        return list([f[0] for f in cls.fields if f[0] is not None])

    @classmethod
    def _get_struct_format(cls):
        return '<' + str.join('', map(lambda f: f[1], cls.fields))

    @classmethod
    def get_size(cls):
        return struct.calcsize(cls._get_struct_format())

    @classmethod
    def from_bytes(cls, byte_str):
        kwargs = cls.map_raw_to_attrs(dict(zip(cls.keys(), struct.unpack(cls._get_struct_format(), byte_str))))
        return cls(**kwargs)
