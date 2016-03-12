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

from .common import decode_ja2_string, Ja2FileHeader, encode_ja2_string
from .ETRLE import etrle_compress, etrle_decompress

# We expect that no normalized image is larger than the fullscreen size
MAX_NORMALIZED_IMAGE_SIZE = 640 * 480

class StiFileFormatException(Exception):
    """Raised when a STI file is incorrectly formatted"""
    pass


class StiHeader(Ja2FileHeader):
    format_in_file = '<4sLLLLHH20sB3sL12s'
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
        'unused',
        'aux_data_size',
        'unused2'
    ]
    default_values = [
        'STCI',
        0,
        0,
        0,
        40,
        0,
        0,
        None,
        8,
        '123',
        0,
        '123456789012'
    ]

    flag_bits = {
        'RGB': 2,
        'INDEXED': 3,
        'ZLIB': 4,
        'ETRLE': 5
    }

    def __init__(self, data):
        super(StiHeader, self).__init__(data)
        aux_object_data_size = struct.calcsize(AuxObjectData.format_in_file)

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
            self.animated = self.aux_data_size != 0
            expected_aux_data_size = self.format_specific_header.number_of_images * aux_object_data_size
            if self.animated and self.aux_data_size != expected_aux_data_size:
                raise(StiFileFormatException("Application Data expected to be {} was {}".format(
                    self.format_specific_header.number_of_images * struct.calcsize(AuxObjectData.format_in_file),
                    self.aux_data_size
                )))

    def get_attributes_from_data(self, data_dict):
        data_dict['file_identifier'] = decode_ja2_string(data_dict["file_identifier"])
        return data_dict

    def get_data_from_attributes(self, attributes_dict):
        attributes_dict['file_identifier'] = encode_ja2_string(attributes_dict["file_identifier"], pad=4)
        attributes_dict['format_specific_header'] = self.format_specific_header.to_bytes()
        return attributes_dict


class Sti16BitHeader(Ja2FileHeader):
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


class Sti8BitHeader(Ja2FileHeader):
    format_in_file = '<LHBBB11s'
    field_names = [
        'number_of_palette_colors',
        'number_of_images',
        'red_color_depth',
        'green_color_depth',
        'blue_color_depth',
        'unused'
    ]


class StiSubImageHeader(Ja2FileHeader):
    format_in_file = '<LLHHHH'
    field_names = [
        'offset',
        'length',
        'offset_x',
        'offset_y',
        'height',
        'width'
    ]


