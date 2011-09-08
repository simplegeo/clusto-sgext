#!/usr/bin/python2.6
from eventlet.queue import LifoQueue as Queue
import eventlet
eventlet.monkey_patch()

from clusto import script_helper
from sgext.drivers import SGServer, EC2Zone
from clusto.drivers import Pool
from clusto.services.config import conf, get_logger
import clusto
import sgext

import kombu

from traceback import format_exc
from time import sleep, time
import logging
import sys

QUEUE_HOSTS = conf('barker.hosts')
QUEUE_EXCHANGE = conf('barker.exchange')
QUEUE_NAME = conf('barker.queue')
QUEUE_VHOST = conf('barker.vhost')
QUEUE_USER = conf('barker.user')
QUEUE_PASSWORD = conf('barker.password')

EC2_SUBKEYS = {
    'ami-id': 'ami',
    'kernel-id': 'kernel',
    'instance-type': 'type',
    'local-hostname': 'private-dns',
    'public-hostname': 'public-dns',
}

log = get_logger('clusto.barker', level='DEBUG')

def barker_callback(body):
    if not 'ec2' in body:
        return
    if not 'instance-id' in body['ec2']:
        return
    ec2 = body['ec2']
    log.debug(ec2['instance-id'])

    try:
        clusto.begin_transaction()
        server = clusto.get_or_create(ec2['instance-id'], SGServer)

        if not server.attr_values(key='ec2', subkey='instance-id'):
            server.set_attr(key='ec2', subkey='instance-id', value=ec2['instance-id'])

        zone = clusto.get(ec2['placement'])
        if not zone:
            zone = EC2Zone(ec2['placement'])
        else:
            zone = zone[0]
        if not server in zone:
            zone.insert(server)

        for key, subkey in EC2_SUBKEYS.items():
            server.set_attr(key='ec2', subkey=subkey, value=ec2[key])

        previous_ec2sg = server.attr_values(key='ec2',subkey='security-group')
        for group in set(previous_ec2sg).difference(set(ec2['security-groups'])):
            server.del_attrs(key='ec2',subkey='security-group', value=group)

        for i,group in enumerate(sorted(ec2['security-groups'])):
            server.set_attr(key='ec2', subkey='security-group', number=i, value=group)
            if group.find('_') != -1:
                environment, role = group.lower().split('_', 1)
                p = clusto.get_or_create(environment, Pool)
                if not p.attrs(key='pooltype', value='environment'):
                    p.set_attr(key='pooltype', value='environment')
                if not server in p:
                    p.insert(server)
                p = clusto.get_or_create(role, Pool)
                if not p.attrs(key='pooltype', value='role'):
                    p.set_attr(key='pooltype', value='role')
                if not server in p:
                    p.insert(server)

        #server.bind_ip_to_osport(ec2['local-ipv4'], 'nic-eth', 0)
        #server.bind_ip_to_osport(ec2['public-ipv4'], 'nic-eth', 0)
        if len(server.attrs(key='ip', subkey='ipstring')) != 2:
            server.del_attrs(key='ip', subkey='ipstring')
            server.add_attr(key='ip', subkey='ipstring', value=ec2['local-ipv4'], number=0)
            server.add_attr(key='ip', subkey='ipstring', value=ec2['public-ipv4'], number=0)

        system = body['os']
        server.set_attr(key='system', subkey='memory',
                        value=int(system['memory']['MemTotal']) / 1024)
        server.set_attr(key='system', subkey='hostname',
                        value=system['hostname'])
        server.set_attr(key='system', subkey='os',
                        value=system['operatingsystemrelease'])
        if 'cpu' in system and len(system['cpu']) > 0:
            server.set_attr(key='system', subkey='cputype',
                            value=system['cpu'][0]['model name'])
            server.set_attr(key='system', subkey='cpucount',
                            value=len(system['cpu']))
            server.set_attr(key='system', subkey='cpucache',
                            value=system['cpu'][0]['cache size'])

        if 'kernelrelease' in system:
            server.set_attr(key='system', subkey='kernelrelease',
                            value=system['kernelrelease'])

        previous_disk = server.attr_key_tuples(key='disk')
        incoming_disk = []
        blockmap = [(v.replace('/dev/', ''), k) for k, v in ec2['block-device-mapping'].items() if k != 'root']
        blockmap = dict(blockmap)
        total_disk = 0
        for i, disk in enumerate(system['disks']):
            for subkey in disk.keys():
                server.set_attr(key='disk', subkey=subkey, number=i, value=str(disk[subkey]))
                incoming_disk.append(('disk',i,subkey))
            if disk['osname'] in blockmap:
                server.set_attr(key='disk', subkey='ec2-type', number=i, value=blockmap[disk['osname']])
                incoming_disk.append(('disk',i,'ec2-type'))
            total_disk += disk['size']
        total_disk = total_disk / 1073741824
        server.set_attr(key='system', subkey='disk', value=total_disk)

        for attr in set(previous_disk).difference(set(incoming_disk)):
            server.del_attrs(key=attr[0],subkey=attr[2],number=attr[1])

        for subkey, value in body.get('sgmetadata', {}).items():
            server.set_attr(key='sgmetadata', subkey=subkey, value=value)
            if subkey == 'clusterid' and value:
                cluster = clusto.get_or_create(value, Pool)
                if not cluster.attrs(key='pooltype', value='clusterid'):
                    cluster.set_attr(key='pooltype', value='clusterid')
                if not server in cluster:
                    cluster.insert(server)
            if subkey == 'role' and value:
                if len(server.attr_values(key='puppet', subkey='class', merge_container_attrs=True)) == 0:
                    server.set_attr(key='puppet', subkey='class',
                                    value='site::role::%s' % value)

        if len(server.attr_values(key='puppet', subkey='class', merge_container_attrs=True)) == 0:
            log.warning('Found host %s with no role set, using site::role::base' % ec2['instance-id'])
            server.set_attr(key='puppet', subkey='class',
                            value='site::role::base')

        #server.set_attr(key='barker', subkey='last_updated', value=int(time()))

        try:
            owners = body['owners']
            for owner, reason in owners.iteritems():
                server.set_attr(key='owner', subkey=owner, value=reason)
        except KeyError:
            pass

        clusto.commit()
    except:
        log.warning('Exception from %s: %s' % (ec2['instance-id'], format_exc()))
        clusto.rollback_transaction()

