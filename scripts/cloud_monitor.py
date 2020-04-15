import atexit
import docker
from docker import types
from apscheduler.schedulers.background import BackgroundScheduler
from client_sim.models import *
from django.conf import settings
from django.utils.timezone import make_aware
from io import BytesIO
from django.db.models import F, Q
import boto3
import time
import paramiko


def dolog(fn, step, *txt):
    l = Log.objects.create(function=fn, step=step, log=",".join(map(str, txt)))
    l.save()


def set_command_variables(cmd, variables):
    cmdout = cmd
    vardict = json.loads(variables)
    for v in vardict:
        cmdout = cmdout.replace("{{" + v + "}}", vardict[v])

    return cmdout


def wait_for_client(client, instanceip, instance_un, image_def_un, key):
    maxloops = 5
    lcount = 0

    use_un = instance_un
    if use_un == "" or use_un is None:
        use_un = image_def_un

    while lcount <= maxloops:
        lcount += 1
        try:
            print("sync_cloud::instance_automation::wait_for_client", lcount)
            # Here 'ubuntu' is user name and 'instance_ip' is public IP of EC2
            client.connect(hostname=instanceip, username=use_un, pkey=key, timeout=5)

            # Execute a command(cmd) after connecting/ssh to an instance
            stdin, stdout, stderr = client.exec_command("pwd")
            ret = stdout.read()
            print("sync_cloud::instance_automation::client_status", lcount, stdout.read(), stderr.read())
            if ret:
                return True

            goodclient = True
        except Exception as e:
            print("sync_cloud::instance_automation::exception", lcount, e)
            # print(" -", e, "; Trying again...")
            time.sleep(5)

    return False


def instance_automation(instances):
    for i in instances:
        cmdout = {}
        client = None

        rdata = i.instanceautomationscript()
        if rdata != "" and rdata is not None:
            if (str(i.last_deployed_hash) != str(i.instanceautomationscripthash())) or i.force_script:
                print("sync_cloud::instance_automation::client_needs_update", i)
                key = paramiko.RSAKey.from_private_key_file(i.cloud.publickey.fspath())
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                r = wait_for_client(client, i.publicip, i.username, i.cloudimage.default_username, key)

                if r:
                    print("sync_cloud::instance_automation::client_ready", r)
            # rdata = i.instanceautomationscript()
            # if rdata != "" and rdata is not None:
            #     if (str(i.last_deployed_hash) != str(i.instanceautomationscripthash())) or i.force_script:
                    i.force_script = False
                    i.skip_sync = True
                    i.save()
                    cmdlist = rdata.split("\n")
                    for cmdnum in range(0, len(cmdlist)):
                        try:
                            newcmd = set_command_variables(cmdlist[cmdnum], i.automationvars)
                            print("executing", newcmd)
                            cmd = newcmd.replace("\r", "").replace("\\n", "\n").replace("$", "\$")
                            stdin, stdout, stderr = client.exec_command(cmd)
                            cmdout[str(cmdnum)] = {"command": "", "stdout": "", "stderr": ""}
                            cmdout[str(cmdnum)]["command"] = cmd
                            cmdout[str(cmdnum)]["stdout"] = stdout.read().decode("UTF-8")
                            cmdout[str(cmdnum)]["stderr"] = stderr.read().decode("UTF-8")
                        except Exception as e:
                            cmdout[str(cmdnum)] = {"command": cmdlist[cmdnum], "stdout": "", "stderr": "Exception:" + str(e) + "(" + str(type(e).__name__) + ")"}
                            # cmdout = str(cmdout) + "\nException:" + str(e) + "(" + str(type(e).__name__) + ")"

                    i.last_deployed_hash = i.instanceautomationscripthash()
                    i.last_sync_log = str(cmdout)
                    i.skip_sync = True
                    i.save()
                else:
                    i.last_sync_log = "Error: Unable to connect to Instance via SSH. Disabling Instance Automation..." + str(i.instanceautomation)
                    i.last_deployed_hash = None
                    i.instanceautomation = None
                    i.skip_sync = True
                    i.save()


