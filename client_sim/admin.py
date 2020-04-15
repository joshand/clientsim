from django.contrib import admin
from client_sim.models import *


class NetworkAdmin(admin.ModelAdmin):
    readonly_fields = ('networkid', 'last_update', 'last_sync', 'dockernetwork', 'hostnetwork', 'networkimpairmentscript', 'networkimpairmentscripthash', 'last_deployed_hash')


class ClientAdmin(admin.ModelAdmin):
    readonly_fields = ('clientid', 'last_update', 'last_sync', 'dockercontainername', 'dockercontainerscript', 'dockercontainerscripthash', 'last_deployed_hash', 'last_sync_log', 'ipaddress')


class CloudAdmin(admin.ModelAdmin):
    readonly_fields = ('last_update', 'last_sync', 'last_sync_log')


class CloudVPCAdmin(admin.ModelAdmin):
    # readonly_fields = ('last_update', 'last_sync', 'rawdata', 'cloudid', 'cidr', 'last_sync_log')

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['last_update', 'last_sync', 'rawdata', 'cloudid', 'cidr', 'last_sync_log']
        else:
            return ['last_update', 'last_sync', 'rawdata', 'cloudid', 'last_sync_log']


class CloudSubnetAdmin(admin.ModelAdmin):
    # readonly_fields = ('last_update', 'last_sync', 'rawdata', 'cloudid', 'cidr', 'last_sync_log')

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['last_update', 'last_sync', 'rawdata', 'cloudid', 'cidr', 'last_sync_log']
        else:
            return ['last_update', 'last_sync', 'rawdata', 'cloudid', 'last_sync_log']


class CloudInstanceAdmin(admin.ModelAdmin):
    # readonly_fields = ('last_update', 'last_sync', 'rawdata', 'cloudid', 'publicip', 'publicdns')

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['last_update', 'last_sync', 'rawdata', 'cloudid', 'privateip', 'publicip', 'publicdns', 'last_sync_log', 'imagesize', 'cloudimage', 'cloudsubnet', 'instanceautomationscript', 'instanceautomationscripthash', 'last_deployed_hash']
        else:
            return ['last_update', 'last_sync', 'rawdata', 'cloudid', 'privateip', 'publicip', 'publicdns', 'last_sync_log', 'instanceautomationscript', 'instanceautomationscripthash', 'last_deployed_hash']


class CloudSecurityGroupAdmin(admin.ModelAdmin):
    # readonly_fields = ('last_update', 'last_sync', 'rawdata', 'cloudid', 'inboundrules', 'outboundrules', 'last_sync_log')

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['last_update', 'last_sync', 'rawdata', 'cloudid', 'inboundrules', 'outboundrules', 'last_sync_log', 'cloudvpc']
        else:
            return ['last_update', 'last_sync', 'rawdata', 'cloudid', 'inboundrules', 'outboundrules', 'last_sync_log']


class CloudImageAdmin(admin.ModelAdmin):
    readonly_fields = ('last_update', 'last_sync', 'rawdata', 'description', 'last_sync_log')


class UploadAdmin(admin.ModelAdmin):
    readonly_fields = ('filedata', 'fspath')


class InstanceAutomationAdmin(admin.ModelAdmin):
    readonly_fields = ('getvariables', )


admin.site.register(Network, NetworkAdmin)
admin.site.register(Client, ClientAdmin)
admin.site.register(Upload, UploadAdmin)
admin.site.register(Cloud, CloudAdmin)
admin.site.register(CloudVPC, CloudVPCAdmin)
admin.site.register(CloudSubnet, CloudSubnetAdmin)
admin.site.register(CloudInstance, CloudInstanceAdmin)
admin.site.register(CloudSecurityGroup, CloudSecurityGroupAdmin)
admin.site.register(CloudImage, CloudImageAdmin)
admin.site.register(InstanceAutomation, InstanceAutomationAdmin)
# admin.site.register(Network)
# admin.site.register(Client)
# admin.site.register(Upload)

admin.site.register(NetworkType)
admin.site.register(ContainerType)
admin.site.register(Container)
admin.site.register(EventDay)
# admin.site.register(WANProfile)
# admin.site.register(WANEvent)
admin.site.register(LinkProfile)
admin.site.register(LinkEvent)
admin.site.register(Log)
admin.site.register(Interface)
admin.site.register(App)
admin.site.register(AppProfile)
admin.site.register(AppEvent)
admin.site.register(Dashboard)
admin.site.register(CloudType)
# admin.site.register(Cloud)
# admin.site.register(CloudVPC)
# admin.site.register(CloudSubnet)
# admin.site.register(CloudInstance)
# admin.site.register(CloudSecurityGroup)
# admin.site.register(CloudImage)
# admin.site.register(InstanceAutomation)
admin.site.register(Task)
