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

from functools import partial
import struct


def decode_ja2_string(string):
    return string.decode("ascii").replace("\x00", "")

def encode_ja2_string(string, pad=None):
    encoded = (string+'\x00').encode("ascii")
    if pad is not None:
        return encoded.ljust(pad, b'\x00')
    return encoded

class Ja2FileHeader(object):
    format_in_file = ''
    field_names = []
    default_data = []
    flags = None

    def __init__(self, data=None):
        if data:
            raw_data = dict(zip(self.field_names, struct.unpack(self.format_in_file, data)))
            attributes = self.get_attributes_from_data(raw_data)
        else:
            attributes = dict(zip(self.field_names, self.default_data))

        for key in attributes:
            setattr(self, key, attributes[key])

    def get_attributes_from_data(self, data_dict):
        return data_dict

    def get_data_from_attributes(self, attribute_dict):
        return attribute_dict

    def to_bytes(self):
        attributes = dict(zip(self.field_names, map(partial(getattr, self), self.field_names)))
        raw_data = self.get_data_from_attributes(attributes)
        return struct.pack(self.format_in_file, *list(map(raw_data.get, self.field_names)))

    def get_flag(self, flag_name):
        if self.flags is None:
            raise Exception('{}: No flags set')
        if flag_name not in self.flag_bits:
            raise Exception('{}: Unknown Flag: "{}"', self.__class__.__name__, flag_name)
        return (self.flags >> self.flag_bits[flag_name]) & 1 == 1

    def __str__(self):
        return '<{}: {}>'.format(self.__class__.__name__, dict(zip(self.field_names, map(lambda f: getattr(self, f), self.field_names))))
