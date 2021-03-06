import unittest
from PIL import Image, ImagePalette
from .fixtures import *
from ja2py.fileformats import Sti16BitHeader, Sti8BitHeader, StiHeader, StiSubImageHeader, AuxObjectData,\
                              is_16bit_sti, is_8bit_sti, load_16bit_sti, load_8bit_sti, save_16bit_sti, save_8bit_sti
from ja2py.content import Image16Bit, Images8Bit, SubImage8Bit
from ja2py.fileformats.Sti import StiImagePlugin, StiImageEncoder, validate_spec, _color_components


class TestSti16BitHeader(unittest.TestCase):
    def test_size(self):
        self.assertEqual(Sti16BitHeader.get_size(), 20)

    def test_read_from_bytes(self):
        test_bytes = (b'\x01\x00\x00\x00' + b'\x02\x00\x00\x00' + b'\x03\x00\x00\x00' + b'\x04\x00\x00\x00' +
                      b'\x05' + b'\x06' + b'\x07' + b'\x08')

        header = Sti16BitHeader.from_bytes(test_bytes)

        self.assertEqual(header['red_color_mask'], 1)
        self.assertEqual(header['green_color_mask'], 2)
        self.assertEqual(header['blue_color_mask'], 3)
        self.assertEqual(header['alpha_channel_mask'], 4)
        self.assertEqual(header['red_color_depth'], 5)
        self.assertEqual(header['green_color_depth'], 6)
        self.assertEqual(header['blue_color_depth'], 7)
        self.assertEqual(header['alpha_channel_depth'], 8)

    def test_write_to_bytes(self):
        header = Sti16BitHeader(
            red_color_mask=8,
            green_color_mask=7,
            blue_color_mask=6,
            alpha_channel_mask=5,
            red_color_depth=4,
            green_color_depth=3,
            blue_color_depth=2,
            alpha_channel_depth=1
        )
        expected = (b'\x08\x00\x00\x00' + b'\x07\x00\x00\x00' + b'\x06\x00\x00\x00' + b'\x05\x00\x00\x00' +
                    b'\x04' + b'\x03' + b'\x02' + b'\x01')

        self.assertEqual(bytes(header), expected)

    def test_idempotency(self):
        field_values = {
            'red_color_mask': 1231,
            'green_color_mask': 7121,
            'blue_color_mask': 1235,
            'alpha_channel_mask': 1235,
            'red_color_depth': 25,
            'green_color_depth': 3,
            'blue_color_depth': 1,
            'alpha_channel_depth': 123
        }
        header = Sti16BitHeader(**field_values)

        regenerated_header = Sti16BitHeader.from_bytes(bytes(header))

        for key, value in field_values.items():
            self.assertEqual(regenerated_header[key], value)


class TestSti8BitHeader(unittest.TestCase):
    def test_size(self):
        self.assertEqual(Sti8BitHeader.get_size(), 20)

    def test_read_from_bytes(self):
        test_bytes = b'\x01\x00\x00\x00' + b'\x02\x00' + b'\x03' + b'\x04' + b'\x05' + (11 * b'\x00')

        header = Sti8BitHeader.from_bytes(test_bytes)

        self.assertEqual(header['number_of_palette_colors'], 1)
        self.assertEqual(header['number_of_images'], 2)
        self.assertEqual(header['red_color_depth'], 3)
        self.assertEqual(header['green_color_depth'], 4)
        self.assertEqual(header['blue_color_depth'], 5)

    def test_write_to_bytes(self):
        header = Sti8BitHeader(
            number_of_palette_colors=5,
            number_of_images=4,
            red_color_depth=3,
            green_color_depth=2,
            blue_color_depth=1
        )
        expected = b'\x05\x00\x00\x00' + b'\x04\x00' + b'\x03' + b'\x02' + b'\x01' + (11 * b'\x00')

        self.assertEqual(bytes(header), expected)

    def test_idempotency(self):
        field_values = {
            'number_of_palette_colors': 25,
            'number_of_images': 12,
            'red_color_depth': 66,
            'green_color_depth': 3,
            'blue_color_depth': 1
        }
        header = Sti8BitHeader(**field_values)

        regenerated_header = Sti8BitHeader.from_bytes(bytes(header))

        for key, value in field_values.items():
            self.assertEqual(regenerated_header[key], value)


