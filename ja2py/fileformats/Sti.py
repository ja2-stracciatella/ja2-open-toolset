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
from PIL import Image, ImageFile, ImagePalette

from .common import Ja2FileHeader
from ..content import Image16Bit, Images8Bit, SubImage8Bit
from .ETRLE import etrle_decompress, etrle_compress


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
            'AUX_OBJECT_DATA': 0,
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

    flags = {
        'flags': {
            'FULL_TILE': 0,
            'ANIMATED_TILE': 1,
            'DYNAMIC_TILE': 2,
            'INTERACTIVE_TILE': 3,
            'IGNORES_HEIGHT': 4,
            'USES_LAND_Z': 5,
        }
    }


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
    aux_data = {
        'wall_orientation': aux_image_data['wall_orientation'],
        'number_of_tiles': aux_image_data['number_of_tiles'],
        'tile_location_index': aux_image_data['tile_location_index'],
        'current_frame': aux_image_data['current_frame'],
        'number_of_frames': aux_image_data['number_of_frames'],
        'full_tile': aux_image_data.get_flag('flags', 'FULL_TILE'),
        'animated_tile': aux_image_data.get_flag('flags', 'ANIMATED_TILE'),
        'dynamic_tile': aux_image_data.get_flag('flags', 'DYNAMIC_TILE'),
        'interactive_tile': aux_image_data.get_flag('flags', 'INTERACTIVE_TILE'),
        'ignores_height': aux_image_data.get_flag('flags', 'IGNORES_HEIGHT'),
        'uses_land_z': aux_image_data.get_flag('flags', 'USES_LAND_Z'),
    } if aux_image_data else None

    return SubImage8Bit(
        image,
        offsets=(sub_image_header['offset_x'], sub_image_header['offset_y']),
        aux_data=aux_data
    )


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
        palette,
        width=header['width'],
        height=header['height']
    )


def save_16bit_sti(ja2_image, file):
    if not isinstance(ja2_image, Image16Bit):
        raise ValueError('Input needs to be of type Image16Bit')

    width, height = ja2_image.size[0], ja2_image.size[1]
    image_size = width * height * 2
    raw_image = ja2_image.image
    format_specific_header = Sti16BitHeader(
        red_color_mask=0xF800,
        green_color_mask=0x7E0,
        blue_color_mask=0x1F,
        alpha_channel_mask=0,
        red_color_depth=5,
        green_color_depth=6,
        blue_color_depth=5,
        alpha_channel_depth=0
    )
    header = StiHeader(
        file_identifier=b'STCI',
        initial_size=image_size,
        size_after_compression=image_size,
        transparent_color=0,
        width=width,
        height=height,
        format_specific_header=bytes(format_specific_header),
        color_depth=16,
        aux_data_size=0,
        flags=0
    )
    header.set_flag('flags', 'RGB', True)

    file.write(bytes(header))

    for y in range(height):
        for x in range(width):
            pix = raw_image.getpixel((x, y))
            r = pix[0] >> 3
            g = pix[1] >> 3
            b = pix[2] >> 3
            rgb = b + (g << 6) + (r << 11)
            file.write(struct.pack('<H', rgb))


def _sub_image_to_bytes(sub_image):
    width = sub_image.image.size[0]
    height = sub_image.image.size[1]
    compressed_buffer = io.BytesIO()
    uncompressed_data = sub_image.image.tobytes()

    for i in range(height):
        compressed_buffer.write(etrle_compress(uncompressed_data[i*width:(i+1)*width]))
        compressed_buffer.write(b'\x00')
    return compressed_buffer.getvalue()


def _palette_to_bytes(palette):
    buffer = io.BytesIO()

    if not palette.rawmode:
        wrong_order = palette.tobytes()
        number_of_colors = int(len(wrong_order) / 3)
        for i in range(number_of_colors):
            buffer.write(wrong_order[i:i+1] + wrong_order[number_of_colors+i:number_of_colors+i+1] + wrong_order[2*number_of_colors+i:2*number_of_colors+i+1])
    else:
        buffer.write(palette.palette)

    return buffer.getvalue()


