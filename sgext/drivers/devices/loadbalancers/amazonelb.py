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
    """Exception raised by AmazonELB instances when errors occur."""
    pass


class AmazonELB(BasicAppliance):
    """Driver for modeling and controlling Amazon Elastic Load
    Balancers."""
    _driver_name = 'amazonelb'

    def __init__(self, name, elbname, **kwargs):
        BasicAppliance.__init__(self, name, **kwargs)
        self.set_attr(key='elb', subkey='name', value=elbname)
        self.credentials = get_credentials()

    def _get_boto_connection(self):
        """Internal method. Returns the boto connection object for this ELB."""
        region = self.attr_value(key='ec2', subkey='region',
                                 merge_container_attrs=True)
        if region is None:
            raise SGELBException('Cannot find attribute with key="ec2", '
                                 'subkey="region" on AmazonELB object named '
                                 '"%s" or any of it\'s parents.' % self.name)
        conn = boto.ec2.elb.connect_to_region(region)
        if conn is None:
            raise SGELBException('Could not establish connection to region %s'
                                 % region)
        return conn

    def _get_boto_elb_object(self):
        """Internal method. Return the boto object for this ELB."""
        conn = self._get_boto_connection()
        lbs = conn.get_all_load_balancers(self.elb_name)
        if len(lbs) < 1:
            raise SGELBException('Could not find ELB named %s in AWS!'
                                 % self.elb_name)
        elif len(lbs) > 1:
            raise SGELBException('Found multiple ELBs named %s in AWS!'
                                 % self.elb_name)
        return lbs[0]

    @property
    def elb_name(self):
        return self.attr_value(key='elb', subkey='name')

    @property
    def hostname(self):
        return self._get_boto_elb_object().dns_name

    def enable_zone(self, name_or_entity):
        conn = self._get_boto_connection()

        if isinstance(name_or_entity, str):
            name = name_or_entity
        else:
            name = name_or_entity.name

            conn.enable_availability_zones(str(self.elb_name), [name])

    def disable_zone(self, name_or_entity):
        conn = self._get_boto_connection()

        if isinstance(name_or_entity, str):
            name = name_or_entity
        else:
            name = name_or_entity.name

        conn.disable_availability_zones(str(self.elb_name), [name])

    def get_state(self):
        conn = self._get_boto_connection()
        return conn.describe_instance_health(str(self.elb_name))
