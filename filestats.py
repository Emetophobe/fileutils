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


def stat_path(path, symlinks, dotfiles, recursive):
    """ Stat a single file or an entire directory tree. """
    if os.path.isdir(path):
        return stat_dir(path, symlinks, dotfiles, recursive)
    elif os.path.isfile(path):
        return stat_file(path)
    else:
        raise ValueError(f'Invalid path: {path}')


def stat_dir(path, symlinks, dotfiles, recursive):
    """ Walk the directory tree and yield tuples of files and their stats. """
    for entry in walk_tree(os.path.abspath(path), symlinks=symlinks,
                           dotfiles=dotfiles, recursive=recursive):
        yield (entry.path, entry.stat())


def stat_file(path):
    """ Yield a single file and its stats """
    yield (os.path.abspath(path), os.stat(path))


# Internal dictionary of stats and their descriptions
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


def _detect_stats():
    """ Get dictionary of stats supported by the current system. """
    test_stats = dir(os.stat(__file__))
    return {k: v for k, v in ALL_STATS.items() if k in test_stats}


# Store dictionary of supported stats
SUPPORTED_STATS = _detect_stats()


def parse_args():
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

    # Create argument for each supported stat
    for name, desc in SUPPORTED_STATS.items():
        stats_group.add_argument(
            f'--{name.removeprefix("st_")}',  # use short form (i.e --dev instead of --st_dev)
            dest=name,
            help=desc,
            action='store_true',
            default=argparse.SUPPRESS  # This preserves the order that the user specified
        )

    return parser, parser.parse_args()


def _build_from_stats(stats: list) -> tuple:
    # Build stats from --stats arguments (i.e --stats size, mtime)
    unique_stats = set()
    for stat in stats:
        stat = stat.rstrip(',')
        for st_key in SUPPORTED_STATS.keys():
            if stat.removeprefix('st_') == st_key.removeprefix('st_'):
                if st_key in unique_stats:
                    raise ValueError(f'Duplicate stat: {stat}')
                # Make sure to add the full keyname and not the short form
                unique_stats.add(st_key)
                break
        else:
            raise ValueError(f'Unsupported stat: {stat}')

    return tuple(unique_stats)


def _build_from_args(args: dict) -> tuple:
    # Build stats from individual arguments (i.e --size --mtime)
    return tuple(key for key in args.keys() if key.startswith('st_'))


def _format_stats(stat_result, display_stats):
    # Convert a stat_result object into a tuple for display
    return tuple(str(getattr(stat_result, st)) for st in display_stats)


def main():
    parser, args = parse_args()

    # Parse stats to display
    try:
        if args.all:
            display_stats = SUPPORTED_STATS.keys()
        elif args.stats:
            display_stats = _build_from_stats(args.stats)
        else:
            display_stats = _build_from_args(vars(args))
    except ValueError as e:
        parser.error(e)

    # Use defaults stats if none were specified
    if not display_stats:
        display_stats = DEFAULT_STATS

    # Get file stats
    try:
        filestats = list(stat_path(args.path, args.symlinks, args.dotfiles, recursive=True))
    except (ValueError, OSError) as e:
        sys.exit('Error:', e)

    if not filestats:
        sys.exit('Error: Found 0 files in the specified path.')

    # Print results
    # TODO: make a nicer header
    print('path,', ', '.join(display_stats))
    for path, stats in filestats:
        try:
            print(f'{path},', ', '.join(_format_stats(stats, display_stats)))
        except UnicodeError:
            bad_file = path.encode('utf-8', 'replace').decode('utf-8')
            print(f'Error reading {bad_file} '
                  f'(contains non-unicode characters)',
                  file=sys.stderr)


if __name__ == '__main__':
    main()