def get_aws_vpcs(key, secret, region, vpcid=None):
    ec2 = boto3.client('ec2', region_name=region,
                         aws_access_key_id=key,
                         aws_secret_access_key=secret)

    vpcs = None
    try:
        if vpcid:
            vpcs = ec2.describe_vpcs(
                Filters=[
                    {
                        'Name': 'vpc-id',
                        'Values': [vpcid]
                    },
                ]
            )
        else:
            vpcs = ec2.describe_vpcs()
    except Exception as e:
        print("Error", e)
    ec2 = None
    if len(vpcs["Vpcs"]) > 0:
        return vpcs["Vpcs"]
    else:
        return []


def create_aws_vpcs(obj):
    for o in obj:
        logdata = ""
        dt = make_aware(datetime.datetime.now())
        try:
            ec2 = boto3.resource('ec2', region_name=o.cloud.zone,
                                 aws_access_key_id=o.cloud.key,
                                 aws_secret_access_key=o.cloud.secret)

            vpc = ec2.create_vpc(
                CidrBlock=o.cidr,
            )
            logdata += "Add VPC: " + str(vpc) + "\n"
            ret = vpc.create_tags(
                Tags=[
                    {
                        'Key': 'Name',
                        'Value': o.description
                    },
                ]
            )
            logdata += "Set Name: " + str(ret) + "\n"

            i = get_aws_vpcs(o.cloud.key, o.cloud.secret, o.cloud.zone, vpcid=vpc.id)
            o.cloudid = vpc.id
            o.rawdata = i[0]
        except Exception as e:
            logdata += "Exception " + str(e)

        o.last_sync = dt
        o.last_update = dt
        o.skip_sync = True
        o.last_sync_log = logdata
        o.save()

    return []


def update_aws_vpcs(obj):
    for o in obj:
        logdata = ""
        dt = make_aware(datetime.datetime.now())
        try:
            ec2 = boto3.resource('ec2', region_name=o.cloud.zone,
                                 aws_access_key_id=o.cloud.key,
                                 aws_secret_access_key=o.cloud.secret)

            vpc = ec2.Vpc(o.cloudid)

            ret = vpc.create_tags(
                DryRun=False,
                Tags=[
                    {
                        'Key': 'Name',
                        'Value': o.description
                    },
                ]
            )
            logdata += "Update Name: " + str(ret) + "\n"

            i = get_aws_vpcs(o.cloud.key, o.cloud.secret, o.cloud.zone, vpcid=o.cloudid)

            o.rawdata = i[0]
        except Exception as e:
            logdata += "Exception " + str(e)

        o.last_sync = dt
        o.last_update = dt
        o.skip_sync = True
        o.last_sync_log = logdata
        o.save()

    return []


def get_aws_subnets(key, secret, region, subnetid=None):
    ec2 = boto3.client('ec2', region_name=region,
                         aws_access_key_id=key,
                         aws_secret_access_key=secret)

    nets = None
    try:
        if subnetid:
            nets = ec2.describe_subnets(
                Filters=[
                    {
                        'Name': 'subnet-id',
                        'Values': [subnetid]
                    },
                ]
            )
        else:
            nets = ec2.describe_subnets()
    except Exception as e:
        print("Error", e)
    ec2 = None
    if len(nets["Subnets"]) > 0:
        return nets["Subnets"]
    else:
        return []


def create_aws_subnets(obj):
    for o in obj:
        logdata = ""
        dt = make_aware(datetime.datetime.now())
        try:
            ec2 = boto3.resource('ec2', region_name=o.cloud.zone,
                                 aws_access_key_id=o.cloud.key,
                                 aws_secret_access_key=o.cloud.secret)

            vpc = ec2.Vpc(o.vpc.cloudid)
            subnet = vpc.create_subnet(
                CidrBlock=o.cidr,
            )
            logdata += "Add Subnet: " + str(subnet) + "\n"
            ret = subnet.create_tags(
                Tags=[
                    {
                        'Key': 'Name',
                        'Value': o.description
                    },
                ]
            )
            logdata += "Set Name: " + str(ret) + "\n"

            ec2 = None
            ec2 = boto3.client('ec2', region_name=o.cloud.zone,
                               aws_access_key_id=o.cloud.key,
                               aws_secret_access_key=o.cloud.secret)

            ret = ec2.modify_subnet_attribute(
                MapPublicIpOnLaunch={
                    'Value': o.assign_public_ip
                },
                SubnetId=subnet.id
            )
            logdata += "Change MapPublicIpOnLaunch: " + str(ret) + "\n"

            i = get_aws_subnets(o.cloud.key, o.cloud.secret, o.cloud.zone, subnetid=subnet.id)
            o.cloudid = subnet.id
            o.rawdata = i[0]
        except Exception as e:
            logdata += "Exception " + str(e)

        o.last_sync = dt
        o.last_update = dt
        o.skip_sync = True
        o.last_sync_log = logdata
        o.save()

    return []


