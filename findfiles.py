#!/usr/bin/env python
# Copyright (c) 2019-2023 Mike Cunningham
# https://github.com/emetophobe/fileutils


import os
import sys
import time
import argparse
import fnmatch
import re


def walk_tree(path, excludes=None, dotfiles=False, symlinks=False, recursive=True):
    """ Walk the directory path and yield file entries.

        Uses os.scandir() which is much faster than os.walk(), especially if you need
        to stat files (os.scandir() caches stat() results in each DirEntry object).
    """

    if not excludes:
        excludes = []

    with os.scandir(path) as scanit:
        while True:
            try:
                # Get the next DirEntry object
                entry = next(scanit)

                # Ignore dot files?
                if not dotfiles and entry.name.startswith('.'):
                    continue

                # Exclude entry?
                # TODO: use fnmatch?
                if entry.path in excludes or entry.name in excludes:
                    continue

                # Is it a directory?
                try:
                    is_dir = entry.is_dir(follow_symlinks=symlinks)
                except OSError:  # same behaviour as os.path.isdir()
                    is_dir = False

                # Recursively search subdirs for files
                if is_dir and recursive:
                    yield from walk_tree(entry.path, excludes, dotfiles, symlinks, recursive)

                # Yield file entries
                elif entry.is_file(follow_symlinks=symlinks):
                    yield entry

            except OSError as e:
                print(f'Error reading {e.filename} ({e.strerror})', file=sys.stderr)
                continue

            except StopIteration:
                break


def find_files(path, compiled_pattern=None, excludes=None, dotfiles=True,
               symlinks=False, minsize=None, maxsize=None):
    """ Find files matching the specified filters. """
    for entry in walk_tree(path, excludes=excludes, dotfiles=dotfiles,
                           symlinks=symlinks, recursive=True):
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


def print_unicode_error(filename, error):
    """ Print error message for filename with unrecognizable unicode characters. """
    bad_file = filename.encode('utf-8', 'replace').decode('utf-8')
    print(f'Error reading {bad_file} '
          f'(contains non-unicode characters)',
          file=sys.stderr)


def parse_args():
    desc = 'Find files using regular expressions or Unix-style wildcard pattern matching.'
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument(
        'path',
        help='top level directory',
        type=os.path.abspath)  # use absolute paths

    parser.add_argument(
        '-e', '--exclude',
        help='list of files or directories to exclude (default: None)',
        nargs='*',
    )

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
        help='show summary and elapsed time',
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

    args = parser.parse_args()

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
        args.compiled_pattern = None
        if args.pattern:
            args.compiled_pattern = re.compile(fnmatch.translate(args.pattern))
        elif args.regexp:
            args.compiled_pattern = re.compile(args.regexp)
    except re.error:
        parser.error('Invalid pattern.')

    return args


def main():
    args = parse_args()

    # Find files
    try:
        start_time = time.perf_counter()
        files = list(find_files(args.path,
                                compiled_pattern=args.compiled_pattern,
                                excludes=args.exclude,
                                dotfiles=args.dotfiles,
                                symlinks=args.symlinks,
                                minsize=args.minsize,
                                maxsize=args.maxsize))
        elapsed_time = time.perf_counter() - start_time
    except OSError as e:
        print(f'Error reading {e.filename} ({e.strerror})', file=sys.stderr)
        return 1

    # Print results
    for filename in files:
        try:
            print(filename)
        except UnicodeError as error:
            print_unicode_error(filename, error)

    if args.summary:
        print(f'\nFound {len(files):,} files in {elapsed_time:.04f} seconds.')

    return 0


if __name__ == '__main__':
    sys.exit(main())
