#!/usr/bin/env python
# Copyright (c) 2019-2022 Mike Cunningham
# https://github.com/emetophobe/fileutils


import os
import sys
import hashlib
import argparse
import textwrap


# Default hashlib algorithm
DEFAULT_ALGORITHM = 'sha3_256'


def create_hash(filename, algorithm: str) -> str:
    """ Hash a file using the specified algorithm. """
    hasher = hashlib.new(algorithm)
    with open(filename, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_supported_algorithms() -> list[str]:
    """ Return a list of available hashlib algorithms. """
    return sorted(hashlib.algorithms_available)


def get_formatted_algorithms() -> str:
    """ Return the list of supported algorithms as a human readable string. """
    supported_algorithms = ', '.join(get_supported_algorithms())
    return textwrap.fill(supported_algorithms, 70)


def main(args=None):
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description='Generate file hashes using Python\'s built-in hashlib module.',
        epilog=f'Supported algorithms:\n\n{get_formatted_algorithms()}',
    )

    parser.add_argument(
        'filename',
        help='file to hash',
    )

    parser.add_argument(
        '-a',
        '--algorithm',
        metavar='algorithm',
        type=str.lower,  # force lowercase
        default=DEFAULT_ALGORITHM,
        help='specify a hashlib algorithm (default: %(default)s)',
    )

    args = parser.parse_args(args)

    if not os.path.isfile(args.filename):
        if os.path.isdir(args.filename):
            parser.error('Invalid filename. Must be a file, not a directory.')
        parser.error('Invalid filename.')

    if args.algorithm not in hashlib.algorithms_available:
        parser.error('Invalid algorithm. Use --help for a list of supported algorithms.')

    try:
        digest = create_hash(args.filename, args.algorithm)
        print(f'{args.algorithm}: {digest}')
        return 0
    except OSError as e:
        print(f'Error reading {e.filename} ({e.strerror})')
        return 1


if __name__ == '__main__':
    sys.exit(main())
