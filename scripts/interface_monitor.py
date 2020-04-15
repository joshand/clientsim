#!/usr/bin/env python3
# While systemd has the prefixes set in the following way:
# en = ethernet
# wl = wlan
# ww = wwan
# There are still instances where an interface won't have these.
# Which, is why I made this script.
# https://gist.github.com/Lvl4Sword/86e73ca79bea24c9e05e35fbd1de45aa
import os
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from getmac import get_mac_address
from client_sim.models import *


def dolog(fn, step, *txt):
    l = Log.objects.create(function=fn, step=step, log=",".join(map(str, txt)))
    l.save()


def get_interfaces():
    interfaces = os.listdir('/sys/class/net')
    return interfaces


def detect_virtual_interfaces(interfaces):
    for each in interfaces:
        real_path = os.path.realpath(os.path.join('/sys/class/net/', each))
        if '/devices/virtual/net/' in real_path:
            interfaces.remove(each)
    return interfaces


def detect_ethernet(clean_interfaces):
    ethernet_interfaces = []
    for each in clean_interfaces:
        try:
            # with open('/sys/class/net/{0}/speed'.format(each), 'r') as speed_file:
            #     for line in speed_file:
            #         ethernet_interfaces.append(each)
            if os.path.exists('/sys/class/net/{0}/speed'.format(each)):
                ethernet_interfaces.append(each)
        except OSError:
            pass

    return ethernet_interfaces


def detect_wireless(clean_interfaces):
    wireless_interfaces = []
    for each in clean_interfaces:
        if os.path.isdir('/sys/class/net/{0}/wireless'.format(each)):
            wireless_interfaces.append(each)

    return wireless_interfaces


def import_networks():
    interfaces = get_interfaces()
    clean_interfaces = detect_virtual_interfaces(interfaces)
    eth = detect_ethernet(clean_interfaces)
    wls = detect_wireless(clean_interfaces)

    dockerbr = "docker0"
    m = get_mac_address(interface=dockerbr)
    iface = Interface.objects.filter(name__iexact=dockerbr)
    if len(iface) <= 0:
        n = Interface.objects.create(name=dockerbr, macaddress=m, description=dockerbr)
        n.save()

    for i in eth:
        if "." in i:
            # don't import subinterfaces
            pass
        else:
            m = get_mac_address(interface=i)
            iface = Interface.objects.filter(name__iexact=i)
            if len(iface) <= 0:
                n = Interface.objects.create(name=i, macaddress=m, description=i)
                n.save()
            # print(i, m)

    for i in wls:
        m = get_mac_address(interface=i)
        # print(i, m)
        iface = Interface.objects.filter(name__iexact=i)
        if len(iface) <= 0:
            n = Interface.objects.create(name=i, macaddress=m, description=i)
            n.save()
        # print(i, m)

    # print(eth, wls)


def run():
    # Enable the job scheduler to run schedule jobs
    cron = BackgroundScheduler()

    # Explicitly kick off the background thread
    cron.start()
    cron.remove_all_jobs()
    job0 = cron.add_job(import_networks)
    job1 = cron.add_job(import_networks, 'interval', seconds=60)

    # Shutdown your cron thread if the web process is stopped
    atexit.register(lambda: cron.shutdown(wait=False))


# if __name__ == '__main__':
#     interfaces = get_interfaces()
#
#     clean_interfaces = detect_virtual_interfaces(interfaces)
#
#     detect_ethernet(clean_interfaces)
#     if not ethernet_interfaces:
#         print('No ethernet detected!')
#     else:
#         print('Ethernet:', ', '.join(ethernet_interfaces))
#
#     detect_wireless(clean_interfaces)
#     if not wireless_interfaces:
#         print('No wireless detected!')
#     else:
#         print('Wireless:', ', '.join(wireless_interfaces))