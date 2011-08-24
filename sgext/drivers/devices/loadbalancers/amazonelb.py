from clusto.drivers.devices.appliance.basicappliance import BasicAppliance
import boto.ec2.elb

class AmazonELB(BasicAppliance):
    _driver_name = 'amazonelb'

    def __init__(self, name, elbname, **kwargs):
        BasicAppliance.__init__(self, name, **kwargs)
        self.set_attr(key='elb', subkey='name', value='elbname')

    def get_boto_connection(self):
        region = self.attr_value(key='ec2', subkey='region', merge_container_attrs=True)
        return boto.ec2.elb.connect_to_region(region)

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
