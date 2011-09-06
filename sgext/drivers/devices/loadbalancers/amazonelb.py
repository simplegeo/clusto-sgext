# -*- coding: utf-8 -*-
#
# © 2011 SimpleGeo, Inc. All rights reserved.
# Author: Jeremy Grosser <jeremy@simplegeo.com>
# Author: Paul Lathrop <paul@simplegeo.com>
#

"""Control the Amazon Elastic Load Balancer from Clusto."""

import boto.ec2.elb

from clusto.drivers.devices.appliance.basicappliance import BasicAppliance
from sgext.util import SGException
from sgext.util.aws import get_credentials


class SGELBException(SGException):
    pass


class AmazonELB(BasicAppliance):
    _driver_name = 'amazonelb'

    def __init__(self, name, elbname, **kwargs):
        BasicAppliance.__init__(self, name, **kwargs)
        self.set_attr(key='elb', subkey='name', value=elbname)
        self.credentials = get_credentials()

    def get_boto_connection(self):
        region = self.attr_value(key='ec2', subkey='region', merge_container_attrs=True)
        if region is None:
            raise SGELBException('Cannot find attribute with key="ec2", '
                                 'subkey="region" on AmazonELB object named '
                                 '"%s" or any of it\'s parents.' % self.name)
        conn = boto.ec2.elb.connect_to_region(region)
        if conn is None:
            raise SGELBException('Could not establish connection to region %s' % region)
        return conn

    def enable_zone(self, name_or_entity):
        conn = self.get_boto_connection()

        if isinstance(name_or_entity, str):
            name = name_or_entity
        else:
            name = name_or_entity.name

        conn.enable_availability_zones(self.attr_value(key='elb', subkey='name'), [name])

    def disable_zone(self, name_or_entity):
        conn = self.get_boto_connection()

        if isinstance(name_or_entity, str):
            name = name_or_entity
        else:
            name = name_or_entity.name

        conn.disable_availability_zones(self.attr_value(key='elb', subkey='name'), [name])

    def get_state(self):
        conn = self.get_boto_connection()
        return conn.describe_instance_health(self.attr_value(key='elb', subkey='name'))