def update_aws_subnets(obj):
    for o in obj:
        logdata = ""
        dt = make_aware(datetime.datetime.now())
        try:
            ec2 = boto3.resource('ec2', region_name=o.cloud.zone,
                                 aws_access_key_id=o.cloud.key,
                                 aws_secret_access_key=o.cloud.secret)

            subnet = ec2.Subnet(o.cloudid)

            ret = subnet.create_tags(
                DryRun=False,
                Tags=[
                    {
                        'Key': 'Name',
                        'Value': o.description
                    },
                ]
            )
            logdata += "Update Name: " + str(ret) + "\n"
            ec2 = None

            ec2 = boto3.client('ec2', region_name=o.cloud.zone,
                               aws_access_key_id=o.cloud.key,
                               aws_secret_access_key=o.cloud.secret)

            ret = ec2.modify_subnet_attribute(
                MapPublicIpOnLaunch={
                    'Value': o.assign_public_ip
                },
                SubnetId=o.cloudid
            )
            logdata += "Change MapPublicIpOnLaunch: " + str(ret) + "\n"

            i = get_aws_subnets(o.cloud.key, o.cloud.secret, o.cloud.zone, subnetid=o.cloudid)
            o.rawdata = i[0]
        except Exception as e:
            logdata += "Exception " + str(e)

        o.last_sync = dt
        o.last_update = dt
        o.skip_sync = True
        o.last_sync_log = logdata
        o.save()

    return []


def get_aws_securitygroups(key, secret, region, groupid=None):
    ec2 = boto3.client('ec2', region_name=region,
                         aws_access_key_id=key,
                         aws_secret_access_key=secret)

    sgs = None
    try:
        if groupid:
            sgs = ec2.describe_security_groups(
                Filters=[
                    {
                            'Name': 'group-id',
                            'Values': [groupid]
                    },
                ]
            )
        else:
            sgs = ec2.describe_security_groups()
    except Exception as e:
        print("Error", e)
    ec2 = None
    if len(sgs["SecurityGroups"]) > 0:
        return sgs["SecurityGroups"]
    else:
        return []


def create_aws_securitygroups(obj):
    for o in obj:
        logdata = ""
        dt = make_aware(datetime.datetime.now())
        try:
            ec2 = boto3.resource('ec2', region_name=o.cloud.zone,
                                 aws_access_key_id=o.cloud.key,
                                 aws_secret_access_key=o.cloud.secret)

            sg = ec2.Vpc(o.cloudvpc.cloudid)

            ret = sg.create_security_group(
                DryRun=False,
                Tags=[
                    {
                        'Key': 'Name',
                        'Value': o.description
                    },
                ]
            )
            logdata += "Update Name: " + str(ret) + "\n"

            i = get_aws_securitygroups(o.cloud.key, o.cloud.secret, o.cloud.zone, groupid=o.cloudid)
            o.rawdata = i[0]
        except Exception as e:
            logdata += "Exception " + str(e)

        o.last_sync = dt
        o.last_update = dt
        o.skip_sync = True
        o.last_sync_log = logdata
        o.save()
    return []


