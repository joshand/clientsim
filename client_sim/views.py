from django.shortcuts import render
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from rest_framework import viewsets
from django.http import HttpResponseRedirect
from django.shortcuts import render
from .forms import UploadFileForm
from .models import *
from .serializers import *


def show_home(request):
    return render(request, 'home.html')


def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            # instance = Upload(file=request.FILES['file'].file.read(), description=request.FILES['file'])
            # instance.save()
            form.save()
            return HttpResponseRedirect('/upload/')
    else:
        form = UploadFileForm()
    return render(request, 'upload.html', {'form': form})


def show_log(request):
    cli_parm = request.GET.get("cli")
    cli = Client.objects.filter(id=cli_parm)
    if cli:
        clientid = cli[0].clientid
        client = docker.from_env()
        dlogs = client.containers.get(clientid).logs(until=120)
    else:
        dlogs = None
    return render(request, 'logs.html', {'logs': dlogs})


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


class LogViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Log entries to be viewed, edited or deleted.

    retrieve:
    Return a Log entry.

    list:
    Return all Log entries.
    """
    queryset = Log.objects.all().order_by('dt')
    serializer_class = LogSerializer


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
    queryset = ServerSetting.objects.all().order_by('last_update')
    serializer_class = ServerSettingSerializer
