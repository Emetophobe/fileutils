#!/usr/bin/env python
# Copyright (c) 2019-2023 Mike Cunningham
# https://github.com/emetophobe/fileutils


import os
import argparse


def get_files(path, excludes=None):
    """ Get files in the given directory path. Yields relative file paths. """
    excludes = excludes or []
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in excludes]

        for filename in files:
            yield os.path.relpath(os.path.join(root, filename), path)


def compare_dirs(left, right, excludes=None):
    left = os.path.abspath(left)
    right = os.path.abspath(right)

    left_files = list(get_files(left, excludes))
    right_files = list(get_files(right, excludes))

    shared_files = [f for f in left_files if f in right_files]
    left_only = [f for f in left_files if f not in shared_files]
    right_only = [f for f in right_files if f not in shared_files]

    print('{:,} shared files'.format(len(shared_files)))
    print_files('=', shared_files)

    print('{:,} files unique to {}'.format(len(left_only), left))
    print_files('>', left_only)

    print('{:,} files unique to {}'.format(len(right_only), right))
    print_files('<', right_only)


def print_files(direction, files):
    if len(files) > 0:
        for filename in files:
            print(direction, filename)
    print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('left', help='left directory')
    parser.add_argument('right', help='right directory')
    parser.add_argument('-e', '--excludes', help='list of paths to exclude (wildcards are allowed)', nargs='*')
    args = parser.parse_args()

    if not os.path.isdir(args.left):
        parser.error(f'Invalid directory: {args.left}')
    elif not os.path.isdir(args.right):
        parser.error(f'Invalid directory: {args.right}')
    elif os.path.abspath(args.left) == os.path.abspath(args.right):
        parser.error('Two different directory paths are required.')

    try:
        compare_dirs(args.left, args.right, args.excludes)
    except OSError as e:
        print('Error reading file {} ({})'.format(e.filename, e.strerror))
