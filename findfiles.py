#!/usr/bin/env python
# Copyright (c) 2019-2022 Mike Cunningham
# https://github.com/emetophobe/fileutils


import os
import sys
import time
import argparse
import fnmatch
import re


EXCLUDE_DIRS = ['$RECYCLE.BIN', 'System Volume Information']


def find_files(path, dotfiles=True, symlinks=False, compiled_re=None, minsize=None, maxsize=None):
    """ Yield all file entries in the given path. Also recursively searches subdirectories. """
    filter_size = minsize is not None or maxsize is not None
    with os.scandir(os.path.abspath(path)) as scanit:
        while True:
            try:
                entry = next(scanit)
            except StopIteration:
                break

            try:
                if entry.name.startswith('.') and not dotfiles:
                    continue

                elif entry.is_dir(follow_symlinks=symlinks):
                    # Recursively search subdirectories
                    yield from find_files(entry.path, dotfiles, symlinks,
                                          compiled_re, minsize, maxsize)

                elif entry.is_file(follow_symlinks=symlinks):
                    # Pattern matching
                    if compiled_re and not compiled_re.search(entry.path):
                        continue

                    # Size matching
                    if filter_size:
                        size = entry.stat().st_size
                        if minsize is not None and minsize > size:
                            continue
                        elif maxsize is not None and maxsize < size:
                            continue

                    # Made it past the filters, yield the file path
                    yield entry.path

            except OSError as e:
                print(f'Error reading {path} ({e.strerror})', file=sys.stderr)


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        'path',
        help='the top level search directory')

    parser.add_argument(
        '-d', '--dotfiles',
        help='Show dot files (default: False)',
        action='store_true')

    parser.add_argument(
        '-l', '--symlinks',
        help='Follow symbolic links (default: False)',
        action='store_true')

    parser.add_argument(
        '--summary',
        help='Show file count and scan duration',
        action='store_true'
    )

    pattern_group = parser.add_mutually_exclusive_group()

    pattern_group.add_argument(
        '-f', '--fnmatch',
        dest='pattern',
        help='Unix-style filename pattern matching. '
        '(Quotes are required for wildcards; i.e "*.py")',
        default=None)

    pattern_group.add_argument(
        '-r', '--regexp',
        help='Match filenames with a regular expression',
        default=None)

    size_group = parser.add_argument_group('size options')

    size_group.add_argument(
        '-x', '--size',
        help='Limit files to an exact size (in bytes)',
        dest='exactsize',
        type=int)

    size_group.add_argument(
        '-n', '--minsize',
        help='Set a minimum file size (in bytes)',
        type=int)

    size_group.add_argument(
        '-m', '--maxsize',
        help='Set a maximum file size (in bytes)',
        type=int)

    return (parser.parse_args(), parser)


def main():
    args, parser = parse_args()

    if not os.path.isdir(args.path):
        parser.error('Invalid search directory')

    if args.exactsize is not None and (args.minsize is not None or args.maxsize is not None):
        parser.error('cannot use --size with --minsize/--maxsize')

    if args.exactsize:
        args.minsize = args.maxsize = args.exactsize

    # Compile the optional pattern/regexp
    try:
        if args.pattern:
            compiled_pattern = re.compile(fnmatch.translate(args.pattern))
        elif args.regexp:
            compiled_pattern = re.compile(args.regexp)
        else:
            compiled_pattern = None
    except re.error:
        parser.error('Invalid pattern.')

    # Find files
    try:
        start_time = time.perf_counter()
        files = list(find_files(args.path, args.dotfiles, args.symlinks,
                                compiled_pattern, args.minsize, args.maxsize))
        elapsed_time = time.perf_counter() - start_time
    except OSError as e:
        print(f'Error reading {e.filename} ({e.strerror})')
        return 0

    # Print results
    for filename in files:
        try:
            print(filename)
        except UnicodeError as e:
            print('Error reading filename with unicode characters:', e)

    if args.summary:
        print(f'\nFound {len(files):,} files in {elapsed_time:.04f} seconds.')

    return 1


if __name__ == '__main__':
    sys.exit(main())
