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


import os
import sys
import argparse

# search for ja2py in the parent dir of this file
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from ja2py.content.Npc import NpcData, NPC_RECORD_LENGTH


def main():
    parser = argparse.ArgumentParser(description='Dump NPCDATA file')
    parser.add_argument('npc_file', help="path to the NPC file")
    args = parser.parse_args()

    with open(args.npc_file, 'rb') as npc_file:
        idx = 0
        while True:
            b = npc_file.read(NPC_RECORD_LENGTH)
            if len(b) < NPC_RECORD_LENGTH:
                break
            record = NpcData(b)
            print("Record #{}".format(idx))
            idx = idx + 1
            record.pretty_print()


if __name__ == "__main__":
    main()
