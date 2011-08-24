#!/usr/bin/env python
from clusto import script_helper
import clusto

import sgext
from sgext.drivers import EC2Zone

import csv
import sys

class EC2Report(script_helper.Script):
    def run(self, args):
        keys = args.keys.split(",")
        writer = csv.writer(sys.stdout)
        writer.writerow(['name', 'zone'] + keys)
        for entity in clusto.get_from_pools(args.pools):
            attrs = [entity.name, entity.parents(clusto_types=[EC2Zone])[0].name]
            for key in keys:
                k, sk = key.split('_', 1)
                attrs += [unicode(x).strip() for x in entity.attr_values(key=k, subkey=sk)]
            writer.writerow(attrs)

    def _add_arguments(self, parser):
        parser.add_argument("-k", "--keys", dest="keys", required=True, help="Comma-delimited list of keys to report on")
        parser.add_argument('pools', nargs='*')

    def add_subparser(self, subparsers):
        parser = self._setup_subparser(subparsers)
        self._add_arguments(parser)


def main():
    ec2report, args = script_helper.init_arguments(EC2Report)
    return ec2report.run(args)

if __name__ == '__main__':
    sys.exit(main())
