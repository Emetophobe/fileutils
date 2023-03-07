#!/usr/bin/env python
# Copyright (c) 2019-2023 Mike Cunningham
# https://github.com/emetophobe/fileutils


import os
import sys
import argparse
from findfiles import walk_tree


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


def stat_path(path, dotfiles=True, recursive=True, symlinks=False):
    """ Stat a single file or an entire directory. Returns a generator.

    Args:
        path (str | Path): the file or directory path.
        dotfiles (bool): include dotfiles and directories. Defaults to True.
        recursive (bool): recursively search subdirectories. Defaults to True.
        symlinks (bool): follow symbolic links. Defaults to False.

    Raises:
        ValueError: if path is invalid.

    Returns:
        A generator which yields tuples of file paths and their stats.
    """
    if os.path.isdir(path):
        return stat_dir(path, dotfiles, recursive, symlinks)
    elif os.path.isfile(path):
        return stat_file(path)
    else:
        raise ValueError(f'Invalid path: {path}')


def stat_dir(path, dotfiles=True, recursive=True, symlinks=False):
    """ Walk the directory tree and yield tuples of files and their stats.

    Args:
        path (str | Path): the file or directory path.
        dotfiles (bool): include dotfiles and directories. Defaults to True.
        recursive (bool): recursively search subdirectories. Defaults to True.
        symlinks (bool): follow symbolic links. Defaults to False.

    Raises:
        ValueError: if path is invalid.

    Yields:
        tuple: a 2-tuple of file paths and their stat results.
    """
    for entry in walk_tree(path, symlinks=symlinks, dotfiles=dotfiles,
                           recursive=recursive):
        yield entry.path, entry.stat()


def stat_file(path):
    """ Yield a tuple of the file path and its stat results.

    Args:
        path (str | Path): the file or directory path.

    Yields:
        tuple: a 2-tuple of the file path and its stat results.
    """
    yield path, os.stat(path)


def _detect_stats():
    """ Get dictionary of stats supported by the current system. """
    all_stats = {
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

    stats = dir(os.stat(__file__))
    return {k: v for k, v in all_stats.items() if k in stats}


# Store dictionary of stats supported by the current system
SUPPORTED_STATS = _detect_stats()


def _parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        'path',
        help='file or directory path',
        type=os.path.abspath  # use absolute paths
    )

    parser.add_argument(
        '-d', '--dotfiles',
        help='show dot files and directories',
        action='store_true'
    )

    parser.add_argument(
        '-l', '--symlinks',
        help='follow symbolic links',
        action='store_true'
    )

    stats_group = parser.add_argument_group('file stats')

    stats_group.add_argument(
        '-s', '--stats',
        help=f'select stats to display (default: {", ".join(DEFAULT_STATS)})',
        nargs='+'
    )

    stats_group.add_argument(
        '--all',
        help='show all stats',
        action='store_true'
    )

    # Create arguments for the supported stats
    for name, desc in SUPPORTED_STATS.items():
        stats_group.add_argument(
            f'--{name.removeprefix("st_")}',
            dest=name,
            help=desc,
            action='store_true',
            default=argparse.SUPPRESS  # This preserves order of stat arguments
        )

    return parser, parser.parse_args()


def _build_from_stats(stats):
    # Build stats from --stats arguments (i.e --stats size, mtime)
    unique_stats = set()
    for statname in stats:
        statname = statname.rstrip(',')
        for st_key in SUPPORTED_STATS.keys():
            if statname.removeprefix('st_') == st_key.removeprefix('st_'):
                if st_key in unique_stats:
                    raise ValueError(f'Duplicate stat: {statname}')
                unique_stats.add(st_key)
                break
        else:
            raise ValueError(f'Unsupported stat: {statname}')

    return tuple(unique_stats)


def _build_from_args(args):
    # Build stats from individual arguments (i.e --size --mtime)
    return tuple(key for key in args.keys() if key.startswith('st_'))


def main():
    parser, args = _parse_args()

    # Parse list of stats to display
    try:
        if args.all:
            display_stats = SUPPORTED_STATS.keys()
        elif args.stats:
            display_stats = _build_from_stats(args.stats)
        else:
            display_stats = _build_from_args(vars(args))
    except ValueError as e:
        parser.error(e)

    if not display_stats:
        display_stats = DEFAULT_STATS

    # Get file stats
    try:
        filestats = list(stat_path(args.path,
                                   dotfiles=args.dotfiles,
                                   symlinks=args.symlinks,
                                   recursive=True))
    except (ValueError, OSError) as e:
        sys.exit(f'Error: {e}')

    if not filestats:
        sys.exit('Error: Found 0 files in the specified path.')

    # Print header (TODO: write a nicer header)
    print('path,', ', '.join(display_stats))

    # Print file stats
    for path, stats in filestats:
        formatted = tuple(str(getattr(stats, st)) for st in display_stats)
        print(f'{path},', ', '.join(formatted))


if __name__ == '__main__':
    main()
