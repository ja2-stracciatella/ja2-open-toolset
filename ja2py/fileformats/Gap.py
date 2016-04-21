import struct
from collections import namedtuple

gap_struct = '<II'

Gap = namedtuple('Gap', ['start', 'end'])

def load_gap(f):
    gap_size = struct.calcsize(gap_struct)
    data = f.read(gap_size)
    gaps = []
    while data:
        if len(data) != gap_size:
            raise ValueError('Incorrect number of bytes in gap file')
        start, end = struct.unpack(gap_struct, data)
        gaps.append(Gap(start=start, end=end))
        data = f.read(gap_size)
    return gaps
