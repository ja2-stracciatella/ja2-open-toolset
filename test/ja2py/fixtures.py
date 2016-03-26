from io import BytesIO
from ja2py.fileformats import Sti16BitHeader, Sti8BitHeader, StiHeader, StiSubImageHeader, AuxObjectData
from ja2py.fileformats import etrle_compress


def create_non_image_buffer():
    return BytesIO(512 * b'0x00')


def create_8_bit_sti():
    format_header = Sti8BitHeader(
        number_of_palette_colors=2,
        number_of_images=1,
        red_color_depth=1,
        green_color_depth=1,
        blue_color_depth=1,
    )
    header = StiHeader(
        file_identifier=b'STCI',
        initial_size=1,
        size_after_compression=1,
        transparent_color=0,
        flags=8,
        height=1,
        width=1,
        format_specific_header=bytes(format_header),
        color_depth=1,
        aux_data_size=0,
    )
    palette = b'\x01\x02\x03\x04\x05\x06'
    data1 = etrle_compress(b'\x00\x01')
    sub_header1 = StiSubImageHeader(
        offset=0,
        length=len(data1),
        offset_x=0,
        offset_y=0,
        height=2,
        width=1
    )

    return BytesIO(bytes(header) + palette + bytes(sub_header1) + data1)


def create_8_bit_multi_image_sti():
    format_header = Sti8BitHeader(
        number_of_palette_colors=2,
        number_of_images=2,
        red_color_depth=1,
        green_color_depth=1,
        blue_color_depth=1,
    )
    header = StiHeader(
        file_identifier=b'STCI',
        initial_size=3,
        size_after_compression=3,
        transparent_color=0,
        flags=8,
        height=1,
        width=1,
        format_specific_header=bytes(format_header),
        color_depth=1,
        aux_data_size=0,
    )

    data1 = etrle_compress(b'\x00\x01')
    sub_header1 = StiSubImageHeader(
        offset=0,
        length=len(data1),
        offset_x=0,
        offset_y=0,
        height=1,
        width=2
    )
    data2 = etrle_compress(b'\x01\x01\x00\x00\x00\x00')
    sub_header2 = StiSubImageHeader(
        offset=len(data1),
        length=len(data2),
        offset_x=1,
        offset_y=2,
        height=3,
        width=2
    )
    palette = b'\x01\x02\x03\x04\x05\x06'

    return BytesIO(bytes(header) + palette + bytes(sub_header1) + bytes(sub_header2) + data1 + data2)


def create_8_bit_animated_sti():
    format_header = Sti8BitHeader(
        number_of_palette_colors=1,
        number_of_images=2,
        red_color_depth=4,
        green_color_depth=3,
        blue_color_depth=2,
    )
    header = StiHeader(
        file_identifier=b'STCI',
        initial_size=3,
        size_after_compression=3,
        transparent_color=0,
        flags=8,
        height=3,
        width=1,
        format_specific_header=bytes(format_header),
        color_depth=1,
        aux_data_size=32,
    )

    data1 = etrle_compress(b'\x00\x01')
    sub_header1 = StiSubImageHeader(
        offset=0,
        length=len(data1),
        offset_x=0,
        offset_y=0,
        height=1,
        width=2
    )
    aux_data_1 = AuxObjectData(
        wall_orientation=0,
        number_of_tiles=1,
        tile_location_index=2,
        current_frame=0,
        number_of_frames=2,
        flags=8,
    )

    data2 = etrle_compress(b'\x01\x01\x00\x00\x00\x00')
    sub_header2 = StiSubImageHeader(
        offset=len(data1),
        length=len(data2),
        offset_x=1,
        offset_y=2,
        height=3,
        width=2
    )
    aux_data_2 = AuxObjectData(
        wall_orientation=0,
        number_of_tiles=1,
        tile_location_index=2,
        current_frame=1,
        number_of_frames=0,
        flags=8,
    )
    palette = b'\x01\x02\x03'

    return BytesIO(bytes(header) + palette + bytes(sub_header1) + bytes(sub_header2) + data1 + data2 +
                   bytes(aux_data_1) + bytes(aux_data_2))


def create_16_bit_sti():
    format_header = Sti16BitHeader(
        red_color_mask=0xF800,
        green_color_mask=0x7E0,
        blue_color_mask=0x1F,
        alpha_channel_mask=5,
        red_color_depth=4,
        green_color_depth=3,
        blue_color_depth=2,
        alpha_channel_depth=0
    )
    header = StiHeader(
        file_identifier=b'STCI',
        initial_size=8,
        size_after_compression=8,
        transparent_color=0,
        flags=4,
        height=2,
        width=3,
        format_specific_header=bytes(format_header),
        color_depth=16,
        aux_data_size=1,
    )
    data = b'\x51\x52\x53\x54\x55\x56\x57\x58\x59\x60\x61\x62'

    return BytesIO(bytes(header) + data)
