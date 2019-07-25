#!/usr/bin/env python3

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

import argparse
import os
import sys

# search for ja2py in the parent dir of this file
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# load the image plugin
import ja2py.fileformats.Sti
from PIL import Image


def main():
    parser = argparse.ArgumentParser(description='STI image creator - INDEXED ETRLE')
    parser.add_argument('files', metavar='FILE', nargs='+', help="path to an image file")
    parser.add_argument(
        '-o',
        '--output',
        default=None,
        help="path to the output file. By default, it's the first FILE with the extension replaced with '.STI'"
    )
    parser.add_argument(
        '-v',
        '--verbose',
        action='store_true',
        default=False,
        help="be verbose, e.g. print the names of the files"
    )
    args = parser.parse_args()
    output = args.output or os.path.splitext(args.files[0])[0] + ".STI"
    if args.verbose:
        for file in args.files:
            print("Input file : {}".format(file))
        print("Output file: {}".format(output))

    images = [Image.open(file) for file in args.files]
    images[0].save(output, format='STCI', save_all=True, flags=['INDEXED', 'ETRLE'], append_images=images[1:]) # calls StiImagePlugin._save_all_handler


if __name__ == "__main__":
    main()