class BarkerConsumer(clusto.script_helper.Script):
    def __init__(self):
        clusto.script_helper.Script.__init__(self)
        self.queue = None

    def callback(self, body, message):
        if self.queue.qsize() > 500:
            log.warning('Dropping message, queue size is over 500')
            return
        self.queue.put(body)

    def run(self, args):
        self.queue = Queue()
        for hostname in QUEUE_HOSTS:
            eventlet.spawn_n(self.consumer, hostname)

        while True:
            body = self.queue.get()
            log.debug('Queue size %s' % self.queue.qsize())
            barker_callback(body)

    def consumer(self, hostname):
        exchange = kombu.Exchange(QUEUE_EXCHANGE, type='fanout',
                                  delivery_mode='transient')
        queue = kombu.Queue(QUEUE_NAME, exchange)
        try:
            connection = kombu.BrokerConnection(
                hostname=hostname,
                userid=QUEUE_USER,
                password=QUEUE_PASSWORD,
                virtual_host=QUEUE_VHOST)
            channel = connection.channel()
            consumer = kombu.Consumer(channel, queue,
                                      callbacks=[self.callback],
                                      no_ack=True)
            consumer.consume()

            log.info('%s consumer running' % hostname)
            while True:
                try:
                    connection.drain_events()
                except Exception, e:
                    log.error(str(e))
        except Exception, e:
            log.error(format_exc())
            raise e
        finally:
            if connection:
                connection.release()

def main():
    barker_consumer, args = script_helper.init_arguments(BarkerConsumer)
    return barker_consumer.run(args)

if __name__ == '__main__':
    sys.exit(main())
