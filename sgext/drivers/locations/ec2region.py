from clusto.drivers.locations.datacenters.basicdatacenter import BasicDatacenter

class EC2Region(BasicDatacenter):
    _driver_name = 'ec2region'

    def __init__(self, name_driver_entity, **kwargs):
        BasicDatacenter.__init__(self, name_driver_entity, **kwargs)
        self.set_attr(key='ec2', subkey='region', value=self.name)
