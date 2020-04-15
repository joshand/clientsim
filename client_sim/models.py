from django.db import models
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
import uuid
import docker
import random
import string
from django.conf import settings
import json
import datetime
import django.utils.timezone
import re
import hashlib
from django.utils.timezone import make_aware
import requests
import boto3
from django.db.models import Q
from rest_framework import authentication


class BearerAuthentication(authentication.TokenAuthentication):
    """
    Simple token based authentication using utvsapitoken.

    Clients should authenticate by passing the token key in the 'Authorization'
    HTTP header, prepended with the string 'Bearer '.  For example:

        Authorization: Bearer 1234567890abcdefghijklmnopqrstuvwxyz1234
    """
    keyword = 'Bearer'


"""
root@photon-mi-team [ ~ ]# docker network ls
NETWORK ID          NAME                DRIVER              SCOPE
0dfa7ef44d99        bridge              bridge              local
1a26017c1aa7        host                host                local
74bd7344b343        macvlan40           macvlan             local
1ffc5dc56a8b        macvlan50           macvlan             local
ced3dce58346        macvlan440          macvlan             local
14c88f3b8ae2        macvlan450          macvlan             local
def5adeaa128        none                null                local
"""


def dolog(fn, step, *txt):
    l = Log.objects.create(function=fn, step=step, log=",".join(map(str, txt)))
    l.save()


def fix_up_command(cmd):
    outcmd = cmd
    while "{{" in outcmd:
        fn = outcmd[outcmd.find("{{")+2:outcmd.find("}}")]
        u = Upload.objects.filter(Q(file=fn) | Q(description=fn))
        if len(u) > 0:
            contents = u[0].filedata().replace("\r\n", "{{br}}").replace("\n", "{{br}}").replace("\r", "{{br}}").replace("{{br}}", "\\n")
            contents = contents.replace("{{", "<~<").replace("}}", ">~>")
            outcmd = outcmd.replace("{{" + fn + "}}", "\\n" + contents + "\\n")

    return outcmd.replace("<~<", "{{").replace(">~>", "}}")


class Upload(models.Model):
    description = models.CharField(max_length=255, blank=True)
    # file = models.BinaryField(editable=False)
    file = models.FileField(upload_to='.')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.description

    def filedata(self):
        try:
            try:
                return self.file.read().decode("utf-8")
            except:
                return self.file.read()
        except:
            return self.file

    def fspath(self):
        return "/opt/files/" + self.file.name


@receiver(post_save, sender=Upload)
def post_save_upload(sender, instance=None, created=False, **kwargs):
    post_save.disconnect(post_save_upload, sender=Upload)
    instance.description = str(instance.file)
    instance.save()
    post_save.connect(post_save_upload, sender=Upload)


class InstanceAutomation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    description = models.CharField("Shell Commands", max_length=100, blank=False, null=False)
    rawdata = models.TextField(blank=True, null=True, default=None)

    def __str__(self):
        return self.description

    def getvariables(self):
        try:
            fixcmd = fix_up_command(self.rawdata)
            outlist = []
            outdict = {}
            while "{{" in fixcmd and "}}" in fixcmd:
                outvar = fixcmd[fixcmd.find("{{")+2:fixcmd.find("}}")]
                outlist.append(outvar)
                outdict[outvar] = ''
                fixcmd = fixcmd.replace("{{" + outvar + "}}", "")

            return json.dumps(outdict)
        except:
            return ""


class CloudType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    description = models.CharField("Dashboard Integration Description", max_length=100, blank=False, null=False)

    def __str__(self):
        return self.description