def save_8bit_sti(ja2_images, file):
    if not isinstance(ja2_images, Images8Bit):
        raise ValueError('Input needs to be of type Images8Bit')

    aux_data = list(i.aux_data for i in ja2_images.images if i.aux_data is not None)
    if len(aux_data) != 0 and not len(aux_data) == len(ja2_images):
        raise ValueError('Either all or none of the sub_images needs to have aux_data to save')

    palette_bytes = _palette_to_bytes(ja2_images.palette).ljust(256 * 3, b'\x00')

    initial_size = ja2_images.width * ja2_images.height
    compressed_images = list(_sub_image_to_bytes(s) for s in ja2_images.images)
    compressed_image_sizes = list(len(i) for i in compressed_images)
    offsets = list(sum(compressed_image_sizes[:i]) for i in range(len(compressed_images)))
    size_after_compression = sum(compressed_image_sizes)
    sub_image_headers = list(
        StiSubImageHeader(
            offset=offset,
            length=comp_size,
            offset_x=sub.offsets[0],
            offset_y=sub.offsets[1],
            height=sub.image.size[1],
            width=sub.image.size[0]
        )
        for sub, comp_size, offset in zip(ja2_images.images, compressed_image_sizes, offsets)
    )

    format_specific_header = Sti8BitHeader(
        number_of_palette_colors=256,
        number_of_images=len(ja2_images),
        red_color_depth=8,
        green_color_depth=8,
        blue_color_depth=8
    )
    header = StiHeader(
        file_identifier=b'STCI',
        initial_size=initial_size,
        size_after_compression=size_after_compression,
        transparent_color=0,
        width=ja2_images.width,
        height=ja2_images.height,
        format_specific_header=bytes(format_specific_header),
        color_depth=8,
        aux_data_size=len(aux_data) * AuxObjectData.get_size(),
        flags=0
    )
    header.set_flag('flags', 'INDEXED', True)
    header.set_flag('flags', 'ETRLE', True)

    file.write(bytes(header))
    file.write(palette_bytes)
    for sub_image_header in sub_image_headers:
        file.write(bytes(sub_image_header))
    for compressed in compressed_images:
        file.write(compressed)
    for aux in aux_data:
        aux_header = AuxObjectData(
            wall_orientation=aux['wall_orientation'],
            number_of_tiles=aux['number_of_tiles'],
            tile_location_index=aux['tile_location_index'],
            current_frame=aux['current_frame'],
            number_of_frames=aux['number_of_frames'],
            flags=0
        )
        aux_header.set_flag('flags', 'FULL_TILE', aux['full_tile'])
        aux_header.set_flag('flags', 'ANIMATED_TILE', aux['animated_tile'])
        aux_header.set_flag('flags', 'DYNAMIC_TILE', aux['dynamic_tile'])
        aux_header.set_flag('flags', 'INTERACTIVE_TILE', aux['interactive_tile'])
        aux_header.set_flag('flags', 'IGNORES_HEIGHT', aux['ignores_height'])
        aux_header.set_flag('flags', 'USES_LAND_Z', aux['uses_land_z'])
        file.write(bytes(aux_header))


def _color_components(color, masks):
    def component(color, mask):
        if mask == 0:
            return 0xFF # defaults to white/opaque
        byte = color & mask
        shift = 8 - mask.bit_length()
        if shift > 0:
            return byte << shift
        elif shift < 0:
            return byte >> -shift
        return byte
    components = [component(color, mask) for mask in masks]
    return tuple(components)


