#!/usr/bin/env python
# Copyright (c) 2019-2022 Mike Cunningham
# https://github.com/emetophobe/fileutils


import os
import sys
import argparse
import time


def stat_dir(path, recursive=True, symlinks=True, dotfiles=False):
    """ Recursively yield file entries from the specified path. """
    try:
        scanit = os.scandir(os.path.abspath(path))  # Always use absolute paths
    except OSError as e:
        print(f'Error reading {e.filename} ({e.strerror})', flush=True, file=sys.stderr)
        return

    with scanit:
        while True:
            try:
                # Get the next DirEntry object
                entry = next(scanit)

                # Ignore dot files?
                if not dotfiles and entry.name.startswith('.'):
                    continue

                # Is it a symlink?
                try:
                    is_symlink = entry.is_symlink()
                except OSError:  # same behaviour as os.path.islink()
                    is_symlink = False

                if is_symlink and not symlinks:
                    continue

                # Is it a directory?
                try:
                    is_dir = entry.is_dir()
                except OSError:  # same behaviour as os.path.isdir()
                    is_dir = False

                # Recursively search subdirs for files
                if is_dir and recursive:
                    yield from stat_dir(entry.path, recursive, symlinks, dotfiles)

                # Yield every file entry that is found
                elif entry.is_file():
                    yield entry

            except OSError as e:
                print(f'Error reading {e.filename} ({e.strerror})', file=sys.stderr)
                continue

            except StopIteration:
                break


def file_stats(path, displayed_stats, symlinks=False, dotfiles=False):
    """ Generator which yields file paths and their stats. """
    def _stats_to_tuple(stat_result):
        return tuple(getattr(stat_result, st) for st in displayed_stats)

    if os.path.isdir(path):
        # Scan the entire directory tree
        for entry in stat_dir(path, symlinks=symlinks, dotfiles=dotfiles):
            yield (entry.path,) + _stats_to_tuple(entry.stat())
    elif os.path.isfile(path):
        # Stat a single file
        yield (os.path.abspath(path),) + _stats_to_tuple(os.stat(path))
    else:
        raise ValueError(f'Invalid path: {path}')


#
# _internal stuff used by argparse
#


# Default stats to display if none are specified
DEFAULT_STATS = (
    'st_mode',
    'st_ino',
    'st_dev',
    'st_nlink',
    'st_uid',
    'st_gid',
    'st_size',
    'st_atime',
    'st_mtime',
    'st_ctime'
)


# Dictionary of stats and their descriptions
ALL_STATS = {
    # Attributes available on all plaforms
    'st_mode': 'file type and file mode bits (permissions).',
    'st_ino': 'inode number on Unix or file index on Windows',
    'st_dev': 'identifier of the device',
    'st_nlink': 'number of hard links',
    'st_uid': 'user identifier of the file owner',
    'st_gid': 'group identifier of the file owner',
    'st_size': 'file size in bytes',
    'st_atime': 'last access time in seconds',
    'st_mtime': 'last modified time in seconds',
    'st_ctime': 'creation time in seconds',
    'st_atime_ns': 'last access time in nanoseconds',
    'st_mtime_ns': 'last modified time in nanoseconds',
    'st_ctime_ns': 'creation time in nanoseconds',

    # Unix-specific attributes
    'st_blocks': 'number of blocks allocated for the file',
    'st_blksize': 'prefered blocksize',
    'st_rdev': 'type of device if an inode device',
    'st_flags': 'user defined flags for the file',
    'st_gen': 'file generation number',
    'st_birthtime': 'time of file creation',

    # Solaris-specific attributes
    'st_fstype': 'filesystem type that contains the file',

    # MacOS-specific attributes
    'st_rsize': 'real size of the file',
    'st_creator': 'creator of the file',
    'st_type': 'file type',

    # Windows-specific attributes
    'st_file_attributes': 'windows file attributes',
    'st_reparse_tag': 'tag identifying the type of reparse point',
}


def _detect_attributes():
    """ Get dictionary of attributes supported by the current system. """
    test_stats = dir(os.stat(__file__))
    return {k: v for k, v in ALL_STATS.items() if k in test_stats}


# Store dictionary of supported attributes
SUPPORTED_ATTRIBUTES = _detect_attributes()


def _parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        'path',
        help='file or directory path',
    )

    parser.add_argument(
        '-d', '--dotfiles',
        help='show dot files and directories',
        action='store_true'
    )

    parser.add_argument(
        '-s', '--symlinks',
        help='follow symbolic links',
        action='store_true'
    )

    stats_group = parser.add_argument_group('file stats')

    stats_group.add_argument(
        '-a', '--attributes',
        help=f'select which stats to display (default: {", ".join(DEFAULT_STATS)})',
        nargs='+'
    )

    stats_group.add_argument(
        '--all',
        help='show all stats',
        action='store_true'
    )

    # Add the supported attributes
    for name, help_text in SUPPORTED_ATTRIBUTES.items():
        stats_group.add_argument(
            f'--{name.removeprefix("st_")}',  # use short form (i.e --dev instead of --st_dev)
            dest=name,
            help=help_text,
            action='store_true',
            default=argparse.SUPPRESS  # This preserves the order that the user specified
        )

    return (parser.parse_args(), parser)


def _build_from_attributes(attributes: list) -> tuple:
    tracked_stats = set()
    for attribute in attributes:
        attribute = attribute.rstrip(',')
        for st_key in SUPPORTED_ATTRIBUTES.keys():
            if attribute.removeprefix('st_') == st_key.removeprefix('st_'):
                if st_key in tracked_stats:
                    raise ValueError(f'Duplicate attribute: {attribute}')
                tracked_stats.add(st_key)
                break
        else:
            raise ValueError(f'Unsupported attribute: {attribute}')

    return tuple(tracked_stats)


def _build_from_args(args: dict) -> tuple:
    tracked_stats = [key for key in args.keys() if key.startswith('st_')]

    # Use defaults if none were specified
    if not tracked_stats:
        tracked_stats = DEFAULT_STATS

    return tuple(tracked_stats)


def main():
    args, parser = _parse_args()

    # Parse stats to display
    try:
        if args.all:
            displayed_stats = SUPPORTED_ATTRIBUTES.keys()
        elif args.attributes:
            displayed_stats = _build_from_attributes(args.attributes)
        else:
            displayed_stats = _build_from_args(vars(args))
    except ValueError as e:
        parser.error(e)

    try:
        # Get the list of file stats
        start_time = time.perf_counter()
        filestats = list(file_stats(args.path, displayed_stats, args.symlinks, args.dotfiles))
        elapsed_time = time.perf_counter() - start_time

        # Display the header
        print('path,', ', '.join(displayed_stats))

        # Print the paths and their stats
        for stats in filestats:
            print(', '.join([str(stat) for stat in stats]))

        files = 'file' if len(filestats) == 1 else 'files'
        print(f'\nFound {len(filestats):,} {files} in {elapsed_time:.04f} seconds.')

    except (ValueError, OSError) as e:
        print('Error:', e, file=sys.stderr)


if __name__ == '__main__':
    main()
