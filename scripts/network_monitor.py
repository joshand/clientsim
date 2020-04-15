import atexit
import docker
from docker import types
from apscheduler.schedulers.background import BackgroundScheduler
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
        if n.addrpool:
            ipam_pool = docker.types.IPAMPool(subnet=n.subnet, gateway=n.dg, iprange=n.addrpool)
            ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])
        elif n.dg and n.subnet:
            ipam_pool = docker.types.IPAMPool(subnet=n.subnet, gateway=n.dg)
            ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])
        else:
            ipam_config = None

        if n.networktype.driver == "macvlan":
            if settings.TRUNK_INTERFACE == "":
                append_log(log, "create_docker_macvlan",
                      "request to connect macvlan, but no trunk interface defined")
            else:
                netname = "macvlan" + str(n.vlan)
                netopt = {"parent": settings.TRUNK_INTERFACE + "." + str(n.vlan)}
                if delete_existing:
                    append_log(log, "resync_docker_network", n.networkid)
                    client.networks.get(n.networkid).remove()
                    n.networkid = None
                    n.skip_sync = True
                    n.save()

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


def sync_docker_networks():
    log = []
    try:
        client = docker.from_env()
        dnets = client.networks.list()
        append_log(log, "sync_docker_networks", dnets)
        # First, check to see if all relevant Docker networks exist in the database. If not, import them.
        for dn in dnets:
            # print(dn.attrs)
            drivers = NetworkType.objects.filter(driver__iexact=dn.attrs["Driver"])
            nets = Network.objects.filter(networkid__iexact=dn.id)
            if len(nets) <= 0 and len(drivers) > 0:
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

        # Next, check to see if there are any networks in database that do not exist in Docker
        nets = Network.objects.filter(networkid__isnull=True)
        create_docker_nets(client, nets, log)
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
        create_docker_nets(client, nets, log, delete_existing=True)
        # for n in nets:
            # print(n, n.last_sync, n.last_update)
            # client.networks.
            # I think containers have to be detached before deleting...

        # Next, check for Link Impairment script
        nets = Network.objects.filter(networkid__isnull=False)
        for n in nets:
            if (str(n.last_deployed_hash) != str(n.networkimpairmentscripthash())) or n.force_script:
                n.force_script = False
                n.skip_sync = True
                n.save()

                s = n.networkimpairmentscript()
                # print(s)
                if s:
                    lines = s.split("\r\n")
                    for l in lines:
                        # print("****", l) #{{interface}}
                        newl = l.replace("{{interface}}", n.hostnetwork())
                        out = subprocess.Popen(newl.split(" "),
                                               stdout=subprocess.PIPE,
                                               stderr=subprocess.STDOUT)
                        stdout, stderr = out.communicate()
                        append_log(log, "apply_impairment_script", newl, stdout, stderr)

                n.last_deployed_hash = n.networkimpairmentscripthash()
                n.skip_sync = True
                n.save()

    except Exception as e:
        append_log(log, "import_docker_nets_into_db", "error", e)

    db_log("network_monitor", log)


def run():
    # Enable the job scheduler to run schedule jobs
    cron = BackgroundScheduler()

    # Explicitly kick off the background thread
    cron.start()
    cron.remove_all_jobs()
    job0 = cron.add_job(sync_docker_networks)
    job1 = cron.add_job(sync_docker_networks, 'interval', seconds=10)

    # Shutdown your cron thread if the web process is stopped
    atexit.register(lambda: cron.shutdown(wait=False))
