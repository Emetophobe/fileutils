#!/usr/bin/env python
# Copyright (c) 2019-2023 Mike Cunningham
# https://github.com/emetophobe/fileutils


import os
import sys
import argparse
import fnmatch
import re


def walk_tree(path, excludes=None, dotfiles=False, symlinks=False,
              recursive=True, onerror=None):
    """ Walk a directory tree and yield file entries.

    Uses os.scandir() which is 4-5x faster than os.walk().

    Entries are meant to be short lived and not stored in a data structure.
    If you need up to date file metadata call os.stat(entry.path)

    Args:
        path (str):
            Top level search directory.

        excludes (list[str], optional): Defaults to None.
            List of filenames or directories to exclude.

        dotfiles (bool, optional): Defaults to False.
            Include dotfiles and directories (paths that start with a ".")

        symlinks (bool, optional): Defaults to False.
            Follow symbolic links.

        recursive (bool, optional): Defaults to True
            Recursively search subdirectories.

        onerror (Callable, optional): Defaults to None.
            Specify a callback function for handling OSError exceptions.

    Raises:
        OSError: if path could not be read.

    Yields:
        os.DirEntry: a file entry with path and cached stat result.
    """

    if not excludes:
        excludes = []

    with os.scandir(path) as scanit:
        while True:
            # Fetch all entries
            try:
                entry: os.DirEntry = next(scanit)
            except StopIteration:
                break

            # Ignore dot files?
            if not dotfiles and entry.name.startswith('.'):
                continue

            # Exclude entry?
            # TODO: use fnmatch instead?
            if entry.path in excludes or entry.name in excludes:
                continue

            # Is it a directory?
            try:
                is_dir = entry.is_dir()
            except OSError:  # same behaviour as os.path.isdir()
                is_dir = False

            # Is it a symlink?
            try:
                is_symlink = entry.is_symlink()
            except OSError:  # same behaviour as os.path.isdir()
                is_symlink = False

            if is_symlink and not symlinks:
                continue

            try:
                # Recursively search subdirs for files
                if is_dir and recursive:
                    yield from walk_tree(entry.path, excludes, dotfiles,
                                         symlinks, recursive, onerror)
                # Yield file entries
                elif entry.is_file():
                    yield entry

            except OSError as e:
                if onerror:
                    onerror(e)


def find_files(path, compiled_pattern=None, excludes=None, minsize=None, maxsize=None,
               onerror=None, dotfiles=True, symlinks=False, recursive=True):
    """ Find files matching the search parameters.

    Exceptions are silently ignored unless an onerror callback is specified.

    Args:
        path (str | os.PathLike):
            Top level search directory.

        compiled_pattern (re.Pattern, optional): Defaults to None.
            Match files based on a compiled regular expression.

        excludes (list, optional): Defaults to None.
            List of files or directories to exclude.

        minsize (int, optional): Defaults to None.
            Minimum file size in bytes.

        maxsize (int, optional): Defaults to None.
            Maximum file size in bytes.

        onerror (Callable, optional): Defaults to None
            Callback function used to handle OSError exceptions.

        dotfiles (bool, optional): Defaults to True.
            Include dotfiles and directories.

        symlinks (bool, optional): Defaults to False.
            Follow symbolic links.

        recursive (bool, optional): Defaults to True
            Recursively search subdirectories.

    Yields:
        os.DirEntry: File entry with cached stat results.
    """
    for entry in walk_tree(path,
                           excludes=excludes,
                           dotfiles=dotfiles,
                           symlinks=symlinks,
                           onerror=onerror,
                           recursive=recursive):
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


def print_unicode_error(filename, _error):
    """ Print error message for filename with unrecognizable unicode characters. """
    bad_file = filename.encode('utf-8', 'replace').decode('utf-8')
    print(f'Error reading {bad_file} '
          f'(contains non-unicode characters)',
          file=sys.stderr)


def main():
    desc = 'Find files using regular expressions or wildcard pattern matching.'
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument(
        'path',
        help='top level directory',
        type=os.path.abspath)  # use absolute paths

    parser.add_argument(
        '-e', '--exclude',
        help='list of files or directories to exclude (default: None)',
        dest='excludes',
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

    pattern_group = parser.add_mutually_exclusive_group()

    pattern_group.add_argument(
        '-f', '--fnmatch',
        dest='pattern',
        help='unix-style filename pattern matching. '
        'Use double quotes for wildcards; i.e "*.py"',
        default=None)

    pattern_group.add_argument(
        '-r', '--regexp',
        help='match filenames with a regular expression',
        default=None)

    size_group = parser.add_argument_group('size options')

    size_group.add_argument(
        '-x', '--size',
        help='exact file size in bytes',
        dest='exactsize',
        type=int)

    size_group.add_argument(
        '-n', '--minsize',
        help='minimum file size in bytes',
        type=int)

    size_group.add_argument(
        '-m', '--maxsize',
        help='maximum file size in bytes',
        type=int)

    args = parser.parse_args()

    # Make sure the path is valid
    if not os.path.isdir(args.path):
        parser.error('Invalid search path. Must be a valid directory.')

    # Set exact size
    if args.exactsize:
        if args.minsize is not None or args.maxsize is not None:
            parser.error('Cannot use --size with --minsize/--maxsize')
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
        files = list(find_files(args.path,
                                compiled_pattern=compiled_pattern,
                                excludes=args.excludes,
                                dotfiles=args.dotfiles,
                                symlinks=args.symlinks,
                                minsize=args.minsize,
                                maxsize=args.maxsize))
    except OSError as e:
        print(f'Error reading {e.filename} ({e.strerror})', file=sys.stderr)
        return 1

    # Print results
    for filename in files:
        try:
            print(filename)
        except UnicodeError as error:
            print_unicode_error(filename, error)

    return 0


if __name__ == '__main__':
    sys.exit(main())