def update_aws_securitygroups(obj):
    for o in obj:
        logdata = ""
        dt = make_aware(datetime.datetime.now())
        try:
            ec2 = boto3.resource('ec2', region_name=o.cloud.zone,
                                 aws_access_key_id=o.cloud.key,
                                 aws_secret_access_key=o.cloud.secret)

            sg = ec2.SecurityGroup(o.cloudid)

            ret = sg.create_tags(
                DryRun=False,
                Tags=[
                    {
                        'Key': 'Name',
                        'Value': o.description
                    },
                ]
            )
            logdata += "Update Name: " + str(ret) + "\n"

            i = get_aws_securitygroups(o.cloud.key, o.cloud.secret, o.cloud.zone, groupid=o.cloudid)
            o.rawdata = i[0]
        except Exception as e:
            logdata += "Exception " + str(e)

        o.last_sync = dt
        o.last_update = dt
        o.skip_sync = True
        o.last_sync_log = logdata
        o.save()

    return []


def get_aws_instances(key, secret, region, instanceid=None):
    ec2 = boto3.client('ec2', region_name=region,
                         aws_access_key_id=key,
                         aws_secret_access_key=secret)

    instances = None
    while not instances:
        try:
            if instanceid:
                instances = ec2.describe_instances(
                    Filters=[
                        {
                            'Name': 'instance-id',
                            'Values': [instanceid]
                        },
                        {
                            'Name': 'instance-state-name',
                            'Values': ["pending", "running", "shutting-down", "stopping", "stopped"]
                        },
                    ]
                )
            else:
                instances = ec2.describe_instances(
                    Filters=[
                        {
                            'Name': 'instance-state-name',
                            'Values': ["pending", "running", "shutting-down", "stopping", "stopped"]
                        },
                    ]
                )
        except Exception as e:
            print("Error", e)
    ec2 = None
    if len(instances["Reservations"]) > 0:
        return instances["Reservations"]
    else:
        return []


def get_aws_instance_userdata(instance):
    ec2 = boto3.resource('ec2', region_name=instance.cloud.zone,
                         aws_access_key_id=instance.cloud.key,
                         aws_secret_access_key=instance.cloud.secret)

    instances = ec2.instances.filter(InstanceIds=[instance.cloudid])
    for i in instances:
        ud = i.describe_attribute(Attribute='userData')
        if "UserData" in ud:
            if "Value" in ud["UserData"]:
                return ud["UserData"]["Value"]
    return None


def create_aws_instances(obj):
    outinst = []

    for o in obj:
        logdata = ""
        dt = make_aware(datetime.datetime.now())
        try:
            ec2 = boto3.resource('ec2', region_name=o.cloud.zone,
                                 aws_access_key_id=o.cloud.key,
                                 aws_secret_access_key=o.cloud.secret)

            # create a new EC2 instance
            # instances = None
            # while not instances:
            # print(o.cloudimage.cloudid, o.imagesize, o.cloudsubnet.cloudid, str(o.cloud.publickey).replace(".pem", ""), o.cloudsecuritygroup.all())
            res = [sub.cloudid for sub in o.cloudsecuritygroup.all()]
            logdata += "Selected SG(s): " + str(res) + "\n"
            if True:
                try:
                    instances = ec2.create_instances(
                        ImageId=o.cloudimage.cloudid,
                        MinCount=1,
                        MaxCount=1,
                        InstanceType=o.imagesize,
                        UserData=o.userdata,
                        SubnetId=o.cloudsubnet.cloudid,
                        KeyName=str(o.cloud.publickey).replace(".pem", ""),
                        SecurityGroupIds=res
                    )
                    outinst.append(instances)
                    curinst = instances[0]
                    logdata += "Created Instance " + str(curinst.id) + "\n"
                except Exception as e:
                    # print("Error", e)
                    logdata += "Error " + str(e) + "\n"
                    curinst = {}
            ec2 = None

            logdata += config_aws_instance(o, curinst.id, src_dst_check=o.srcdstcheck, instance_name=o.description,
                                           security_groups=o.cloudsecuritygroup.all())
            i = get_aws_instances(o.cloud.key, o.cloud.secret, o.cloud.zone, instanceid=curinst.id)[0]["Instances"][0]
            o.publicdns = i["PublicDnsName"]
            o.publicip = i["PublicIpAddress"]
            o.privateip = i["PrivateIpAddress"]
            o.rawdata = str(i)
            o.cloudid = curinst.id
        except Exception as e:
            logdata += "Exception " + str(e)

        o.last_sync = dt
        o.last_update = dt
        o.skip_sync = True
        o.last_sync_log = logdata
        o.save()

        # o.cloud.force_rebuild = True
        # o.cloud.save()

    # print("create_aws_instances", outinst)
    return outinst


