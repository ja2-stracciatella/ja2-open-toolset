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
import PIL.Image
import io

from .common import decode_ja2_string

class StiFileFormatException(Exception):
    """Raised when a STI file is incorrectly formatted"""
    pass

class StiHeader:
    format_in_file = '<4sLLLLHH20sBH17s'
    field_names = [
        'file_identifier',
        'initial_size',
        'size_after_compression',
        'transparent_color',
        'flags',
        'height',
        'width',
        'format_specific_header',
        'color_depth',
        'application_data_size',
        'unused'
    ]

    flag_bits = {
        'RGB': 2,
        'INDEXED': 3,
        'ZLIB': 4,
        'ETRLE': 5
    }

    def __init__(self, data):
        data = dict(zip(StiHeader.field_names, struct.unpack(StiHeader.format_in_file, data)))
        data['file_identifier'] = decode_ja2_string(data["file_identifier"])
        for key in data:
            if key != 'unused':
                setattr(self, key, data[key])

        print(data)
        if self.file_identifier != 'STCI':
            raise StiFileFormatException('Not a STI File')
        if self.get_flag('RGB') and self.get_flag('INDEXED'):
            raise StiFileFormatException('Both RGB and Indexed flags are set')
        if self.get_flag('ZLIB'):
            raise StiFileFormatException('Zlib compression not supported')
        if self.get_flag('RGB') and self.color_depth != 16:
            raise StiFileFormatException('Indexed format specified, but color depth is {} bytes'.format(self.color_depth))
        if self.get_flag('INDEXED') and self.color_depth != 8:
            raise StiFileFormatException('RGB format specified, but color depth is {} bytes'.format(self.color_depth))

        if self.get_flag('RGB'):
            self.mode = 'rgb'
            self.format_specific_header = Sti16BitHeader(self.format_specific_header)
        else:
            self.mode = 'indexed'
            self.format_specific_header = Sti8BitHeader(self.format_specific_header)
        self.animated = self.application_data_size != 0

    def get_flag(self, flag_name):
        return (self.flags >> StiHeader.flag_bits[flag_name]) & 1 == 1

class Sti16BitHeader:
    format_in_file = '<LLLLBBBB'
    field_names = [
        'red_color_mask',
        'green_color_mask',
        'blue_color_mask',
        'alpha_channel_mask',
        'red_color_depth',
        'green_color_depth',
        'blue_color_depth',
        'alpha_channel_depth',
    ]

    def __init__(self, data):
        data = dict(zip(Sti16BitHeader.field_names, struct.unpack(Sti16BitHeader.format_in_file, data)))
        for key in data:
            if key != 'unused':
                setattr(self, key, data[key])


class Sti8BitHeader:
    format_in_file = '<LHBBB11s'
    field_names = [
        'number_of_palette_colors',
        'number_of_images',
        'red_color_depth',
        'green_color_depth',
        'blue_color_depth',
        'unused'
    ]

    def __init__(self, data):
        data = dict(zip(Sti8BitHeader.field_names, struct.unpack(Sti8BitHeader.format_in_file, data)))
        for key in data:
            if key != 'unused':
                setattr(self, key, data[key])

class Sti:
    def __init__(self, sti_filename):
        header_size = struct.calcsize(StiHeader.format_in_file)

        if isinstance(sti_filename, str):
            sti_filename = os.path.expanduser(os.path.expandvars(sti_filename))
            sti_filename = os.path.normpath(os.path.abspath(sti_filename))
            self.file = open(sti_filename, 'rb')
        else:
            self.file = sti_filename

        self.header = StiHeader(self.file.read(header_size))

        if self.header.mode == 'rgb':
            self._load_16bit_rgb_image()

    def _load_16bit_rgb_image(self):
        number_of_pixels = self.header.width * self.header.height
        red_color_mask = self.header.format_specific_header.red_color_mask
        green_color_mask = self.header.format_specific_header.green_color_mask
        blue_color_mask = self.header.format_specific_header.blue_color_mask
        pixel_bytes = struct.unpack('<{}H'.format(number_of_pixels), self.file.read(number_of_pixels * 2))
        rgb_image_buffer = io.BytesIO()

        for pixel_short in pixel_bytes:
            r = (pixel_short & red_color_mask) >> 8
            g = (pixel_short & green_color_mask) >> 3
            b = (pixel_short & blue_color_mask) << 3
            rgb_image_buffer.write(struct.pack('BBB', r, g, b))
        rgb_image_buffer.seek(0, os.SEEK_SET)

        self.images = [
            [
                PIL.Image.frombytes(
                    'RGB',
                    (self.header.width, self.header.height),
                    rgb_image_buffer.read(),
                    'raw'
                )
            ]
        ]
