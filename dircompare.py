#!/usr/bin/env python
# Copyright (c) 2019-2023 Mike Cunningham
# https://github.com/emetophobe/fileutils


import filecmp
import argparse


class DirCompare(filecmp.dircmp):
    """ Improved dircmp with nicer report(). """

    def report(self):
        if self.left_only:
            print('\nOnly in', self.left, ':')
            self._print_files(self.left_only)

        if self.right_only:
            print('\nOnly in', self.right, ':')
            self._print_files(self.right_only)

        if self.same_files:
            print('Identical files:')
            self._print_files(self.same_files)

        if self.diff_files:
            print('Differing files:')
            self._print_files(self.diff_files)

        if self.funny_files:
            print('Trouble with common files:')
            self._print_files(self.funny_files)

        if self.common_dirs:
            print('Common subdirectories:')
            self._print_files(self.common_dirs)

        if self.common_funny:
            print('Common funny cases:')
            self.print_files(self.common_funny)

    def _print_files(self, files, indent='  '):
        """ Convenience method to print a list of files. """
        files.sort()
        for line in files:
            print(indent, line)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('left', help='left directory')
    parser.add_argument('right', help='right directory')

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '-p', '--partial',
        help='Print report on self and immediate subdirs',
        action='store_true'
    )

    group.add_argument(
        '-f', '--full',
        help='Print report on self and all subdirs recursively',
        action='store_true'
    )

    args = parser.parse_args()

    dc = DirCompare(args.left, args.right)
    if args.partial:
        dc.report_partial_closure()
    elif args.full:
        dc.report_full_closure()
    else:
        dc.report()
