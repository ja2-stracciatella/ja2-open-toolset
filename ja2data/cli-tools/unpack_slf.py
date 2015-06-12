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

# TODO: Find out how to import properly...
sys.path.append(os.getcwd())

from fileformats import SlfFS
from fs.osfs import OSFS
from fs.mountfs import MountFS

def main():
    parser = argparse.ArgumentParser(description='SLF Unpacker')
    parser.add_argument('slf_file', help="path to the SLF file")
    parser.add_argument(
        '-o',
        '--output-folder',
        default=None,
        help="folder for extracted files.  By default, files extracted alongside the slf file in a subdirectory.  For example, content of foo/bar/maps.slf is extracted into folder foo/bar/maps"
    )
    parser.add_argument(
        '-v',
        '--verbose',
        action='store_true',
        default=False,
        help="be verbose, e.g. print names of the extracted files"
    )
    args = parser.parse_args()

    slf_file = args.slf_file
    slf_file = os.path.expanduser(os.path.expandvars(slf_file))
    slf_file = os.path.normpath(os.path.abspath(slf_file))

    if not os.path.exists(slf_file):
        print("Error: '{}' is not found".format(args.slf_file), file=sys.stderr)
        exit(1)

    output_folder = args.output_folder
    if output_folder is None:
        output_folder = os.path.join(os.path.dirname(slf_file),
                                     os.path.splitext(os.path.basename(slf_file))[0])
    output_folder = os.path.expanduser(os.path.expandvars(output_folder))
    output_folder = os.path.normpath(os.path.abspath(output_folder))

    if not os.path.exists(output_folder):
        os.mkdir(output_folder)

    if args.verbose:
        print("Input file:    {}".format(slf_file))
        print("Output folder: {}".format(output_folder))

    slf_fs = SlfFS(slf_file)
    out_fs = OSFS(output_folder)

    combined_fs = MountFS()
    combined_fs.mountdir('slf', slf_fs)
    combined_fs.mountdir('out', out_fs)
    combined_fs.copydir('/slf', '/out', overwrite=True)

    if args.verbose:
        print("done")


if __name__ == "__main__":
    main()
