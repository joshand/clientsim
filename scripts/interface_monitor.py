#!/usr/bin/env python3
# While systemd has the prefixes set in the following way:
# en = ethernet
# wl = wlan
# ww = wwan
# There are still instances where an interface won't have these.
# Which, is why I made this script.
# https://gist.github.com/Lvl4Sword/86e73ca79bea24c9e05e35fbd1de45aa
import os
# import atexit
# from apscheduler.schedulers.background import BackgroundScheduler
from getmac import get_mac_address
from client_sim.models import *
from scripts.dblog import *
import subprocess


def get_interfaces(log):
    try:
        interfaces = os.listdir('/sys/class/net')
    except Exception as e:
        append_log(log, "get_interfaces::unable to list /sys/class/net. probably not linux.", e)
        interfaces = []

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
                if os.path.isdir('/sys/class/net/{0}/device'.format(each)):
                    if not os.path.isdir('/sys/class/net/{0}/wireless'.format(each)):
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


def detect_bridge(clean_interfaces):
    bridge_interfaces = []
    for each in clean_interfaces:
        if os.path.isdir('/sys/class/net/{0}/bridge'.format(each)):
            if each != "docker0":
                bridge_interfaces.append(each)

    return bridge_interfaces


def exec_cmd(bridge, cmdlist, log):
    for l in cmdlist:
        newl = l[:]
        # if not bridge.dg and newl.find("{{bridgedg}}") >= 0:
        #     continue

        newl = newl.replace("{{interface}}", bridge.interface.name)
        newl = newl.replace("{{bridgeinterface}}", bridge.name)
        # newl = newl.replace("{{bridgeip}}", bridge.subnet)
        # if bridge.dg:
        #     newl = newl.replace("{{bridgedg}}", bridge.dg)
        # newl = newl.replace("{{vethint}}", bridge.name + "-int")
        # newl = newl.replace("{{vethext}}", bridge.name + "-ext")
        out = subprocess.Popen(newl.split(" "),
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
        stdout, stderr = out.communicate()
        append_log(log, "create_bridge::exec_cmd", newl, stdout, stderr)


def import_networks():
    imported_networks = []
    log = []
    interfaces = get_interfaces(log)
    bri = detect_bridge(interfaces)

    clean_interfaces = detect_virtual_interfaces(interfaces)
    eth = detect_ethernet(clean_interfaces)
    wls = detect_wireless(clean_interfaces)
    append_log(log, "interface_monitor::import_networks::eth", eth)
    append_log(log, "interface_monitor::import_networks::wls", wls)

    dockerbr = "docker0"
    imported_networks.append(dockerbr)
    m = get_mac_address(interface=dockerbr)
    iface, created = Interface.objects.update_or_create(name__iexact=dockerbr,
                                                        defaults={"macaddress": m, "wired": True})
    if created:
        iface.description = dockerbr
        iface.save()

    for i in eth:
        if "." in i:
            # don't import subinterfaces
            pass
        else:
            m = get_mac_address(interface=i)
            if i.strip() == "":
                continue
            imported_networks.append(i.strip())
            iface, created = Interface.objects.update_or_create(name=i.strip(),
                                                                defaults={"macaddress": m, "wired": True})
            if created:
                iface.description = i
                iface.save()

    for i in wls:
        m = get_mac_address(interface=i)
        # print(i, m)
        if i.strip() == "":
            continue
        imported_networks.append(i.strip())
        iface, created = Interface.objects.update_or_create(name=i.strip(),
                                                            defaults={"macaddress": m, "wired": False})
        if created:
            iface.description = i
            iface.save()

    removed_ints = Interface.objects.exclude(name__in=imported_networks)
    for interface in removed_ints:
        interface.active = False
        interface.save()

    for interface in imported_networks:
        cmd = "ip link set " + interface + " up"
        out = subprocess.Popen(cmd.split(" "),
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
        stdout, stderr = out.communicate()
        # print(cmd, stdout, stderr)

    # Don't need to create bridge here; Docker will create it
    # dis_count = Bridge.objects.exclude(name__in=bri).update(is_configured=False)
    # bri = Bridge.objects.filter(is_configured=False)
    # for b in bri:
    #     cmdlist = [
    #         "brctl addbr {{bridgeinterface}}",
    #         "ip link set {{bridgeinterface}} up",
    #         "iw dev {{interface}} set 4addr on",
    #         "brctl addif {{bridgeinterface}} {{interface}}"
    #         # "ip addr add {{bridgeip}} dev {{bridgeinterface}}",
    #         # "ip route add default via {{bridgedg}} dev {{bridgeinterface}}",
    #         # "ip link add {{vethint}} type veth peer name {{vethext}}",
    #         # "brctl addif {{bridgeinterface}} {{vethext}}"
    #     ]
    #     exec_cmd(b, cmdlist, log)
    #
    #     b.is_configured = True
    #     b.save()

    # print(eth, wls)
    db_log("interface_monitor", log)


def delete_bridge(bridge_id):
    log = []
    bri = Bridge.objects.filter(id=bridge_id)
    for b in bri:
        cmdlist = [
            "ip link set {{bridgeinterface}} down",
            "brctl delbr {{bridgeinterface}}"
        ]
        exec_cmd(b, cmdlist, log)

    db_log("interface_monitor", log)


def run():
    import_networks()
