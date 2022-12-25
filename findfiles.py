#!/usr/bin/env python
# Copyright (c) 2019-2022 Mike Cunningham
# https://github.com/emetophobe/fileutils


import os
import sys
import time
import argparse
import fnmatch
import re

from filestats import walk_tree


def find_files(path, dotfiles=True, symlinks=False, compiled_pattern=None, minsize=None, maxsize=None):
    """ Find files in the directory path matching the specified filters. """
    for entry in walk_tree(path, dotfiles=dotfiles, symlinks=symlinks, recursive=True):
        # Pattern matching
        if compiled_pattern and not compiled_pattern.search(entry.path):
            continue

        # Size matching
        if minsize is not None and minsize > entry.stat().st_size:
            continue
        elif maxsize is not None and maxsize < entry.stat().st_size:
            continue

        # Yield file paths
        yield entry.path


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        'path',
        help='top level directory',
        type=os.path.abspath)  # use absolute paths

    parser.add_argument(
        '-d', '--dotfiles',
        help='show dot files (default: False)',
        action='store_true')

    parser.add_argument(
        '-l', '--symlinks',
        help='follow symbolic links (default: False)',
        action='store_true')

    parser.add_argument(
        '-s', '--summary',
        help='show file count and duration',
        action='store_true')

    pattern_group = parser.add_mutually_exclusive_group()

    pattern_group.add_argument(
        '-f', '--fnmatch',
        dest='pattern',
        help='unix-style filename pattern matching. '
        '(Quotes are required for wildcards; i.e "*.py")',
        default=None)

    pattern_group.add_argument(
        '-r', '--regexp',
        help='match filenames with a regular expression',
        default=None)

    size_group = parser.add_argument_group('size options')

    size_group.add_argument(
        '-x', '--size',
        help='limit files to an exact size (in bytes)',
        dest='exactsize',
        type=int)

    size_group.add_argument(
        '-n', '--minsize',
        help='set a minimum file size (in bytes)',
        type=int)

    size_group.add_argument(
        '-m', '--maxsize',
        help='set a maximum file size (in bytes)',
        type=int)

    return (parser.parse_args(), parser)


def convert_filename(value: str) -> str:
    """Convert the filename to a version that can be safely displayed. """
    return value.encode('utf-8', 'replace').decode('utf-8')


def main():
    args, parser = parse_args()

    # Make sure the path is valid
    if not os.path.isdir(args.path):
        parser.error('Invalid search path. Must be a valid directory.')

    if args.exactsize:
        # Don't allow minsize or maxsize to be used with exactsize
        if args.minsize is not None or args.maxsize is not None:
            parser.error('cannot use --size with --minsize/--maxsize')

        # Set the exact size
        args.minsize = args.maxsize = args.exactsize

    # Compile the optional pattern/regexp
    try:
        compiled_pattern = None
        if args.pattern:
            compiled_pattern = re.compile(fnmatch.translate(args.pattern))
        elif args.regexp:
            compiled_pattern = re.compile(args.regexp)
    except re.error:
        parser.error('Invalid pattern.')

    # Find files
    try:
        start_time = time.perf_counter()
        files = list(find_files(args.path, args.dotfiles, args.symlinks,
                                compiled_pattern, args.minsize, args.maxsize))
        elapsed_time = time.perf_counter() - start_time
    except OSError as e:
        print(f'Error reading {e.filename} ({e.strerror})', file=sys.stderr)
        return 1

    # Print results
    for filename in files:
        try:
            print(filename)
        except UnicodeError:
            print(f'Error reading {convert_filename(filename)} '
                  f'(contains unrecognizable characters)',
                  file=sys.stderr)

    if args.summary:
        print(f'\nFound {len(files):,} files in {elapsed_time:.04f} seconds.')

    return 0


if __name__ == '__main__':
    sys.exit(main())
