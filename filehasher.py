#!/usr/bin/env python
# Copyright (c) 2019-2023 Mike Cunningham
# https://github.com/emetophobe/fileutils

import os
import sys
import hashlib
import argparse
import textwrap


from findfiles import walk_tree, print_unicode_error


# Default hashlib algorithm
DEFAULT_ALGORITHM = 'sha3_256'


def hash_file(path, algorithm):
    """ Hash a file using the specified algorithm. """
    hasher = hashlib.new(algorithm)
    with open(path, 'rb') as infile:
        while chunk := infile.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def hash_dir(path, algorithm, recursive=False):
    """ Hash every file in a directory. Yields tuples of filepaths and their hashes. """
    for entry in walk_tree(path, recursive=recursive):
        yield entry.path, hash_file(entry.path, algorithm)


def supported_algorithms():
    """ Return the list of supported algorithms. """
    return sorted(hashlib.algorithms_available)


def format_algorithms():
    """ Return the list of supported algorithms as a text-wrapped string. """
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
        help='recurse directories (default: False)'
    )

    args = parser.parse_args()

    if args.algorithm not in hashlib.algorithms_available:
        parser.error('Invalid algorithm. Use --help for a list of supported algorithms.')

    try:
        if os.path.isfile(args.path):
            print(hash_file(args.path, args.algorithm))

        elif os.path.isdir(args.path):
            for filename, digest in hash_dir(**vars(args)):
                try:
                    print(digest, filename)
                except UnicodeError as error:
                    print_unicode_error(filename, error)
        else:
            parser.error('Invalid path. No such file or directory.')
    except OSError as e:
        print(f'Error reading {e.path} ({e.strerror})', file=sys.stderr)


if __name__ == '__main__':
    main()