def update_aws_instances(obj):
    for o in obj:
        logdata = ""
        dt = make_aware(datetime.datetime.now())
        try:
            if o.userdata != o.prevuserdata:
                logdata = config_aws_instance(o, o.cloudid, src_dst_check=o.srcdstcheck, instance_name=o.description,
                                              security_groups=o.cloudsecuritygroup.all(), user_data=o.userdata)
                o.prevuserdata = o.userdata
            else:
                logdata = config_aws_instance(o, o.cloudid, src_dst_check=o.srcdstcheck, instance_name=o.description,
                                              security_groups=o.cloudsecuritygroup.all())

            i = get_aws_instances(o.cloud.key, o.cloud.secret, o.cloud.zone, instanceid=o.cloudid)
            o.rawdata = i[0]
        except Exception as e:
            logdata += "Exception " + str(e)

        o.last_sync = dt
        o.last_update = dt
        o.skip_sync = True
        o.last_sync_log = logdata
        o.save()

    # print("update_aws_instances", obj)
    return []


def config_aws_instance(o, instance_id, src_dst_check=None, instance_name=None, security_groups=None, user_data=None):
    logdata = ""
    try:
        ec2 = boto3.resource('ec2', region_name=o.cloud.zone,
                             aws_access_key_id=o.cloud.key,
                             aws_secret_access_key=o.cloud.secret)

        instance = ec2.Instance(instance_id)

        if instance_name is not None:
            ret = instance.create_tags(
                DryRun=False,
                Tags=[
                    {
                        'Key': 'Name',
                        'Value': instance_name
                    },
                ]
            )
            logdata += "Update Name: " + str(ret) + "\n"

        if security_groups is not None:
            res = [sub.cloudid for sub in security_groups]
            ret = instance.modify_attribute(
                Groups=res
            )
            logdata += "Update Security Groups: " + str(ret) + "\n"

        if user_data is not None and user_data != "":
            ret = stop_aws_instance(o, instance_id)
            logdata += "Stop Instance: " + str(ret) + "\n"
            ret = instance.modify_attribute(
                UserData={"Value": user_data}
            )
            logdata += "Update User-Data: " + str(ret) + "\n"
            ret = start_aws_instance(o, instance_id)
            logdata += "Start Instance: " + str(ret) + "\n"

        if src_dst_check is not None:
            ret = instance.modify_attribute(
                SourceDestCheck={
                    'Value': False
                }
            )
            logdata += "Update SrcDstCheck: " + str(ret) + "\n"
    except Exception as e:
        logdata += "Exception " + str(e)

    ec2 = None
    return logdata


def stop_aws_instance(o, instanceid):
    logdata = ""
    try:
        ec2 = boto3.client('ec2', region_name=o.cloud.zone,
                             aws_access_key_id=o.cloud.key,
                             aws_secret_access_key=o.cloud.secret)

        response = ec2.stop_instances(
            InstanceIds=[
                instanceid,
            ],
        )
        respstat = response["StoppingInstances"][0]["CurrentState"]
        while respstat["Name"] != "stopped":
            time.sleep(2)
            response = get_aws_instances(o.cloud.key, o.cloud.secret, o.cloud.zone, instanceid=instanceid)
            respstat = response[0]["Instances"][0]["State"]
            logdata += "Waiting for stop... current state=" + respstat["Name"]
    except Exception as e:
        logdata += "Exception " + str(e)

    return logdata