class TestStiHeader(unittest.TestCase):
    def test_size(self):
        self.assertEqual(StiHeader.get_size(), 64)

    def test_read_from_bytes(self):
        test_bytes = (b'TEST' + b'\x01\x00\x00\x00' + b'\x02\x00\x00\x00' + b'\x03\x00\x00\x00' + b'\x04\x00\x00\x00' +
                      b'\x05\x00' + b'\x06\x00' + b'a' + 18 * b'\x01' + b'b' + b'\x07' + b'\x00' * 3 +
                      b'\x08\x00\x00\x00' + 12 * b'\x00')

        header = StiHeader.from_bytes(test_bytes)

        self.assertEqual(header['file_identifier'], b'TEST')
        self.assertEqual(header['initial_size'], 1)
        self.assertEqual(header['size_after_compression'], 2)
        self.assertEqual(header['transparent_color'], 3)
        self.assertEqual(header['flags'], 4)
        self.assertEqual(header['height'], 5)
        self.assertEqual(header['width'], 6)
        self.assertEqual(header['format_specific_header'], b'a' + 18 * b'\x01' + b'b')
        self.assertEqual(header['color_depth'], 7)
        self.assertEqual(header['aux_data_size'], 8)

    def test_write_to_bytes(self):
        header = StiHeader(
            file_identifier=b'STSI',
            initial_size=8,
            size_after_compression=7,
            transparent_color=6,
            flags=5,
            height=4,
            width=3,
            format_specific_header=b'b' + 18 * b'\x01' + b'a',
            color_depth=2,
            aux_data_size=1,
        )
        expected = (b'STSI' + b'\x08\x00\x00\x00' + b'\x07\x00\x00\x00' + b'\x06\x00\x00\x00' + b'\x05\x00\x00\x00' +
                    b'\x04\x00' + b'\x03\x00' + b'b' + 18 * b'\x01' + b'a' + b'\x02' + b'\x00' * 3 +
                    b'\x01\x00\x00\x00' + 12 * b'\x00')

        self.assertEqual(bytes(header), expected)

    def test_flags(self):
        header = StiHeader(flags=0)

        header.set_flag('flags', 'RGB', True)
        self.assertEqual(header['flags'], 4)

        header.set_flag('flags', 'INDEXED', True)
        self.assertEqual(header['flags'], 12)

        header.set_flag('flags', 'ZLIB', True)
        self.assertEqual(header['flags'], 28)

        header.set_flag('flags', 'ETRLE', True)
        self.assertEqual(header['flags'], 60)

    def test_idempotency(self):
        field_values = {
            'file_identifier': b'WRST',
            'initial_size': 123112,
            'size_after_compression': 3213,
            'transparent_color': 31,
            'flags': 6,
            'height': 12,
            'width': 11,
            'format_specific_header': b'c' + 18 * b'\x12' + b'd',
            'color_depth': 22,
            'aux_data_size': 9,
        }
        header = StiHeader(**field_values)

        regenerated_header = StiHeader.from_bytes(bytes(header))

        for key, value in field_values.items():
            self.assertEqual(regenerated_header[key], value)


class TestStiSubImageHeader(unittest.TestCase):
    def test_size(self):
        self.assertEqual(StiSubImageHeader.get_size(), 16)

    def test_read_from_bytes(self):
        test_bytes = b'\x01\x00\x00\x00' + b'\x02\x00\x00\x00' + b'\x03\x00' + b'\x04\x00' + b'\x05\x00' + b'\x06\x00'

        header = StiSubImageHeader.from_bytes(test_bytes)

        self.assertEqual(header['offset'], 1)
        self.assertEqual(header['length'], 2)
        self.assertEqual(header['offset_x'], 3)
        self.assertEqual(header['offset_y'], 4)
        self.assertEqual(header['height'], 5)
        self.assertEqual(header['width'], 6)

    def test_write_to_bytes(self):
        header = StiSubImageHeader(
            offset=6,
            length=5,
            offset_x=4,
            offset_y=3,
            height=2,
            width=1
        )
        expected = b'\x06\x00\x00\x00' + b'\x05\x00\x00\x00' + b'\x04\x00' + b'\x03\x00' + b'\x02\x00' + b'\x01\x00'

        self.assertEqual(bytes(header), expected)

    def test_idempotency(self):
        field_values = {
            'offset': 255,
            'length': 127,
            'offset_x': 66,
            'offset_y': 33,
            'height': 31,
            'width': 1
        }
        header = StiSubImageHeader(**field_values)

        regenerated_header = StiSubImageHeader.from_bytes(bytes(header))

        for key, value in field_values.items():
            self.assertEqual(regenerated_header[key], value)


class TestAuxObjectData(unittest.TestCase):
    def test_size(self):
        self.assertEqual(AuxObjectData.get_size(), 16)

    def test_read_from_bytes(self):
        test_bytes = b'\x01' + b'\x02' + b'\x03\x00' + 3 * b'\x00' + b'\x04' + b'\x05' + b'\x06' + 6 * b'\x00'

        header = AuxObjectData.from_bytes(test_bytes)

        self.assertEqual(header['wall_orientation'], 1)
        self.assertEqual(header['number_of_tiles'], 2)
        self.assertEqual(header['tile_location_index'], 3)
        self.assertEqual(header['current_frame'], 4)
        self.assertEqual(header['number_of_frames'], 5)
        self.assertEqual(header['flags'], 6)

    def test_flags(self):
        header = AuxObjectData(flags=0)

        header.set_flag('flags', 'FULL_TILE', True)
        self.assertEqual(header['flags'], 1)

        header.set_flag('flags', 'ANIMATED_TILE', True)
        self.assertEqual(header['flags'], 3)

        header.set_flag('flags', 'DYNAMIC_TILE', True)
        self.assertEqual(header['flags'], 7)

        header.set_flag('flags', 'INTERACTIVE_TILE', True)
        self.assertEqual(header['flags'], 15)

        header.set_flag('flags', 'IGNORES_HEIGHT', True)
        self.assertEqual(header['flags'], 31)

        header.set_flag('flags', 'USES_LAND_Z', True)
        self.assertEqual(header['flags'], 63)

    def test_write_to_bytes(self):
        header = AuxObjectData(
            wall_orientation=6,
            number_of_tiles=5,
            tile_location_index=4,
            current_frame=3,
            number_of_frames=2,
            flags=1
        )
        expected = b'\x06' + b'\x05' + b'\x04\x00' + 3 * b'\x00' + b'\x03' + b'\x02' + b'\x01' + 6 * b'\x00'

        self.assertEqual(bytes(header), expected)

    def test_idempotency(self):
        field_values = {
            'wall_orientation': 255,
            'number_of_tiles': 127,
            'tile_location_index': 66,
            'current_frame': 33,
            'number_of_frames': 31,
            'flags': 1
        }
        header = AuxObjectData(**field_values)

        regenerated_header = AuxObjectData.from_bytes(bytes(header))

        for key, value in field_values.items():
            self.assertEqual(regenerated_header[key], value)


