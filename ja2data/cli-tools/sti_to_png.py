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

sys.path.append(os.getcwd())

from fileformats import Sti


def main():
    parser = argparse.ArgumentParser(description='STI to PNG Converter')
    parser.add_argument('sti_file', help="path to the STI file")
    parser.add_argument(
        '-o',
        '--output-file',
        default=None,
        help="output file for converted STI. For animated files this will be used as a base for numerated files. By default the file(s) will be named the same as the STI file."
    )
    parser.add_argument(
        '-v',
        '--verbose',
        action='store_true',
        default=False,
        help="be verbose, e.g. print information about the converted file"
    )
    args = parser.parse_args()

    sti_file = args.sti_file
    sti_file = os.path.expanduser(os.path.expandvars(sti_file))
    sti_file = os.path.normpath(os.path.abspath(sti_file))

    if not args.output_file:
        output_file = os.path.join(os.path.dirname(sti_file),
                                   os.path.splitext(os.path.basename(sti_file))[0] + '.png')
    output_file = os.path.expanduser(os.path.expandvars(output_file))
    output_file = os.path.normpath(os.path.abspath(output_file))

    if args.verbose:
        print("Input file:    {}".format(sti_file))
        print("Output file: {}".format(output_file))

    with open(sti_file, 'rb') as file:
        sti = Sti(file)

        if args.verbose:
            print("File Details: ")
            print("Data Type: {} {}bit".format(sti.header.mode, sti.header.color_depth))
            print("Animated: {}".format(sti.header.animated))
            if sti.header.animated:
                print("Number of single images: {}".format(sti.header.format_specific_header.number_of_images))

        if not sti.header.animated:
            sti.images[0][0].save(output_file)

if __name__ == "__main__":
    main()