class StiImagePlugin(ImageFile.ImageFile):
    """Image plugin for Pillow/PIL that can load STI files."""

    format = "STCI"
    format_description = "Sir-Tech's Crazy Image"

    def _open(self):
        """Reads file information without image data."""
        self.fp.seek(0, 0) # from start
        header = StiHeader.from_bytes(self.fp.read(StiHeader.get_size()))
        if header['file_identifier'] != b'STCI':
            raise SyntaxError('not a STCI file')
        assert not header.get_flag('flags', 'ZLIB'), "TODO ZLIB compression" # XXX need example
        self.size = (header['width'], header['height'])
        if header.get_flag('flags', 'RGB'):
            # raw color image
            assert not header.get_flag('flags', 'INDEXED'), "RGB and INDEXED at the same time"
            assert not header.get_flag('flags', 'AUX_OBJECT_DATA'), "TODO aux object data in RGB" # XXX need example
            rgb_header = Sti16BitHeader.from_bytes(header['format_specific_header'])
            assert rgb_header['alpha_channel_mask'] == 0, "TODO alpha channel in RGB" # XXX need example
            self.mode = 'RGB'
            depth = header['color_depth']
            masks = ( rgb_header['red_color_mask'], rgb_header['green_color_mask'], rgb_header['blue_color_mask'] )
            self.tile = [ # single image
                (self.format, (0, 0) + self.size, StiHeader.get_size(), ('rgb', depth, masks, header['size_after_compression']))
            ]
            self.info['header'] = header
            self.info['rgb_header'] = rgb_header
            self.info['boxes'] = [(0, 0) + self.size]
            self.info["transparency"] = _color_components(header['transparent_color'], masks)
        elif header.get_flag('flags', 'INDEXED'):
            # palette color image
            indexed_header = Sti8BitHeader.from_bytes(header['format_specific_header'])
            assert indexed_header['number_of_palette_colors'] == 256
            assert indexed_header['red_color_depth'] == 8
            assert indexed_header['green_color_depth'] == 8
            assert indexed_header['blue_color_depth'] == 8
            num_bytes = indexed_header['number_of_palette_colors'] * 3
            raw = struct.unpack('<{}B'.format(num_bytes), self.fp.read(num_bytes))
            self.mode = 'P'
            self.palette = ImagePalette.ImagePalette("RGB", raw[0::3] + raw[1::3] + raw[2::3])
            self.palette.dirty = True
            subimage_headers = [StiSubImageHeader.from_bytes(self.fp.read(StiSubImageHeader.get_size())) for _ in range(indexed_header['number_of_images'])]
            boxes = self._generate_boxes(subimage_headers)
            offset = self.fp.tell()
            if header.get_flag('flags', 'AUX_OBJECT_DATA'):
                self.fp.seek(header['size_after_compression'], 1) # from current
                aux_object_data = [AuxObjectData.from_bytes(self.fp.read(AuxObjectData.get_size())) for _ in range(indexed_header['number_of_images'])]
                self.info['aux_object_data'] = aux_object_data
            self.tile = [
                (self.format, (0, 0) + self.size, offset, ('fill', header['transparent_color'])) # XXX wall index is another possibility
            ]
            for box, subimage in zip(boxes, subimage_headers):
                if header.get_flag('flags', 'ETRLE'):
                    parameters = ('etrle', subimage['length'], header['transparent_color']) # etrle indexes
                else:
                    parameters = ('copy', subimage['length']) # raw indexes
                tile = (self.format, box, offset + subimage['offset'], parameters)
                self.tile.append(tile)
            self.info['header'] = header
            self.info['indexed_header'] = indexed_header
            self.info['subimage_headers'] = subimage_headers
            self.info['boxes'] = boxes
            self.info["transparency"] = header['transparent_color']
        else:
            raise SyntaxError('unknown image mode')

    def _generate_boxes(self, subimage_headers):
        """
        The main image size of indexed images seems to be the canvas size.
        STIconvert.cc has code to generate subimages by processing wall indexes (WI=255)
        At least one official STI image can't fit all subimages in the canvas, so this function resizes the image.
        """
        assert len(subimage_headers) > 0, "TODO 0 subimages" # XXX need example
        boxes = []
        width = 0
        height = 0
        for subimage in subimage_headers:
            if width > 0:
                width += 1 # 1 pixel vertical line between images
            box = (width, 0, width + subimage['width'], subimage['height'])
            boxes.append(box)
            width += subimage['width']
            if height < subimage['height']:
                height = subimage['height']
        self.size = width, height
        return boxes


