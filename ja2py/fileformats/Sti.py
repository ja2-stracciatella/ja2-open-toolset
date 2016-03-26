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
from PIL import Image, ImagePalette

from .common import Ja2FileHeader
from ..content import Image16Bit, Images8Bit, SubImage8Bit
from .ETRLE import etrle_decompress


class Sti16BitHeader(Ja2FileHeader):
    fields = [
        ('red_color_mask', 'L'),
        ('green_color_mask', 'L'),
        ('blue_color_mask', 'L'),
        ('alpha_channel_mask', 'L'),
        ('red_color_depth', 'B'),
        ('green_color_depth', 'B'),
        ('blue_color_depth', 'B'),
        ('alpha_channel_depth', 'B')
    ]


class Sti8BitHeader(Ja2FileHeader):
    fields = [
        ('number_of_palette_colors', 'L'),
        ('number_of_images', 'H'),
        ('red_color_depth', 'B'),
        ('green_color_depth', 'B'),
        ('blue_color_depth', 'B'),
        (None, '11x')
    ]


class StiHeader(Ja2FileHeader):
    fields = [
        ('file_identifier', '4s'),
        ('initial_size', 'L'),
        ('size_after_compression', 'L'),
        ('transparent_color', 'L'),
        ('flags', 'L'),
        ('height', 'H'),
        ('width', 'H'),
        ('format_specific_header', '20s'),
        ('color_depth', 'B'),
        (None, '3x'),
        ('aux_data_size', 'L'),
        (None, '12x')
    ]

    flags = {
        'flags': {
            'RGB': 2,
            'INDEXED': 3,
            'ZLIB': 4,
            'ETRLE': 5
        }
    }


class StiSubImageHeader(Ja2FileHeader):
    fields = [
        ('offset', 'L'),
        ('length', 'L'),
        ('offset_x', 'H'),
        ('offset_y', 'H'),
        ('height', 'H'),
        ('width', 'H')
    ]


class AuxObjectData(Ja2FileHeader):
    fields = [
        ('wall_orientation', 'B'),
        ('number_of_tiles', 'B'),
        ('tile_location_index', 'H'),
        (None, '3x'),
        ('current_frame', 'B'),
        ('number_of_frames', 'B'),
        ('flags', 'B'),
        (None, '6x')
    ]


def _get_filelike(file):
    if isinstance(file, str):
        filename = os.path.expanduser(os.path.expandvars(file))
        filename = os.path.normpath(os.path.abspath(filename))
        return open(filename, 'rb')
    else:
        return file


def is_16bit_sti(file):
    f = _get_filelike(file)
    header = StiHeader.from_bytes(f.read(StiHeader.get_size()))
    f.seek(0, 0)
    if header['file_identifier'] != b'STCI':
        return False
    return header.get_flag('flags', 'RGB') and not header.get_flag('flags', 'INDEXED')


def is_8bit_sti(file):
    f = _get_filelike(file)
    header = StiHeader.from_bytes(f.read(StiHeader.get_size()))
    f.seek(0, 0)
    if header['file_identifier'] != b'STCI':
        return False
    return header.get_flag('flags', 'INDEXED') and not header.get_flag('flags', 'RGB')


def load_16bit_sti(file):
    if not is_16bit_sti(file):
        raise ValueError('Not a 16bit sti file')
    f = _get_filelike(file)

    header = StiHeader.from_bytes(f.read(StiHeader.get_size()))
    header_16bit = Sti16BitHeader.from_bytes(header['format_specific_header'])

    number_of_pixels = header['width'] * header['height']
    red_color_mask = header_16bit['red_color_mask']
    green_color_mask = header_16bit['green_color_mask']
    blue_color_mask = header_16bit['blue_color_mask']
    pixel_bytes = struct.unpack('<{}H'.format(number_of_pixels), f.read(number_of_pixels * 2))

    rgb_image_buffer = io.BytesIO()
    for pixel_short in pixel_bytes:
        r = (pixel_short & red_color_mask) >> 8
        g = (pixel_short & green_color_mask) >> 3
        b = (pixel_short & blue_color_mask) << 3
        rgb_image_buffer.write(struct.pack('BBB', r, g, b))
    rgb_image_buffer.seek(0, os.SEEK_SET)

    img = Image.frombytes(
        'RGB',
        (header['width'], header['height']),
        rgb_image_buffer.read(),
        'raw'
    )

    return Image16Bit(img)


def _load_raw_sub_image(f, palette, sub_image_header):
    compressed_data = f.read(sub_image_header['length'])
    uncompressed_data = etrle_decompress(compressed_data)

    img = Image.frombytes(
        'P',
        (sub_image_header['width'], sub_image_header['height']),
        uncompressed_data,
        'raw'
    )
    img.putpalette(palette)

    return img


def _to_sub_image(image, sub_image_header, aux_image_data):
    sub = SubImage8Bit(image)

    sub.offsets = (sub_image_header['offset_x'], sub_image_header['offset_y'])

    if aux_image_data:
        sub.aux_data = {
            'wall_orientation': aux_image_data['wall_orientation'],
            'number_of_tiles': aux_image_data['number_of_tiles'],
            'tile_location_index': aux_image_data['tile_location_index'],
            'current_frame': aux_image_data['current_frame'],
            'number_of_frames': aux_image_data['number_of_frames'],
        }

    return sub


def load_8bit_sti(file):
    if not is_8bit_sti(file):
        raise ValueError('Not a non-animated 8bit sti file')
    f = _get_filelike(file)

    header = StiHeader.from_bytes(f.read(StiHeader.get_size()))
    header_8bit = Sti8BitHeader.from_bytes(header['format_specific_header'])

    palette_colors = [struct.unpack('BBB', f.read(3)) for _ in range(header_8bit['number_of_palette_colors'])]
    colors_in_right_order = [x[0] for x in palette_colors] + [x[1] for x in palette_colors] + [x[2] for x in palette_colors]
    palette = ImagePalette.ImagePalette("RGB", colors_in_right_order, 3 * header_8bit['number_of_palette_colors'])

    sub_image_headers = [StiSubImageHeader.from_bytes(f.read(StiSubImageHeader.get_size()))
                         for _ in range(header_8bit['number_of_images'])]
    images = [_load_raw_sub_image(f, palette, s) for s in sub_image_headers]

    aux_image_data = [None] * len(images)
    if header['aux_data_size'] != 0:
        aux_image_data = [AuxObjectData.from_bytes(f.read(AuxObjectData.get_size()))
                          for _ in range(header_8bit['number_of_images'])]

    return Images8Bit(
        list([_to_sub_image(i, s, a) for i, s, a in zip(images, sub_image_headers, aux_image_data)]),
        palette
    )


