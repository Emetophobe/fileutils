#!/usr/bin/env python
# Copyright (c) 2019-2023 Mike Cunningham
# https://github.com/emetophobe/fileutils


import os
import sys
import hashlib
import argparse
import textwrap
from findfiles import walk_tree


# Default hashlib algorithm
DEFAULT_ALGORITHM = 'sha3_256'


def hash_file(path, algorithm='sha3_256', buffer_size=262144):
    """ Hash a file and return its hex digest.

    See hashlib.algorithms_available and hashlib.algorithms_guaranteed  for a
    list of supported algorithms.

    Example command (run from a shell or command line):

    `python -c "import hashlib;print(hashlib.algorithms_guaranteed)"`

    Args:
        path (str | Path): the file path.
        algorithm (str, optional): a hashlib algorithm. Defaults to "sha3_256".
        buffer_size (int, optional): read buffer size. Defaults to 262144.

    Returns:
        str: the hex digest string.
    """

    if not algorithm:
        algorithm = DEFAULT_ALGORITHM

    with open(path, 'rb') as infile:
        hasher = hashlib.new(algorithm)

        # This is taken directly from file_digest() which was added in 3.11
        # Source: https://github.com/python/cpython/blob/3.11/Lib/hashlib.py#L292-L300

        buffer = bytearray(buffer_size)
        view = memoryview(buffer)

        while True:
            size = infile.readinto(buffer)
            if not size:
                break
            hasher.update(view[:size])

    return hasher.hexdigest()


def hash_dir(path, algorithm='sha3_256', recursive=True):
    """ Hash every file in a directory. Yields tuples of filepaths and their hashes.

    Args:
        path (str | Path): the top-level directory path.
        algorithm (str): specify a hashlib algorithm. Defaults to 'sha3_256'.
        recursive (bool, optional): includes files in subdirectories. Defaults to True.

    Yields:
        tuple[str, str]: tuple of the path and its hex digest.
    """
    for entry in walk_tree(path, recursive=recursive):
        yield (entry.path, hash_file(entry.path, algorithm))


def supported_algorithms():
    """ Returns a list of supported algorithms. """
    return sorted(hashlib.algorithms_available)


def format_algorithms():
    """ Returns a list of supported algorithms as a text-wrapped string. """
    return textwrap.fill(', '.join(supported_algorithms()), 70)


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description="Generate file hashes using Python's built-in hashlib module.",
        epilog=f'Supported algorithms:\n\n{format_algorithms()}',
    )

    parser.add_argument(
        'path',
        type=os.path.abspath,  # force absolute path
        help='file or directory path',
    )

    parser.add_argument(
        '-a', '--algorithm',
        metavar='algorithm',
        type=str.lower,  # force lowercase
        default=DEFAULT_ALGORITHM,
        help='select a hashlib algorithm (default: %(default)s)',
    )

    parser.add_argument(
        '-r', '--recursive',
        action='store_true',
        help='recursively search subdirs (default: False)'
    )

    args = parser.parse_args()

    if args.algorithm not in hashlib.algorithms_available:
        parser.error('Invalid algorithm. Use --help for a list of supported algorithms.')

    try:
        if os.path.isfile(args.path):
            print(hash_file(args.path, args.algorithm))

        elif os.path.isdir(args.path):
            for filename, digest in hash_dir(**vars(args)):
                print(digest, filename)
        else:
            parser.error('Invalid path (not a file or directory)')
    except OSError as e:
        print(f'Error reading {e.path} ({e.strerror})', file=sys.stderr)


if __name__ == '__main__':
    main()
