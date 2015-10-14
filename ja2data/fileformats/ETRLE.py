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

import io
import struct

ALPHA_VALUE = 0
IS_COMPRESSED_BYTE_MASK = 0x80
NUMBER_OF_BYTES_MASK = 0x7F


class EtrleException(Exception):
    """Raised when an error in compression or decompression occurs"""
    pass


class ERTLE:
    def __init__(self, data):
        self.data = data

    def decompress(self):
        number_of_compressed_bytes = len(self.data)
        compressed_bytes = struct.unpack('<{}B'.format(number_of_compressed_bytes), self.data)
        extracted_buffer = io.BytesIO()
        bytes_til_next_control_byte = 0

        for current_byte in compressed_bytes:
            if bytes_til_next_control_byte == 0:
                is_compressed_alpha_byte = ((current_byte & IS_COMPRESSED_BYTE_MASK) >> 7) == 1
                length_of_subsequence = current_byte & NUMBER_OF_BYTES_MASK
                if is_compressed_alpha_byte:
                    for s in range(length_of_subsequence):
                        extracted_buffer.write(struct.pack('<B', ALPHA_VALUE))
                else:
                    bytes_til_next_control_byte = length_of_subsequence
            else:
                extracted_buffer.write(struct.pack('<B', current_byte))
                bytes_til_next_control_byte -= 1

        if bytes_til_next_control_byte != 0:
            raise EtrleException('Not enough data to decompress')

        return extracted_buffer.getvalue()

    def compress(self):
        current = 0
        current_lookahead = 0
        length = 0
        source_length = len(self.data)
        compressed_buffer = io.BytesIO()

        while current < source_length:
            if self.data[current] == 0:
                while current_lookahead < source_length and self.data[current_lookahead] == 0 and length < NUMBER_OF_BYTES_MASK:
                    current_lookahead += 1
                    length += 1
                compressed_buffer.write(struct.pack('<B', length | IS_COMPRESSED_BYTE_MASK))
            else:
                while current_lookahead < source_length and self.data[current_lookahead] != 0 and length < NUMBER_OF_BYTES_MASK:
                    current_lookahead += 1
                    length += 1
                compressed_buffer.write(struct.pack('<B', length))
                compressed_buffer.write(struct.pack('<{}B'.format(length), *self.data[current:current+length]))

            current += length
            current_lookahead = current
            length = 0

        compressed_buffer.write(struct.pack('<B', 0))

        return compressed_buffer.getvalue()







