from PIL import ImagePalette

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
        if image.mode != 'P':
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
        for sub_image in images:
            if sub_image.image.palette.getdata() != palette.getdata():
                raise ValueError('All images need to have the same palette for Images8Bit')
        self._palette = palette
        self._images = list(images)

    @property
    def palette(self):
        return self._palette

    @property
    def images(self):
        return self._images

    def __len__(self):
        return len(self._images)

