import json
import sys
import time
import configargparse
from lxml import html
import pkg_resources
import requests

__version__ = pkg_resources.get_distribution('ifbcloud').version
requests.packages.urllib3.disable_warnings()


class IfbSession(object):

    instance_types = {'c2.small': 9,
                      'c2.large': 10,
                      'c2.xlarge': 11,
                      'c3.medium': 1,
                      'c3.large': 2,
                      'c3.xlarge': 3,
                      'm1.medium': 6,
                      }
    login_url = 'https://cloud.france-bioinformatique.fr/accounts/login'
    instance_url = 'https://cloud.france-bioinformatique.fr/cloud/instance/'

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = requests.session()
        self.csrftoken = self.get_csrftoken()
        self.welcome = self.login()
        self.appliances_by_name = self.get_appliances()
        self.appliances_by_id = {v: k for k, v in self.appliances_by_name.items()}

    def get_csrftoken(self):
        self.session.get(self.login_url, verify=False)
        return self.session.cookies.get_dict()['csrftoken']

    def login(self, next_url='/cloud/instance'):
        login_data = dict(username=self.username,
                          password=self.password,
                          csrfmiddlewaretoken=self.csrftoken,
                          next=next_url)
        return self.session.post(self.login_url, data=login_data, headers=dict(Referer=self.login_url), verify=False)

    def get_appliances(self):
        tree = html.fromstring(self.welcome.content)
        table = tree.xpath('//*[@id="id_appliance"]/option')
        return {item.text: int(item.values()[0]) for item in table}

    @property
    def disks(self):
        r = self.login(next_url='/cloud/storage')
        tree = html.fromstring(r.content)
        element = tree.xpath('//*[@id="storages"]/tbody')[0]
        skip = 0
        disks = []
        disk = dict()
        for i, e in enumerate(element.itertext()):
            if i - skip == 0:
                disk['Name'] = e
            if i - skip == 1:
                disk['Size'] = e
            if i - skip == 2:
                disk['UUID'] = e
                skip = i + 1
                disks.append(disk)
                disk = dict()
        return disks

    def start_instance(self, vm_name, instance_type, disk_uuid='', appliance_id=206):
        new_instance_data = {'csrfmiddlewaretoken': self.csrftoken,
                             'appliance': appliance_id,
                             'filter_thematic_fields': '',
                             'filter_tools': '',
                             'vm_name': vm_name,
                             'instance_type': self.instance_types[instance_type],
                             'instance_number': '1',
                             'storage': disk_uuid,
                             'form_type': 'instance_creation'}
        return self.session.post(self.instance_url,
                                 data=new_instance_data,
                                 headers=dict(Referer=self.instance_url),
                                 verify=False)

    @property
    def status(self):
        r = self.login()
        tree = html.fromstring(r.content)
        instance = tree.xpath('//table[@id="instances"]')[0]
        instances = []
        instance_d = dict()
        header_lines = 12
        for i, t in enumerate(instance.itertext()):
            if i <= header_lines:  # Headers
                continue
            if i - header_lines == 1:
                instance_d['ID'] = t
                continue
            if i - header_lines == 2:
                instance_d['Name'] = t
                continue
            if i - header_lines == 3:
                instance_d['Status'] = t
                continue
            if i - header_lines == 4:
                instance_d['Appliance'] = t
                continue
            if i - header_lines == 5:
                instance_d['CPU%'] = t
                continue
            if i - header_lines == 6:
                instance_d['CPU'] = t
                continue
            if i - header_lines == 7:
                instance_d['Mem.'] = t
                continue
            if i - header_lines == 8:
                instance_d['#Storage'] = t
                continue
            if i - header_lines == 9:
                instance_d['Storage'] = t
                continue
            if t.startswith('host ='):
                instance_d['IP'] = t.split('host = ')[1]
                header_lines += 27  # Skip the rest and continue with next VM
                instances.append(instance_d)
                instance_d = dict()
        return instances

    def get_instance_ip(self, vm_name=None, vm_id=None, count=0):
        """
        Get the instances' IP. One of vm_name or vm_id needs to be supplied.
        """
        if not vm_name and not vm_id:
            raise Exception("Need either vm_name or vm_id")
        if count > 5:
            raise Exception("Instance not found")
        if vm_id:
            key = 'ID'
            value = vm_id
        else:
            key = 'Name'
            value = vm_name
        for vm in self.status:
            if vm.get(key, None) == value:
                return vm['IP']
        time.sleep(10)
        return self.get_instance_ip(vm_name, count)

    def get_instance_id(self, vm_name):
        for vm in self.status:
            if vm.get('Name', None) == vm_name:
                return vm['ID']

    def get_disk_uuid(self, disk_name):
        for disk in self.disks:
            if disk.get('Name', None) == disk_name:
                return disk['UUID']

    def shutdown_instance(self, instance_id):
        shutdown_data = {'csrfmiddlewaretoken': self.csrftoken,
                         'operation': 'shutdown',
                         'targets': instance_id,
                         'instances_length': 25,  # No clue what this is
                         'form_type': 'instance_operation'
                         }
        return self.session.post(self.instance_url,
                                 data=shutdown_data,
                                 headers=dict(Referer=self.instance_url),
                                 verify=False)


