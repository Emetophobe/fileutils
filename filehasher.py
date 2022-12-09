#!/usr/bin/env python
# Copyright (c) 2019-2022 Mike Cunningham
# https://github.com/emetophobe/fileutils


import os
import hashlib
import argparse
import textwrap

# Default hashlib algorithm
DEFAULT_ALGORITHM = 'sha3_256'


def create_hash(filename, algorithm):
    """ Hash a file using the specified algorithm. """
    hasher = hashlib.new(algorithm)
    with open(filename, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_supported_algorithms():
    """ Return a list of available hashlib algorithms. """
    return sorted(hashlib.algorithms_available)


if __name__ == '__main__':
    supported_algorithms = ', '.join(get_supported_algorithms())

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description='Calculate file hashes using Python\'s built-in hashlib module.',
        epilog=f'Supported algorithms:\n\n{textwrap.fill(supported_algorithms, 70)}',
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

    args = parser.parse_args()

    if not os.path.isfile(args.filename):
        parser.error(f'Invalid filename {args.filename!r} (must be a valid file)')

    if args.algorithm not in hashlib.algorithms_available:
        parser.error(f'Invalid algorithm: {args.algorithm}. Use --help for a list of supported algorithms.')

    try:
        digest = create_hash(args.filename, args.algorithm)
        print(f'{args.algorithm}: {digest}')
    except OSError as e:
        print(f'Error reading {e.filename!r} ({e.strerror})')
