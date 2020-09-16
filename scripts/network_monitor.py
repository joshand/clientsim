import sys
import os
import traceback
# import atexit
import docker
from docker import types
# from apscheduler.schedulers.background import BackgroundScheduler
from client_sim.models import *
from django.conf import settings
from django.db.models import F
from django.utils.timezone import make_aware
import subprocess
from scripts.dblog import *


"""
  376  docker network create -d macvlan --subnet=10.99.14.0/24 --gateway=10.99.14.1 -o parent=eth0.40 macvlan40
  377  docker network create -d macvlan --subnet=10.99.12.0/24 --gateway=10.99.12.1 -o parent=eth0.50 macvlan50
  378  docker network create -d macvlan --subnet=10.99.54.0/24 --gateway=10.99.54.1 -o parent=eth0.440 macvlan440
  379  docker network create -d macvlan --subnet=10.99.55.0/24 --gateway=10.99.55.1 -o parent=eth0.450 macvlan450
 """


# def dolog(fn, step, *txt):
#     l = Log.objects.create(function=fn, step=step, log=",".join(map(str, txt)))
#     l.save()


def create_docker_nets(client, nets, log, delete_existing=False):
    for n in nets:
        if n.subnet is None or n.subnet.strip() == "None":
            continue
        append_log(log, "rebuild_docker_network::start_check::", n.networkid)

        # networks = client.networks.list()
        # for network in networks:
        #     print(network.attrs["IPAM"])

        if n.addrpool:
            ipam_pool = docker.types.IPAMPool(subnet=n.subnet, gateway=n.dg, iprange=n.addrpool)
            ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])
        elif n.dg and n.subnet:
            ipam_pool = docker.types.IPAMPool(subnet=n.subnet, gateway=n.dg)
            ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])
        else:
            ipam_config = None

        # cli_restart = []
        if (n.force_rebuild or delete_existing) and n.networkid:
            try:
                net = client.networks.get(n.networkid)
                append_log(log, "rebuild_docker_network", n.networkid, net.name)
                if net.name != "bridge":
                    for c in net.containers:
                        append_log(log, "stopping container", c)
                        c.stop()
                        # cli_restart.append(c)
                        # c.pause()
                    net.remove()
                    n.networkid = None
                    n.skip_sync = True
                    n.force_rebuild = False
                    n.save()
                else:
                    append_log(log, "rebuild_docker_network - cannot update 'bridge'; skipping")
                    n.skip_sync = True
                    n.force_rebuild = False
                    n.save()
            except Exception as e:
                append_log(log, "rebuild_docker_network::exception::network no longer exists?", e)
                n.networkid = None
                n.skip_sync = True
                n.force_rebuild = False
                n.save()

        if n.networktype.driver == "macvlan":
            # if settings.TRUNK_INTERFACE == "":
            #     append_log(log, "create_docker_macvlan",
            #           "request to connect macvlan, but no trunk interface defined")
            # else:
            if n.interface.name:
                netname = "macvlan" + str(n.vlan)
                if n.dot1q:
                    netopt = {"parent": n.interface.name + "." + str(n.vlan)}
                else:
                    netopt = {"parent": n.interface.name}

                if n.networktype.driveropt:
                    netopt = {**netopt, **json.loads(n.networktype.driveropt)}

                append_log(log, "create_docker_macvlan", netname, ipam_config, netopt)
                dt = make_aware(datetime.datetime.now())
                if ipam_config:
                    newnet = client.networks.create(netname, driver="macvlan", ipam=ipam_config, options=netopt)
                else:
                    newnet = client.networks.create(netname, driver="macvlan", options=netopt)
                n.networkid = newnet.id
                n.last_sync = dt
                n.last_update = dt
                n.skip_sync = True
                n.save()
        elif n.networktype.driver == "ipvlan":
            if n.interface.name:
                netname = "ipvlan" + str(n.vlan)
                if n.dot1q:
                    netopt = {"parent": n.interface.name + "." + str(n.vlan)}
                else:
                    netopt = {"parent": n.interface.name}

                if n.networktype.driveropt:
                    netopt = {**netopt, **json.loads(n.networktype.driveropt)}

                append_log(log, "create_docker_macvlan", netname, ipam_config, netopt)
                dt = make_aware(datetime.datetime.now())
                if ipam_config:
                    newnet = client.networks.create(netname, driver="macvlan", ipam=ipam_config, options=netopt)
                else:
                    newnet = client.networks.create(netname, driver="macvlan", options=netopt)
                n.networkid = newnet.id
                n.last_sync = dt
                n.last_update = dt
                n.skip_sync = True
                n.save()
        elif n.networktype.driver == "bridge" and str(n.interface.name) != "docker0":
            if n.interface.name:
                netname = n.name
                netopt = {"parent": n.interface.name}

                if n.networktype.driveropt:
                    netopt = {**netopt, **json.loads(n.networktype.driveropt)}

                append_log(log, "create_docker_bridge", netname, ipam_config, netopt)
                dt = make_aware(datetime.datetime.now())
                if ipam_config:
                    newnet = client.networks.create(netname, driver="bridge", ipam=ipam_config, options=netopt)
                else:
                    newnet = client.networks.create(netname, driver="bridge", options=netopt)
                n.networkid = newnet.id
                n.last_sync = dt
                n.last_update = dt
                n.skip_sync = True
                n.save()
        else:
            append_log(log, "create_docker_unknown", n.networktype.driver)

        # for c in cli_restart:
        #     append_log(log, "starting container", c)
        #     c.unpause()