def start_aws_instance(o, instanceid):
    logdata = ""
    try:
        ec2 = boto3.client('ec2', region_name=o.cloud.zone,
                             aws_access_key_id=o.cloud.key,
                             aws_secret_access_key=o.cloud.secret)

        response = ec2.start_instances(
            InstanceIds=[
                instanceid,
            ],
        )
        respstat = response["StartingInstances"][0]["CurrentState"]
        while respstat["Name"] != "running":
            time.sleep(2)
            response = get_aws_instances(o.cloud.key, o.cloud.secret, o.cloud.zone, instanceid=instanceid)
            respstat = response[0]["Instances"][0]["State"]
            logdata += "Waiting for start... current state=" + respstat["Name"]
    except Exception as e:
        logdata += "Exception " + str(e)

    return logdata


def get_aws_image(key, secret, region, imageid):
    ec2 = boto3.client('ec2', region_name=region,
                         aws_access_key_id=key,
                         aws_secret_access_key=secret)

    amis = None
    try:
        amis = ec2.describe_images(
            Filters=[
                {
                    'Name': 'image-id',
                    'Values': [imageid]
                },
            ]
        )
    except Exception as e:
        print("Error", e)
    ec2 = None
    if len(amis["Images"]) > 0:
        return amis["Images"][0]
    else:
        return []


