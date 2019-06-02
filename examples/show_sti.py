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
    parser = argparse.ArgumentParser(description='STI image viewer (Pillow/PIL)')
    parser.add_argument('FILE', help="path to the STI file")
    args = parser.parse_args()

    img = Image.open(args.FILE)
    img.show()

if __name__ == "__main__":
    main()