class TestIsStiFormat(unittest.TestCase):
    funcs = [
        is_16bit_sti,
        is_8bit_sti,
    ]
    truthy_values = {
        create_non_image_buffer: None,
        create_16_bit_sti: is_16bit_sti,
        create_8_bit_sti: is_8bit_sti,
        create_8_bit_multi_image_sti: is_8bit_sti,
        create_8_bit_animated_sti: is_8bit_sti,
    }

    def test_sti_formats(self):
        for create_fn, expected_truthy_fn in self.truthy_values.items():
            truthy_fns = list(filter(lambda f: f(create_fn()), self.funcs))
            self.assertEqual(truthy_fns, [expected_truthy_fn] if expected_truthy_fn else [])


class TestLoad16BitSti(unittest.TestCase):
    def test_not_a_16_bit_sti(self):
        with self.assertRaises(ValueError):
            load_16bit_sti(create_non_image_buffer())

    def test_returns_16_bit_image(self):
        img = load_16bit_sti(create_16_bit_sti())
        self.assertIsInstance(img, Image16Bit)

    def test_dimensions(self):
        img = load_16bit_sti(create_16_bit_sti())

        self.assertEqual(img.size, (3, 2))

    def test_image_data(self):
        img = load_16bit_sti(create_16_bit_sti())

        self.assertEqual(img.image.tobytes(), b'PH\x88P\x88\x98P\xc8\xa8X\x08\xb8`\x08\xc8`L\x08')


class TestLoad8BitSti(unittest.TestCase):
    def test_not_a_8_bit_sti(self):
        with self.assertRaises(ValueError):
            load_8bit_sti(create_non_image_buffer())

    def test_returns_8bit_images(self):
        img = load_8bit_sti(create_8_bit_multi_image_sti())
        self.assertIsInstance(img, Images8Bit)

    def test_width_height(self):
        img = load_8bit_sti(create_8_bit_multi_image_sti())
        self.assertEqual(img.width, 8)
        self.assertEqual(img.height, 9)

    def test_palette(self):
        img = load_8bit_sti(create_8_bit_multi_image_sti())
        self.assertIsInstance(img.palette, ImagePalette.ImagePalette)

    def test_len_single(self):
        img = load_8bit_sti(create_8_bit_sti())
        self.assertEqual(len(img), 1)

    def test_len_multi(self):
        img = load_8bit_sti(create_8_bit_multi_image_sti())
        self.assertEqual(len(img), 2)

    def test_offsets(self):
        img = load_8bit_sti(create_8_bit_multi_image_sti())
        self.assertEqual(img.images[0].offsets, (0, 0))
        self.assertEqual(img.images[1].offsets, (1, 2))

    def test_colors(self):
        img = load_8bit_sti(create_8_bit_multi_image_sti())
        self.assertEqual(img.images[0].image.convert('RGB').getpixel((0, 0)), (1, 2, 3))

    def test_aux_object_data(self):
        img = load_8bit_sti(create_8_bit_animated_sti())

        self.assertEqual(img.images[0].aux_data, {
            'wall_orientation': 0,
            'number_of_tiles': 1,
            'tile_location_index': 2,
            'current_frame': 0,
            'number_of_frames': 2,
            'full_tile': False,
            'animated_tile': True,
            'dynamic_tile': False,
            'interactive_tile': False,
            'ignores_height': False,
            'uses_land_z': False,
        })
        self.assertEqual(img.images[1].aux_data, {
            'wall_orientation': 0,
            'number_of_tiles': 1,
            'tile_location_index': 2,
            'current_frame': 1,
            'number_of_frames': 0,
            'full_tile': False,
            'animated_tile': False,
            'dynamic_tile': False,
            'interactive_tile': False,
            'ignores_height': False,
            'uses_land_z': False,
        })


class TestWrite16BitSti(unittest.TestCase):
    def test_write(self):
        img = Image16Bit(Image.new('RGB', (3, 1), color=(255, 0, 0)))
        buffer = BytesIO()

        save_16bit_sti(img, buffer)

        self.assertEqual(buffer.getvalue(), b'STCI\x06\x00\x00\x00\x06\x00\x00\x00' +
                                            b'\x00\x00\x00\x00' + b'\x04\x00\x00\x00' + b'\x01\x00\x03\x00' +
                                            b'\x00\xF8\x00\x00\xe0\x07\x00\x00\x1f\x00\x00\x00\x00\x00\x00\x00' +
                                            b'\x05\x06\x05\x00' + b'\x10\x00\x00\x00' + b'\x00\x00\x00\x00' +
                                            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
                                            (b'\x00\xF8' * 3)

                         )

    def test_write_with_wrong_type(self):
        img = {}
        buffer = BytesIO()

        with self.assertRaises(ValueError):
            save_16bit_sti(img, buffer)
        self.assertEqual(buffer.getvalue(), b'')