def update_cloud(clouds):
    logdata = ""
    curvpc = None
    cursubnet = None
    cursg = None

    dt = make_aware(datetime.datetime.now())
    # if len(clouds) > 0:
    #     print("updating clouds")
    for c in clouds:
        # obj = CloudVPC.objects.all().exclude(last_sync=F('last_update'))
        # if len(obj) > 0:
        #     update_aws_vpcs(c.key, c.secret, c.zone, obj)
        vpcs = get_aws_vpcs(c.key, c.secret, c.zone)
        for v in vpcs:
            vpc = CloudVPC.objects.filter(cloudid=v["VpcId"])
            desc = v["CidrBlock"]
            for t in v.get("Tags", []):
                if t.get("Key", "") == "Name":
                    desc = t.get("Value", "")
            if len(vpc) <= 0:
                curvpc = CloudVPC.objects.create(cloud=c, description=desc, cidr=v["CidrBlock"], cloudid=v["VpcId"], rawdata=str(v), last_sync=dt, last_update=dt, skip_sync=True)
                logdata += "Adding VPC: " + str(curvpc) + "\n"
            else:
                curvpc = vpc[0]
                curvpc.cidr = v["CidrBlock"]
                curvpc.description = desc
                curvpc.rawdata = str(v)
                curvpc.last_sync = dt
                curvpc.last_update = dt
                curvpc.skip_sync = True
                logdata += "Updating VPC: " + str(curvpc) + "\n"
                curvpc.save()
            # obj = CloudSubnet.objects.all().exclude(last_sync=F('last_update'))
            # if len(obj) > 0:
            #     update_aws_subnets(c.key, c.secret, c.zone, obj)
            subnets = get_aws_subnets(c.key, c.secret, c.zone)      #, v["VpcId"]
            for s in subnets:
                subnet = CloudSubnet.objects.filter(cloudid=s["SubnetId"])
                desc = s["CidrBlock"]
                for t in s.get("Tags", []):
                    if t.get("Key", "") == "Name":
                        desc = t.get("Value", "")

                if len(subnet) <= 0:
                    cursubnet = CloudSubnet.objects.create(cloud=c, description=desc, assign_public_ip=s["MapPublicIpOnLaunch"], cidr=s["CidrBlock"], vpc=curvpc, cloudid=s["SubnetId"], rawdata=str(s), last_sync=dt, last_update=dt, skip_sync=True)
                    logdata += "Adding Subnet: " + str(cursubnet) + "\n"
                else:
                    cursubnet = subnet[0]
                    cursubnet.description = desc
                    cursubnet.cidr = s["CidrBlock"]
                    cursubnet.assign_public_ip = s["MapPublicIpOnLaunch"]
                    cursubnet.vpc = curvpc
                    cursubnet.rawdata = str(s)
                    cursubnet.last_sync = dt
                    cursubnet.last_update = dt
                    cursubnet.skip_sync = True
                    logdata += "Updating Subnet: " + str(cursubnet) + "\n"
                    cursubnet.save()
        # obj = CloudSecurityGroup.objects.all().exclude(last_sync=F('last_update'))
        # if len(obj) > 0:
        #     update_aws_securitygroups(c.key, c.secret, c.zone, obj)
        sgs = get_aws_securitygroups(c.key, c.secret, c.zone)
        for sg in sgs:
            groups = CloudSecurityGroup.objects.filter(cloudid=sg["GroupId"])
            assignvpc = CloudVPC.objects.filter(cloudid=sg["VpcId"])[0]
            desc = sg["Description"]
            for t in sg.get("Tags", []):
                if t.get("Key", "") == "Name":
                    desc = t.get("Value", "")

            if len(groups) <= 0:
                cursg = CloudSecurityGroup.objects.create(cloud=c, description=desc, cloudvpc=assignvpc, cloudid=sg["GroupId"], rawdata=str(sg), last_sync=dt, last_update=dt, skip_sync=True)
                logdata += "Adding SG: " + str(cursg) + "\n"
            else:
                cursg = groups[0]
                cursg.description = desc
                cursg.cloudvpc = assignvpc
                cursg.rawdata = str(sg)
                cursg.last_sync = dt
                cursg.last_update = dt
                cursg.skip_sync = True
                logdata += "Updating SG: " + str(cursg) + "\n"
                cursg.save()

        # obj = CloudInstance.objects.all().exclude(last_sync=F('last_update'))
        # if len(obj) > 0:
        #     update_aws_instances(c.key, c.secret, c.zone, obj)
        instres = get_aws_instances(c.key, c.secret, c.zone)
        for inst in instres:
            for i in inst["Instances"]:
                imgraw = get_aws_image(c.key, c.secret, c.zone, i["ImageId"])
                img = CloudImage.objects.filter(cloudid=i["ImageId"])
                if len(img) <= 0:
                    curi = CloudImage.objects.create(cloud=c, description=i["Name"], cloudid=i["ImageId"], rawdata=imgraw["Name"], last_sync=dt, last_update=dt, skip_sync=True)
                    logdata += "Adding Image: " + str(curi) + "\n"
                else:
                    curi = img[0]
                    curi.description = imgraw["Name"]
                    curi.rawdata = imgraw
                    curi.last_sync = dt
                    curi.last_update = dt
                    curi.skip_sync = True
                    logdata += "Updating Image: " + str(curi) + "\n"
                    curi.save()

                instances = CloudInstance.objects.filter(cloudid=i["InstanceId"])
                ud = get_aws_instance_userdata(instances[0])

                desc = i["PublicDnsName"]
                for t in i.get("Tags", []):
                    if t.get("Key", "") == "Name":
                        desc = t.get("Value", "")

                dbsgs = []
                instsgs = i["SecurityGroups"]
                for isg in instsgs:
                    thissg = CloudSecurityGroup.objects.filter(cloudid=isg["GroupId"])
                    dbsgs.append(thissg[0])

                thissubnet = CloudSubnet.objects.filter(cloudid=i["SubnetId"])[0]

                if len(instances) <= 0:
                    curinst = CloudInstance.objects.create(cloud=c, description=desc, imagesize=i["InstanceType"], srcdstcheck=i["SourceDestCheck"], cloudimage=curi, cloudsubnet=thissubnet, cloudid=i["InstanceId"], rawdata=str(i), last_sync=dt, last_update=dt, skip_sync=True, publicip=i["PublicIpAddress"], publicdns=i["PublicDnsName"], privateip=i["PrivateIpAddress"], userdata=ud, prevuserdata=ud)      # cloudvpc=curvpc,
                    # curinst.cloudsecuritygroup.add(cursg)
                    for d in dbsgs:
                        curinst.cloudsecuritygroup.add(d)
                    logdata += "Adding Instance: " + str(curinst) + "\n"
                    curinst.save()
                else:
                    curinst = instances[0]
                    curinst.imagesize = i["InstanceType"]
                    curinst.description = desc
                    curinst.userdata = ud
                    curinst.prevuserdata = ud
                    curinst.publicdns = i["PublicDnsName"]
                    curinst.publicip = i["PublicIpAddress"]
                    curinst.privateip = i["PrivateIpAddress"]
                    curinst.srcdstcheck = i["SourceDestCheck"]
                    curinst.cloudimage = curi
                    curinst.cloudsubnet = thissubnet
                    # curinst.cloudvpc = curvpc
                    curinst.rawdata = str(i)
                    curinst.cloudsecuritygroup.clear()
                    # curinst.cloudsecuritygroup.add(cursg)
                    for d in dbsgs:
                        curinst.cloudsecuritygroup.add(d)
                    curinst.last_sync = dt
                    curinst.last_update = dt
                    curinst.skip_sync = True
                    logdata += "Updating Instance: " + str(curinst) + "\n"
                    curinst.save()

        c.last_sync = dt
        c.last_update = dt
        c.force_rebuild = False
        c.last_sync_log = logdata
        c.skip_sync = True
        c.save()


