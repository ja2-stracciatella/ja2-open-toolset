class Image16Bit(object):
    def __init__(self, image):
        self._image = image

    @property
    def width(self):
        return self._image.size[0]

    @property
    def height(self):
        return self._image.size[1]

    @property
    def image(self):
        return self._image


class SubImage8Bit(object):
    def __init__(self, image):
        self._image = image
        self.offsets = (0, 0)
        self.aux_data = None

    @property
    def image(self):
        return self._image


class Images8Bit(object):
    def __init__(self, images, palette):
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