class TestWrite8BitSti(unittest.TestCase):
    def test_write_with_wrong_type(self):
        img = {}
        buffer = BytesIO()

        with self.assertRaises(ValueError):
            save_8bit_sti(img, buffer)
        self.assertEqual(buffer.getvalue(), b'')

    def test_write_with_single_image(self):
        palette = ImagePalette.ImagePalette('RGB', b'\x01\x02\x03\x04\x05\x06', 6)
        img = SubImage8Bit(Image.new('P', (2, 2), color=1))
        img.image.putpalette(palette)
        imgs = Images8Bit([img], palette=palette, width=9, height=8)
        buffer = BytesIO()

        save_8bit_sti(imgs, buffer)

        self.assertEqual(buffer.getvalue(),
                         # Header
                         b'STCI\x48\x00\x00\x00\x08\x00\x00\x00' +
                         b'\x00\x00\x00\x00' + b'\x28\x00\x00\x00' + b'\x08\x00\x09\x00' +
                         b'\x00\x01\x00\x00\x01\x00\x08\x08\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
                         b'\x08' + (3 * b'\x00') + b'\x00\x00\x00\x00' + (12 * b'\x00') +
                         # Palette
                         b'\x01\x03\x05' + b'\x02\x04\x06' + (254 * b'\x00\x00\x00') +
                         # Sub Image Header
                         b'\x00\x00\x00\x00' + b'\x08\x00\x00\x00' + b'\x00\x00' + b'\x00\x00' + b'\x02\x00' + b'\x02\x00' +
                         # Data
                         b'\x02\x01\x01\x00\x02\x01\x01\x00')

    def test_write_with_raw_palette(self):
        palette = ImagePalette.raw('RGB', b'\x01\x02\x03\x04\x05\x06')
        img = SubImage8Bit(Image.new('P', (2, 2), color=1))
        img.image.putpalette(palette)
        imgs = Images8Bit([img], palette=palette, width=9, height=8)
        buffer = BytesIO()

        save_8bit_sti(imgs, buffer)

        self.assertEqual(buffer.getvalue(),
                         # Header
                         b'STCI\x48\x00\x00\x00\x08\x00\x00\x00' +
                         b'\x00\x00\x00\x00' + b'\x28\x00\x00\x00' + b'\x08\x00\x09\x00' +
                         b'\x00\x01\x00\x00\x01\x00\x08\x08\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
                         b'\x08' + (3 * b'\x00') + b'\x00\x00\x00\x00' + (12 * b'\x00') +
                         # Palette
                         b'\x01\x02\x03' + b'\x04\x05\x06' + (254 * b'\x00\x00\x00') +
                         # Sub Image Header
                         b'\x00\x00\x00\x00' + b'\x08\x00\x00\x00' + b'\x00\x00' + b'\x00\x00' + b'\x02\x00' + b'\x02\x00' +
                         # Data
                         b'\x02\x01\x01\x00\x02\x01\x01\x00')

    def test_write_with_multiple_images(self):
        palette = ImagePalette.ImagePalette('RGB', b'\x01\x01\x01', 3)
        img1 = SubImage8Bit(Image.new('P', (2, 2), color=1))
        img2 = SubImage8Bit(Image.new('P', (3, 1), color=0), offsets=(5, 6))
        img1.image.putpalette(palette)
        img2.image.putpalette(palette)
        imgs = Images8Bit([img1, img2], palette=palette)
        buffer = BytesIO()

        save_8bit_sti(imgs, buffer)

        self.assertEqual(buffer.getvalue(),
                         # Header
                         b'STCI\x00\x00\x00\x00\x0a\x00\x00\x00' +
                         b'\x00\x00\x00\x00' + b'\x28\x00\x00\x00' + b'\x00\x00\x00\x00' +
                         b'\x00\x01\x00\x00\x02\x00\x08\x08\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
                         b'\x08' + (3 * b'\x00') + b'\x00\x00\x00\x00' + (12 * b'\x00') +
                         # Palette
                         b'\x01\x01\x01' + (255 * b'\x00\x00\x00') +
                         # Sub Image Header
                         b'\x00\x00\x00\x00' + b'\x08\x00\x00\x00' + b'\x00\x00' + b'\x00\x00' + b'\x02\x00' + b'\x02\x00' +
                         b'\x08\x00\x00\x00' + b'\x02\x00\x00\x00' + b'\x05\x00' + b'\x06\x00' + b'\x01\x00' + b'\x03\x00' +
                         # Data
                         b'\x02\x01\x01\x00\x02\x01\x01\x00' +
                         b'\x83\x00')


    def test_write_with_multiple_images_mixed_aux_data(self):
        palette = ImagePalette.ImagePalette('RGB', b'\x01\x01\x01\x02\x02\x02', 6)
        img1 = SubImage8Bit(Image.new('P', (2, 2), color=1))
        img2 = SubImage8Bit(Image.new('P', (3, 1), color=0), offsets=(5, 6), aux_data={})
        img1.image.putpalette(palette)
        img2.image.putpalette(palette)
        imgs = Images8Bit([img1, img2], palette=palette)
        buffer = BytesIO()

        with self.assertRaises(ValueError):
            save_8bit_sti(imgs, buffer)

    def test_write_with_multiple_images_with_aux_data(self):
        palette = ImagePalette.ImagePalette('RGB', b'\x01\x01\x01', 3)
        img1 = SubImage8Bit(Image.new('P', (2, 2), color=1), aux_data={
            'wall_orientation': 1,
            'number_of_tiles': 2,
            'tile_location_index': 3,
            'current_frame': 4,
            'number_of_frames': 5,
            'full_tile': True,
            'animated_tile': True,
            'dynamic_tile': False,
            'interactive_tile': False,
            'ignores_height': False,
            'uses_land_z': False,
        })
        img2 = SubImage8Bit(Image.new('P', (3, 1), color=0), aux_data={
            'wall_orientation': 6,
            'number_of_tiles': 7,
            'tile_location_index': 8,
            'current_frame': 9,
            'number_of_frames': 10,
            'full_tile': True,
            'animated_tile': False,
            'dynamic_tile': False,
            'interactive_tile': False,
            'ignores_height': False,
            'uses_land_z': False,
        })
        img1.image.putpalette(palette)
        img2.image.putpalette(palette)
        imgs = Images8Bit([img1, img2], palette=palette)
        buffer = BytesIO()

        save_8bit_sti(imgs, buffer)

        self.assertEqual(buffer.getvalue(),
                         # Header
                         b'STCI\x00\x00\x00\x00\x0a\x00\x00\x00' +
                         b'\x00\x00\x00\x00' + b'\x28\x00\x00\x00' + b'\x00\x00\x00\x00' +
                         b'\x00\x01\x00\x00\x02\x00\x08\x08\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
                         b'\x08' + (3 * b'\x00') + b'\x20\x00\x00\x00' + (12 * b'\x00') +
                         # Palette
                         b'\x01\x01\x01' + (255 * b'\x00\x00\x00') +
                         # Sub Image Header
                         b'\x00\x00\x00\x00' + b'\x08\x00\x00\x00' + b'\x00\x00' + b'\x00\x00' + b'\x02\x00' + b'\x02\x00' +
                         b'\x08\x00\x00\x00' + b'\x02\x00\x00\x00' + b'\x00\x00' + b'\x00\x00' + b'\x01\x00' + b'\x03\x00' +
                         # Data
                         b'\x02\x01\x01\x00\x02\x01\x01\x00' +
                         b'\x83\x00' +
                         # Aux Data
                         b'\x01\x02\x03\x00' + (3*b'\x00') + b'\x04\x05\x03' + (6*b'\x00') +
                         b'\x06\x07\x08\x00' + (3*b'\x00') + b'\x09\x0A\x01' + (6*b'\x00'))


