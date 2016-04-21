from functools import reduce
from PIL import Image, ImagePalette

class Image16Bit(object):
    def __init__(self, image):
        if image.mode != 'RGB':
            raise ValueError('The image for Image16Bit needs to be an RGB image')
        self._image = image

    @property
    def size(self):
        return self._image.size

    @property
    def image(self):
        return self._image


class SubImage8Bit(object):
    def __init__(self, image, offsets=(0, 0), aux_data=None):
        if not isinstance(image, Image.Image) or image.mode != 'P':
            raise ValueError('The image for SubImage8Bit needs to be a indexed image')
        if not isinstance(offsets, tuple) or len(offsets) != 2:
            raise ValueError('The offset for SubImage8Bit needs to be a tuple of length 2')
        if aux_data is not None and not isinstance(aux_data, dict):
            raise ValueError('The aux_data for SubImage8Bit needs to be a dict')

        self._image = image
        self.offsets = offsets
        self.aux_data = aux_data

    @property
    def image(self):
        return self._image


class Images8Bit(object):
    def __init__(self, images, palette):
        if not isinstance(palette, ImagePalette.ImagePalette):
            raise ValueError('palette needs to be an ImagePalette for Images8Bit')
        self._palette = palette

        for sub_image in images:
            self._validate_sub_image(sub_image)
        self._images = tuple(images)

    def _validate_sub_image(self, sub_image):
        if not isinstance(sub_image, SubImage8Bit):
            raise ValueError('All images need be of SubImage8Bit class for Images8Bit')
        if sub_image.image.palette.getdata() != self._palette.getdata():
            raise ValueError('All images need to have the same palette for Images8Bit')

    @property
    def palette(self):
        return self._palette

    @property
    def images(self):
        return self._images

    @property
    def animated(self):
        return any(i.aux_data is not None and i.aux_data['number_of_frames'] != 0 for i in self._images)

    @property
    def animations(self):
        def reducer(acc, sub_img):
            if sub_img.aux_data['number_of_frames'] != 0:
                acc.append([])
            acc[-1].append(sub_img)
            return acc
        if not self.animated:
            return None
        return tuple(tuple(i) for i in reduce(reducer, self._images, []))

    def append(self, sub_img):
        self._validate_sub_image(sub_img)
        self._images = self._images + (sub_img,)

    def insert(self, i, sub_img):
        if i < 0 or i > len(self._images):
            raise ValueError('Index {{0}} out of bounds'.format(i))
        self._validate_sub_image(sub_img)
        self._images = self._images[:i] + (sub_img,) + self._images[i:]

    def remove(self, sub_img):
        if sub_img not in self._images:
            raise ValueError('SubImage is not in images')
        self._images = tuple(i for i in self._images if i is not sub_img)

    def __len__(self):
        return len(self._images)

