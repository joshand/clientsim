import atexit
import docker
from docker import types
from apscheduler.schedulers.background import BackgroundScheduler
from client_sim.models import *
from django.conf import settings
from django.utils.timezone import make_aware
from io import BytesIO
from django.db.models import F


def dolog(fn, step, *txt):
    l = Log.objects.create(function=fn, step=step, log=",".join(map(str, txt)))
    l.save()


def create_docker_containers(client, containers, delete_existing=False):
    for c in containers:
        cmdout = ""
        newcli = None
        if delete_existing:
            # dolog("sync_docker_containers", "deleting_existing_container", c.clientid, c)
            cmdout += "Deleting existing container " + str(c.clientid) + "\n"
            try:
                ret = client.containers.get(c.clientid).remove(force=True)
            except Exception as e:
                # dolog("sync_docker_containers", "deleting_existing_container", "error", e)
                cmdout += "Exception " + str(e) + "\n"
            c.force_rebuild = False
            c.last_deployed_hash = None
            c.clientid = None
            c.skip_sync = True
            c.save()

        if c.container.containertype.name == "PUBLISHED":
            newcli = client.containers.run(c.container.path, c.container.cmd, network=c.network.dockernetwork(),
                                           mac_address=c.macaddress, hostname=c.hostname, name=c.dockercontainername(),
                                           detach=True, tty=True, remove=True)
            # dolog("sync_docker_containers", "create_new_container_published", newcli)
            cmdout += "New Published Container " + str(newcli) + "\n"
        elif c.container.containertype.name == "DOCKERFILE":
            df = str(c.container.dockerfile) + "\n"
            f = BytesIO(df.encode('utf-8'))
            try:
                client2 = docker.APIClient(base_url='unix://var/run/docker.sock')
                response = [line for line in client2.build(
                    fileobj=f, rm=True, tag=c.container.buildcontainername
                )]
                # newimg = client.images.build(fileobj=f, custom_context=True, tag=c.container.buildcontainername)
                # dolog("sync_docker_containers", "create_new_image", "success", response)
                cmdout += "New Build Image " + str(response) + "\n"
            except Exception as e:
                # dolog("sync_docker_containers", "create_new_image", "error", e)
                cmdout += "Build Image Exception " + str(e) + "\n"

            try:
                # print(c.container.buildcontainername, c.container.cmd, c.network.dockernetwork(), c.macaddress, c.hostname, c.dockercontainername())
                newcli = client.containers.run(c.container.buildcontainername, c.container.cmd, network=c.network.dockernetwork(),
                                               mac_address=c.macaddress, hostname=c.hostname, name=c.dockercontainername(),
                                               detach=True, tty=True, remove=True)
                # dolog("sync_docker_containers", "create_new_container_built", "success", newcli)
                cmdout += "New Build Container " + str(newcli) + "\n"
            except Exception as e:
                # dolog("sync_docker_containers", "create_new_container_built", "error", e)
                cmdout += "Build Container Exception " + str(e) + "\n"

        # print(c, c.container.path, c.container.cmd, newcli)

        if newcli:
            # ipaddr = newcli.attrs['NetworkSettings']['IPAddress']
            # if ipaddr is None or ipaddr == "":
            #     ipaddr = newcli.attrs['NetworkSettings']['Networks'][c.network.dockernetwork()]['IPAddress']
            # c.ipaddress = ipaddr

            dt = make_aware(datetime.datetime.now())
            c.clientid = newcli.id
            c.last_sync = dt
            c.last_update = dt
            c.skip_sync = True
            c.last_sync_log = str(cmdout)
            c.save()


def sync_container_ips(containers):
    client = docker.from_env()
    for c in containers:
        newcli = client.containers.get(c.clientid)
        ipaddr = newcli.attrs['NetworkSettings']['IPAddress']
        if ipaddr is None or ipaddr == "":
            ipaddr = newcli.attrs['NetworkSettings']['Networks'][c.network.dockernetwork()]['IPAddress']
        # print("containerip", c.clientid, ipaddr)
        c.ipaddress = ipaddr
        c.skip_sync = True
        c.save()


