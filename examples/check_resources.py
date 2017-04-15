#!/usr/bin/env python3

"""
This script can be used to scan the ja-straciatella source tree and compare 
the hardcoded resouce names to the contents of the game's data dir.

For additional information, look at the docstring of check_resource_file(...).
"""

import difflib
import glob
import os
import re
from ja2py.fileformats import SlfFS


# taken from src/game/Directories.h:
RESOURCES = {
  "AMBIENTDIR":     "ambient",
  "ANIMSDIR":       "anims",
  "BATTLESNDSDIR":  "battlesnds",
  "BIGITEMSDIR":    "bigitems",
  "BINARYDATADIR":  "binarydata",
  "CURSORSDIR":     "cursors",
  "EDITORDIR":      "editor",
  "FACESDIR":       "faces",
  "FONTSDIR":       "fonts",
  "INTERFACEDIR":   "interface",
  "INTRODIR":       "intro",
  "LAPTOPDIR":      "laptop",
  "LOADSCREENSDIR": "loadscreens",
  "MERCEDTDIR":     "mercedt",
  "MUSICDIR":       "music",
  "NPC_SPEECHDIR":  "npc_speech",
  "NPCDATADIR":     "npcdata",
  "SOUNDSDIR":      "sounds",
  "SPEECHDIR":      "speech",
  "STSOUNDSDIR":    "stsounds",
  "TEMPDIR":        "temp",
  "TILECACHEDIR":   "tilecache"
}


def aggregate_resource_list(path, pattern_string, directory_string):
    """Seach the source files in path for lines containing resources starting
    with pattern_string.

    Return a list of tuples of these resources.
    The tuple contains (directory, name, location in source file)."""
    # Use dictionary to get a unique list:
    ret = {}
    pattern = re.compile(b'[\s(,]+'+pattern_string.encode()+b'\s*"([^"]*)"')
    for path, _, filenames in os.walk(path):
        for filename in filenames:
            # skip Directories.h:
            #if filename.lower() == "directories.h":
            #    continue
            filepath = os.path.join(path, filename)
            with open(filepath, "rb") as in_:
                for linenr, line in enumerate(in_):
                    mo = pattern.search(line)
                    if mo:
                        name = mo.group(1).decode()
                        # skip directory definition (e.g. in src/game/Directories.h)
                        if not name[0] == "/":
                            continue
                        location = "{}:{} {}".format(filepath, linenr, line.decode()).strip()
                        ret[(directory_string, name, location)] = True
    return list(ret.keys())


def find_case_insensitive(name, path):
    """Find a file named name inside path in a case-insensitive manner.

    Return full path to file with correct case."""
    name = name.lower()
    for item in os.listdir(path):
        if item.lower() == name:
            return os.path.join(path, item)
    return None

def find_local_file(name, dirname, data_path):
    """Try to find a local file named name in dirname inside data_path.
    Both name and dirname are case-insensitive.

    Return success."""
    dirname_found = find_case_insensitive(dirname, data_path)
    if dirname_found is None:
        return False

    file_found = find_case_insensitive(name, dirname_found)
    #if not file_found is None:
        #print("Found local file {}.".format(file_found))
    return not file_found is None

def check_resource_file(resources, archive_name, data_path, sequence_match_ratio_threshold = 0.75):
    """Check if a list of resources can be found.

    resources is expected to be a tuple returned by aggregate_resource_list(...).

    Strategy:
    1. Search archive named archive_name inside data_path.
    2. If the archive is found, search inside for the specified resources.
    3. Search for local files inside data_path.
    4. If both strategies fail, try to use fuzzy matching to find the correct
       resource name in the archive.

    Output: Errors (and possible matches).
    """
    path = find_case_insensitive(archive_name, data_path)
    if path is None:
        print("Archive '{}' not found.".format(archive_name))
        for resource_dirname, resource, location in resources:
            ret = find_local_file(resource[1:], resource_dirname, data_path)
            if not ret:
                print(location)
                print("  File '{}{}' not found.".format(resource_dirname, resource))
                print()
        return
    print("Using archive '{}'.".format(path))

    slf_fs = SlfFS(path)
    not_in_slf = []
    for resource_dirname, resource, location in resources:
        #resource = resource[1:].upper()

        # Search archive:
        found = slf_fs.isfile(resource[1:].upper())

        # Search local file:
        if not found:
            found = find_local_file(resource[1:], resource_dirname, data_path)

        if not found:
            not_in_slf.append((resource_dirname, resource, location))

    if len(not_in_slf) == 0:
        print("Everything okay.")
        return

    print("Trying to match resources to files in slf archive...")
    # Use walk to generate a list of files (including those in subdirectories):
    slf_resources = []
    for currentdir, items in slf_fs.walk("/"):
        for item in items:
            temp = currentdir
            if temp[-1] != "/":
                temp += "/"
            temp += item
            slf_resources.append(temp.lower())
            #print(currentdir.lower(), item.lower())


    for resource_dirname, resource, location in not_in_slf:
        print(location)
        print("  File: '{}{}'".format(resource_dirname, resource))
        found_something = False
        for slf_resource in slf_resources:
            ratio = difflib.SequenceMatcher(None, resource, slf_resource).ratio()
            if ratio < sequence_match_ratio_threshold:
                continue
            print("  Possible match: '{}' ({: 3}%)".format(slf_resource.lower(), int(ratio*100)))
            found_something = True
        if not found_something:
            print("  No possible matches.")
        print()


def main():
    import sys
    if len(sys.argv) < 3:
        print(__doc__)
        print("Usage: {} (path_to_data_directory) (path_to_src_directory)".format(sys.argv[0]))
        return
    path_data = sys.argv[1]
    path_src = sys.argv[2]

    for key, val in RESOURCES.items():
        filelist = aggregate_resource_list(path_src, key, val)
        archive_name = "{}.slf".format(val)
        check_resource_file(filelist, archive_name, path_data)
        print()
        print()

if __name__ == '__main__':
    main()
