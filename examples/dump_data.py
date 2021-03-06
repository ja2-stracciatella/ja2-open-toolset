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
import glob
import json

sys.path.append(os.getcwd())

from ja2py.fileformats import SlfFS, Sti, is_8bit_sti, is_16bit_sti, load_8bit_sti, load_16bit_sti, load_gap
from sti_to_png import write_8bit_png_from_sti, write_24bit_png_from_sti


def dump_file(output_folder, file_path, slf_fs, args):
    to_path = os.path.join(output_folder, file_path[1:])
    to_dir = os.path.dirname(to_path)
    if args.verbose:
        print("Dumping raw file: {}".format(file_path))

    if not os.path.exists(to_dir):
        os.makedirs(to_dir)
    with slf_fs.open(file_path, 'rb') as from_file, open(to_path, 'wb') as to_file:
        to_file.write(from_file.read())


def dump_sti(output_folder, file_path, slf_fs, args):
    png_file_path = os.path.splitext(file_path)[0] + '.png'
    to_path = os.path.join(output_folder, png_file_path[1:])
    to_dir = os.path.dirname(to_path)
    if args.verbose:
        print("Dumping PNGs from STI file: {}".format(file_path))

    with slf_fs.open(file_path, 'rb') as file:
        if not os.path.exists(to_dir):
            os.makedirs(to_dir)
        if is_8bit_sti(file):
            sti = load_8bit_sti(file)
            to_path = os.path.splitext(to_path)[0] + '.STI' if len(sti.images) > 1 else os.path.splitext(to_path)[0] + '.png'
            write_8bit_png_from_sti(to_path, sti, verbose=args.verbose)
        elif is_16bit_sti(file):
            sti = load_16bit_sti(file)
            write_24bit_png_from_sti(to_path, sti, verbose=args.verbose)


def dump_gap(output_folder, file_path, slf_fs, args):
    json_file_path = os.path.splitext(file_path)[0] + '.gap.json'
    to_path = os.path.join(output_folder, json_file_path[1:])
    to_dir = os.path.dirname(to_path)
    if args.verbose:
        print("Dumping JSON from GAP file: {}".format(file_path))
    if not os.path.exists(to_dir):
        os.makedirs(to_dir)

    with slf_fs.open(file_path, 'rb') as from_file, open(to_path, 'w', encoding='utf8') as to_file:
        gap_list = load_gap(from_file)
        json.dump(gap_list, to_file, indent=2)


def dump_directory(output_folder, slf_fs, directory, args):
    special_file_handlers = {
        '.sti': dump_sti,
        '.gap': dump_gap
    }

    for file in slf_fs.listdir(directory, files_only=True):
        extension = os.path.splitext(file)[1].lower()
        slf_folder = os.path.splitext(os.path.basename(slf_fs.file_name))[0]
        args_to_dump = (
            os.path.join(output_folder, slf_folder),
            os.path.join(directory, file),
            slf_fs,
            args
        )

        if extension in special_file_handlers:
            special_file_handlers[extension](*args_to_dump)
        else:
            dump_file(*args_to_dump)
    for dir in slf_fs.listdir(directory, dirs_only=True):
        dump_directory(output_folder, slf_fs, os.path.join(directory, dir), args)

def main():
    parser = argparse.ArgumentParser(description='Jagged Alliance 2 Data Dump')
    parser.add_argument('ja2_data_dir', help="path to the Jagged Alliance 2 Data Folder (should contain STI Files)")
    parser.add_argument(
        '-o',
        '--output-folder',
        default=None,
        help="folder for extracted files.  By default, files extracted alongside the slf file in a subdirector called Dump."
    )
    parser.add_argument(
        '-v',
        '--verbose',
        action='store_true',
        default=False,
        help="be verbose, e.g. print names of the extracted files"
    )
    args = parser.parse_args()

    ja2_data_dir = os.path.expanduser(os.path.expandvars(args.ja2_data_dir))
    ja2_data_dir = os.path.normpath(os.path.abspath(ja2_data_dir))

    output_folder = args.output_folder
    if output_folder is None:
        output_folder = os.path.join(ja2_data_dir,
                                     'Dump')
    output_folder = os.path.expanduser(os.path.expandvars(output_folder))
    output_folder = os.path.normpath(os.path.abspath(output_folder))

    globbing_path = os.path.join(ja2_data_dir, '*.slf')
    if args.verbose:
        print("Dumping Files matching {} to {}".format(globbing_path, output_folder))

    for slf_path in glob.iglob(globbing_path):
        if args.verbose:
            print("Loading SLF file {0}".format(slf_path))
        slf_fs = SlfFS(slf_path)
        dump_directory(output_folder, slf_fs, '/', args)


if __name__ == "__main__":
    main()
