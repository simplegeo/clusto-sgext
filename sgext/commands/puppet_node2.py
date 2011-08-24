#!/usr/bin/env python
from clusto import script_helper
import clusto
import yaml
import sys

import sgext

class PuppetNode2(script_helper.Script):
    def lookup(self, name):
        try:
            server = clusto.get_by_name(name)
            return server
        except LookupError:
            try:
                server = clusto.get_by_name(name.split('.', 1)[0])
                return server
            except LookupError:
                return False

    def run(self, args):
        server = self.lookup(args.hostname)
        if not server:
            server = self.lookup('default')
        if not server:
            return -1

        result = {
            'classes': [],
            'parameters': {},
        }

        disabled = False

        for attr in server.attrs(merge_container_attrs=True):
            key = str(attr.key)
            subkey = (attr.subkey != None) and str(attr.subkey) or None

            if isinstance(attr.value, int):
                value = int(attr.value)
            else:
                value = str(attr.value)

            if subkey == 'disabled' and value:
                disabled = True
                break

            if key == 'puppet':
                if subkey == 'environment' and not 'environment' in result:
                    result['environment'] = value

                if subkey == 'class':
                    if value not in result['classes']:
                        result['classes'].append(value)
                    continue

                if subkey not in result['parameters']:
                    result['parameters'][subkey] = value

                continue

            paramname = '%s__%s' % ('clusto', key)
            if subkey:
                paramname = paramname + '__' + subkey

            if paramname not in result['parameters']:
                result['parameters'][paramname] = value

        result['parameters']['pools'] = [str(p.name) for p in server.parents(clusto_types=['pool'])]
    
        clusters = [p for p in server.parents(clusto_types=['pool']) if p.attr_values('pooltype', value='cluster')]

        peers = {}
        for c in clusters:
            servers = c.contents(search_children=True, clusto_types=['server', 'virtualserver'])

            for server in servers:
                if server not in peers:
                    ips = server.get_ips()
                    if ips:
                        peers[str(ips[0])] = [str(x.name) for x in server.parents()]

        result['parameters']['peers'] = peers
        result['parameters']['siblings'] = [str(sib.attr_value(key='ec2', subkey='public-dns')) for sib in server.siblings()]

        if disabled:
            result['classes'] = []
            result['parameters'] = {}

        if not [x for x in result.values() if x]:
            return -1

        yaml.dump(result, sys.stdout, default_flow_style=False, explicit_start=True, indent=2)

    def _add_arguments(self, parser):
        parser.add_argument('hostname')

    def add_subparser(self, subparsers):
        parser = self._setup_subparser(subparsers)
        self._add_arguments(parser)


def main():
    puppet_node2, args = script_helper.init_arguments(PuppetNode2)
    return puppet_node2.run(args)

if __name__ == '__main__':
    sys.exit(main())
