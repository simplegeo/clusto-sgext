#!/usr/bin/env python
from clusto import script_helper
import clusto

import simplejson as json
import bottle
import sys
import os


@bottle.get('/attributes/:name.json')
def get_attributes(name):
    obj = clusto.get_by_name(name)
    results = {}
    for attr in obj.attrs(merge_container_attrs=True):
        if not attr.key in results:
            results[attr.key] = {}
        if attr.subkey in results[attr.key]:
            results[attr.key][attr.subkey] = [results[attr.subkey]]
            results[attr.key][attr.subkey].append(attr.value)
        else:
            results[attr.key][attr.subkey] = attr.value
    print results

    bottle.response.content_type = 'application/json'
    return json.dumps(results, indent=2, sort_keys=True)


class Chefd(script_helper.Script):
    def __init__(self):
        script_helper.Script.__init__(self)

    def run(self, args):
        bottle.debug(True)
        bottle.run(port=9997)

def main():
    cmd, args = script_helper.init_arguments(Chefd)
    return cmd.run(args)

if __name__ == '__main__':
    sys.exit(main())