class TestStiImagePlugin(unittest.TestCase):
    def test_open_save_colors(self):
        rgb_header = Sti16BitHeader(
            red_color_mask=0x0000ff,
            green_color_mask=0x00ff00,
            blue_color_mask=0xff0000,
            alpha_channel_mask=0x000000,
            red_color_depth=8,
            green_color_depth=8,
            blue_color_depth=8,
            alpha_channel_depth=0
        )
        header = StiHeader(
            file_identifier=b'STCI',
            initial_size=3,
            size_after_compression=3,
            transparent_color=0,
            flags=0,
            height=1,
            width=1,
            format_specific_header=bytes(rgb_header),
            color_depth=24,
            aux_data_size=0,
        )
        header.set_flag('flags', 'RGB', True)
        image_data = b'\x01\x02\x03'
        data = bytes(header) + image_data
        buf = BytesIO(data)
        img = Image.open(buf)
        self.assertEqual(img.format, StiImagePlugin.format)
        self.assertEqual(img.mode, 'RGB')
        self.assertEqual(img.size, (1, 1))
        self.assertEqual(img.getpixel((0, 0)), (1,2,3))
        self.assertEqual(bytes(img.info['header']), bytes(header))
        self.assertEqual(bytes(img.info['rgb_header']), bytes(rgb_header))
        buf = BytesIO()
        img.save(buf, format=StiImagePlugin.format, flags=['RGB'], spec='RGB')
        self.assertEqual(buf.getvalue(), data)

    def test_open_save_colors_custom_spec_with_alpha(self):
        spec = (0x03,0xc0,0x0c,0x30, 2,2,2,2, 8)
        rgb_header = Sti16BitHeader(
            red_color_mask = spec[0],
            green_color_mask = spec[1],
            blue_color_mask = spec[2],
            alpha_channel_mask = spec[3],
            red_color_depth = spec[4],
            green_color_depth = spec[5],
            blue_color_depth = spec[6],
            alpha_channel_depth = spec[7],
        )
        header = StiHeader(
            file_identifier = b'STCI',
            initial_size = spec[8] // 8,
            size_after_compression = spec[8] // 8,
            transparent_color = 0,
            flags = 0,
            height = 1,
            width = 1,
            format_specific_header = bytes(rgb_header),
            color_depth = spec[8],
            aux_data_size = 0,
        )
        header.set_flag('flags', 'RGB', True)
        image_data = b'\x8d'
        data = bytes(header) + image_data
        buf = BytesIO(data)
        img = Image.open(buf)
        self.assertEqual(img.format, StiImagePlugin.format)
        self.assertEqual(img.mode, 'RGBA')
        self.assertEqual(img.size, (1, 1))
        self.assertEqual(img.getpixel((0, 0)), (85, 170, 255, 0))
        self.assertEqual(bytes(img.info['header']), bytes(header))
        self.assertEqual(bytes(img.info['rgb_header']), bytes(rgb_header))
        buf = BytesIO()
        img.save(buf, format=StiImagePlugin.format, flags=['RGB'], spec=spec)
        self.assertEqual(buf.getvalue(), data)

    def test_open_save_indexes(self):
        indexed_header = Sti8BitHeader(
            number_of_palette_colors = 256,
            number_of_images = 0,
            red_color_depth = 8,
            green_color_depth = 8,
            blue_color_depth = 8
        )
        header = StiHeader(
            file_identifier = b'STCI',
            initial_size = 1,
            size_after_compression = 1,
            transparent_color = 0,
            flags = 0,
            height = 1,
            width = 1,
            format_specific_header = bytes(indexed_header),
            color_depth = 8,
            aux_data_size = 0,
        )
        header.set_flag('flags', 'INDEXED', True)
        palette_colors = bytes([i for i in range(256) for _ in range(3)])
        palette_bands = bytes([i for _ in range(3) for i in range(256)])
        image_data = b'\x01'
        data = bytes(header) + palette_colors + image_data
        img = Image.open(BytesIO(data))
        self.assertEqual(img.format, StiImagePlugin.format)
        self.assertEqual(img.mode, 'P')
        self.assertEqual(palette_bands, img.palette.tobytes()) # Pillow returns bands
        self.assertEqual(img.size, (1, 1))
        self.assertEqual(img.getpixel((0, 0)), 1)
        self.assertEqual(bytes(img.info['header']), bytes(header))
        self.assertEqual(bytes(img.info['indexed_header']), bytes(indexed_header))
        buf = BytesIO()
        img.save(buf, format=StiImagePlugin.format, flags=['INDEXED'])
        self.assertEqual(buf.getvalue(), data)

    def test_open_save_etrle(self):
        indexed_header = Sti8BitHeader(
            number_of_palette_colors=256,
            number_of_images=1,
            red_color_depth=8,
            green_color_depth=8,
            blue_color_depth=8
        )
        header = StiHeader(
            file_identifier=b'STCI',
            initial_size=1,
            size_after_compression=2,
            transparent_color=0,
            flags=0,
            height=1,
            width=1,
            format_specific_header=bytes(indexed_header),
            color_depth=8,
            aux_data_size=0,
        )
        header.set_flag('flags', 'INDEXED', True)
        header.set_flag('flags', 'ETRLE', True)
        palette_colors = bytes([i for i in range(256) for _ in range(3)])
        palette_bands = bytes([i for _ in range(3) for i in range(256)])
        subimage_data = b'\x81\x00'
        subimage_header = StiSubImageHeader(
            offset = 0,
            length = len(subimage_data),
            offset_x = 0,
            offset_y = 0,
            height = 1,
            width = 1,
        )
        data = bytes(header) + palette_colors + bytes(subimage_header) + subimage_data
        img = Image.open(BytesIO(data))
        self.assertEqual(img.format, StiImagePlugin.format)
        self.assertEqual(img.mode, 'P')
        self.assertEqual(palette_bands, img.palette.tobytes())
        self.assertEqual(img.size, (1, 1))
        self.assertEqual(img.getpixel((0, 0)), 0)
        self.assertEqual(bytes(img.info['header']), bytes(header))
        self.assertEqual(bytes(img.info['indexed_header']), bytes(indexed_header))
        buf = BytesIO()
        img.save(buf, format=StiImagePlugin.format, flags=['INDEXED', 'ETRLE'])
        print(data)
        print(buf.getvalue())
        self.assertEqual(buf.getvalue(), data)

    def test_save_all_open_etrle(self):
        img1 = Image.new('RGB', (1,1))
        img1.putpixel((0,0), (1,2,3))
        img2 = Image.new('RGB', (1,1))
        img2.putpixel((0,0), (3,2,1))
        buf = BytesIO()
        img1.save(buf, format=StiImagePlugin.format, save_all=True, append_images=[img2])
        sti = Image.open(buf)
        self.assertEqual(sti.mode, 'P') # INDEXED ETRLE
        # XXX composite image, will probably change in the future
        self.assertEqual(sti.size, (3,1))
        self.assertEqual(len(sti.info['boxes']), 2)
        for box, original in zip(sti.info['boxes'], [img1, img2]):
            img = sti.crop(box).convert(original.mode)
            self.assertEqual(list(img.getdata()), list(original.getdata()))


