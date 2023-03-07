#!/usr/bin/env python
# Copyright (c) 2019-2023 Mike Cunningham
# https://github.com/emetophobe/fileutils


import os
import sys
import time
import hashlib
import argparse
from collections import defaultdict
from filehasher import hash_file, format_algorithms
from findfiles import walk_tree


# Default hashlib algorithm
DEFAULT_ALGORITHM = 'sha3_256'


def find_dupes(directory, algorithm='sha3_256', excludes=None,
               dotfiles=False, symlinks=False):
    """ Find duplicate files by comparing file hashes.

    Args:
        directory (str | Path):
            Top level search directory.

        algorithm (str, optional):
            A hashlib algorithm. Defaults to 'sha3_256'.

        excludes (list, optional):
            List of files and directories to exclude. Defaults to None.

        dotfiles (bool, optional):
            Include dotfiles and directories. Defaults to False.

        symlinks (bool, optional):
            Follow symbolic links. Defaults to False.

    Returns:
        dict[str, list[str]]: a dictionary of hashes and duplicate file paths.
    """
    if not algorithm:
        algorithm = DEFAULT_ALGORITHM

    if not excludes:
        excludes = []

    # Hash every file in the directory
    hashes = defaultdict(list[str])
    for entry in walk_tree(directory, excludes=excludes, symlinks=symlinks,
                           dotfiles=dotfiles, recursive=True):
        try:
            digest = hash_file(entry.path, algorithm)
            hashes[digest].append(entry.path)
        except OSError as e:
            print(f'Error reading {e.filename} ({e.strerror})', file=sys.stderr)

    # Return a subset of the dictionary with duplicate hashes
    return {k: v for k, v in hashes.items() if len(v) > 1}


def main():
    parser = argparse.ArgumentParser(
        description="Find duplicate files using Python's hashlib module.",
        epilog=f'List of supported algorithms:\n\n{format_algorithms()}',
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        'directory',
        help='top level search directory',
        type=os.path.abspath  # force absolute paths
    )

    parser.add_argument(
        '-a', '--algorithm',
        help='specify a hashlib algorithm (default: %(default)s)',
        metavar='algorithm',
        type=str.lower,  # force lowercase
        default=DEFAULT_ALGORITHM,
    )

    parser.add_argument(
        '-e', '--excludes',
        help='list of files and directories to exclude (default: None)',
        metavar='excludes',
        nargs='*',
    )

    parser.add_argument(
        '-d', '--dotfiles',
        help='include dotfiles (default: False)',
        action='store_true'
    )

    parser.add_argument(
        '-l', '--symlinks',
        help='follow symlinks (default: False)',
        action='store_true'
    )

    args = parser.parse_args()

    # Make sure the directory exists
    if not os.path.isdir(args.directory):
        parser.error('Invalid directory.')

    # Make sure the algorithm is supported
    if args.algorithm not in hashlib.algorithms_available:
        parser.error(f'Invalid algorithm: {args.algorithm}.')

    # Find duplicate files
    try:
        print('Searching for duplicates. This may take a while...', flush=True)
        start_time = time.perf_counter()
        dupes = find_dupes(**vars(args))
        elapsed_time = time.perf_counter() - start_time
    except OSError as e:
        print(f'Error reading {e.filename} ({e.strerror})', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('Aborted.')
        return 1

    # Print results
    for digest, files in dupes.items():
        print(f'\n{args.algorithm}: {digest}\n')
        for filename in files:
            print(f'  {filename}')

    print(f'\nFound {len(dupes):,} duplicate hashes in {elapsed_time:.2f} seconds.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
