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
import struct
from operator import attrgetter
from PIL import Image, ImagePalette

from .common import decode_ja2_string
from .ETRLE import ERTLE

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
            self.animated = False
        else:
            self.mode = 'indexed'
            self.format_specific_header = Sti8BitHeader(self.format_specific_header)
            self.animated = self.format_specific_header.number_of_images != 1

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


class StiSubImageHeader:
    format_in_file = '<LLHHHH'
    field_names = [
        'offset',
        'length',
        'offset_x',
        'offset_y',
        'height',
        'width'
    ]

    def __init__(self, data):
        data = dict(zip(StiSubImageHeader.field_names, struct.unpack(StiSubImageHeader.format_in_file, data)))
        for key in data:
            setattr(self, key, data[key])

class AuxObjectData:
    format_in_file = '<BBH3sBBB6s'
    field_names = [
        'wall_orientation',
        'number_of_tiles',
        'tile_location_index',
        'unused',
        'current_frame',
        'number_of_frames',
        'flags',
        'unused'
    ]

    def __init__(self, data):
        data = dict(zip(AuxObjectData.field_names, struct.unpack(AuxObjectData.format_in_file, data)))
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
            self.images = [[self._load_16bit_rgb_image()]]
        else:
            self._load_color_palette()
            self._load_sub_image_headers()
            self.start_of_image_data = self.file.tell()
            if not self.header.animated:
                self.images = [[self._load_8bit_indexed_image(self.sub_image_headers[0])]]
            else:
                self._load_aux_object_data()

                self.images = []
                for sub_image_header, aux_object_data in zip(self.sub_image_headers, self.aux_object_data):
                    if aux_object_data.number_of_frames != 0:
                        self.images.append([])
                    self.images[-1].append(self._load_8bit_indexed_image(sub_image_header))

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

        return Image.frombytes(
            'RGB',
            (self.header.width, self.header.height),
            rgb_image_buffer.read(),
            'raw'
        )

    def _load_color_palette(self):
        number_of_palette_bytes = self.header.format_specific_header.number_of_palette_colors * 3
        self.palette = ImagePalette.raw("RGB", self.file.read(number_of_palette_bytes))

    def _load_sub_image_headers(self):
        sub_header_size = struct.calcsize(StiSubImageHeader.format_in_file)
        self.sub_image_headers = []
        for i in range(self.header.format_specific_header.number_of_images):
            data = self.file.read(sub_header_size)
            self.sub_image_headers.append(StiSubImageHeader(data))

    def _load_aux_object_data(self):
        aux_object_size = struct.calcsize(StiSubImageHeader.format_in_file)
        last_subimage_header = max(self.sub_image_headers, key=attrgetter('offset'))

        self.file.seek(
            self.start_of_image_data +
            last_subimage_header.offset +
            last_subimage_header.length, os.SEEK_SET)

        self.aux_object_data = []
        for i in range(self.header.format_specific_header.number_of_images):
            data = self.file.read(aux_object_size)
            self.aux_object_data.append(AuxObjectData(data))

    def _load_8bit_indexed_image(self, sub_image_header):
        self.file.seek(self.start_of_image_data + sub_image_header.offset, os.SEEK_SET)
        compressed_data = self.file.read(sub_image_header.length)
        uncompressed_data = ERTLE(compressed_data).decompress()

        image = Image.frombytes(
            'P',
            (sub_image_header.width, sub_image_header.height),
            uncompressed_data,
            'raw'
        )
        image.putpalette(self.palette)

        return image

