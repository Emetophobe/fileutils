#!/usr/bin/env python
# Copyright (C) 2019-2022 Mike Cunningham
# https://github.com/emetophobe/fileutils


import os
import time
import hashlib
import argparse
import textwrap

from collections import defaultdict
from filehasher import create_hash


# Default hashlib algorithm
# See hashlib.algorithms_guaranteed and hashlib.algorithms_available for a complete list
DEFAULT_ALGORITHM = 'sha3_256'


def find_dupes(directory, algorithm, excludes=None):
    """Create a dictionary of duplicate hashes (keys) and filenames (values). """

    excludes = excludes or []
    hashes = defaultdict(list)

    # Walk the entire directory tree and hash every file
    for root, dirs, files in os.walk(os.path.abspath(directory), topdown=True):
        dirs[:] = [d for d in dirs if d not in excludes]
        for filename in files:
            filename = os.path.join(root, filename)
            try:
                # Add the filename and its hash to the dictionary
                digest = create_hash(filename, algorithm)
                hashes[digest].append(filename)
            except OSError as e:
                print(f'Error reading file: {e.filename} ({e.strerror})')

    # Return a new dict with only hashes that have multiple values (duplicates)
    return {k: v for k, v in hashes.items() if len(v) > 1}


def main():
    supported_algorithms = textwrap.fill(', '.join(sorted(hashlib.algorithms_available)), 70)

    parser = argparse.ArgumentParser(
        description='Find duplicate files by comparing checksums.',
        epilog=f'List of supported algorithms:\n\n{supported_algorithms}',
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        'directory',
        help='top level directory to search'
    )

    parser.add_argument(
        '-a',
        '--algorithm',
        metavar='algorithm',
        type=str.lower,  # force lowercase
        default=DEFAULT_ALGORITHM,
        help='specify a hashlib algorithm (default: %(default)s)',
    )

    parser.add_argument(
        '-e', '--excludes',
        help='optional list of files or directories to exclude',
        metavar='excludes',
        nargs='*',
    )

    args = parser.parse_args()

    # Make sure the directory exists
    if not os.path.isdir(args.directory):
        parser.error(f'Invalid directory: {args.directory}')

    # Make sure the algorithm is supported
    if args.algorithm not in hashlib.algorithms_available:
        parser.error(f'Invalid algorithm: {args.algorithm}. Use --help for a list of supported algorithms.')

    # Get duplicate files
    print('Searching for duplicates. This may take a while...', flush=True)
    start_time = time.perf_counter()
    dupes = find_dupes(args.directory, args.algorithm, args.excludes)
    elapsed_time = time.perf_counter() - start_time

    # Print results
    print()
    for digest, files in dupes.items():
        print(digest)
        for filename in files:
            print('    ', filename)
        print()

    print(f'Found {len(dupes)} duplicate hashes in {elapsed_time:.2f} seconds.')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Aborted.')
