# import atexit
import docker
from docker import types
# from apscheduler.schedulers.background import BackgroundScheduler
from client_sim.models import *
from django.conf import settings
from django.utils.timezone import make_aware
from io import BytesIO
from django.db.models import F
from scripts.dblog import *
import traceback
import sys

# def dolog(fn, step, *txt):
#     l = Log.objects.create(function=fn, step=step, log=",".join(map(str, txt)))
#     l.save()


def check_parse_files(dockerfile, cmdout):
    ss = ServerSetting.objects.all()
    if len(ss) != 1:
        print("No ServerSetting defined (or multiple defined, which is not allowed). Not fixing up dockerfile...")
        return dockerfile
    df = dockerfile[:]
    # df = df.replace("{{workdir}}", str(os.path.dirname(os.path.realpath("manage.py"))) + "/upload")
    df.replace("COPY", "ADD")
    while df.find("{<") != -1:
        f_start = df.find("{<")
        f_end = df.find(">}", f_start)
        fn = df[f_start + 2:f_end]
        upload = Upload.objects.filter(file__endswith=fn)
        if len(upload) != 1:
            cmdout += "Unable to locate file '" + fn + "' in Uploads!"
            return None
        url = (ss[0].baseurl + "file/" + str(upload[0].id))
        df = df.replace("{<" + fn + ">}", url)
    return df


def create_docker_containers(client, containers, log, delete_existing=False):
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

        try:
            if c.container.containertype.name == "PUBLISHED":
                if c.network:
                    newcli = client.containers.run(c.container.path, c.container.cmd, network=c.network.dockernetwork(),
                                                   mac_address=c.macaddress, hostname=c.hostname,
                                                   name=c.dockercontainername(), detach=True, tty=True, remove=True)
                elif c.bridge:
                    newcli = client.containers.run(c.container.path, c.container.cmd, network=c.bridge.dockernetwork(),
                                                   mac_address=c.macaddress, hostname=c.hostname,
                                                   name=c.dockercontainername(), detach=True, tty=True, remove=True)

                # dolog("sync_docker_containers", "create_new_container_published", newcli)
                cmdout += "New Published Container " + str(newcli) + "\n"
            elif c.container.containertype.name == "DOCKERFILE":
                df = str(c.container.get_dockerfile()) + "\n"
                df = check_parse_files(df, cmdout)
                f = BytesIO(df.encode('utf-8'))
                try:
                    base_path = str(os.path.dirname(os.path.realpath("manage.py"))) + "/upload"
                    client2 = docker.APIClient(base_url='unix://var/run/docker.sock')
                    response = [line for line in client2.build(
                        fileobj=f, rm=True, tag=c.container.buildcontainername, path=base_path
                    )]
                    # newimg = client.images.build(fileobj=f, custom_context=True, tag=c.container.buildcontainername)
                    # dolog("sync_docker_containers", "create_new_image", "success", response)
                    # print("DOCKERFILE", c.container, str(response))
                    cmdout += "New Build Image " + str(response) + "\n"
                except Exception as e:
                    # print(sys.exc_info()[-1].tb_lineno, "\n", sys.exc_info())
                    # dolog("sync_docker_containers", "create_new_image", "error", e)
                    append_log(log, "sync_docker::create_docker_containers::exception re-creating container...", e,
                               traceback.print_exc())
                    cmdout += "Build Image Exception " + str(e) + "\n"
                try:
                    if c.bridge:
                        net = c.bridge.dockernetwork()
                    else:
                        net = c.network.dockernetwork()

                    # print(c.container.buildcontainername, cmd, net, c.macaddress, c.hostname, c.dockercontainername())

                    if c.container.cmd:
                        newcli = client.containers.run(c.container.buildcontainername, c.container.cmd,
                                                       network=net, ports=c.portbind,
                                                       mac_address=c.macaddress, hostname=c.hostname,
                                                       name=c.dockercontainername(),
                                                       detach=True, tty=True, remove=True)
                    else:
                        newcli = client.containers.run(c.container.buildcontainername,
                                                       network=net, ports=c.portbind,
                                                       mac_address=c.macaddress, hostname=c.hostname,
                                                       name=c.dockercontainername(),
                                                       detach=True, tty=True, remove=True)

                    # dolog("sync_docker_containers", "create_new_container_built", "success", newcli)
                    cmdout += "New Build Container " + str(newcli) + "\n"
                except Exception as e:
                    # print(sys.exc_info()[-1].tb_lineno, "\n", sys.exc_info())
                    # dolog("sync_docker_containers", "create_new_container_built", "error", e)
                    append_log(log, "sync_docker::create_docker_containers::exception re-creating container...", e,
                               traceback.print_exc())
                    cmdout += "Build Container Exception " + str(e) + "\n"
        except Exception as e:
            # print(sys.exc_info()[-1].tb_lineno, "\n", sys.exc_info())
            append_log(log, "sync_docker::create_docker_containers::exception re-creating container...", e, sys.exc_info())

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


