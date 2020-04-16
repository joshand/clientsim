from rest_framework import serializers
from .models import *


class UploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Upload
        fields = ('id', 'url', 'description', 'file', 'uploaded_at')
        read_only_fields = ('id', 'url', 'uploaded_at')


class InstanceAutomationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstanceAutomation
        fields = ('id', 'url', 'description', 'rawdata')
        read_only_fields = ('id', 'url', 'rawdata')


class CloudTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CloudType
        fields = ('id', 'url', 'description')
        read_only_fields = ('id', 'url')


class CloudSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cloud
        fields = ('id', 'url', 'cloudtype', 'key', 'secret', 'zone', 'vpc', 'publickey', 'force_rebuild', 'skip_sync', 'last_update', 'last_sync', 'last_sync_log')
        read_only_fields = ('id', 'url', 'last_update', 'last_sync', 'last_sync_log')


class CloudImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CloudImage
        fields = ('id', 'url', 'description', 'default_username', 'cloudid', 'rawdata', 'skip_sync', 'last_update', 'last_sync', 'last_sync_log')
        read_only_fields = ('id', 'url', 'cloudid', 'rawdata', 'last_update', 'last_sync', 'last_sync_log')


class CloudVPCSerializer(serializers.ModelSerializer):
    class Meta:
        model = CloudVPC
        fields = ('id', 'url', 'cloud', 'cidr', 'description', 'cloudid', 'rawdata', 'skip_sync', 'last_update', 'last_sync', 'last_sync_log')
        read_only_fields = ('id', 'url', 'cloudid', 'rawdata', 'last_update', 'last_sync', 'last_sync_log')


class CloudSubnetSerializer(serializers.ModelSerializer):
    class Meta:
        model = CloudSubnet
        fields = ('id', 'url', 'cloud', 'vpc', 'cidr', 'description', 'cloudid', 'rawdata', 'assign_public_ip', 'skip_sync', 'last_update', 'last_sync', 'last_sync_log')
        read_only_fields = ('id', 'url', 'cloudid', 'rawdata', 'last_update', 'last_sync', 'last_sync_log')


class CloudSecurityGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CloudSecurityGroup
        fields = ('id', 'url', 'cloud', 'description', 'cloudvpc', 'cloudid', 'rawdata', 'skip_sync', 'last_update', 'last_sync', 'last_sync_log')
        read_only_fields = ('id', 'url', 'cloudid', 'rawdata', 'last_update', 'last_sync', 'last_sync_log')


class CloudInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CloudInstance
        fields = ('id', 'url', 'cloud', 'cloudimage', 'instanceautomation', 'automationvars', 'cloudsubnet', 'cloudsecuritygroup', 'srcdstcheck', 'username', 'description', 'publicip', 'publicdns', 'privateip', 'cloudid', 'imagesize', 'userdata', 'prevuserdata', 'rawdata', 'force_script', 'skip_sync', 'last_update', 'last_sync', 'last_sync_log', 'last_deployed_hash', 'instanceautomationscript', 'instanceautomationscripthash')
        read_only_fields = ('id', 'url', 'publicip', 'publicdns', 'privateip', 'cloudid', 'prevuserdata', 'rawdata', 'last_update', 'last_sync', 'last_sync_log', 'last_deployed_hash', 'instanceautomationscript', 'instanceautomationscripthash')


class DashboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dashboard
        fields = ('id', 'url', 'description', 'baseurl', 'apikey', 'orgid', 'netid', 'username', 'password')
        read_only_fields = ('id', 'url')


class DashboardLicenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardLicense
        fields = ('id', 'url', 'license', 'dashboard')
        read_only_fields = ('id', 'url')


# class LogSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Log
#         fields = ('id', 'url', 'dt', 'function', 'step', 'log')
#         read_only_fields = ('id', 'url')


class NetworkTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetworkType
        fields = ('id', 'url', 'driver', 'description')
        read_only_fields = ('id', 'url')


class InterfaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interface
        fields = ('id', 'url', 'name', 'macaddress', 'description')
        read_only_fields = ('id', 'url', 'name', 'macaddress')


class BridgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bridge
        fields = ('id', 'url', 'name', 'interface', 'description')
        read_only_fields = ('id', 'url')


class ContainerTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContainerType
        fields = ('id', 'url', 'name', 'description')
        read_only_fields = ('id', 'url')


class ContainerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Container
        fields = ('id', 'url', 'containertype', 'path', 'cmd', 'dockerfile', 'buildcontainername', 'clientscript', 'description', 'active')
        read_only_fields = ('id', 'url')


class NetworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Network
        fields = ('id', 'url', 'interface', 'networktype', 'vlan', 'subnet', 'dg', 'addrpool', 'networkid', 'description', 'active', 'force_script', 'skip_sync', 'last_update', 'last_sync', 'last_deployed_hash', 'dockernetwork', 'hostnetwork', 'networkimpairmentscript', 'networkimpairmentscripthash')
        read_only_fields = ('id', 'url', 'last_update', 'last_sync', 'last_deployed_hash', 'dockernetwork', 'hostnetwork', 'networkimpairmentscript', 'networkimpairmentscripthash')


class AppSerializer(serializers.ModelSerializer):
    class Meta:
        model = App
        fields = ('id', 'url', 'description', 'appurl')
        read_only_fields = ('id', 'url')


class AppProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppProfile
        fields = ('id', 'url', 'description', 'pdelay')
        read_only_fields = ('id', 'url')


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ('id', 'url', 'network', 'dashboard', 'container', 'ipaddress', 'macaddress', 'hostname', 'clientid', 'description', 'useragent', 'app', 'active', 'force_rebuild', 'force_script', 'skip_sync', 'last_update', 'last_sync', 'last_sync_log', 'last_deployed_hash', 'dockercontainername', 'dockercontainerscript', 'dockercontainerscripthash')
        read_only_fields = ('id', 'url', 'skip_sync', 'last_update', 'last_sync', 'last_sync_log', 'last_deployed_hash', 'dockercontainername', 'dockercontainerscript', 'dockercontainerscripthash')


class LinkProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = LinkProfile
        fields = ('id', 'url', 'description', 'default_profile', 'tcdata')
        read_only_fields = ('id', 'url')


class EventDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = EventDay
        fields = ('id', 'url', 'daynum', 'dayname')
        read_only_fields = ('id', 'url')


class LinkEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = LinkEvent
        fields = ('id', 'url', 'day', 'starttime', 'endtime', 'network', 'linkprofile')
        read_only_fields = ('id', 'url')


class AppEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppEvent
        fields = ('id', 'url', 'day', 'starttime', 'endtime', 'app', 'appprofile')
        read_only_fields = ('id', 'url')


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ('id', 'url', 'description', 'task_data', 'last_update')
        read_only_fields = ('id', 'url', 'description', 'task_data', 'last_update')


class ServerSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServerSetting
        fields = ('id', 'url', 'ipaddress')
        read_only_fields = ('id', 'url')
