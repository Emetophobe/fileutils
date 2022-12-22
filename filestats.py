#!/usr/bin/env python
# Copyright (c) 2019-2022 Mike Cunningham
# https://github.com/emetophobe/fileutils


import os
import sys
import argparse


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


def walk_tree(path, symlinks=False, dotfiles=False, recursive=True):
    """ Recursively yield file entries from the specified path. """
    with os.scandir(path) as scanit:
        while True:
            try:
                # Get the next DirEntry object
                entry = next(scanit)

                # Ignore dot files?
                if not dotfiles and entry.name.startswith('.'):
                    continue

                # Is it a directory?
                try:
                    is_dir = entry.is_dir(follow_symlinks=symlinks)
                except OSError:  # same behaviour as os.path.isdir()
                    is_dir = False

                # Recursively search subdirs for files
                if is_dir and recursive:
                    yield from walk_tree(entry.path, symlinks, dotfiles, recursive)

                # Yield every file entry that is found
                elif entry.is_file(follow_symlinks=symlinks):
                    yield entry

            except OSError as e:
                print(f'Error reading {e.filename} ({e.strerror})', file=sys.stderr)
                continue

            except StopIteration:
                break


def stat_path(path, display_stats, symlinks=False, dotfiles=False):
    """ Yield file stats from the specified path. """
    def stats_to_tuple(stat_result):
        # Helper to convert a stat_result object into a tuple
        return tuple(getattr(stat_result, st) for st in display_stats)

    if os.path.isfile(path):
        yield (path,) + stats_to_tuple(os.stat(path))
    elif os.path.isdir(path):
        for entry in walk_tree(path, symlinks=symlinks, dotfiles=dotfiles, recursive=True):
            yield (entry.path,) + stats_to_tuple(entry.stat())
    else:
        raise ValueError('Invalid path')


class ArgumentBuilder:

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

    def __init__(self):
        # Get dictionary of stats supported by the current system
        self.supported_stats = self.get_supported_stats()

    def parse_args(self) -> argparse.Namespace:
        self.parser = argparse.ArgumentParser()

        self.parser.add_argument(
            'path',
            help='file or directory path',
            type=os.path.abspath,  # Use absolute paths
        )

        self.parser.add_argument(
            '-d', '--dotfiles',
            help='show dot files and directories',
            action='store_true'
        )

        self.parser.add_argument(
            '-l', '--symlinks',
            help='follow symbolic links',
            action='store_true'
        )

        self.stats_group = self.parser.add_argument_group('file stats')

        self.stats_group.add_argument(
            '-a', '--all',
            help='show all stats',
            action='store_true'
        )

        self.stats_group.add_argument(
            '-s', '--stats',
            help=f'select which stats to display (default: {", ".join(DEFAULT_STATS)})',
            nargs='+'
        )

        # Add all the supported stat arguments (--mtime, --size, etc..)
        for name, description in self.supported_stats.items():
            self.stats_group.add_argument(
                f'--{name.removeprefix("st_")}',  # use short form (i.e --dev instead of --st_dev)
                dest=name,
                help=description,
                action='store_true',
                default=argparse.SUPPRESS  # This preserves the order the user entered them
            )

        # Parse args and do basic validation
        self.args = self.parser.parse_args()

        # Make sure the path is valid
        if not os.path.exists(self.args.path):
            self.parser.error('Invalid path.')

        # Get display stats
        try:
            self._build_display_stats()
        except ValueError as e:
            self.parser.error(e)

        # All done, return the args namespace
        return self.args

    def get_supported_stats(self) -> dict:
        # Get dictionary of stats supported by the current system
        test_stats = dir(os.stat(__file__))
        return {k: v for k, v in self.ALL_STATS.items() if k in test_stats}

    def _build_display_stats(self) -> None:
        # Build tuple of display stats from user arguments
        if self.args.all:
            display_stats = self.supported_stats.keys()
        elif self.args.stats:
            display_stats = self._build_from_stats()
        else:
            display_stats = self._build_from_args()

        if not display_stats:
            display_stats = DEFAULT_STATS

        for stat in display_stats:
            if stat not in self.supported_stats.keys():
                raise ValueError(f'Unsupported stat: {stat}')

        self.args.display_stats = display_stats

    def _build_from_stats(self) -> tuple:
        # Build stats from --stats argument (i.e --stats size, mtime)
        unique_stats = set()
        for stat in self.args.stats:
            stat = stat.rstrip(',')
            for st_key in self.supported_stats.keys():
                if stat.removeprefix('st_') == st_key.removeprefix('st_'):
                    if st_key in unique_stats:
                        raise ValueError(f'Duplicate stat: {stat}')
                    # Make sure to add the full key name and not the short form
                    unique_stats.add(st_key)
                    break
            else:
                raise ValueError(f'Unsupported stat: {stat}')

        return tuple(unique_stats)

    def _build_from_args(self) -> tuple:
        # Build stats from individual arguments (i.e --size --mtime)
        args = vars(self.args)
        return tuple(key for key in args.keys() if key.startswith('st_'))


def main():
    args = ArgumentBuilder().parse_args()

    # Get file stats
    try:
        filestats = list(stat_path(args.path, args.display_stats, args.symlinks, args.dotfiles))
    except OSError as e:
        print(f'Error reading {e.filename} ({e.strerror})', file=sys.stderr)
        return 1

    if not filestats:
        print('Found 0 files in the specified path.', file=sys.stderr)
        return 1

    # Print results (TODO: write a nicer header)
    print('path,', ', '.join(args.display_stats))
    for stats in filestats:
        print(', '.join(str(s) for s in stats))

    return 0


if __name__ == '__main__':
    sys.exit(main())
