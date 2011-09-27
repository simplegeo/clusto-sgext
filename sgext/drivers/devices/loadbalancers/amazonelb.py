# -*- coding: utf-8 -*-
#
# © 2011 SimpleGeo, Inc. All rights reserved.
# Author: Jeremy Grosser <jeremy@simplegeo.com>
# Author: Paul Lathrop <paul@simplegeo.com>
#

"""
Control the Amazon Elastic Load Balancer from Clusto.
"""

import boto.ec2.elb
from boto.exception import BotoServerError
import clusto
from clusto.drivers.devices.appliance.basicappliance import BasicAppliance

import sgext.drivers
from sgext.util.connections import backoff, retry
from sgext.util import SGException, get_names


class SGELBException(SGException):
    """
    Exception raised by AmazonELB instances when errors occur.
    """
    pass


class AmazonELB(BasicAppliance):
    """
    Driver for modeling and controlling Amazon Elastic Load
    Balancers.
    """
    _driver_name = 'amazonelb'

    def __init__(self, name, elbname, **kwargs):
        BasicAppliance.__init__(self, name, **kwargs)
        self.set_attr(key='elb', subkey='name', value=elbname)

    def _get_boto_connection(self):
        """
        Internal method. Returns the boto connection object for this ELB.
        """
        region = self.region
        if region is None:
            raise SGELBException('Cannot find attribute with key="ec2", '
                                 'subkey="region" on AmazonELB object named '
                                 '"%s" or any of it\'s parents.' % self.name)
        conn = boto.ec2.elb.connect_to_region(region)
        if conn is None:
            raise SGELBException('Could not establish connection to region %s'
                                 % region)
        return conn

    @retry(max_=-1, exceptions=BotoServerError)
    @backoff(exceptions=BotoServerError)
    def _get_boto_elb_object(self):
        """
        Internal method. Return the boto object for this ELB.
        """
        conn = self._get_boto_connection()
        lbs = conn.get_all_load_balancers(str(self.elb_name))
        if len(lbs) < 1:
            raise SGELBException('Could not find ELB named %s in AWS!'
                                 % self.elb_name)
        elif len(lbs) > 1:
            raise SGELBException('Found multiple ELBs named %s in AWS!'
                                 % self.elb_name)
        return lbs[0]

    @property
    def region(self):
        return self.attr_value(key='ec2', subkey='region',
                               merge_container_attrs=True)

    @property
    def elb_name(self):
        """
        Return the aws name of this AmazonELB object.
        """
        return self.attr_value(key='elb', subkey='name')

    @property
    def hostname(self):
        """
        Return the public DNS for this ELB.
        """
        return self._get_boto_elb_object().dns_name

    @property
    def availability_zones(self):
        """
        Return the list of active availability zones for this ELB.
        """
        return self._get_boto_elb_object().availability_zones

    @property
    def listeners(self):
        """
        Return the list of active listeners for this ELB.
        """
        return self._get_boto_elb_object().listeners

    @retry(max_=-1, exceptions=BotoServerError)
    @backoff(exceptions=BotoServerError)
    def enable_zones(self, names_or_entities):
        """
        Enable availability zones for this ELB.
        """
        if len(names_or_entities) < 1:
            raise ValueError('Must provide a non-empty name, object, or '
                             'sequence.')
        elb = self._get_boto_elb_object()
        names = get_names(names_or_entities, exception_type=SGELBException,
                          message='Invalid object/string passed as '
                          'availability zone')
        elb.enable_zones(names)

    def enable_zone(self, name_or_entity):
        """
        Enable an availability zone for this ELB.
        """
        self.enable_zones(name_or_entity)

    @retry(max_=-1, exceptions=BotoServerError)
    @backoff(exceptions=BotoServerError)
    def disable_zones(self, names_or_entities):
        """
        Disable availability zones for this ELB.
        """
        if len(names_or_entities) < 1:
            raise ValueError('Must provide a non-empty name, object, or '
                             'sequence.')
        elb = self._get_boto_elb_object()
        names = get_names(names_or_entities, exception_type=SGELBException,
                          message='Invalid object/string passed as '
                          'availability zone')
        elb.disable_zones(names)

    def disable_zone(self, name_or_entity):
        """
        Disable an availability zone for this ELB.
        """
        self.disable_zones(name_or_entity)

    @retry(max_=-1, exceptions=BotoServerError)
    @backoff(exceptions=BotoServerError)
    def instance_health(self, instances=None):
        """
        Return the instance health for the specified instances in
        this ELB (or all instances if none are specified.)
        """
        if instances is not None:
            instances = get_names(instances, exception_type=SGELBException,
                                  message='Invalid object/string passed '
                                  'as instance')
        return self._get_boto_elb_object().get_instance_health(instances)