class TestStiImageEncoder(unittest.TestCase):
    def test_colors_official_spec(self):
        data = [(0x00,0x00,0x00), (0xff,0xff,0xff),
                (0x07,0x03,0x07), (0xf8,0xfc,0xf8)]
        bytes = b'\x00\x00\xff\xff'\
              + b'\x00\x00\xff\xff'
        img = Image.new('RGB', (2, 2))
        img.putdata(data)
        self.assertEqual(img.tobytes(StiImagePlugin.format, 'colors', 'BGR;16'), bytes)

    def test_colors_default_spec(self):
        data = [(0x00,0x00,0x00), (0xff,0xff,0xff),
                (0x07,0x03,0x07), (0xf8,0xfc,0xf8)]
        bytes = b'\x00\x00\xff\xff'\
              + b'\x00\x00\xff\xff'
        img = Image.new('RGB', (2, 2))
        img.putdata(data)
        self.assertEqual(img.tobytes(StiImagePlugin.format, 'colors', None), bytes) # 'BGR;16'

    def test_colors_custom_spec(self):
        data = [(0x00,0x00,0x00,0x00), (0xff,0xff,0xff,0xff),
                (0x3f,0x3f,0x3f,0x3f), (0xc0,0xc0,0xc0,0xc0)]
        bytes = b'\x00\xff'\
              + b'\x00\xff'
        spec = (0x03,0x30,0x0c,0xc0, 2,2,2,2, 8)
        img = Image.new('RGBA', (2, 2))
        img.putdata(data)
        self.assertEqual(img.tobytes(StiImagePlugin.format, 'colors', spec), bytes)

    def test_colors_raw_encoder(self):
        data = [(0,1,2), (3,4,5),
                (6,7,8), (9,10,11)]
        bytes = b'\x00\x01\x02\x03\x04\x05'\
              + b'\x06\x07\x08\x09\x0a\x0b'
        img = Image.new('RGB', (2, 2))
        img.putdata(data)
        self.assertIn('RGB', StiImageEncoder.RAWMODES)
        self.assertEqual(img.tobytes(StiImagePlugin.format, 'colors', 'RGB'), bytes)

    def test_colors_force_alpha(self):
        data = [(0,1,2), (3,4,5),
                (6,7,8), (9,10,11)]
        bytes = b'\x00\x01\x02\xff\x03\x04\x05\xff'\
              + b'\x06\x07\x08\xff\x09\x0a\x0b\xff'
        img = Image.new('RGB', (2, 2))
        img.putdata(data)
        self.assertEqual(img.tobytes(StiImagePlugin.format, 'colors', 'RGBA'), bytes)

    def test_colors_force_no_alpha(self):
        data = [(0,1,2,255), (3,4,5,200),
                (6,7,8,100), (9,10,11,0)]
        bytes = b'\x00\x01\x02\x03\x04\x05'\
              + b'\x06\x07\x08\x09\x0a\x0b'
        img = Image.new('RGBA', (2, 2))
        img.putdata(data)
        self.assertEqual(img.tobytes(StiImagePlugin.format, 'colors', 'RGB'), bytes)

    def test_colors_small_bufsize(self):
        data = [(0x00,0x00,0x00,0x00), (0xff,0xff,0xff,0xff),
                (0x0f,0x0f,0x0f,0x0f), (0xf0,0xf0,0xf0,0xf0)]
        want = [b'\x00', b'\x00', b'\xff', b'\xff',
                b'\x00', b'\x00', b'\xff', b'\xff']
        spec = (0x000f,0xf000,0x00f0,0x0f00, 4,4,4,4, 16)
        img = Image.new('RGBA', (2, 2))
        img.putdata(data)
        have = []
        encoder = StiImageEncoder('RGBA', 'colors', spec)
        encoder.setimage(img.im)
        for i in range(len(want)):
            n, errcode, buffer = encoder.encode(1)
            have.append(buffer)
            if errcode > 0:
                break
        else:
            assert False, "too many encode cycles"
        self.assertEqual(have, want)

    def test_indexes(self):
        data = [1, 2,
                3, 4]
        bytes = b'\x01\x02'\
              + b'\x03\x04'
        img = Image.new('P', (2, 2))
        img.putdata(data)
        self.assertEqual(img.tobytes(StiImagePlugin.format, 'indexes'), bytes)

    def test_indexes_small_bufsize(self):
        data = [1, 2,
                3, 4]
        want = [b'\x01', b'\x02',
                b'\x03', b'\x04']
        img = Image.new('P', (2, 2))
        img.putdata(data)
        have = []
        encoder = StiImageEncoder('P', 'indexes')
        encoder.setimage(img.im)
        for i in range(len(want)):
            n, errcode, buffer = encoder.encode(1)
            have.append(buffer)
            if errcode > 0:
                break
        else:
            assert False, "too many encode cycles"
        self.assertEqual(have, want)

    def test_etrle(self):
        data = [1, 2,
                3, 4]
        bytes = b'\x02\x01\x02\x00'\
              + b'\x02\x03\x04\x00'
        img = Image.new('P', (2, 2))
        img.putdata(data)
        self.assertEqual(img.tobytes(StiImagePlugin.format, 'etrle'), bytes)

    def test_etrle_all_0s(self):
        data = [0, 0,
                0, 0]
        bytes = b'\x82\x00'\
              + b'\x82\x00'
        img = Image.new('P', (2, 2))
        img.putdata(data)
        self.assertEqual(img.tobytes(StiImagePlugin.format, 'etrle'), bytes)

    def test_etrle_lone_0s(self):
        data = [0, 1, 2,
                3, 0, 4,
                5, 6, 0]
        bytes = b'\x03\x00\x01\x02\x00'\
              + b'\x03\x03\x00\x04\x00'\
              + b'\x02\x05\x06\x81\x00'
        img = Image.new('P', (3, 3))
        img.putdata(data)
        self.assertEqual(img.tobytes(StiImagePlugin.format, 'etrle'), bytes)

    def test_etrle_length_limit_with_0s(self):
        data = [0] * 130
        bytes = b'\xff\x83\x00'
        img = Image.new('P', (130, 1))
        img.putdata(data)
        self.assertEqual(img.tobytes(StiImagePlugin.format, 'etrle'), bytes)

    def test_etrle_length_limit_with_1s(self):
        data = [1] * 130
        bytes = b'\x7f' + b'\x01' * 127 + b'\x03' + b'\x01' * 3 + b'\x00'
        img = Image.new('P', (130, 1))
        img.putdata(data)
        self.assertEqual(img.tobytes(StiImagePlugin.format, 'etrle'), bytes)

    def test_etrle_transitions(self):
        data = [0, 0, 1, 1, 0, 0,
                2, 2, 0, 0, 3, 3]
        bytes = b'\x82\x02\x01\x01\x82\x00'\
              + b'\x02\x02\x02\x82\x02\x03\x03\x00'
        img = Image.new('P', (6, 2))
        img.putdata(data)
        self.assertEqual(img.tobytes(StiImagePlugin.format, 'etrle'), bytes)

    def test_etrle_small_bufsize(self):
        data = [1, 2,
                3, 4]
        want = [b'\x02\x01', b'\x02\x00',
                b'\x02\x03', b'\x04\x00']
        img = Image.new('P', (2, 2))
        img.putdata(data)
        have = []
        encoder = StiImageEncoder('P', 'etrle')
        encoder.setimage(img.im)
        for i in range(len(want)):
            n, errcode, buffer = encoder.encode(2)
            have.append(buffer)
            if errcode > 0:
                break
        else:
            assert False, "too many encode cycles"
        self.assertEqual(have, want)

    def test_not_implemented(self):
        data = [0]
        img = Image.new('P', (1, 1))
        img.putdata(data)
        with self.assertRaises(NotImplementedError):
            img.tobytes(StiImagePlugin.format, 'not_implemented')
        encoder = StiImageEncoder('P', 'indexes')
        encoder.setimage(img.im)
        encoder.do = 'not_implemented' # override 'indexes'
        with self.assertRaises(NotImplementedError):
            encoder.encode()