def sync_docker_clients():
    client = docker.from_env()
    # First, check to see if there are any clients in database that do not exist in Docker
    conts = Client.objects.filter(clientid__isnull=True)
    print("sync_docker::create_docker_containers::phase_1", conts)
    create_docker_containers(client, conts)

    # Last, see if any clients have been updated and need to be re-synced
    conts = Client.objects.all().exclude(last_sync=F('last_update'))
    # print(conts)
    print("sync_docker::create_docker_containers::phase_2", conts)
    create_docker_containers(client, conts, delete_existing=True)

    # Next, check to see if there are any clients in database that are tagged with 'force_rebuild'
    conts = Client.objects.filter(force_rebuild=True)
    print("sync_docker::create_docker_containers::phase_3", conts)
    create_docker_containers(client, conts, delete_existing=True)

    # Sync Container IPs
    sync_container_ips(Client.objects.all())

    # Next, send script to client
    conts = Client.objects.filter(clientid__isnull=False)
    for c in conts:
        cmdout = ""
        if c.dockercontainerscripthash() != "":
            if (str(c.last_deployed_hash) != str(c.dockercontainerscripthash())) or c.force_script:
                print("sync_docker::create_docker_containers::script_deployment", c)
                c.force_script = False
                c.skip_sync = True
                c.save()

                scr = c.dockercontainerscript()
                scr = scr.replace("\r\n", "{{br}}").replace("\n", "{{br}}").replace("\r", "{{br}}").replace("{{br}}", "\n")
                # .replace("\r\n", "{{br}}").replace("\n", "{{br}}").replace("\r", "{{br}}").replace("{{br}}", "\\n")
                cmd = "bash -c \"echo '" + scr + "' > ~/script.sh\""
                start = "bash /root/script.sh &"
                # print(cmd)
                try:
                    cmd_restart = client.containers.get(c.clientid).restart()
                    print("sync_docker::container_restart", cmd_restart, "::next_cmd::" + cmd)
                    # dolog("sync_docker::client_monitor", "script_update", "cont_restart", cmd_restart)
                    cmdout += "Restart Container: " + str(cmd_restart) + "\n"
                    cmd_res = client.containers.get(c.clientid).exec_run(cmd)
                    cmdout += "Execute Command: " + str(cmd) + "\n"
                    print("sync_docker::create_docker_containers::code_deploy", cmd_res)
                    cmdout += "Command Result: " + str(cmd_res) + "\n"
                    # if cmd_res.exit_code != 0:
                    #     dolog("client_monitor", "script_update", "error", cmd, cmd_res)
                    # else:
                    #     dolog("client_monitor", "script_update", "success", cmd, cmd_res)

                    start_res = client.containers.get(c.clientid).exec_run(start, detach=True)
                    print("sync_docker::create_docker_containers::script_start", start_res)
                    cmdout += "Start Script Result: " + str(cmd_res) + "\n"
                    # if start_res.exit_code != 0:
                    #     dolog("client_monitor", "script_update", "error", start, start_res)
                    # else:
                    #     dolog("client_monitor", "script_update", "success", start, start_res)

                    c.last_deployed_hash = c.dockercontainerscripthash()
                    c.skip_sync = True
                    c.last_sync_log = str(cmdout)
                    c.save()
                    print("sync_docker::create_docker_containers::done")
                except Exception as e:
                    print("sync_docker::script_update::exception", e)
                    # dolog("sync_docker_containers", "updating_container_script", "error", e)
                    cmdout += "Exception: " + str(e) + "\n"
        else:
            if c.force_script:
                c.force_script = False
                c.skip_sync = True
                c.save()

        # else:
        #     print("no script update", str(c.last_deployed_hash), str(c.dockercontainerscripthash()))


# Enable the job scheduler to run schedule jobs
cron = BackgroundScheduler()

# Explicitly kick off the background thread
cron.start()
cron.remove_all_jobs()
job0 = cron.add_job(sync_docker_clients)
job1 = cron.add_job(sync_docker_clients, 'interval', seconds=10)

# Shutdown your cron thread if the web process is stopped
atexit.register(lambda: cron.shutdown(wait=False))
