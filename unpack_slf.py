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
# Foobar is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Foobar.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import argparse
import collections
import os.path
import struct
import sys


SLF_HEADER_FORMAT = "<256s256siiHHii"
SLF_ENTRY_FORMAT  = "<256sIIBB2xqh2x"

SlfHeader = collections.namedtuple(
    "SlfHeader",
    "libName,libPath,entries,used,sort,version,containsSubdirs,reserved".split(","))

SlfEntry = collections.namedtuple(
    "SlfEntry",
    "fileName,offset,length,state,reserved,time,reserved2")


def extractEntry(slfFile, entry, outputFolder):
    """Extract one entry from the SLF file.

    :param slfFile      open slf file
    :param entry        instance of SlfEntry._asdict()
    :param outputFolder path to the output folder.  It should already exist.
    """
    with open(os.path.join(outputFolder, entry["fileName"]), "wb") as outFile:
        slfFile.seek(entry["offset"], os.SEEK_SET)
        outFile.write(slfFile.read(entry["length"]))


def extract(inputFile, outputFolder, beVerbose):
    """Extract content of SLF file into a folder.

    :param inputFile    path to the SLF file
    :param outputFolder path to the output folder.  It should already exist.
    :param beVerbose    be verbose, e.g. print names of the extracted files.
    """
    with open(inputFile, "rb") as f:
        headerData = f.read(struct.calcsize(SLF_HEADER_FORMAT))
        header = SlfHeader(*struct.unpack(SLF_HEADER_FORMAT, headerData))._asdict()
        header["libName"] = header["libName"].decode("ascii").replace("\x00", "")
        header["libPath"] = header["libPath"].decode("ascii").replace("\x00", "")
        if beVerbose:
            print("SLF Header:")
            print("  Library name:      ", header["libName"])
            print("  Library path:      ", header["libPath"])
            print("  Entries:           ", header["entries"])

        # go to the end of the file and read list of entries
        # and extract files
        entries = []
        for i in range(header["entries"]):
            f.seek(-struct.calcsize(SLF_ENTRY_FORMAT) * (header["entries"] - i), os.SEEK_END)
            entryData = f.read(struct.calcsize(SLF_ENTRY_FORMAT))
            entry = SlfEntry(*struct.unpack(SLF_ENTRY_FORMAT, entryData))._asdict()
            if int(entry["state"]) == 0:
                entry["fileName"] = entry["fileName"].decode("ascii").replace("\x00", "")
                # print(entry)
                if beVerbose:
                    print(entry["fileName"])
                extractEntry(f, entry, outputFolder)


def main():
    parser = argparse.ArgumentParser(description='SLF Unpaker')
    parser.add_argument('SLF_FILE', help="path to the SLF file")
    parser.add_argument('--output-folder', default=None,
                        help="folder for extracted files.  By default, files extracted alongside the slf file in a subdirectory.  For example, content of foo/bar/maps.slf is extracted into folder foo/bar/maps")
    parser.add_argument('-v', action='store_true', default=False,
                        help="be verbose, e.g. print names of the extracted files")
    args = parser.parse_args()

    if not os.path.exists(args.SLF_FILE):
        print("Error: '{}' is not found".format(args.SLF_FILE), file=sys.stderr)
        exit(1)

    if args.output_folder is None:
        args.output_folder = os.path.join(os.path.dirname(args.SLF_FILE),
                                          os.path.splitext(os.path.basename(args.SLF_FILE))[0])

    if not os.path.exists(args.output_folder):
        os.mkdir(args.output_folder)


    if args.v:
        print("Input file:    {}".format(args.SLF_FILE))
        print("Output folder: {}".format(args.output_folder))

    extract(args.SLF_FILE, args.output_folder, args.v)

    if args.v:
        print("done")


if __name__ == "__main__":
    main()
