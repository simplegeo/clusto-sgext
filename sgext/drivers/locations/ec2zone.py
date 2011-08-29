from clusto.drivers.categories.pool import Pool

class EC2Zone(Pool):
    _clusto_type = 'zone'
    _driver_name = 'ec2zone'

    def __init__(self, name_driver_entity, **kwargs):
        Pool.__init__(self, name_driver_entity, **kwargs)
        self.set_attr(key='ec2', subkey='zone', value=self.name)
