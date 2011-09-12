#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# © 2011 SimpleGeo, Inc. All rights reserved.
# Author: Paul Lathrop <paul@simplegeo.com>
#

"""Command-line utility for controlling Amazon Elastic Load
Balancers."""

import os
import sys
from time import sleep, time

from clusto import script_helper
import clusto

from sgext.drivers import AmazonELB
from sgext.util.aws import get_credentials, has_aws_environment


class ELB(script_helper.Script):
    """
    Command-line utility for controlling Amazon Elastic Load
    Balancers.
    """

    _usage = """
             clusto-elb elbname action [options]
             clusto-elb list

             Command-line utility for controlling Amazon Elastic Load
             Balancers.

             Available actions for `clusto-elb elbname action`:
               status:  Print the status of the ELB and exit.
               enable:  Enable a given AZ in the ELB. Must specify --zone. If a
                        timeout is specified, the command will block until the
                        AZ is enabled (active in the ELB and all instances are
                        reported healthy) or until the timeout elapses. If
                        the timeout is 0, will block until the AZ is enabled or
                        the command is interrupted.
               disable: Disable a given AZ in the ELB. Must specify --zone. Same
                        timeout behavior as 'enable'.
               waitfor: Wait for an AZ to be enabled or disabled. Must specify
                        zone and --wait-condition. Same timeout behavior as
                        enable'.

            The alternate form `clusto-elb list` will list the available
            ELBs.
            """

    def _add_arguments(self, parser):
        parser.add_argument('elbname', help='The name of the ELB you wish to '
                            'control. Can be either the name of the object in '
                            'clusto or the AWS name.', nargs='?')
        parser.add_argument('action', help='Action you wish to perform on the '
                            'specified ELB.', nargs='?',
                            choices=['status', 'enable', 'disable', 'waitfor'])
        parser.add_argument('-z', '--zone', default=None, help='Availability '
                            'zone you wish to enable/disable.')
        parser.add_argument('-t', '--timeout', type=int, default=120,
                            help='Time (in seconds) to wait for a zone to '
                            'finish enabling/disabling before timing out.'
                            'Default is 2 minutes (120).')
        parser.add_argument('--danger-zone', action='store_true',
                            default=False, help='Skip verification of '
                            'actions. Only use this if you are sure you know '
                            'what you are doing.')
        parser.add_argument('--batch', action='store_true',
                            default=False, help='Do not request credentials '
                            'interactively if they cannot be loaded from the '
                            'environment.')
        parser.add_argument('--wait-condition', default=None,
                            choices=['enabled', 'disabled'],
                            help='State you wish the specified zone to be '
                            'in before the command returns.')
        parser.usage = self._usage

    def add_subparser(self, subparsers):
        parser = self._setup_subparser(subparsers)
        self._add_arguments(parser)

    def usage(self, elb, args):
        print 'Unknown action %s. Try %s --help!' % (args.action, sys.argv[0])

    def _find_elb(self, name):
        entities = clusto.get_entities(attrs=({'key': 'elb',
                                               'subkey': 'name',
                                               'value': name},))
        if len(entities) < 1:
            raise LookupError('No ELB named %s found!' % name)
        elif len(entities) > 1:
            raise LookupError('Multiple ELBs named %s found!' % name)
        return entities[0]

    def status(self, elb, args):
        sys.stdout.write('ELB: ')
        sys.stdout.write(elb.elb_name.ljust(12))
        sys.stdout.write('DNS Name: ')
        sys.stdout.write(elb.hostname.ljust(45))
        sys.stdout.write('Region: %s\n' % elb.region)
        sys.stdout.write('Active Availability Zones: %s\n\n'
                         % ', '.join(elb.availability_zones))
        sys.stdout.write('  Instance ID'.ljust(18))
        sys.stdout.write('Status\n')
        for instance_health in elb.instance_health():
            sys.stdout.write('   %s' % instance_health.instance_id.ljust(15))
            sys.stdout.write('%s\n' % instance_health.state)
        sys.stdout.flush()
        return 0

    def _enabled(self, zone, elb):
        def instance_enabled(instance_health):
            return instance_health.state == 'InService'
        zone_enabled = zone in elb.availability_zones
        instances_healthy = all(map(instance_enabled, elb.instance_health()))
        return zone_enabled and instances_healthy

    def _disabled(self, zone, elb):
        return zone not in elb.availability_zones

    def _await(self, function, args, timeout=120):
        if timeout != 0:
            start = int(time())
            while not function(*args):
                sleep(1)
                elapsed = int(time()) - start
                if timeout <= elapsed:
                    raise TimeoutException()
        else:
            while not function(*args):
                sleep(1)

    def _verify(self, action, elb, zone):
        prompt = 'Are you sure you want to %s %s for %s? [N/yes] '
        verify = raw_input(prompt % (action, zone, elb.elb_name))
        if str(verify) != 'yes':
            raise StandardError('You must type "yes" to confirm.')

    def enable(self, elb, args):
        if args.zone is None:
            raise StandardError('You must specify a zone to enable.')
        if not args.danger_zone:
            self._verify('enable', elb, args.zone)
        elb.enable_zone(args.zone)
        try:
            self._await(self._enabled, (args.zone, elb), args.timeout)
        except TimeoutException:
            raise TimeoutException('Timed out enabling %s' % args.zone)
        finally:
            print
            self.status(elb, args)
            print

    def disable(self, elb, args):
        if args.zone is None:
            raise StandardError('You must specify a zone to disable.')
        if not args.danger_zone:
            self._verify('disable', elb, args.zone)
        elb.disable_zone(args.zone)
        try:
            self._await(self._disabled, (args.zone, elb), args.timeout)
        except TimeoutException:
            raise TimeoutException('Timed out enabling %s' % args.zone)
        finally:
            print
            self.status(elb, args)
            print

    def waitfor(self, elb, args):
        if args.zone is None:
            raise StandardError('You must specify a zone to wait for.')
        if args.wait_condition is None:
            raise StandardError('You must specify a condition to wait for.')
        try:
            self._await(self.getattr('_%s' % args.wait_condition),
                        (args.zone, elb),
                        args.timeout)
        except TimeoutException:
            raise TimeoutException('Timed out waiting for %s to become %s' %
                                   args.zone, args.wait_condition)
        finally:
            print
            self.status(elb, args)
            print

    def list(self):
        entities = clusto.get_entities(clusto_types=[AmazonELB])
        if len(entities) < 1:
            print 'No ELB object found in Clusto.'
            print
            return 0
        else:
            sys.stdout.write('Name'.ljust(15))
            sys.stdout.write('Clusto Name\n')
            for entity in entities:
                sys.stdout.write(entity.elb_name.ljust(15))
                sys.stdout.write(entity.name)
                sys.stdout.write('\n')
                print

    def run(self, args):
        cred = get_credentials(args.batch)
        if (cred is not None) and (not has_aws_environment()):
            os.environ['AWS_ACCESS_KEY_ID'] = cred['aws_access_key_id']
            os.environ['AWS_SECRET_ACCESS_KEY'] = cred['aws_secret_access_key']
        elif (cred is None) and args.batch:
            raise StandardError('Could not load AWS credentials and batch '
                                'is enabled! Please set credentials in the '
                                'environment or the boto config in order to '
                                'use batch mode.')
        if args.elbname is None and args.action is None:
            print self._usage
            print
            print '%s: error: too few arguments' % sys.argv[0]
            return 1
        if args.elbname == 'list' and args.action is None:
            args.elbname = None
            return self.list()
        try:
            dispatch = getattr(self, args.action)
        except AttributeError:
            dispatch = self.usage
        try:
            elb = clusto.get_by_name(args.elbname)
            if not isinstance(elb, AmazonELB):
                raise LookupError
        except LookupError:
            elb = self._find_elb(args.elbname)
        result = dispatch(elb, args)
        return result


class TimeoutException(Exception):
    pass


def main():
    elb_control, args = script_helper.init_arguments(ELB)
    return elb_control.run(args)


if __name__ == '__main__':
    sys.exit(main())
