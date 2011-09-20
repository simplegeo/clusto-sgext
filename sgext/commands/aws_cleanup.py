#!/usr/bin/env python
from clusto import script_helper
import clusto

import simplejson as json
import httplib2
import sys


class AWSCleanup(script_helper.Script):
    def __init__(self):
        script_helper.Script.__init__(self)

    def run(self, args):
        servers = dict([(x.name, x) for x in clusto.get_entities(clusto_types=['server']) if x.name != 'default']) # Don't even consider the 'default' object.

        instances = []
        reasons = {}

        http = httplib2.Http()
        http.add_credentials(*os.environ['AMAZINGHORSE_CREDS'].split(':', 1))
        for region in ('us-east-1', 'us-west-1'):
            resp, content = http.request('https://amazinghorse.simplegeo.com:4430/aws/ec2/%s/instance/' % region)
            for instance in json.loads(content):
                if instance['state'] == 'running':
                    instances.append(instance['id'])
                else:
                    if 'reason' in instance:
                        reasons[instance['id']] = instance['reason']

        output = []
        for server in servers:
            if not server in instances:
                print 'Instance: %s' % server
                print 'IP: %s' % ' '.join(servers[server].attr_values(key='ip', subkey='ipstring'))
                print 'Parents: %s' % ' '.join([x.name for x in servers[server].parents()])
                if server in reasons:
                    print 'Termination reason: %s' % reasons[server]
                clusto.delete_entity(servers[server].entity)

def main():
    cmd, args = script_helper.init_arguments(AWSCleanup)
    return cmd.run(args)

if __name__ == '__main__':
    sys.exit(main())
