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

from ja2py.fileformats.Sti import load_8bit_sti, load_16bit_sti, is_8bit_sti, is_16bit_sti

def write_image(output_file, image, transparency=0, verbose=False):
    if verbose:
        print("Writing:  {}".format(output_file))
    image.save(output_file, transparency=transparency)

def write_sequence_of_8bit_images_to_target_directory(sequence, target_directory, verbose=False):
    for image_index, sub_image in enumerate(sequence):
        image_file = os.path.join(target_directory, '{}.png'.format(image_index))
        write_image(image_file, sub_image.image, verbose=verbose)


def write_24bit_png_from_sti(output_file, sti, verbose=False):
    return write_image(output_file, sti.image, transparency=None, verbose=verbose)


def write_8bit_png_from_sti(output_file, sti, verbose=False):
    if len(sti.images) > 1:
        base_dir = output_file
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

        if sti.animated:
            for i, animation in enumerate(sti.animations):
                animation_dir = os.path.join(base_dir, 'ANI{}'.format(i))
                if not os.path.exists(animation_dir):
                    os.makedirs(animation_dir)
                write_sequence_of_8bit_images_to_target_directory(animation, animation_dir, verbose=verbose)
        else:
            write_sequence_of_8bit_images_to_target_directory(sti.images, base_dir, verbose=verbose)
    else:
        write_image(output_file, sti.images[0].image, verbose=verbose)


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

    output_file = args.output_file
    if not output_file:
        output_file = os.path.join(os.path.dirname(sti_file),
                                   os.path.splitext(os.path.basename(sti_file))[0] + '.png')
    output_file = os.path.expanduser(os.path.expandvars(output_file))
    output_file = os.path.normpath(os.path.abspath(output_file))

    if args.verbose:
        print("Input file:  {}".format(sti_file))
        print("Output file: {}".format(output_file))

    with open(sti_file, 'rb') as file:
        if is_8bit_sti(file):
            sti = load_8bit_sti(file)
            if args.verbose:
                print("File Details: ")
                print("Data Type: indexed 8bit")
                print("Number of single images: {}".format(len(sti)))
                for i, sub_image in enumerate(sti.images):
                    print("Subimage {}: Size {}x{}, Shift +{}+{}".format(
                        i+1,
                        sub_image.image.size[0],
                        sub_image.image.size[1],
                        sub_image.offsets[0],
                        sub_image.offsets[1]
                    ))
            write_8bit_png_from_sti(output_file, sti, verbose=args.verbose)
        elif is_16bit_sti(file):
            sti = load_16bit_sti(file)
            if args.verbose:
                print("File Details: ")
                print("Data Type: RGB 16bit")
                write_24bit_png_from_sti(output_file, sti, verbose=args.verbose)

        if args.verbose:
            print("Done")

if __name__ == "__main__":
    main()
