from clusto.drivers import Driver

class EC2Zone(Driver):
    _clusto_type = 'zone'
    _driver_name = 'ec2zone'

    def __init__(self, name_driver_entity, **kwargs):
        Driver.__init__(self, name_driver_entity, **kwargs)
        self.set_attr(key='ec2', subkey='zone', value=self.name)