class StiImageDecoder(ImageFile.PyDecoder):
    """Decoder for images in a STI file."""

    def init(self, args):
        do = args[0]
        if do == 'rgb':
            self.decode = self.decode_rgb
            self.depth = args[1]
            self.masks = args[2]
            self.bytes = args[3]
            assert self.mode == 'RGB' and len(self.masks) == 3, "TODO rgb mode {} {}".format(self.mode, self.masks) # XXX RGBA?
            assert self.depth in [16], "TODO color depth {}".format(self.depth) # XXX due to the size of the masks the maximum is 32
            assert isinstance(self.bytes, int) and self.bytes >= 0
        elif do == 'fill':
            self.decode = self.decode_fill
            self.color = args[1]
        elif do == 'copy':
            self.decode = self.decode_copy
            self.bytes = args[1]
            assert self.mode == "P"
            assert isinstance(self.bytes, int) and self.bytes >= 0
        elif do == 'etrle':
            self.decode = self.decode_etrle
            self.bytes = args[1]
            self.transparent = args[2]
            self.data = bytearray()
            assert self.mode == "P"
            assert isinstance(self.bytes, int) and self.bytes >= 0
            assert isinstance(self.transparent, int) and self.transparent == 0 # XXX etrle_decompress expects index 0
        else:
            raise NotImplementedError("unsupported args {}".format(args))
        self.x = 0
        self.y = 0

    def positions(self):
        """iterates over all positions"""
        while self.y < self.state.ysize:
            while self.x < self.state.xsize:
                yield self.x + self.state.xoff, self.y + self.state.yoff
                self.x += 1
            self.y += 1
            self.x = 0

    def decode(self, buffer):
        raise NotImplementedError("placeholder")

    def decode_rgb(self, buffer):
        """copy colors"""
        assert self.depth == 16
        offset = 0
        pixels = self.im.pixel_access()
        for x, y in self.positions():
            assert self.bytes >= 2, "not enough data"
            if offset + 2 > len(buffer):
                return offset, 0 # get more data
            color = struct.unpack_from("<H", buffer, offset)[0]
            pixels[x, y] = _color_components(color, self.masks)
            offset += 2
            self.bytes -= 2
        assert self.bytes == 0, "too much data"
        return -1, 0 # done

    def decode_fill(self, buffer):
        """fill with color"""
        pixels = self.im.pixel_access()
        for x, y in self.positions():
            pixels[x, y] = self.color
        return -1, 0 # done

    def decode_copy(self, buffer):
        """copy raw indexes"""
        offset = 0
        pixels = self.im.pixel_access()
        for x, y in self.positions():
            if offset == len(buffer):
                return offset, 0 # get more data
            assert self.bytes > 0, "not enough data"
            pixels[x, y] = buffer[offset]
            offset += 1
            self.bytes -= 1
        assert self.bytes == 0, "too much data"
        return -1, 0 # done

    def decode_etrle(self, buffer):
        """copy etrle indexes"""
        if self.bytes > 0:
            bytes = min(self.bytes, len(buffer))
            self.data.extend(buffer[:self.bytes])
            self.bytes -= bytes
            if self.bytes > 0:
                return len(buffer), 0 # get more data
        self.data = etrle_decompress(self.data)
        offset = 0
        pixels = self.im.pixel_access()
        for x, y in self.positions():
            assert offset < len(self.data), "not enough data"
            pixels[x, y] = self.data[offset]
            offset += 1
        assert offset == len(self.data), "too much data"
        self.data = None
        return -1, 0 # done


# register STI image plugin
Image.register_decoder(StiImagePlugin.format, StiImageDecoder)
Image.register_open(StiImagePlugin.format, StiImagePlugin, lambda x: len(x) >= 4 and x[:4] == b'STCI')
Image.register_extension(StiImagePlugin.format, '.sti')

