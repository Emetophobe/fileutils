#!/usr/bin/env python
# Copyright (c) 2019-2023 Mike Cunningham
# https://github.com/emetophobe/fileutils


import filecmp
import argparse


class DirCompare(filecmp.dircmp):
    """ Improved dircmp with nicer report(). """

    def report(self):
        """ Custom report method with nicer output. """
        self._print_files(f'Only in {self.left}', self.left_only)
        self._print_files(f'Only in {self.right}', self.right_only)
        self._print_files('Identical files', self.same_files)
        self._print_files('Differing files', self.diff_files)
        self._print_files('Trouble with common files', self.funny_files)
        self._print_files('Common subdirectories', self.common_dirs)
        self._print_files('Common funny cases', self.common_files)

    def _print_files(self, header, files):
        # Convenience method to print a header and a list of files
        if files:
            print(f'\n{header}:')
            for path in sorted(files):
                print(f'  {path}')


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
