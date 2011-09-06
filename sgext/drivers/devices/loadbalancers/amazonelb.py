# -*- coding: utf-8 -*-
#
# © 2011 SimpleGeo, Inc. All rights reserved.
# Author: Jeremy Grosser <jeremy@simplegeo.com>
# Author: Paul Lathrop <paul@simplegeo.com>
#

"""Control the Amazon Elastic Load Balancer from Clusto."""

import types

import boto.ec2.elb

from clusto.drivers.devices.appliance.basicappliance import BasicAppliance
import sgext.drivers
from sgext.util import SGException, get_names
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
        conn = boto.ec2.elb.connect_to_region(region, **self.credentials)
        if conn is None:
            raise SGELBException('Could not establish connection to region %s'
                                 % region)
        return conn

    def _get_boto_elb_object(self):
        """Internal method. Return the boto object for this ELB."""
        conn = self._get_boto_connection()
        lbs = conn.get_all_load_balancers(str(self.elb_name))
        if len(lbs) < 1:
            raise SGELBException('Could not find ELB named %s in AWS!'
                                 % self.elb_name)
        elif len(lbs) > 1:
            raise SGELBException('Found multiple ELBs named %s in AWS!'
                                 % self.elb_name)
        return lbs[0]

    def update_instances(self):
        """Fetch the registered instances for this ELB from the AWS
        API and insert them into the ELB object (if they exist as
        clusto objects)."""
        elb = self._get_boto_elb_object()
        elb_instances = [instance.id for instance in elb.instances]
        self_instances = self.contents()
        for instance in self_instances:
            if instance.name not in elb_instances:
                BasicAppliance.remove(self, instance)
        for instance_id in elb_instances:
            if instance_id not in [instance.name
                                   for instance in self_instances]:
                # Insert all already-registered instances into the ELB if
                # they exist as clusto objects already.
                try:
                    BasicAppliance.insert(self, get_by_name(instance_id))
                except LookupError:
                    pass

    def insert(self, instance):
        """Register instances for this ELB and add them as children in
        clusto."""
        BasicAppliance.insert(self, instance)
        if not isinstance(instance, sgext.drivers.SGServer):
            return
        elb = self._get_boto_elb_object()
        try:
            elb.register_instances(str(instance.name))
        except BotoServerError:
            BasicAppliance.remove(self, instance)
            raise SGELBException('Could not register instance %s for ELB %s'
                                 % (instance.name, self.elb_name))

    def remove(self, instances):
        """De-register instances for this ELB and remove them as
        children in clusto."""
        if not isinstance(instance, SGServer):
            BasicAppliance.remove(self, instance)
            return
        elb = self._get_boto_elb_object()
        try:
            elb.deregister_instances(str(instance.name))
        except BotoServerError:
            raise SGELBException('Could not deregister instance %s for ELB %s'
                                 % (instance.name, self.elb_name))
        BasicAppliance.remove(self, instance)

    @property
    def elb_name(self):
        """Return the aws name of this AmazonELB object."""
        return self.attr_value(key='elb', subkey='name')

    @property
    def hostname(self):
        """Return the public DNS for this ELB."""
        return self._get_boto_elb_object().dns_name

    @property
    def availability_zones(self):
        """Return the list of active availability zones for this ELB."""
        return self._get_boto_elb_object().availability_zones

    @property
    def listeners(self):
        """Return the list of active listeners for this ELB."""
        return self._get_boto_elb_object().listeners

    def enable_zones(self, names_or_entities):
        """Enable availability zones for this ELB."""
        if len(names_or_entities) < 1:
            raise ValueError('Must provide a non-empty name, object, or sequence.')
        elb = self._get_boto_elb_object()
        names = get_names(names_or_entities, exception_type=SGELBException,
                          message='Invalid object/string passed as availability zone')
        elb.enable_zones(names)

    def enable_zone(self, name_or_entity):
        """Enable an availability zone for this ELB."""
        self.enable_zones(name_or_entity)

    def disable_zones(self, names_or_entities):
        """Disable availability zones for this ELB."""
        if len(names_or_entities) < 1:
            raise ValueError('Must provide a non-empty name, object, or sequence.')
        elb = self._get_boto_elb_object()
        names = get_names(names_or_entities, exception_type=SGELBException,
                          message='Invalid object/string passed as availability zone')
        elb.disable_zones(names)

    def disable_zone(self, name_or_entity):
        """Disable an availability zone for this ELB."""
        self.disable_zones(name_or_entity)

    def instance_health(self, instances=None):
        if instances is not None:
            instances = get_names(instances, exception_type=SGELBException,
                                  message='Invalid object/string passed as instance')
        return self._get_boto_elb_object().get_instance_health(instances)

    def get_state(self):
        return self.instance_health()
