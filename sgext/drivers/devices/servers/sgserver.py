from clusto.drivers.devices.servers.basicserver import BasicServer
from IPy import IP
import boto.ec2
import urllib2
import urllib
import socket
import json
import sys

from sgext.util import SGException

class Request(urllib2.Request):
    def __init__(self, method, url, data=None):
        if isinstance(data, dict):
            data = urllib.urlencode(data)

        urllib2.Request.__init__(self, url, data=data)
        self.method = method

    def get_method(self):
        return self.method


class SGServer(BasicServer):
    _driver_name = 'sgserver'
    _portmeta = {
        'nic-eth': {'numports': 1},
    }

    def get_boto_connection(self):
        region = self.attr_value(key='ec2', subkey='region', merge_container_values=True)
        return boto.ec2.connect_to_region(region)

    def get_best_ip(self):
        for dnsname in self.attr_values(key='ec2', subkey='public-dns'):
            try:
                ip = socket.gethostbyname(dnsname)
                return ip
            except Exception, e:
                pass
        ips = self.attr_values(key='ip', subkey='ipstring')
        for ip in ips:
            if IP(ip).iptype() != 'PRIVATE':
                return ip
        if not ips:
            raise SGException('Unable to determine IP for %s' % self.name)

    def reboot(self):
        conn = self.get_boto_connection()
        conn.reboot_instances([self.attr_value(key='ec2', subkey='instance-id')])

    def opsd_request(self, method, endpoint, data={}):
        url = 'http://%s:9666%s' % (self.get_best_ip(), endpoint)
        resp = urllib2.urlopen(Request(method, url, data))
        return json.loads(resp.read())

    def start_service(self, name, provider='monit'):
        return self.opsd_request('POST', '/v0/service/%s/%s.json' % (provider, name), {'action': 'start'})

    def stop_service(self, name, provider='monit'):
        return self.opsd_request('POST', '/v0/service/%s/%s.json' % (provider, name), {'action': 'stop'})

    def restart_service(self, name, provider='monit'):
        return self.opsd_request('POST', '/v0/service/%s/%s.json' % (provider, name), {'action': 'restart'})

    def get_service(self, name=None, provider='monit'):
        if name is None:
            return self.opsd_request('GET', '/v0/service/%s/' % provider)
        else:
            return self.opsd_request('GET', '/v0/service/%s/%s.json' % (provider, name))

    def install_package(self, name, provider='apt'):
        result = self.opsd_request('POST', '/v0/package/%s/%s.json' % (provider, name), {'action': 'install'})
        if result.get('status', None) != 'ok':
            raise SGException('Error installing package: %s' % result)

    def remove_package(self, name, provider='apt'):
        result = self.opsd_request('POST', '/v0/package/%s/%s.json' % (provider, name), {'action': 'remove'})
        if result.get('status', None) != 'ok':
            raise SGException('Error removing package: %s' % result)

    def apt_update(self):
        result = self.opsd_request('POST', '/v0/package/apt/update.json')
        if result.get('status', None) != 'ok':
            raise SGException('Error performing apt update: %s' % result)

    def get_package(self, name=None, provider='apt'):
        if name is None:
            return self.opsd_request('GET', '/v0/package/%s/' % provider)
        else:
            return self.opsd_request('GET', '/v0/package/%s/%s.json' % (provider, name))

    def run_test(self, name, provider='consumption'):
        return self.opsd_request('GET', '/v0/test/%s/%s.json' % (provider, name))

    def get_tests(self, provider='consumption'):
        return self.opsd_request('GET', '/v0/test/%s/' % provider)

    def run_puppet(self):
        result = self.opsd_request('POST', '/v0/config/puppet/run.json')
        if result.get('status', None) != 'ok':
            raise SGException('Error running puppet: %s' % result)

    def enable_puppet(self):
        result = self.opsd_request('POST', '/v0/config/puppet/state.json', {
            'action': 'enable',
        })
        if result.get('status', None) != 'ok':
            raise SGException('Error enabling puppet: %s' % result)

    def disable_puppet(self):
        result = self.opsd_request('POST', '/v0/config/puppet/state.json', {
            'action': 'disable',
        })
        if result.get('status', None) != 'ok':
            raise SGException('Error disabling puppet: %s' % result)
