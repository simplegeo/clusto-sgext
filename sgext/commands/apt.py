# -*- coding: utf-8 -*-
#
# © 2011 SimpleGeo, Inc. All rights reserved.
# Author: Paul Lathrop <paul@simplegeo.com>
#

"""
Command-line utility for querying/manipulating apt repositories.
"""

import sys

import clusto
from clusto import script_helper

from sgext.drivers import Apt


class AptRepository(script_helper.Script):
    """
    Command-line utility for querying/manipulating apt repositories.
    """

    _usage = """
             clusto-apt [options] reponame[/dist[/package]] action
             clusto-apt <list>

             Command-line utility for querying/manipulating apt
             repositories.

             Available actions for `clusto-apt reponame action`:

               list: List the distributions available in the
                     specified repository.

             Available actions for `clusto-apt reponame/dist action`:

               list: List the packages available in the specified
                     dist, along with their version.

             Available actions for `clusto-apt reponame/dist/package
             action`:

               metadata: Print the package metadata for the specified
                         package.
               version:  Print the version string for the specified
                         package.

             The form `clusto-apt` (or `clusto-apt list`) will list
             the clusto IDs of known apt repositories.
             """

    def _add_arguments(self, parser):
        parser.add_argument('-d', '--dest', help='Destination dist. Required '
                            'when promoting a package, ignored otherwise.',
                            default=None)
        parser.add_argument('path', help='In the form: '
                            'reponame[/dist[/package]] - specifies the repo, '
                            'dist, or package you want to query/manipulate.',
                            nargs='?', default='list')
        parser.add_argument('action', help='The query or action you want to '
                            'invoke on the specified repository', nargs='?',
                            default='list')
        parser.usage = self._usage

    def add_subparser(self, subparsers):
        parser = self._setup_subparser(subparsers)
        self._add_arguments(parser)

    def list(self, args):
        if args.path is None or args.reponame is None:
            repos = clusto.get_entities(clusto_types=[Apt])
            print 'Repositories in Clusto:'
            for repo in repos:
                print repo.name.rjust(len(repo.name) + 2)
            return 0
        repo = clusto.get_by_name(args.reponame)
        if args.dist is None:
            print 'Dists in repository %s:' % repo.name
            for dist in repo.dists():
                print dist.rjust(len(dist) + 2)
            return 0
        elif args.package is None:
            pkg_versions = repo.package_versions(args.dist)
            pkg_name_width = len(max([name for (name, ver) in pkg_versions],
                                     key=len))
            pkg_name_width = max(['Package', pkg_name_width], key=len) + 4
            print 'Package'.ljust(pkg_name_width) + 'Version'
            for (name, ver) in pkg_versions:
                print name.ljust(pkg_name_width) + ver
        if args.action == 'version' or args.action == 'list':
            version = repo.package_version(args.package, args.dist)
            print args.package.ljust(len(args.package) + 4) + version

    def promote(self, args):
        repo = clusto.get_by_name(args.reponame)
        return repo.promote(args.package, args.dist, args.dest)

    def metadata(self, args):
        repo = clusto.get_by_name(args.reponame)
        print repo.package(args.package, args.dist)

    def parse_path(self, path):
        result = [None, None, None]
        if path is None:
            return result
        components = path.split('/')
        for idx in range(len(components)):
            result[idx] = components[idx]
        return result

    def run(self, args):
        if args.action == 'list':
            return self.list(args)
        elif args.action == 'metadata':
            return self.metadata(args)
        elif args.action == 'promote':
            if args.package is None:
                raise ValueError('Must specify a package to promote.')
            if args.dest is None:
                raise ValueError('Must specify a destination dist using'
                                 '-d or --dest.')
            return self.promote(args)
        return 0


def main():
    repo, args = script_helper.init_arguments(AptRepository)
    if args.path == 'list':
        args.path = None
        args.action = 'list'
    (args.reponame, args.dist, args.package) = repo.parse_path(args.path)
    return repo.run(args)


if __name__ == '__main__':
    sys.exit(main())