class AuxObjectData(Ja2FileHeader):
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
                self.images = [
                    [
                        self._load_8bit_indexed_image(s) for s in self.sub_image_headers
                    ]
                ]
            else:
                self._load_aux_object_data()

                self.images = []
                for sub_image_header, aux_object_data in zip(self.sub_image_headers, self.aux_object_data):
                    if aux_object_data.number_of_frames != 0 or len(self.images) == 0:
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

    def _16bit_rgb_image_to_bytes(self):
        w, h = self.header.width, self.header.height
        write_buffer = io.BytesIO()
        for y in range(h):
            for x in range(w):
                pix = self.images[0][0].getpixel((x, y))
                r = pix[0] >> 3
                g = pix[1] >> 3
                b = pix[2] >> 3
                rgb = b + (g << 6) + (r << 11)
                write_buffer.write(struct.pack('<H', rgb))
        return write_buffer.getvalue()

    def _load_color_palette(self):
        number_of_palette_bytes = self.header.format_specific_header.number_of_palette_colors * 3
        self.palette = ImagePalette.raw("RGB", self.file.read(number_of_palette_bytes))

    def _color_palette_to_bytes(self):
        if self.palette.rawmode:
            return self.palette.palette
        return self.palette.tobytes()

    def _load_sub_image_headers(self):
        sub_header_size = struct.calcsize(StiSubImageHeader.format_in_file)
        self.sub_image_headers = []
        for i in range(self.header.format_specific_header.number_of_images):
            data = self.file.read(sub_header_size)
            self.sub_image_headers.append(StiSubImageHeader(data))

    def _sub_image_headers_to_bytes(self):
        write_buffer = io.BytesIO()
        for header in self.sub_image_headers:
            write_buffer.write(header.to_bytes())
        return write_buffer.getvalue()

    def _load_aux_object_data(self):
        aux_object_size = struct.calcsize(StiSubImageHeader.format_in_file)

        self.file.seek(
            self.start_of_image_data +
            self.header.size_after_compression, os.SEEK_SET)

        self.aux_object_data = []
        for i in range(self.header.format_specific_header.number_of_images):
            data = self.file.read(aux_object_size)
            self.aux_object_data.append(AuxObjectData(data))

    def _aux_object_data_to_bytes(self):
        write_buffer = io.BytesIO()
        for header in self.aux_object_data:
            write_buffer.write(header.to_bytes())
        return write_buffer.getvalue()

    def _load_8bit_indexed_image(self, sub_image_header):
        self.file.seek(self.start_of_image_data + sub_image_header.offset, os.SEEK_SET)
        compressed_data = self.file.read(sub_image_header.length)
        uncompressed_data = etrle_decompress(compressed_data)

        image = Image.frombytes(
            'P',
            (sub_image_header.width, sub_image_header.height),
            uncompressed_data,
            'raw'
        )
        image.putpalette(self.palette)

        return image

    def _8bit_indexed_image_to_bytes(self, image):
        width = image.size[0]
        height = image.size[1]
        compressed_data = b''
        uncompressed_data = image.tobytes()

        for i in range(height):
            compressed_data += etrle_compress(uncompressed_data[i*width:(i+1)*width]) + b'\x00'
        return compressed_data

    def _update_offsets(self):
        animation_lengths = list(map(len, self.images))
        current_offset = 0
        for i, anim in enumerate(self.images):
            passed_images = sum(animation_lengths[:i])
            for j, img in enumerate(anim):
                sub_image_index = passed_images + j
                length = len(self._8bit_indexed_image_to_bytes(img))

                self.sub_image_headers[sub_image_index].offset = current_offset
                self.sub_image_headers[sub_image_index].length = length

                current_offset += length

        self.header.size_after_compression = current_offset

    def normalize_animated_images(self):
        normalized_images = []
        animation_start_index = 0
        for animation in self.images:
            headers = self.sub_image_headers[animation_start_index:animation_start_index+len(animation)]

            min_offset_x = min([a.offset_x for a in headers])
            min_offset_y = min([a.offset_y for a in headers])
            normalized_offsets_x = [a.offset_x-min_offset_x for a in headers]
            normalized_offsets_y = [a.offset_y-min_offset_y for a in headers]
            max_width = max([o+a.width for o, a in zip(normalized_offsets_x, headers)])
            max_height = max([o+a.height for o, a in zip(normalized_offsets_y, headers)])

            if max_width * max_height > MAX_NORMALIZED_IMAGE_SIZE:
                raise StiFileFormatException(
                    'The offsets are set in such a way that the image size exceeds full-screen.'
                )

            normalized_animation = []
            for i, image in enumerate(animation):
                normalized_image = Image.new('P', (max_width, max_height), 0)
                normalized_image.putpalette(self.palette)
                normalized_image.paste(image, (normalized_offsets_x[i], normalized_offsets_y[i]))
                normalized_animation.append(normalized_image)

            normalized_images.append(normalized_animation)
            animation_start_index += len(headers)

        self.images = normalized_images

    def save(self, to_file):
        self._update_offsets()
        to_file.write(self.header.to_bytes())
        if self.header.mode == 'rgb':
            to_file.write(self._16bit_rgb_image_to_bytes())
        else:
            to_file.write(self._color_palette_to_bytes())
            to_file.write(self._sub_image_headers_to_bytes())
            for animation in self.images:
                for image in animation:
                    to_file.write(self._8bit_indexed_image_to_bytes(image))
            if self.header.animated:
                to_file.write(self._aux_object_data_to_bytes())