def sync_container_ips(containers, log):
    client = docker.from_env()
    for c in containers:
        try:
            newcli = client.containers.get(c.clientid)
        except:
            append_log(log, "sync_docker::create_docker_containers::exception getting client id... clearing client id from db")
            c.clientid = None
            c.save()
            return None

        ipaddr = newcli.attrs['NetworkSettings']['IPAddress']
        if ipaddr is None or ipaddr == "":
            if c.network:
                ipaddr = newcli.attrs['NetworkSettings']['Networks'][c.network.dockernetwork()]['IPAddress']
            else:
                ipaddr = newcli.attrs['NetworkSettings']['Networks'][c.bridge.dockernetwork()]['IPAddress']
        # print("containerip", c.clientid, ipaddr)
        c.ipaddress = ipaddr
        c.skip_sync = True
        c.save()


def sync_docker_clients():
    docker_container_list = []
    log = []
    client = docker.from_env()
    try:
        dconts = client.containers.list()
    except Exception as e:
        append_log(log, "sync_docker_clients::exception getting Docker client list::is Docker installed and running?::", e)
        db_log("client_monitor", log)
        return ""

    append_log(log, "sync_docker_networks::full_docker_network_list::", dconts)
    # First, check to see if all relevant Docker clients exist in the database. If not, import them.
    for dn in dconts:
        docker_container_list.append(dn.id)
        containers = Client.objects.filter(clientid__iexact=dn.id)
        if len(containers) <= 0:
            append_log(log, "import_docker_containers_into_db", dn.id)
            dt = make_aware(datetime.datetime.now())
            Client.objects.create(clientid=dn.id, description="Imported from Docker", active=False, last_sync=dt, last_update=dt)

    # clear clientid for any container in db that doesn't actually exist in Docker
    clients = Client.objects.exclude(clientid__in=docker_container_list).update(clientid=None)

    # Second, check to see if there are any clients in database that do not exist in Docker
    conts = Client.objects.filter(clientid__isnull=True).filter(active=True)
    # print("missing clientid=", conts)
    append_log(log, "sync_docker::create_docker_containers::phase_1", conts)
    create_docker_containers(client, conts, log)

    # Last, see if any clients have been updated and need to be re-synced
    conts = Client.objects.all().exclude(last_sync=F('last_update'))
    # print("out of sync=", conts)
    append_log(log, "sync_docker::create_docker_containers::phase_2", conts)
    create_docker_containers(client, conts, log, delete_existing=True)

    # Next, check to see if there are any clients in database that are tagged with 'force_rebuild'
    conts = Client.objects.filter(force_rebuild=True)
    # print("force_rebuild=", conts)
    append_log(log, "sync_docker::create_docker_containers::phase_3", conts)
    create_docker_containers(client, conts, log, delete_existing=True)

    # Sync Container IPs
    sync_container_ips(Client.objects.all(), log)

    # Next, send script to client
    conts = Client.objects.filter(clientid__isnull=False)
    for c in conts:
        cmdout = ""
        if c.dockercontainerscripthash() != "":
            if (str(c.last_deployed_hash) != str(c.dockercontainerscripthash())) or c.force_script:
                append_log(log, "sync_docker::create_docker_containers::script_deployment", c)
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
                    append_log(log, "sync_docker::container_restart", cmd_restart, "::next_cmd::" + cmd)
                    # dolog("sync_docker::client_monitor", "script_update", "cont_restart", cmd_restart)
                    cmdout += "Restart Container: " + str(cmd_restart) + "\n"
                    cmd_res = client.containers.get(c.clientid).exec_run(cmd)
                    cmdout += "Execute Command: " + str(cmd) + "\n"
                    append_log(log, "sync_docker::create_docker_containers::code_deploy", cmd_res)
                    cmdout += "Command Result: " + str(cmd_res) + "\n"
                    # if cmd_res.exit_code != 0:
                    #     dolog("client_monitor", "script_update", "error", cmd, cmd_res)
                    # else:
                    #     dolog("client_monitor", "script_update", "success", cmd, cmd_res)

                    start_res = client.containers.get(c.clientid).exec_run(start, detach=True)
                    append_log(log, "sync_docker::create_docker_containers::script_start", start_res)
                    cmdout += "Start Script Result: " + str(cmd_res) + "\n"
                    # if start_res.exit_code != 0:
                    #     dolog("client_monitor", "script_update", "error", start, start_res)
                    # else:
                    #     dolog("client_monitor", "script_update", "success", start, start_res)

                    c.last_deployed_hash = c.dockercontainerscripthash()
                    c.skip_sync = True
                    c.last_sync_log = str(cmdout)
                    c.save()
                    append_log(log, "sync_docker::create_docker_containers::done")
                except Exception as e:
                    append_log(log, "sync_docker::script_update::exception", e)
                    # dolog("sync_docker_containers", "updating_container_script", "error", e)
                    cmdout += "Exception: " + str(e) + "\n"
        else:
            if c.force_script:
                c.force_script = False
                c.skip_sync = True
                c.save()

        # else:
        #     print("no script update", str(c.last_deployed_hash), str(c.dockercontainerscripthash()))

    db_log("client_monitor", log)


def delete_container(container_id):
    client = docker.from_env()
    log = []
    clients = Client.objects.filter(id=container_id)
    for n in clients:
        if n.clientid:
            client = client.containers.get(n.clientid)
            append_log(log, "delete_docker_container", n.clientid, client.name)
            client.remove()
        else:
            append_log(log, "delete_docker_client::No clientID. Doesn't exist?")

    db_log("client_monitor", log)


def run():
    sync_docker_clients()