def sync_docker_networks():
    docker_net_list = []
    log = []
    # try:
    client = docker.from_env()
    try:
        dnets = client.networks.list()
    except Exception as e:
        append_log(log, "sync_docker_networks::exception getting Docker network list::is Docker installed and running?::", e)
        db_log("network_monitor", log)
        return ""

    append_log(log, "sync_docker_networks::full_docker_network_list::", dnets)
    # First, check to see if all relevant Docker networks exist in the database. If not, import them.
    for dn in dnets:
        docker_net_list.append(dn.id)
        # print(dn.attrs)
        drivers = NetworkType.objects.filter(driver__iexact=dn.attrs["Driver"])
        networks = Network.objects.filter(networkid__iexact=dn.id)
        bridges = Bridge.objects.filter(networkid__iexact=dn.id)
        if len(networks) <= 0 and len(bridges) <= 0 and len(drivers) > 0:
            if dn.name == "bridge":
                newname = "Default Docker Bridge"
                newint = dn.attrs["Options"]["com.docker.network.bridge.name"]
                ipamcfg = dn.attrs.get("IPAM", {}).get("Config", {})[0]
                newsubnet = ipamcfg.get("Subnet", None)
                newgw = None
                newrange = None
            else:
                newname = dn.name
                newint = dn.attrs["Options"]["parent"].split(".")[0]
                ipamcfg = dn.attrs.get("IPAM", {}).get("Config", {})[0]
                newsubnet = ipamcfg.get("Subnet", None)
                newgw = ipamcfg.get("Gateway", None)
                newrange = ipamcfg.get("IPRange", None)

            intid = Interface.objects.filter(name__iexact=newint)
            if intid:
                append_log(log, "import_docker_nets_into_db", dn.id, drivers[0], newname, newsubnet, newgw, newrange, intid[0])
                dt = make_aware(datetime.datetime.now())
                n = Network.objects.create(networkid=dn.id, networktype=drivers[0], description=newname, interface=intid[0], subnet=newsubnet, dg=newgw, addrpool=newrange, last_sync=dt, last_update=dt)
                n.save()
            else:
                append_log(log, "import_docker_nets_into_db", dn.id, drivers[0], newname, newsubnet, newgw, newrange, newint, "Unable to resolve interface name")

    # clear networkid for any network/bridge in db that doesn't actually exist in Docker
    nets = Network.objects.exclude(networkid__in=docker_net_list).update(networkid=None)
    bridges = Bridge.objects.exclude(networkid__in=docker_net_list).update(networkid=None)

    # Next, check to see if there are any networks in database that do not exist in Docker
    nets = Network.objects.filter(networkid__isnull=True)
    append_log(log, "sync_docker_networks::nets_in_db_not_in_docker::", nets)
    create_docker_nets(client, nets, log)

    bridges = Bridge.objects.filter(networkid__isnull=True)
    append_log(log, "sync_docker_bridges::bridges_in_db_not_in_docker::", nets)
    create_docker_nets(client, bridges, log)

    # for n in nets:
    #     if n.addrpool:
    #         ipam_pool = docker.types.IPAMPool(subnet=n.subnet, gateway=n.dg, iprange=n.addrpool)
    #         ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])
    #     elif n.dg and n.subnet:
    #         ipam_pool = docker.types.IPAMPool(subnet=n.subnet, gateway=n.dg)
    #         ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])
    #     else:
    #         ipam_config = None
    #
    #     if n.networktype.driver == "macvlan":
    #         if settings.TRUNK_INTERFACE == "":
    #             dolog("sync_docker_networks", "create_docker_macvlan", "request to connect macvlan, but no trunk interface defined")
    #         else:
    #             netname = "macvlan" + str(n.vlan)
    #             netopt = {"parent": settings.TRUNK_INTERFACE + "." + str(n.vlan)}
    #             dolog("sync_docker_networks", "create_docker_macvlan", netname, ipam_config, netopt)
    #             dt = datetime.datetime.now()
    #             if ipam_config:
    #                 newnet = client.networks.create(netname, driver="macvlan", ipam=ipam_config, options=netopt, last_sync=dt, last_update=dt)
    #             else:
    #                 newnet = client.networks.create(netname, driver="macvlan", options=netopt, last_sync=dt, last_update=dt)
    #             n.networkid = newnet.id
    #             n.save()

    # Last, see if any networks have been updated and need to be re-synced
    nets = Network.objects.all().exclude(last_sync=F('last_update'))
    append_log(log, "sync_docker_networks::nets_out_of_sync::", nets)
    create_docker_nets(client, nets, log, delete_existing=True)
    nets = Network.objects.all().filter(force_rebuild=True)
    append_log(log, "sync_docker_networks::force_rebuild::", nets)
    create_docker_nets(client, nets, log, delete_existing=True)

    bridges = Bridge.objects.all().exclude(last_sync=F('last_update'))
    append_log(log, "sync_docker_bridges::bridges_out_of_sync::", bridges)
    create_docker_nets(client, bridges, log, delete_existing=True)
    bridges = Bridge.objects.all().filter(force_rebuild=True)
    append_log(log, "sync_docker_bridges::force_rebuild::", bridges)
    create_docker_nets(client, bridges, log, delete_existing=True)

    # for n in nets:
        # print(n, n.last_sync, n.last_update)
        # client.networks.
        # I think containers have to be detached before deleting...

    # Next, check for Link Impairment script
    networks = Network.objects.filter(networkid__isnull=False)
    bridges = Bridge.objects.filter(networkid__isnull=False)
    nets = []
    for o in networks:
        nets.append(o)
    for o in bridges:
        nets.append(o)

    for n in nets:
        if (str(n.last_deployed_hash) != str(n.networkimpairmentscripthash())) or n.force_script:
            n.force_script = False
            n.skip_sync = True
            n.save()

            s = n.networkimpairmentscript()
            # print(s)
            if s:
                lines = s.split("\r\n")
                # print("Getting ready to deploy...", lines)
                for l in lines:
                    # print("****", l) #{{interface}}
                    newl = l.replace("{{interface}}", n.interface.name)
                    out = subprocess.Popen(newl.replace("\n", "\r\n"), shell=True,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.STDOUT)
                    stdout, stderr = out.communicate()
                    print(newl, stdout, stderr)
                    # out = subprocess.run(newl, capture_output=True, shell=True)
                    append_log(log, "apply_impairment_script", newl, stdout, stderr)

            n.last_deployed_hash = n.networkimpairmentscripthash()
            n.skip_sync = True
            n.save()

    # except Exception as e:
    #     exc_type, exc_obj, exc_tb = sys.exc_info()
    #     fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    #     append_log(log, "import_docker_nets_into_db", "error", e, exc_type, fname, exc_tb.tb_lineno)
    #     append_log(log, traceback.format_exc())

    db_log("network_monitor", log)


def delete_network(network_id):
    client = docker.from_env()
    log = []
    nets = Network.objects.filter(id=network_id)
    for n in nets:
        if n.networkid:
            net = client.networks.get(n.networkid)
            append_log(log, "delete_docker_network", n.networkid, net.name)
            if net.name != "bridge":
                for c in net.containers:
                    append_log(log, "stopping container", c)
                    c.stop()
                    # cli_restart.append(c)
                    # c.pause()
                net.remove()
        else:
            append_log(log, "delete_docker_network::No networkID. Doesn't exist?")

    db_log("network_monitor", log)


def run():
    sync_docker_networks()
