# JA2 Open Toolset

This is a set of tools for managing JA2 game resources. Right now the goal is to be able to read and write Jagged
Alliance 2 game resources. Currently this is implemented only by a small Python library.

[![Build Status](https://travis-ci.org/ja2-stracciatella/ja2-open-toolset.svg?branch=master)](https://travis-ci.org/ja2-stracciatella/ja2-open-toolset)

## Features

- Read and Write `.SLF` archives
- Reading STI files

## Installing

Requirement: Python 3.2 or later

- Download or clone this repository
- Optional: Create and enable virtual environment so the dependencies arent installed globally

  ```
  pyvenv venv && source venv/bin/activate
  ```

- Install dependencies

  ```
  pip install -r requirements.txt
  pip install -r requirements-dev.txt
  ```

- Run one of the examples, e.g. extract all slf archives of you JA2 installation

  ```
  python examples/dump_data.py --verbose --output-folder /some/folder /your/ja2/data/dir
  ```

## License

LGPL version 3 or any later version.
