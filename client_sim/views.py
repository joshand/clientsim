from django.shortcuts import render
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from rest_framework import viewsets
from django.http import HttpResponseRedirect
from django.shortcuts import render
from .forms import UploadFileForm
from .models import *
from .serializers import *
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect, reverse, render
from django.contrib.auth import logout
import re
from scripts.interface_monitor import delete_bridge
from scripts.network_monitor import delete_network
from scripts.client_monitor import delete_container
import subprocess
import io
from django.views.decorators.clickjacking import xframe_options_exempt
from django.http import HttpResponse
from urllib.parse import urlparse


def dolanding(request):
    if not request.user.is_authenticated:
        return redirect('/login')

    return redirect("/home")


def show_home(request):
    ss = ServerSetting.objects.all()
    fullurl = request.build_absolute_uri().replace("/home", "")
    domain_port = urlparse(fullurl).netloc
    domain = domain_port.split(":")[0]
    if len(ss) == 0:
        ServerSetting.objects.create(baseurl=fullurl, ipaddress=domain)

    return render(request, 'home/home.html')


@xframe_options_exempt
def get_file(request):
    fileid = request.META['PATH_INFO'].split("/")[-1:][0]
    uploads = Upload.objects.filter(id=fileid)
    if len(uploads) == 1:
        response = HttpResponse(str(uploads[0].filedata()), content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="' + str(uploads[0].file) + '"'
    else:
        response = HttpResponse("", content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="untitled.txt"'

    return response


def status_ipaddr(request):
    out = subprocess.Popen(["ip", "addr"],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
    stdout, stderr = out.communicate()
    outtxt = stdout.decode("utf-8").replace("\n", "<br>")

    crumbs = '<li class="current">Status</li><li class="current">ip addr</li>'
    return render(request, 'home/status_cmd.html', {"crumbs": crumbs, "menuopen": 1, "data": outtxt, "cmd": "ip addr"})


def status_brctl(request):
    out = subprocess.Popen(["brctl", "show"],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
    stdout, stderr = out.communicate()
    outtxt = stdout.decode("utf-8").replace("\n", "<br>")

    crumbs = '<li class="current">Status</li><li class="current">brctl show</li>'
    return render(request, 'home/status_cmd.html', {"crumbs": crumbs, "menuopen": 1, "data": outtxt, "cmd": "brctl show"})


def status_dockernet(request):
    out = subprocess.Popen(["sudo", "docker", "network", "ls"],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
    stdout, stderr = out.communicate()
    outtxt = stdout.decode("utf-8").replace("\n", "<br>")

    crumbs = '<li class="current">Status</li><li class="current">docker network ls</li>'
    return render(request, 'home/status_cmd.html', {"crumbs": crumbs, "menuopen": 1, "data": outtxt, "cmd": "docker network ls"})


def status_dockerps(request):
    out = subprocess.Popen(["sudo", "docker", "ps"],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
    stdout, stderr = out.communicate()
    outtxt = stdout.decode("utf-8").replace("\n", "<br>")

    crumbs = '<li class="current">Status</li><li class="current">docker ps</li>'
    return render(request, 'home/status_cmd.html', {"crumbs": crumbs, "menuopen": 1, "data": outtxt, "cmd": "docker ps"})


def status_iwconfig(request):
    out = subprocess.Popen(["sudo", "iwconfig"],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
    stdout, stderr = out.communicate()
    outtxt = stdout.decode("utf-8").replace("\n", "<br>")

    crumbs = '<li class="current">Status</li><li class="current">iwconfig</li>'
    return render(request, 'home/status_cmd.html', {"crumbs": crumbs, "menuopen": 1, "data": outtxt, "cmd": "iwconfig"})


def config_int(request):
    if not request.user.is_authenticated:
        return redirect('/login')

    if request.method == 'POST':
        postvars = request.POST
        for v in postvars:
            if "intDesc-" in v:
                vid = v.replace("intDesc-", "")
                Interface.objects.filter(id=vid).update(description=request.POST.get(v))

    interfaces = Interface.objects.all()

    crumbs = '<li class="current">Configuration</li><li class="current">Interfaces</li>'
    return render(request, 'home/config_interface.html', {"crumbs": crumbs, "menuopen": 2, "data": interfaces})


def config_wireless(request):
    if not request.user.is_authenticated:
        return redirect('/login')

    if request.method == 'POST':
        postvars = request.POST
        prof_idlist = []
        for v in postvars:
            if "profDesc-" in v:
                vid = v.replace("profDesc-", "")
                prof_idlist.append(vid)

        for profid in prof_idlist:
            desc = request.POST.get("profDesc-" + profid)
            cfg = request.POST.get("profCfg-" + profid)
            if desc == "None" or desc == "": desc = None
            if cfg == "None" or cfg == "": cfg = None
            LinkProfile.objects.filter(id=profid).update(description=desc, tcdata=cfg)

    if request.GET.get("action") == "addprofile":
        LinkProfile.objects.create(description="New Profile", is_wireless=True)

    linkprofiles = LinkProfile.objects.filter(is_wireless=True)

    crumbs = '<li class="current">Configuration</li><li class="current">Wireless Profiles</li>'
    return render(request, 'home/config_wireless.html', {"crumbs": crumbs, "menuopen": 2, "data": linkprofiles})


def config_wired(request):
    if not request.user.is_authenticated:
        return redirect('/login')

    if request.method == 'POST':
        postvars = request.POST
        prof_idlist = []
        for v in postvars:
            if "profDesc-" in v:
                vid = v.replace("profDesc-", "")
                prof_idlist.append(vid)

        for profid in prof_idlist:
            desc = request.POST.get("profDesc-" + profid)
            cfg = request.POST.get("profCfg-" + profid)
            if desc == "None" or desc == "": desc = None
            if cfg == "None" or cfg == "": cfg = None
            LinkProfile.objects.filter(id=profid).update(description=desc, tcdata=cfg)

    if request.GET.get("action") == "addprofile":
        LinkProfile.objects.create(description="New Profile", is_wireless=True)

    linkprofiles = LinkProfile.objects.filter(is_wireless=False)

    crumbs = '<li class="current">Configuration</li><li class="current">Wired Profiles</li>'
    return render(request, 'home/config_wired.html', {"crumbs": crumbs, "menuopen": 2, "data": linkprofiles})


def config_ipam(request):
    if not request.user.is_authenticated:
        return redirect('/login')

    if request.method == 'POST':
        postvars = request.POST
        ipam_idlist = []
        for v in postvars:
            if "poolDesc-" in v:
                vid = v.replace("poolDesc-", "")
                ipam_idlist.append(vid)

        for itemid in ipam_idlist:
            desc = request.POST.get("poolDesc-" + itemid)
            subnet = request.POST.get("poolSub-" + itemid)
            gateway = request.POST.get("poolDG-" + itemid)
            addrpool = request.POST.get("poolPool-" + itemid)
            if desc == "None" or desc == "": desc = None
            if subnet == "None" or subnet == "": subnet = None
            if gateway == "None" or gateway == "": gateway = None
            if addrpool == "None" or addrpool == "": addrpool = None
            IPAMPool.objects.filter(id=itemid).update(description=desc, subnet=subnet, dg=gateway, addrpool=addrpool)

    if request.GET.get("action") == "addpool":
        intid = request.GET.get("id")
        IPAMPool.objects.create(description="New Pool")
    elif request.GET.get("action") == "delpool":
        poolid = request.GET.get("id")
        IPAMPool.objects.filter(id=poolid).delete()

    pools = IPAMPool.objects.all()

    crumbs = '<li class="current">Configuration</li><li class="current">Docker IP Pools</li>'
    return render(request, 'home/config_ipam.html', {"crumbs": crumbs, "menuopen": 2, "data": pools})


def config_vlan(request):
    if not request.user.is_authenticated:
        return redirect('/login')

    if request.method == 'POST':
        postvars = request.POST
        net_idlist = []
        bri_idlist = []
        for v in postvars:
            if "netVlan-" in v:
                vid = v.replace("netVlan-", "")
                net_idlist.append(vid)
            if "briDesc-" in v:
                bid = v.replace("briDesc-", "")
                bri_idlist.append(bid)

        for itemid in net_idlist:
            bridges = Network.objects.filter(id=itemid)[0].interface.bridge_set.all()
            # print(bridges)
            if len(bridges) > 0:
                is_active = False
            else:
                is_active = True
            vlan = request.POST.get("netVlan-" + itemid)
            desc = request.POST.get("netDesc-" + itemid)
            subnet = request.POST.get("netSub-" + itemid)
            gateway = request.POST.get("netDG-" + itemid)
            addrpool = request.POST.get("netPool-" + itemid)
            poolid = request.POST.get("netPool-id-" + itemid)
            profileid = request.POST.get("profileid-" + itemid)
            if vlan == "None" or vlan == "": vlan = None
            if desc == "None" or desc == "": desc = None
            if subnet == "None" or subnet == "": subnet = None
            if gateway == "None" or gateway == "": gateway = None
            if addrpool == "None" or addrpool == "": addrpool = None
            if poolid == "None" or poolid == "": poolid = None
            if profileid == "None" or profileid == "": profileid = None
            pools = IPAMPool.objects.filter(id=poolid)
            linkprofiles = LinkProfile.objects.filter(id=profileid)
            networks = Network.objects.filter(id=itemid)
            if len(networks) == 1:
                networks[0].dot1q = True
                networks[0].vlan = vlan
                networks[0].description = desc
                networks[0].active = is_active
                networks[0].subnet = subnet
                networks[0].dg = gateway
                networks[0].addrpool = addrpool
                if len(linkprofiles) == 1:
                    networks[0].linkprofile = linkprofiles[0]
                # if len(pools) == 1:
                #     networks[0].ippool = pools[0]
                networks[0].save()

        for itemid in bri_idlist:
            desc = request.POST.get("briDesc-" + itemid)
            profileid = request.POST.get("profileid-" + itemid)
            subnet = request.POST.get("briSub-" + itemid)
            gateway = request.POST.get("briDG-" + itemid)
            addrpool = request.POST.get("briPool-" + itemid)
            poolid = request.POST.get("briPool-id-" + itemid)
            if desc == "None" or desc == "": desc = None
            if profileid == "None" or profileid == "": profileid = None
            if subnet == "None" or subnet == "": subnet = None
            if gateway == "None" or gateway == "": gateway = None
            if addrpool == "None" or addrpool == "": addrpool = None
            if poolid == "None" or poolid == "": poolid = None
            pools = IPAMPool.objects.filter(id=poolid)
            linkprofiles = LinkProfile.objects.filter(id=profileid)
            bridges = Bridge.objects.filter(id=itemid)
            if len(bridges) == 1:
                bridges[0].description = desc
                bridges[0].subnet = subnet
                bridges[0].dg = gateway
                bridges[0].addrpool = addrpool
                if len(linkprofiles) == 1:
                    bridges[0].linkprofile = linkprofiles[0]
                # if len(pools) == 1:
                #     bridges[0].ippool = pools[0]
                bridges[0].save()

    if request.GET.get("action") == "addvlan":
        intid = request.GET.get("id")
        interface = Interface.objects.filter(id=intid)
        vlan = NetworkType.objects.filter(driver="macvlan")
        if interface and vlan:
            Network.objects.create(interface=interface[0], networktype=vlan[0], description="New Network", dot1q=True)
    elif request.GET.get("action") == "delvlan":
        netid = request.GET.get("id")
        delete_network(netid)
        Network.objects.filter(id=netid).delete()
    elif request.GET.get("action") == "makebridge":
        intid = request.GET.get("id")
        interface = Interface.objects.filter(id=intid)
        bridge = NetworkType.objects.filter(driver="bridge")

        if interface and bridge:
            Network.objects.filter(interface__id=intid).update(active=False)
            bridgename = "br" + re.sub("[^\d\.]", "", interface[0].name)
            Bridge.objects.update_or_create(interface=interface[0],
                                            defaults={"name": bridgename, "description": "Docker Bridge",
                                                      "networktype": bridge[0]})
    elif request.GET.get("action") == "delbridge":
        briid = request.GET.get("id")
        # delete_bridge(briid)
        Bridge.objects.filter(id=briid).delete()

    interfaces = Interface.objects.all()
    wireless_profiles = LinkProfile.objects.filter(is_wireless=True)
    wireled_profiles = LinkProfile.objects.filter(is_wireless=False)
    pools = IPAMPool.objects.all()

    crumbs = '<li class="current">Configuration</li><li class="current">Logical Interfaces (VLANs)</li>'
    return render(request, 'home/config_logical.html', {"crumbs": crumbs, "menuopen": 2, "data": interfaces,
                                                        "wireless_profiles": wireless_profiles,
                                                        "wired_profiles": wireled_profiles, "pools": pools})


def config_container(request):
    if not request.user.is_authenticated:
        return redirect('/login')

    if request.method == 'POST':
        postvars = request.POST
        cont_idlist = []
        for v in postvars:
            if "contHost-" in v:
                vid = v.replace("contHost-", "")
                cont_idlist.append(vid)
        for itemid in cont_idlist:
            desc = request.POST.get("contDesc-" + itemid)
            host = request.POST.get("contHost-" + itemid)
            mac = request.POST.get("contMac-" + itemid)
            imgid = request.POST.get("contImage-id-" + itemid)
            portjson = request.POST.get("contPort-" + itemid)
            netid = request.POST.get("contVlan-id-" + itemid)
            bridgeid = request.POST.get("contBridge-id-" + itemid)
            if desc == "None" or desc == "": desc = None
            if host == "None" or host == "": host = None
            if mac == "None" or mac == "": mac = None
            if imgid == "None" or imgid == "": imgid = None
            if portjson == "None" or portjson == "": portjson = {}
            if netid == "None" or netid == "": netid = None
            if bridgeid == "None" or bridgeid == "": bridgeid = None
            images = Container.objects.filter(id=imgid)
            networks = Network.objects.filter(id=netid)
            bridges = Bridge.objects.filter(id=bridgeid)
            cli = Client.objects.filter(id=itemid)
            if len(cli) == 1:
                client = cli[0]
                client.description = desc
                client.hostname = host
                client.macaddress = mac
                if networks:
                    client.network = networks[0]
                if bridges:
                    client.bridge = bridges[0]
                if images:
                    client.container = images[0]
                client.portbind = portjson
                client.save()

    if request.GET.get("action") == "addcontainer":
        newcli = Client.objects.create(description="New Container")
        apps = App.objects.all()
        for a in apps:
            newcli.app.add(a)
    elif request.GET.get("action") == "delcontainer":
        contid = request.GET.get("id")
        delete_container(contid)
        Client.objects.filter(id=contid).delete()

    containers = Client.objects.all()
    images = Container.objects.all()
    vlans = Network.objects.all()
    bridges = Bridge.objects.all()

    crumbs = '<li class="current">Configuration</li><li class="current">Docker Containers</li>'
    return render(request, 'home/config_container.html', {"crumbs": crumbs, "menuopen": 2, "data": containers,
                                                          "images": images, "vlans": vlans, "bridges": bridges})


def config_image(request):
    if not request.user.is_authenticated:
        return redirect('/login')

    if request.method == 'POST':
        postvars = request.POST
        img_idlist = []
        for v in postvars:
            if "imgDesc-" in v:
                vid = v.replace("imgDesc-", "")
                img_idlist.append(vid)

        for imgid in img_idlist:
            desc = request.POST.get("imgDesc-" + imgid)
            path = request.POST.get("imgPath-" + imgid)
            dockerfile = request.POST.get("imgDockerfile-" + imgid)
            buildname = request.POST.get("imgBuildname-" + imgid)
            cmd = request.POST.get("imgCmd-" + imgid)
            script = request.POST.get("imgScript-" + imgid)
            imgtypeid = request.POST.get("imgTypeid-" + imgid)
            if desc == "None" or desc == "": desc = None
            if path == "None" or path == "": path = None
            if dockerfile == "None" or dockerfile == "": dockerfile = None
            if buildname == "None" or buildname == "": buildname = None
            if cmd == "None" or cmd == "": cmd = None
            if script == "None" or script == "": script = None
            if imgtypeid == "None" or imgtypeid == "": imgtypeid = None
            imagetypes = ContainerType.objects.filter(id=imgtypeid)
            if len(imagetypes) > 0:
                Container.objects.filter(id=imgid).update(description=desc, path=path, dockerfile=dockerfile,
                                                          buildcontainername=buildname, cmd=cmd, clientscript=script,
                                                          containertype=imagetypes[0], active=True)
            else:
                Container.objects.filter(id=imgid).update(description=desc, path=path, dockerfile=dockerfile,
                                                          buildcontainername=buildname, cmd=cmd, clientscript=script,
                                                          active=True)

    img = None
    if request.GET.get("action") == "addimage":
        Container.objects.create(description="New Image")
    elif request.GET.get("action") == "delimage":
        imgid = request.GET.get("id")
        Container.objects.filter(id=imgid).delete()
    elif request.GET.get("action") == "editimage":
        imgid = request.GET.get("id")
        img = Container.objects.filter(id=imgid)

    if img:
        img = img[0]
        crumbs = '<li class="current">Configuration</li><li><a href="/home/config-image">Docker Images</a></li><li class="current">' + img.description + '</li>'
        images = ContainerType.objects.all()
    else:
        crumbs = '<li class="current">Configuration</li><li class="current">Docker Images</li>'
        images = Container.objects.all()

    return render(request, 'home/config_image.html', {"crumbs": crumbs, "menuopen": 2, "data": images, "image": img})


def upload_file(request):
    form = None
    if request.method == 'POST':
        postvars = request.POST
        file_idlist = []
        for v in postvars:
            if "fileDesc-" in v:
                vid = v.replace("fileDesc-", "")
                file_idlist.append(vid)

        if len(file_idlist) > 0:
            for fileid in file_idlist:
                desc = request.POST.get("fileDesc-" + fileid)
                fn = request.POST.get("fileName-" + fileid)
                contents = request.POST.get("fileContents-" + fileid)
                if desc == "None" or desc == "": desc = None
                if fn == "None" or fn == "": fn = None
                if contents == "None" or contents == "": contents = None
                Upload.objects.filter(id=fileid).update(description=desc)
                upl = Upload.objects.filter(id=fileid)

                if len(upl) == 1:
                    thisfn = str(upl[0].filename())
                    thisfpath = str(upl[0].fspath())

                    f = io.StringIO(contents)
                    os.remove(thisfpath)
                    upl[0].file.save(fn, f)
        else:
            form = UploadFileForm(request.POST, request.FILES)
            if form.is_valid():
                # instance = Upload(file=request.FILES['file'].file.read(), description=request.FILES['file'])
                # instance.save()
                form.save()
                return HttpResponseRedirect(reverse('upload'))
    else:
        form = UploadFileForm()

    file = None
    if request.GET.get("action") == "delupload":
        fileid = request.GET.get("id")
        Upload.objects.filter(id=fileid).delete()
    elif request.GET.get("action") == "editupload":
        fileid = request.GET.get("id")
        file = Upload.objects.filter(id=fileid)

    if file:
        file = file[0]
        uploads = None
        crumbs = '<li class="current">Configuration</li><li><a href="/home/config-upload">Upload Files</a></li><li class="current">' + str(file.file) + '</li>'
    else:
        uploads = Upload.objects.all()
        crumbs = '<li class="current">Configuration</li><li class="current">Upload Files</li>'

    return render(request, 'home/config_upload.html', {"crumbs": crumbs, "menuopen": 2, "form": form, "data": uploads, "file": file})


def show_log(request):
    cli_parm = request.GET.get("cli")
    cli = Client.objects.filter(id=cli_parm)
    if cli:
        clientid = cli[0].clientid
        client = docker.from_env()
        dlogs = client.containers.get(clientid).logs(until=120)
    else:
        dlogs = None
    return render(request, '../old/logs.html', {'logs': dlogs})


class MyLoginView(auth_views.LoginView):
    template_name = "general/login.html"

    def get_context_data(self, **kwargs):
        context = super(MyLoginView, self).get_context_data(**kwargs)
        return context

    def get_success_url(self):
        return reverse('landing')


class MyLogoutView(auth_views.LogoutView):
    def dispatch(self, request, *args, **kwargs):
        logout(request)
        return redirect('/')


class UploadViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Uploaded files to be viewed, edited or deleted.

    retrieve:
    Return an Uploaded file instance.

    list:
    Return all Uploaded files.
    """
    queryset = Upload.objects.all().order_by('description')
    serializer_class = UploadSerializer


class InstanceAutomationViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Instance Automations to be viewed, edited or deleted.

    retrieve:
    Return an Instance Automation.

    list:
    Return all Instance Automations.
    """
    queryset = InstanceAutomation.objects.all().order_by('description')
    serializer_class = InstanceAutomationSerializer


class CloudTypeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Cloud Types to be viewed, edited or deleted.

    retrieve:
    Return a Cloud Type.

    list:
    Return all Cloud Types.
    """
    queryset = CloudType.objects.all().order_by('description')
    serializer_class = CloudTypeSerializer


class CloudViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Clouds to be viewed, edited or deleted.

    retrieve:
    Return a Cloud.

    list:
    Return all Clouds.
    """
    queryset = Cloud.objects.all().order_by('last_update')
    serializer_class = CloudSerializer


class CloudImageViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Cloud Images to be viewed, edited or deleted.

    retrieve:
    Return a Cloud Image.

    list:
    Return all Cloud Images.
    """
    queryset = CloudImage.objects.all().order_by('last_update')
    serializer_class = CloudImageSerializer


class CloudVPCViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Cloud VPCs to be viewed, edited or deleted.

    retrieve:
    Return a Cloud VPC.

    list:
    Return all Cloud VPCs.
    """
    queryset = CloudVPC.objects.all().order_by('last_update')
    serializer_class = CloudVPCSerializer


class CloudSubnetViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Cloud Subnets to be viewed, edited or deleted.

    retrieve:
    Return a Cloud Subnet.

    list:
    Return all Cloud Subnets.
    """
    queryset = CloudSubnet.objects.all().order_by('last_update')
    serializer_class = CloudSubnetSerializer


class CloudSecurityGroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Cloud Security Groups to be viewed, edited or deleted.

    retrieve:
    Return a Cloud Security Group.

    list:
    Return all Cloud Security Groups.
    """
    queryset = CloudSecurityGroup.objects.all().order_by('last_update')
    serializer_class = CloudSecurityGroupSerializer


class CloudInstanceViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Cloud Instances to be viewed, edited or deleted.

    retrieve:
    Return a Cloud Instance.

    list:
    Return all Cloud Instances.
    """
    queryset = CloudInstance.objects.all().order_by('last_update')
    serializer_class = CloudInstanceSerializer


class DashboardViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Meraki Dashboard Instances to be viewed, edited or deleted.

    retrieve:
    Return a Meraki Dashboard Instance.

    list:
    Return all Meraki Dashboard Instances.
    """
    queryset = Dashboard.objects.all().order_by('description')
    serializer_class = DashboardSerializer


class DashboardLicenseViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Meraki Dashboard Licenses to be viewed, edited or deleted.

    retrieve:
    Return a Meraki Dashboard License.

    list:
    Return all Meraki Dashboard Licenses.
    """
    queryset = DashboardLicense.objects.all().order_by('license')
    serializer_class = DashboardLicenseSerializer


# class LogViewSet(viewsets.ModelViewSet):
#     """
#     API endpoint that allows Log entries to be viewed, edited or deleted.
#
#     retrieve:
#     Return a Log entry.
#
#     list:
#     Return all Log entries.
#     """
#     queryset = Log.objects.all().order_by('dt')
#     serializer_class = LogSerializer


class NetworkTypeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Network Types to be viewed, edited or deleted.

    retrieve:
    Return a Network Type.

    list:
    Return all Network Types.
    """
    queryset = NetworkType.objects.all().order_by('description')
    serializer_class = NetworkTypeSerializer


class InterfaceViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Interfaces to be viewed, edited or deleted.

    retrieve:
    Return an Interface.

    list:
    Return all Interfaces.
    """
    queryset = Interface.objects.all().order_by('description')
    serializer_class = InterfaceSerializer


class BridgeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Bridges to be viewed, edited or deleted.

    retrieve:
    Return a Bridge.

    list:
    Return all Bridges.
    """
    queryset = Bridge.objects.all().order_by('description')
    serializer_class = BridgeSerializer


class ContainerTypeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Container Types to be viewed, edited or deleted.

    retrieve:
    Return a Container Type.

    list:
    Return all Container Types.
    """
    queryset = ContainerType.objects.all().order_by('description')
    serializer_class = ContainerTypeSerializer


class ContainerViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Containers to be viewed, edited or deleted.

    retrieve:
    Return a Container.

    list:
    Return all Containers.
    """
    queryset = Container.objects.all().order_by('id')
    serializer_class = ContainerSerializer


class NetworkViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Networks to be viewed, edited or deleted.

    retrieve:
    Return a Network.

    list:
    Return all Networks.
    """
    queryset = Network.objects.all().order_by('description')
    serializer_class = NetworkSerializer


class AppViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Apps to be viewed, edited or deleted.

    retrieve:
    Return an App.

    list:
    Return all Apps.
    """
    queryset = App.objects.all().order_by('description')
    serializer_class = AppSerializer


class AppProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows App Profiles to be viewed, edited or deleted.

    retrieve:
    Return an App Profile.

    list:
    Return all App Profiles.
    """
    queryset = AppProfile.objects.all().order_by('description')
    serializer_class = AppProfileSerializer


class ClientViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Clients to be viewed, edited or deleted.

    retrieve:
    Return a Client.

    list:
    Return all Clients.
    """
    queryset = Client.objects.all().order_by('description')
    serializer_class = ClientSerializer


class LinkProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Link Profiles to be viewed, edited or deleted.

    retrieve:
    Return a Link Profile.

    list:
    Return all Link Profiles.
    """
    queryset = LinkProfile.objects.all().order_by('description')
    serializer_class = LinkProfileSerializer


class EventDayViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Event Days to be viewed, edited or deleted.

    retrieve:
    Return an Event Day.

    list:
    Return all Event Days.
    """
    queryset = EventDay.objects.all().order_by('daynum')
    serializer_class = EventDaySerializer


class LinkEventViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Link Events to be viewed, edited or deleted.

    retrieve:
    Return a Link Event.

    list:
    Return all Link Events.
    """
    queryset = LinkEvent.objects.all().order_by('id')
    serializer_class = LinkEventSerializer


class AppEventViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows App Events to be viewed, edited or deleted.

    retrieve:
    Return an App Event.

    list:
    Return all App Events.
    """
    queryset = AppEvent.objects.all().order_by('id')
    serializer_class = AppEventSerializer


class TaskViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows System Tasks to be viewed.

    retrieve:
    Return a task.

    list:
    Return all tasks.
    """
    queryset = Task.objects.all().order_by('last_update')
    serializer_class = TaskSerializer


class ServerSettingsViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Server Settings to be viewed.

    retrieve:
    Return a Server Setting.

    list:
    Return all Server Settings.
    """
    queryset = ServerSetting.objects.all()
    serializer_class = ServerSettingSerializer