class Test_color_components(unittest.TestCase):
    def _test_color_components(self, spec, colors, components):
        validate_spec(spec)
        found = dict()
        for color in colors:
            for component in _color_components(color, spec):
                self.assertIn(component, components)
                found[component] = True
        self.assertEqual(len(found), len(components))

    def test_0_bits(self):
        spec = (0,0,0,0, 0,0,0,0, 8)
        colors = [0,1]
        components = [255]
        self._test_color_components(spec, colors, components)

    def test_1_bit(self):
        spec = (0x01,0x02,0,0, 1,1,0,0, 8)
        colors = range(256)
        components = [0, 255]
        self._test_color_components(spec, colors, components)

    def test_2_bits(self):
        spec = (0x03,0x0C,0,0, 2,2,0,0, 8)
        colors = range(256)
        components = [0, 85, 170, 255]
        self._test_color_components(spec, colors, components)

    def test_3_bits(self):
        spec = (0x07,0x38,0,0, 3,3,0,0, 8)
        colors = range(256)
        components = [0, 36, 72, 109, 145, 182, 218, 255]
        self._test_color_components(spec, colors, components)

    def test_4_bits(self):
        spec = (0x0F,0xF0,0,0, 4,4,0,0, 8)
        colors = range(256)
        components = [0, 17, 34, 51, 68, 85, 102, 119, 136, 153, 170, 187, 204, 221, 238, 255]
        self._test_color_components(spec, colors, components)

    def test_5_bits(self):
        spec = (0x001F,0x03E0,0,0, 5,5,0,0, 16)
        colors = range(0x400)
        components = [0, 8, 16, 24, 32, 41, 49, 57, 65, 74, 82, 90, 98, 106, 115, 123, 131, 139, 148, 156, 164, 172, 180, 189, 197, 205, 213, 222, 230, 238, 246, 255]
        self._test_color_components(spec, colors, components)

    def test_6_bits(self):
        spec = (0x003F,0x0FC0,0,0, 6,6,0,0, 16)
        colors = range(0x1000)
        components = [0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60, 64, 68, 72, 76, 80, 85, 89, 93, 97, 101, 105, 109, 113, 117, 121, 125, 129, 133, 137, 141, 145, 149, 153, 157, 161, 165, 170, 174, 178, 182, 186, 190, 194, 198, 202, 206, 210, 214, 218, 222, 226, 230, 234, 238, 242, 246, 250, 255]
        self._test_color_components(spec, colors, components)

    def test_7_bits(self):
        spec = (0x007F,0x3F80,0,0, 7,7,0,0, 16)
        colors = range(0x4000)
        components = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 56, 58, 60, 62, 64, 66, 68, 70, 72, 74, 76, 78, 80, 82, 84, 86, 88, 90, 92, 94, 96, 98, 100, 102, 104, 106, 108, 110, 112, 114, 116, 118, 120, 122, 124, 126, 128, 130, 132, 134, 136, 138, 140, 142, 144, 146, 148, 150, 152, 154, 156, 158, 160, 162, 164, 166, 168, 170, 172, 174, 176, 178, 180, 182, 184, 186, 188, 190, 192, 194, 196, 198, 200, 202, 204, 206, 208, 210, 212, 214, 216, 218, 220, 222, 224, 226, 228, 230, 232, 234, 236, 238, 240, 242, 244, 246, 248, 250, 252, 255]
        self._test_color_components(spec, colors, components)

    def test_8_bits(self):
        spec = (0x00FF,0xFF00,0,0, 8,8,0,0, 16)
        colors = range(0x10000)
        components = range(256)
        self._test_color_components(spec, colors, components)

    def test_9_bits(self):
        spec = (0x0001FF,0x03FE00,0,0, 9,9,0,0, 24)
        colors = range(0x40000)
        components = range(256)
        self._test_color_components(spec, colors, components)

