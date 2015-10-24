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
import re
import sys

sys.path.append(os.getcwd())

from ja2py.fileformats import BufferedSlfFS

def main():
    parser = argparse.ArgumentParser(description='Shadowify your Faces.slf')
    parser.add_argument('slf_file', help="path to the SLF file")
    parser.add_argument(
        '-o',
        '--output-file',
        default=None,
        help='File to write the "shadowified" Faces.slf'
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

    if not args.output_file:
        output_file = os.path.join(os.path.dirname(slf_file),
                                   os.path.splitext(os.path.basename(slf_file))[0] + 'Shawowified.slf')
    else:
        output_file = args.output_file
    output_file = os.path.expanduser(os.path.expandvars(output_file))
    output_file = os.path.normpath(os.path.abspath(output_file))

    b = BufferedSlfFS(slf_file)

    for f in b.walkfiles():
        if re.match(r'\/[\d]+.STI', f):
            if args.verbose:
                print("Replacing {} by shadow".format(f))
            if f != '/10.STI':
                b.remove(f)
                b.copy('/10.STI', f)


    b.save(output_file)

if __name__ == "__main__":
    main()

