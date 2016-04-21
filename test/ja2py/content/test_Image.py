import unittest

from ja2py.content import Image16Bit, Images8Bit, SubImage8Bit
from PIL import Image, ImagePalette


class TestImage16Bit(unittest.TestCase):
    def test_constructor(self):
        raw = Image.new('RGB', (2, 2))
        Image16Bit(raw)

    def test_constructor_non_rgb_image_raises(self):
        raw = Image.new('P', (2, 2))
        with self.assertRaises(ValueError):
            Image16Bit(raw)

    def test_width_and_height(self):
        self.assertEqual(Image16Bit(Image.new('RGB', (32, 32))).size, (32, 32))
        self.assertEqual(Image16Bit(Image.new('RGB', (65, 78))).size, (65, 78))

    def test_image(self):
        raw = Image.new('RGB', (2, 2))
        img = Image16Bit(raw)

        self.assertEqual(img.image, raw)


class TestSubImage(unittest.TestCase):
    def test_default_constructor(self):
        raw = Image.new('P', (2, 2))
        sub_img = SubImage8Bit(raw)

        self.assertEqual(sub_img.image, raw)
        self.assertEqual(sub_img.offsets, (0, 0))
        self.assertEqual(sub_img.aux_data, None)

    def test_constructor_with_offset(self):
        raw = Image.new('P', (2, 2))
        sub_img = SubImage8Bit(raw, offsets=(12, 32))

        self.assertEqual(sub_img.offsets, (12, 32))

    def test_constructor_with_aux_data(self):
        raw = Image.new('P', (2, 2))
        aux_data = {'1': 2}
        sub_img = SubImage8Bit(raw, offsets=(12, 32), aux_data=aux_data)

        self.assertEqual(sub_img.aux_data, aux_data)

    def test_constructor_non_indexed_image_raises(self):
        raw = Image.new('RGB', (2, 2))

        with self.assertRaises(ValueError):
            SubImage8Bit(raw)

    def test_constructor_with_non_tuple_or_wrong_tuple_length_for_offset_raises(self):
        raw = Image.new('P', (2, 2))

        with self.assertRaises(ValueError):
            SubImage8Bit(raw, 'Test')
        with self.assertRaises(ValueError):
            SubImage8Bit(raw, (0, 1, 2))

    def test_constructor_with_non_dict_for_aux_dataraises(self):
        raw = Image.new('P', (2, 2))

        with self.assertRaises(ValueError):
            SubImage8Bit(raw, aux_data='Test')


def create_indexed_images():
    raw1 = SubImage8Bit(Image.new('P', (2, 2)))
    raw2 = SubImage8Bit(Image.new('P', (2, 2)))
    palette = ImagePalette.ImagePalette('RGB')
    raw1.image.putpalette(palette.tobytes())
    raw2.image.putpalette(palette.tobytes())
    return [raw1, raw2], palette


class TestImages8Bit(unittest.TestCase):
    def test_default_constructor(self):
        raws, palette = create_indexed_images()
        imgs = Images8Bit(raws, palette)

        self.assertEqual(imgs.images[0], raws[0])
        self.assertEqual(imgs.images[1], raws[1])
        self.assertEqual(imgs.palette, palette)

    def test_images_with_different_palettes_raise(self):
        raws, palette = create_indexed_images()
        other_palette = ImagePalette.ImagePalette('RGB', b'\x01\x01\x01', 3)
        raws[0].image.putpalette(other_palette)

        with self.assertRaises(ValueError):
            Images8Bit(raws, palette)

    def test_images_with_non_palette(self):
        raws, palette = create_indexed_images()

        with self.assertRaises(ValueError):
            Images8Bit(raws, 'Test')

    def test_len(self):
        raws, palette = create_indexed_images()

        self.assertEqual(len(Images8Bit([raws[0]], palette)), 1)
        self.assertEqual(len(Images8Bit(raws, palette)), 2)

    def test_images_are_not_mutable(self):
        raws, palette = create_indexed_images()
        imgs = Images8Bit(raws, palette)

        with self.assertRaises(TypeError):
            imgs.images[0] = raws[1]

    def test_append(self):
        raws, palette = create_indexed_images()
        imgs = Images8Bit([raws[0]], palette)

        imgs.append(raws[1])
        self.assertEqual(len(imgs), 2)
        self.assertEqual(imgs.images[1], raws[1])

        with self.assertRaises(ValueError):
            imgs.append('Test')

        raw3 = SubImage8Bit(Image.new('P', (2, 2)))
        other_palette = ImagePalette.ImagePalette('RGB', b'\x01\x01\x01', 3)
        raw3.image.putpalette(other_palette)
        with self.assertRaises(ValueError):
            imgs.append(raw3)

    def test_insert(self):
        raws, palette = create_indexed_images()
        imgs = Images8Bit(raws, palette)

        raw3 = SubImage8Bit(Image.new('P', (2, 2)))
        raw4 = SubImage8Bit(Image.new('P', (2, 2)))

        imgs.insert(0, raw3)

        self.assertEqual(imgs.images, (raw3, raws[0], raws[1]))

        imgs.insert(2, raw4)
        self.assertEqual(imgs.images, (raw3, raws[0], raw4, raws[1]))

        with self.assertRaises(ValueError):
            imgs.insert(5, raw4)
        with self.assertRaises(ValueError):
            imgs.insert(-1, raw4)
        with self.assertRaises(ValueError):
            imgs.insert(5, '')

    def test_remove(self):
        raws, palette = create_indexed_images()
        raw3 = SubImage8Bit(Image.new('P', (2, 2)))
        raw4 = SubImage8Bit(Image.new('P', (2, 2)))
        imgs = Images8Bit(raws + [ raw3, raw4 ], palette)

        imgs.remove(raws[0])

        self.assertEqual(imgs.images, (raws[1], raw3, raw4))

        imgs.remove(raw4)
        self.assertEqual(imgs.images, (raws[1], raw3))

        with self.assertRaises(ValueError):
            imgs.remove(raw4)

    def test_animated(self):
        raws, palette = create_indexed_images()

        self.assertFalse(Images8Bit(raws, palette).animated)

        raws[0].aux_data = {'number_of_frames': 0}
        self.assertFalse(Images8Bit(raws, palette).animated)

        raws[0].aux_data = {'number_of_frames': 2}
        self.assertTrue(Images8Bit(raws, palette).animated)

    def test_animations_animated_image(self):
        non_animated_raws, non_animated_palette = create_indexed_images()

        raw1 = SubImage8Bit(Image.new('P', (2, 2)), aux_data={'number_of_frames': 1})
        raw2 = SubImage8Bit(Image.new('P', (2, 2)), aux_data={'number_of_frames': 2})
        raw3 = SubImage8Bit(Image.new('P', (2, 2)), aux_data={'number_of_frames': 0})
        palette = ImagePalette.ImagePalette('RGB')
        raw1.image.putpalette(palette.tobytes())
        raw2.image.putpalette(palette.tobytes())
        raw3.image.putpalette(palette.tobytes())

        self.assertEqual(Images8Bit([raw1, raw2, raw3], palette).animations, (
            (raw1, ),
            (raw2,
             raw3)
        ))
        self.assertEqual(Images8Bit([raw2, raw3], palette).animations, (
            (raw2,
             raw3),
        ))
        self.assertEqual(Images8Bit(non_animated_raws, non_animated_palette).animations, None)