class Cloud(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    description = models.CharField("Dashboard Integration Description", max_length=100, blank=False, null=False)
    cloudtype = models.ForeignKey(CloudType, on_delete=models.SET_NULL, null=True, blank=False, default=None)
    key = models.CharField("Access Key", max_length=100, blank=True, null=True, default=None)
    secret = models.CharField("Access Secret", max_length=100, blank=True, null=True, default=None)
    zone = models.CharField("Availability Zone", max_length=100, blank=True, null=True, default=None)
    vpc = models.CharField("VPC", max_length=100, blank=True, null=True, default=None)
    publickey = models.ForeignKey(Upload, on_delete=models.SET_NULL, null=True, blank=True, default=None)
    force_rebuild = models.BooleanField("Force Cloud Sync", default=False, editable=True)
    skip_sync = models.BooleanField(default=False, editable=False)
    last_update = models.DateTimeField(default=django.utils.timezone.now)
    last_sync = models.DateTimeField(null=True, default=None, blank=True)
    last_sync_log = models.TextField(blank=True, null=True, default=None)

    def __str__(self):
        return self.description


@receiver(post_save, sender=Cloud)
def post_save_cloud(sender, instance=None, created=False, **kwargs):
    post_save.disconnect(post_save_cloud, sender=Cloud)
    if not instance.skip_sync:
        instance.last_update = make_aware(datetime.datetime.now())
        instance.save()
    else:
        instance.skip_sync = False
        instance.save()
    post_save.connect(post_save_cloud, sender=Cloud)


class CloudImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cloud = models.ForeignKey(Cloud, on_delete=models.SET_NULL, null=True, blank=False, default=None)
    description = models.CharField(max_length=100, blank=True, null=True, default=None)
    default_username = models.CharField(max_length=100, blank=True, null=True, default=None)
    cloudid = models.CharField(max_length=100, blank=True, null=True, default=None)
    rawdata = models.TextField(blank=True, null=True, default=None)
    skip_sync = models.BooleanField(default=False, editable=False)
    last_update = models.DateTimeField(default=django.utils.timezone.now)
    last_sync = models.DateTimeField(null=True, default=None, blank=True)
    last_sync_log = models.TextField(blank=True, null=True, default=None)

    def __str__(self):
        if self.description:
            return self.cloudid + " (" + self.description + ")"
        else:
            return self.cloudid


@receiver(post_save, sender=CloudImage)
def post_save_cloudimage(sender, instance=None, created=False, **kwargs):
    post_save.disconnect(post_save_cloudimage, sender=CloudImage)
    if not instance.skip_sync:
        instance.last_update = make_aware(datetime.datetime.now())
        instance.save()
    else:
        instance.skip_sync = False
        instance.save()
    post_save.connect(post_save_cloudimage, sender=CloudImage)


class CloudVPC(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cloud = models.ForeignKey(Cloud, on_delete=models.SET_NULL, null=True, blank=False, default=None)
    cidr = models.CharField(max_length=20, blank=True, null=True, default=None)
    description = models.CharField(max_length=100, blank=True, null=True, default=None)
    cloudid = models.CharField(max_length=100, blank=True, null=True, default=None)
    rawdata = models.TextField(blank=True, null=True, default=None)
    skip_sync = models.BooleanField(default=False, editable=False)
    last_update = models.DateTimeField(default=django.utils.timezone.now)
    last_sync = models.DateTimeField(null=True, default=None, blank=True)
    last_sync_log = models.TextField(blank=True, null=True, default=None)

    def __str__(self):
        if self.cloudid:
            return self.cloudid + " (" + self.cidr + " || " + self.description + ")"
        else:
            return "(" + self.cidr + " || " + self.description + ")"


@receiver(post_save, sender=CloudVPC)
def post_save_cloudvpc(sender, instance=None, created=False, **kwargs):
    post_save.disconnect(post_save_cloudvpc, sender=CloudVPC)
    if not instance.skip_sync:
        instance.last_update = make_aware(datetime.datetime.now())
        instance.save()
    else:
        instance.skip_sync = False
        instance.save()
    post_save.connect(post_save_cloudvpc, sender=CloudVPC)


@receiver(pre_delete, sender=CloudVPC)
def pre_delete_cloudvpc(sender, instance=None, created=False, **kwargs):
    if instance.cloudid:
        pre_delete.disconnect(pre_delete_cloudvpc, sender=CloudVPC)
        try:
            ec2 = boto3.client('ec2', region_name=instance.cloud.zone,
                               aws_access_key_id=instance.cloud.key,
                               aws_secret_access_key=instance.cloud.secret)

            response = ec2.delete_vpc(
                VpcId=instance.cloudid,
            )
            dolog("pre_delete_cloudvpc", "pre_delete_cloudvpc", response)
        except Exception as e:
            print("Error removing VPC", e)
        pre_delete.connect(pre_delete_cloudvpc, sender=CloudVPC)


class CloudSubnet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cloud = models.ForeignKey(Cloud, on_delete=models.SET_NULL, null=True, blank=False, default=None)
    vpc = models.ForeignKey(CloudVPC, on_delete=models.SET_NULL, null=True, blank=False, default=None)
    cidr = models.CharField(max_length=20, blank=True, null=True, default=None)
    description = models.CharField(max_length=100, blank=True, null=True, default=None)
    cloudid = models.CharField(max_length=100, blank=True, null=True, default=None)
    rawdata = models.TextField(blank=True, null=True, default=None)
    assign_public_ip = models.BooleanField(default=True, editable=True)
    skip_sync = models.BooleanField(default=False, editable=False)
    last_update = models.DateTimeField(default=django.utils.timezone.now)
    last_sync = models.DateTimeField(null=True, default=None, blank=True)
    last_sync_log = models.TextField(blank=True, null=True, default=None)

    def __str__(self):
        if self.cloudid:
            return self.vpc.cloudid + "/" + self.cloudid + " (" + self.cidr + " || " + self.description + ")"
        else:
            return self.vpc.cloudid + " (" + self.cidr + " || " + self.description + ")"


@receiver(post_save, sender=CloudSubnet)
def post_save_cloudsubnet(sender, instance=None, created=False, **kwargs):
    post_save.disconnect(post_save_cloudsubnet, sender=CloudSubnet)
    if not instance.skip_sync:
        instance.last_update = make_aware(datetime.datetime.now())
        instance.save()
    else:
        instance.skip_sync = False
        instance.save()
    post_save.connect(post_save_cloudsubnet, sender=CloudSubnet)


@receiver(pre_delete, sender=CloudSubnet)
def pre_delete_cloudsubnet(sender, instance=None, created=False, **kwargs):
    if instance.cloudid:
        pre_delete.disconnect(pre_delete_cloudsubnet, sender=CloudSubnet)
        try:
            ec2 = boto3.client('ec2', region_name=instance.cloud.zone,
                               aws_access_key_id=instance.cloud.key,
                               aws_secret_access_key=instance.cloud.secret)

            response = ec2.delete_subnet(
                SubnetId=instance.cloudid,
            )
            dolog("pre_delete_cloudsubnet", "pre_delete_cloudsubnet", response)
        except Exception as e:
            print("Error removing Subnet", e)
        pre_delete.connect(pre_delete_cloudsubnet, sender=CloudSubnet)


def aws_sg_parser(rulelist):
    out = ""
    for r in rulelist:
        if r["IpProtocol"] == "-1":
            prefix = "permit ip"
        else:
            prefix = "permit " + r["IpProtocol"]

        if "FromPort" in r:
            if r["FromPort"] == r["ToPort"]:
                portseq = " eq " + str(r["FromPort"])
            else:
                portseq = " range " + str(r["FromPort"]) + " " + str(r["ToPort"])
        else:
            portseq = " any"

        for v4 in r["IpRanges"]:
            desc = ""
            if "Description" in v4:
                desc = " remark " + v4["Description"]
            out += prefix + " " + v4["CidrIp"] + portseq + desc + "\n"
        for v6 in r["Ipv6Ranges"]:
            desc = ""
            if "Description" in v6:
                desc = " remark " + v6["Description"]
            out += prefix + " " + v6["CidrIpv6"] + portseq + desc + "\n"
        for g in r["UserIdGroupPairs"]:
            desc = ""
            if "Description" in g:
                desc = " remark " + g["Description"]
            out += prefix + " " + g["GroupId"] + portseq + desc + "\n"

    return out


class CloudSecurityGroup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cloud = models.ForeignKey(Cloud, on_delete=models.SET_NULL, null=True, blank=False, default=None)
    description = models.CharField(max_length=100, blank=True, null=True, default=None)
    cloudvpc = models.ForeignKey(CloudVPC, on_delete=models.SET_NULL, null=True, blank=False, default=None)
    cloudid = models.CharField(max_length=100, blank=True, null=True, default=None)
    rawdata = models.TextField(blank=True, null=True, default=None)
    skip_sync = models.BooleanField(default=False, editable=False)
    last_update = models.DateTimeField(default=django.utils.timezone.now)
    last_sync = models.DateTimeField(null=True, default=None, blank=True)
    last_sync_log = models.TextField(blank=True, null=True, default=None)

    def __str__(self):
        return self.cloudid + " (" + self.description + ")"

    def inboundrules(self):
        rules = json.loads(self.rawdata.replace("'", '"'))["IpPermissions"]
        return aws_sg_parser(rules)

    def outboundrules(self):
        rules = json.loads(self.rawdata.replace("'", '"'))["IpPermissionsEgress"]
        return aws_sg_parser(rules)


@receiver(post_save, sender=CloudSecurityGroup)
def post_save_cloudsecuritygroup(sender, instance=None, created=False, **kwargs):
    post_save.disconnect(post_save_cloudsecuritygroup, sender=CloudSecurityGroup)
    if not instance.skip_sync:
        instance.last_update = make_aware(datetime.datetime.now())
        instance.save()
    else:
        instance.skip_sync = False
        instance.save()
    post_save.connect(post_save_cloudsecuritygroup, sender=CloudSecurityGroup)


@receiver(pre_delete, sender=CloudSecurityGroup)
def pre_delete_cloudsecuritygroup(sender, instance=None, created=False, **kwargs):
    if instance.cloudid:
        pre_delete.disconnect(pre_delete_cloudsecuritygroup, sender=CloudSecurityGroup)
        try:
            ec2 = boto3.client('ec2', region_name=instance.cloud.zone,
                               aws_access_key_id=instance.cloud.key,
                               aws_secret_access_key=instance.cloud.secret)

            response = ec2.delete_security_group(
                GroupId=instance.cloudid,
            )
            dolog("pre_delete_cloudsecuritygroup", "pre_delete_cloudsecuritygroup", response)
        except Exception as e:
            print("Error removing Subnet", e)
        pre_delete.connect(pre_delete_cloudsecuritygroup, sender=CloudSecurityGroup)


class CloudInstance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cloud = models.ForeignKey(Cloud, on_delete=models.SET_NULL, null=True, blank=False, default=None)
    cloudimage = models.ForeignKey(CloudImage, on_delete=models.SET_NULL, null=True, blank=False, default=None)
    instanceautomation = models.ForeignKey(InstanceAutomation, on_delete=models.SET_NULL, null=True, blank=True, default=None)
    automationvars = models.TextField(blank=True, null=True, default=None)
    # cloudvpc = models.ForeignKey(CloudVPC, on_delete=models.SET_NULL, null=True, blank=False, default=None)
    cloudsubnet = models.ForeignKey(CloudSubnet, on_delete=models.SET_NULL, null=True, blank=False, default=None)
    cloudsecuritygroup = models.ManyToManyField(CloudSecurityGroup, blank=True)
    srcdstcheck = models.BooleanField(default=True, editable=True)
    username = models.CharField(max_length=100, blank=True, null=True, default=None)
    description = models.CharField(max_length=100, blank=True, null=True, default=None)
    publicip = models.CharField(max_length=100, blank=True, null=True, default=None)
    publicdns = models.CharField(max_length=100, blank=True, null=True, default=None)
    privateip = models.CharField(max_length=100, blank=True, null=True, default=None)
    cloudid = models.CharField(max_length=100, blank=True, null=True, default=None)
    imagesize = models.CharField(max_length=100, blank=True, null=True, default=None)
    userdata = models.TextField(blank=True, null=True, default=None)
    prevuserdata = models.TextField(blank=True, null=True, default=None, editable=False)
    rawdata = models.TextField(blank=True, null=True, default=None)
    force_script = models.BooleanField("Force Instance Script Update", default=False, editable=True)
    skip_sync = models.BooleanField(default=False, editable=False)
    last_update = models.DateTimeField(default=django.utils.timezone.now)
    last_sync = models.DateTimeField(null=True, default=None, blank=True)
    last_sync_log = models.TextField(blank=True, null=True, default=None)
    last_deployed_hash = models.CharField(max_length=32, blank=True, null=True, default=None)

    def __str__(self):
        if self.cloudid:
            return self.cloudid + " (" + self.description + ")"
        else:
            return self.description

    def instanceautomationscript(self):
        return fix_up_command(self.instanceautomation.rawdata)

    def instanceautomationscripthash(self):
        if self.instanceautomationscript() is None or self.instanceautomationscript() == "":
            return ""
        else:
            return hashlib.md5(self.instanceautomationscript().encode("utf-8")).hexdigest()


@receiver(post_save, sender=CloudInstance)
def post_save_cloudinstance(sender, instance=None, created=False, **kwargs):
    post_save.disconnect(post_save_cloudinstance, sender=CloudInstance)
    if instance and instance.instanceautomation and (instance.automationvars is None or instance.automationvars == ""):
        instance.automationvars = instance.instanceautomation.getvariables()
    if not instance.skip_sync:
        instance.last_update = make_aware(datetime.datetime.now())
        instance.save()
    else:
        instance.skip_sync = False
        instance.save()
    post_save.connect(post_save_cloudinstance, sender=CloudInstance)


@receiver(pre_delete, sender=CloudInstance)
def pre_delete_cloudinstance(sender, instance=None, created=False, **kwargs):
    if instance.cloudid:
        pre_delete.disconnect(pre_delete_cloudinstance, sender=CloudInstance)
        try:
            ec2 = boto3.client('ec2', region_name=instance.cloud.zone,
                               aws_access_key_id=instance.cloud.key,
                               aws_secret_access_key=instance.cloud.secret)

            response = ec2.terminate_instances(
                InstanceIds=[instance.cloudid],
            )
            dolog("pre_delete_cloudinstance", "pre_delete_cloudinstance", response)
        except Exception as e:
            print("Error removing Subnet", e)
        pre_delete.connect(pre_delete_cloudinstance, sender=CloudInstance)


class Dashboard(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    description = models.CharField("Dashboard Integration Description", max_length=100, blank=False, null=False)
    baseurl = models.CharField(max_length=64, null=False, blank=False, default="https://api.meraki.com/api/v0")
    apikey = models.CharField(max_length=64, null=False, blank=False)
    orgid = models.CharField(max_length=32, null=True, blank=True, default=None)
    netid = models.CharField(max_length=32, null=True, blank=True, default=None)
    username = models.CharField(max_length=64, null=True, blank=True, default=None)
    password = models.CharField(max_length=64, null=True, blank=True, default=None)

    def __str__(self):
        return self.description


class DashboardLicense(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    license = models.CharField("Dashboard License Key (vMX)", max_length=32, blank=False, null=False)
    dashboard = models.ForeignKey(Dashboard, on_delete=models.SET_NULL, null=True, blank=True, default=None)

    def __str__(self):
        return self.license


class Log(models.Model):
    dt = models.DateTimeField(auto_now=True)
    function = models.CharField(max_length=100, blank=False, null=True, default=None)
    step = models.CharField(max_length=100, blank=False, null=True, default=None)
    log = models.TextField(blank=False, null=False)

    def __str__(self):
        if self.function:
            fx = self.function
        else:
            fx = ""
        if self.step:
            st = self.step
        else:
            st = ""
        return str(self.dt) + "::" + fx + "::" + st + "::" + self.log[0:20]

    class Meta:
        ordering = ['-dt']


class NetworkType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    driver = models.CharField("Docker Network Driver", max_length=20, blank=False, null=False)
    description = models.CharField("Network Type Description", max_length=100, blank=False, null=False)

    def __str__(self):
        return self.description


class Interface(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=15, null=False, blank=False)
    macaddress = models.CharField(max_length=17, null=True, blank=False, default=None)
    description = models.CharField("Interface Description", max_length=100, blank=False, null=False)

    def __str__(self):
        return self.description + " (" + self.name + ")"


class ContainerType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, blank=False, null=False)
    description = models.CharField("Container Type", max_length=100, blank=False, null=False)

    def __str__(self):
        return self.description


class Container(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    containertype = models.ForeignKey(ContainerType, on_delete=models.SET_NULL, null=True, blank=True, default=None)
    path = models.CharField("Docker Container Path", max_length=100, blank=True, null=False)
    cmd = models.CharField("Docker Container Command", max_length=100, blank=True, null=True, default=None)
    dockerfile = models.TextField("Dockerfile Contents", null=True, blank=True, default=None)
    buildcontainername = models.CharField("Docker Build Image Name", max_length=64, null=True, blank=True, default=None)
    clientscript = models.TextField("Client Script Contents", null=True, blank=True, default=None)
    description = models.CharField("Container Description", max_length=100, blank=False, null=False)
    active = models.BooleanField(default=True, editable=True)

    def __str__(self):
        return self.description


class Network(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    interface = models.ForeignKey(Interface, on_delete=models.SET_NULL, null=True, blank=False, default=None)
    networktype = models.ForeignKey(NetworkType, on_delete=models.SET_NULL, null=True)
    vlan = models.IntegerField(blank=True, null=False, default=0)
    subnet = models.CharField(max_length=18, null=True, default=None, blank=True)
    dg = models.CharField(max_length=15, null=True, default=None, blank=True)
    addrpool = models.CharField("Client Address Pool", max_length=18, null=True, default=None, blank=True)
    networkid = models.CharField("Docker Network ID", max_length=64, null=True, default=None, blank=True)
    description = models.CharField("Network Description", max_length=100, blank=False, null=False)
    active = models.BooleanField(default=True, editable=True)
    force_script = models.BooleanField("Force Impairment Script Update", default=False, editable=True)
    skip_sync = models.BooleanField(default=False, editable=False)
    last_update = models.DateTimeField(default=django.utils.timezone.now)
    last_sync = models.DateTimeField(null=True, default=None, blank=True)
    last_deployed_hash = models.CharField(max_length=32, blank=True, null=True, default=None)

    def __str__(self):
        return self.description

    def dockernetwork(self):
        if self.networktype.driver == "macvlan":
            return "macvlan" + str(self.vlan)
        else:
            return "bridge"

    def hostnetwork(self):
        if self.networktype.driver == "macvlan":
            return self.interface.name + "." + str(self.vlan)
        else:
            return str(self.interface.name)

    def networkimpairmentscript(self):
        wd = make_aware(datetime.datetime.now()).isoweekday()
        if wd == 7:
            wd = 0
        t = datetime.datetime.time(datetime.datetime.now())

        evt = LinkEvent.objects.filter(network=self).filter(day__daynum=wd).filter(starttime__lte=t).filter(endtime__gte=t)
        # print(evt)
        if len(evt) > 0:
            curevt = evt[0]
            return curevt.linkprofile.tcdata
        else:
            pro = LinkProfile.objects.filter(default_profile=True)
            if len(pro) > 0:
                curpro = pro[0]
                return curpro.tcdata
            return ""

    def networkimpairmentscripthash(self):
        return hashlib.md5(self.networkimpairmentscript().encode("utf-8")).hexdigest()


@receiver(pre_delete, sender=Network)
def pre_delete_network(sender, instance=None, created=False, **kwargs):
    pre_delete.disconnect(pre_delete_network, sender=Network)
    client = docker.from_env()
    try:
        net = client.networks.get(instance.networkid)
        dolog("network_pre_delete", "delete_docker_network", instance)
        net.remove()
    except Exception as e:
        print("Error removing network", e)
    pre_delete.connect(pre_delete_network, sender=Network)


@receiver(post_save, sender=Network)
def post_save_network(sender, instance=None, created=False, **kwargs):
    post_save.disconnect(post_save_network, sender=Network)
    if not instance.skip_sync:
        instance.last_update = make_aware(datetime.datetime.now())
        instance.save()
    else:
        instance.skip_sync = False
        instance.save()
    post_save.connect(post_save_network, sender=Network)


class App(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    description = models.CharField("Application Description", max_length=100, null=False, default=None)
    appurl = models.CharField("Application (URL)", max_length=100, null=True, blank=False, default=None)

    def __str__(self):
        return self.description + " (" + self.appurl + ")"


class AppProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    description = models.CharField("Application Profile Description", max_length=100, null=False, default=None)
    pdelay = models.IntegerField("Proxy Delay (seconds)", null=False, blank=False, default=0)

    def __str__(self):
        return self.description


def random_bytes(num=6):
    return [random.randrange(256) for _ in range(num)]


def generate_mac(uaa=False, multicast=False, oui=None, separator=':', byte_fmt='%02x'):
    mac = random_bytes()
    if oui:
        if type(oui) == str:
            oui = [int(chunk) for chunk in oui.split(separator)]
        mac = oui + random_bytes(num=6-len(oui))
    else:
        if multicast:
            mac[0] |= 1 # set bit 0
        else:
            mac[0] &= ~1 # clear bit 0
        if uaa:
            mac[0] &= ~(1 << 1) # clear bit 1
        else:
            mac[0] |= 1 << 1 # set bit 1
    return separator.join(byte_fmt % b for b in mac)


def generate_host():
    return ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(settings.DEFAULT_HOSTLEN))


class Client(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    network = models.ForeignKey(Network, on_delete=models.SET_NULL, null=True)
    dashboard = models.ForeignKey(Dashboard, on_delete=models.SET_NULL, null=True, blank=True, default=None)
    container = models.ForeignKey(Container, on_delete=models.SET_NULL, null=True)
    ipaddress = models.CharField(max_length=15, blank=True, null=True, default=None)
    macaddress = models.CharField(max_length=17, blank=True, unique=True, default=generate_mac)
    hostname = models.CharField(max_length=63, blank=True, unique=True, default=generate_host)
    clientid = models.CharField("Docker Container ID", max_length=64, null=True, default=None, blank=True)
    description = models.CharField("Client Description", max_length=100, blank=True, null=False, default=None)
    useragent = models.CharField("HTTP User-Agent", max_length=100, null=True, blank=True, default="Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:72.0) Gecko/20100101 Firefox/72.0")
    app = models.ManyToManyField(App, blank=True)
    active = models.BooleanField(default=True, editable=True)
    force_rebuild = models.BooleanField("Force Container Rebuild", default=False, editable=True)
    force_script = models.BooleanField("Force Container Script Update", default=False, editable=True)
    skip_sync = models.BooleanField(default=False, editable=False)
    last_update = models.DateTimeField(default=django.utils.timezone.now)
    last_sync = models.DateTimeField(null=True, default=None, blank=True)
    last_sync_log = models.TextField(blank=True, null=True, default=None)
    last_deployed_hash = models.CharField(max_length=32, blank=True, null=True, default=None)

    def __str__(self):
        return self.description

    def dockercontainername(self):
        try:
            cname = re.sub(r'\W+', '', self.description).lower() + "_" + self.hostname.lower()
            return str(cname[:40])
        except:
            return None

    def old_dockercontainerscript(self):
        dockerlog = True
        # used to determine whether an app impairment should be applied
        wd = make_aware(datetime.datetime.now()).isoweekday()
        if wd == 7:
            wd = 0
        t = datetime.datetime.time(datetime.datetime.now())

        if dockerlog:
            silent = " -o /proc/1/fd/1"
        else:
            silent = " -q"
        scr = "#!/bin/bash\n"
        scr += "ua=\\\"" + self.useragent + "\\\"\n"
        scr += "url_list=( "
        for a in self.app.all():
            scr += a.url + " "
        scr += ")\n"
        scr += "proxy_list=( "
        for a in self.app.all():
            # used to determine whether an app impairment should be applied
            evt = AppEvent.objects.filter(app=a).filter(day__daynum=wd).filter(starttime__lte=t).filter(endtime__gte=t)
            if len(evt) > 0:
                curevt = evt[0]
                scr += str(curevt.appprofile.pdelay) + " "
            else:
                scr += "0 "
        scr += ")\n"
        scr += "while [ 1 -eq 1 ]; do\n"
        scr += "    n=`expr $RANDOM % " + str(len(self.app.all())) + "`\n"
        scr += "    wait=`expr $RANDOM % 10`\n"
        scr += "    url=${url_list[$n]}\n"
        scr += "    proxy=http://delay:${proxy_list[$n]}@10.101.228.11:9011/\n"
        scr += "    if [ ${proxy_list[$n]} -gt 0 ]\n"
        scr += "    then\n"
        scr += "        export TSOCKS_PASSWORD=${proxy_list[$n]}\n"
        scr += "        tsocks wget --delete-after --user-agent=\\\"$ua\\\" -p $url" + silent + "\n"
        scr += "    else\n"
        scr += "        wget --delete-after --user-agent=\\\"$ua\\\" -p $url" + silent + "\n"
        scr += "    fi\n"
        scr += "    sleep $wait\n"
        scr += "done\n"
        return scr

    def dockercontainerscript(self):
        # used to determine whether an app impairment should be applied
        wd = make_aware(datetime.datetime.now()).isoweekday()
        if wd == 7:
            wd = 0
        t = datetime.datetime.time(datetime.datetime.now())

        urlstring = ""
        for a in self.app.all():
            urlstring += a.appurl + " "

        delaystring = ""
        for a in self.app.all():
            # used to determine whether an app impairment should be applied
            evt = AppEvent.objects.filter(app=a).filter(day__daynum=wd).filter(starttime__lte=t).filter(endtime__gte=t)
            if len(evt) > 0:
                curevt = evt[0]
                delaystring += str(curevt.appprofile.pdelay) + " "
            else:
                delaystring += "0 "

        scr = self.container.clientscript
        scr = scr.replace('"', '\\\"').replace("'", "\\\'")
        if scr is None:
            return ""
        scr = scr.replace("{{user_agent}}", self.useragent)
        scr = scr.replace("{{app_urls}}", urlstring)
        scr = scr.replace("{{app_delays}}", delaystring)
        scr = scr.replace("{{app_count}}", str(len(self.app.all())))
        scr = scr.replace("{{server_ip}}", "10.101.228.11")
        return scr

    def dockercontainerscripthash(self):
        if self.dockercontainerscript() is None or self.dockercontainerscript() == "":
            return ""
        else:
            return hashlib.md5(self.dockercontainerscript().encode("utf-8")).hexdigest()


@receiver(pre_delete, sender=Client)
def pre_delete_client(sender, instance=None, created=False, **kwargs):
    pre_delete.disconnect(pre_delete_client, sender=Client)
    client = docker.from_env()
    try:
        cli = client.containers.get(instance.clientid)
        dolog("client_pre_delete", "delete_docker_container", instance)
        cli.remove(force=True)
    except Exception as e:
        print("Error removing container", e)
    finally:
        print("Exception")
    pre_delete.connect(pre_delete_client, sender=Client)


@receiver(post_save, sender=Client)
def post_save_client(sender, instance=None, created=False, **kwargs):
    post_save.disconnect(post_save_client, sender=Client)
    if not instance.skip_sync:
        instance.last_update = make_aware(datetime.datetime.now())
        instance.save()
    else:
        instance.skip_sync = False
        instance.save()

#     if instance.dashboard and instance.dashboard.apikey and instance.dashboard.orgid and instance.dashboard.netid and instance.dashboard.baseurl:
#         headers = {"X-Cisco-Meraki-API-Key": instance.dashboard.apikey}
#         # url = instance.dashboard.baseurl + "/networks/" + instance.dashboard.netid + "/clients/" + instance.macaddress
#         url = instance.dashboard.baseurl + "/networks/" + instance.dashboard.netid + "/pii/requests"
#         data = {"mac": instance.macaddress, "type": "delete", "datasets": "all"}
#         r = requests.post(url, json=data, headers=headers)
#         dolog("post_save_client", "update_meraki_dashboard", "delete_client", r.status_code, r.content.decode("utf-8"))
#
#         url = instance.dashboard.baseurl + "/networks/" + instance.dashboard.netid + "/clients/provision"
#         data = {"mac": instance.macaddress, "name": instance.hostname, "devicePolicy": "normal"}
#         r = requests.post(url, json=data, headers=headers)
#         dolog("post_save_client", "update_meraki_dashboard", "create_client", r.status_code, r.content.decode("utf-8"))
    post_save.connect(post_save_client, sender=Client)


class LinkProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    description = models.CharField("Link Profile Description", max_length=100, null=False, default=None)
    default_profile = models.BooleanField(default=False, editable=False)
    tcdata = models.TextField("Linux TC Commands", null=True, blank=True, default=None)

    def __str__(self):
        return self.description


class EventDay(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    daynum = models.IntegerField(blank=False, null=False, default=0)
    dayname = models.CharField(max_length=20, null=False, blank=False)

    def __str__(self):
        return self.dayname

    class Meta:
        ordering = ['daynum']


# class WANProfile(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     description = models.CharField("WAN Profile Description", max_length=100, null=False, default=None)
#     tcdata = models.TextField("Linux TC Commands", null=True, blank=True, default=None)
#
#
# class WANEvent(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     day = models.ForeignKey(EventDay, on_delete=models.SET_NULL, null=True)
#     starttime = models.TimeField(default=django.utils.timezone.now)
#     endtime = models.TimeField(default=django.utils.timezone.now)
#     network = models.ForeignKey(Network, on_delete=models.SET_NULL, null=True)
#     wanprofile = models.ForeignKey(WANProfile, on_delete=models.SET_NULL, null=True)


class LinkEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    day = models.ForeignKey(EventDay, on_delete=models.SET_NULL, null=True)
    starttime = models.TimeField(default=django.utils.timezone.now)
    endtime = models.TimeField(default=django.utils.timezone.now)
    network = models.ForeignKey(Network, on_delete=models.SET_NULL, null=True)
    linkprofile = models.ForeignKey(LinkProfile, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        if self.network:
            thisdesc = self.network.description
        else:
            thisdesc = "Network Unspecified"
        return thisdesc + " : " + self.day.dayname + " @ " + str(self.starttime) + "-" + str(self.endtime) + " -> " + self.linkprofile.description

    class Meta:
        ordering = ['network', 'day', 'starttime']


class AppEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    day = models.ForeignKey(EventDay, on_delete=models.SET_NULL, null=True)
    starttime = models.TimeField(default=django.utils.timezone.now)
    endtime = models.TimeField(default=django.utils.timezone.now)
    app = models.ForeignKey(App, on_delete=models.SET_NULL, null=True)
    appprofile = models.ForeignKey(AppProfile, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        if self.app:
            thisdesc = self.app.description
        else:
            thisdesc = "Application Unspecified"
        return thisdesc + " : " + self.day.dayname + " @ " + str(self.starttime) + "-" + str(self.endtime) + " -> " + self.appprofile.description

    class Meta:
        ordering = ['app', 'day', 'starttime']