def parse_args(help=False):
    parent = configargparse.ArgumentParser(prog="ifbcloud version %s" % __version__, add_help=False)
    parent.add_argument('-u', '--username', env_var='IFB_USERNAME', required=True, help="Your IFB username")
    parent.add_argument('-p', '--password', env_var='IFB_PASSWORD', required=True, help="Your IFB password")
    parent.add_argument('--version', action='version', version=__version__)
    args = configargparse.ArgumentParser()
    subparsers = args.add_subparsers(help='Select one of the following subcommands')
    status = subparsers.add_parser('status', parents=[parent], help='Prints the current status of your running IFB VMs')
    status.set_defaults(func=get_instance_status)
    status = subparsers.add_parser('disks', parents=[parent], help='Prints the current status of your IFB disks')
    status.set_defaults(func=get_disk_status)
    status = subparsers.add_parser('appliances', parents=[parent], help='Prints the currently available appliances')
    status.set_defaults(func=get_appliances)
    start = subparsers.add_parser('start', parents=[parent], help='Start a new instance')
    start.set_defaults(func=start_instance)
    start.add_argument('-n', '--name', required=True, help="Name of the instance to start.")
    start.add_argument('-t', '--type', default='c2.small', help="Choose the instance type to start",
                       choices=IfbSession.instance_types.keys())
    start.add_argument('-a', '--appliance', default='',
                       help='Select an appliance by name. '
                            '(Use "ifbcloud appliances" to get a list of all appliances)')
    start.add_argument('-ai', '--appliance_id', default=206, type=int,
                       help='Select an appliance by ID. '
                            '(Use "ifbcloud appliances" to get a list of all appliances)')
    start.add_argument('-dn', '--disk_name', default='', help='Attach the disk of this name to the new instance')
    start.add_argument('-du', '--disk_uuid', default='', help='Attach the disk of this UUID to the new instance')
    stop = subparsers.add_parser('stop', parents=[parent], help='Stop an instance')
    stop.add_argument('-n', '--name', default=None, help="Name of the instance to stop.")
    stop.add_argument('-i', '--id', default=None, help="ID of the instance to stop.")
    stop.set_defaults(func=stop_instance)
    if help:
        return args.parse_args(['-h'])
    return args.parse_args()


def get_ifb(args):
    return IfbSession(args.username, args.password)


def get_instance_status(args):
    ifb = get_ifb(args)
    sys.stdout.write(json.dumps(ifb.status, sort_keys=True, indent=4))


def get_disk_status(args):
    ifb = get_ifb(args)
    sys.stdout.write(json.dumps(ifb.disks, sort_keys=True, indent=4))


def get_appliances(args):
    ifb = get_ifb(args)
    sys.stdout.write(json.dumps(ifb.appliances_by_name, sort_keys=True, indent=4))


def start_instance(args):
    ifb = get_ifb(args)
    uuid = ""
    if args.disk_uuid:
        uuid = args.disk_uuid
    elif args.disk_name:
        uuid = ifb.get_disk_uuid(args.disk_name)
        if not uuid:
            raise Exception("Disk '%s' not found" % args.disk_name)
    appliance_id = args.appliance_id
    if args.appliance:
        appliance_id = ifb.appliances_by_name.get(args.appliance, None)
        if not appliance_id:
            raise Exception("Appliance '%s' not found. Valid appliances are: \n %s" %
                            (args.appliance, ifb.appliances_by_name))
    if appliance_id not in ifb.appliances_by_id:
        raise Exception("Appliance id '%s' not found. Valid appliances are: \n %s" %
                        (appliance_id, ifb.appliances_by_name))
    ifb.start_instance(vm_name=args.name, instance_type=args.type, disk_uuid=uuid, appliance_id=appliance_id)
    sys.stdout.write(ifb.get_instance_ip(args.name))


def stop_instance(args):
    ifb = get_ifb(args)
    if not args.id:
        args.id = ifb.get_instance_id(args.name)
    ifb.shutdown_instance(args.id)


def main():
    args = parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parse_args(help=True)

if __name__ == "__main__":
    main()