def sync_cloud():
    # Process records that have been added to database that need to be pushed to cloud
    obj = CloudVPC.objects.all().exclude(last_sync=F('last_update')).filter(Q(cloudid=None) | Q(cloudid=""))
    if len(obj) > 0:
        print("sync_cloud::cloud_vpc::push", obj)
        os = create_aws_vpcs(obj)
    obj = CloudSubnet.objects.all().exclude(last_sync=F('last_update')).filter(Q(cloudid=None) | Q(cloudid=""))
    if len(obj) > 0:
        print("sync_cloud::cloud_subnet::push", obj)
        os = create_aws_subnets(obj)
    obj = CloudSecurityGroup.objects.all().exclude(last_sync=F('last_update')).filter(Q(cloudid=None) | Q(cloudid=""))
    if len(obj) > 0:
        print("sync_cloud::cloud_sg::push", obj)
        os = create_aws_securitygroups(obj)
    obj = CloudInstance.objects.all().exclude(last_sync=F('last_update')).filter(Q(cloudid=None) | Q(cloudid=""))
    if len(obj) > 0:
        print("sync_cloud::cloud_inst::push", obj)
        os = create_aws_instances(obj)

    # Process records that already exist in cloud that need to be updated
    obj = CloudVPC.objects.all().exclude(last_sync=F('last_update')).exclude(Q(cloudid=None) | Q(cloudid=""))
    if len(obj) > 0:
        print("sync_cloud::cloud_vpc::update", obj)
        os = update_aws_vpcs(obj)
    obj = CloudSubnet.objects.all().exclude(last_sync=F('last_update')).exclude(Q(cloudid=None) | Q(cloudid=""))
    if len(obj) > 0:
        print("sync_cloud::cloud_subnet::update", obj)
        os = update_aws_subnets(obj)
    obj = CloudSecurityGroup.objects.all().exclude(last_sync=F('last_update')).exclude(Q(cloudid=None) | Q(cloudid=""))
    if len(obj) > 0:
        print("sync_cloud::cloud_sg::update", obj)
        os = update_aws_securitygroups(obj)
    obj = CloudInstance.objects.all().exclude(last_sync=F('last_update')).exclude(Q(cloudid=None) | Q(cloudid=""))
    if len(obj) > 0:
        print("sync_cloud::cloud_inst::update", obj)
        os = update_aws_instances(obj)

    # See if any cloud accounts have been updated and need to be re-synced
    clouds1 = Cloud.objects.all().exclude(last_sync=F('last_update'))
    print("sync_cloud::full_cloud_sync::phase1", clouds1)
    update_cloud(clouds1)

    # Sync cloud accounts have been set to force refresh
    clouds2 = Cloud.objects.filter(force_rebuild=True)
    print("sync_cloud::full_cloud_sync::phase2", clouds2)
    update_cloud(clouds2)

    # Instance Automation
    instances = CloudInstance.objects.exclude(instanceautomation=None)
    print("sync_cloud::instance_automation", instances)
    instance_automation(instances)
    # print(clouds1, clouds2)


def run():
    # Enable the job scheduler to run schedule jobs
    cron = BackgroundScheduler()

    # Explicitly kick off the background thread
    cron.start()
    cron.remove_all_jobs()
    job0 = cron.add_job(sync_cloud)
    job1 = cron.add_job(sync_cloud, 'interval', seconds=10)

    # Shutdown your cron thread if the web process is stopped
    atexit.register(lambda: cron.shutdown(wait=False))
