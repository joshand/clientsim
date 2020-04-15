import atexit
from apscheduler.schedulers.background import BackgroundScheduler
import threading
import asyncio
import sys
from client_sim.models import *


def run_tasks():
    if 'runserver' not in sys.argv:
        return None

    try:
        import scripts.interface_monitor
        scripts.interface_monitor.run()
    except:
        print("#### Exception starting scheduled job: interface_monitor")

    try:
        import scripts.network_monitor
        scripts.network_monitor.run()
    except:
        print("#### Exception starting scheduled job: network_monitor")

    try:
        import scripts.client_monitor
        scripts.client_monitor.run()
    except:
        print("#### Exception starting scheduled job: client_monitor")

    try:
        import scripts.cloud_monitor
        scripts.cloud_monitor.run()
    except:
        print("#### Exception starting scheduled job: cloud_monitor")

    # try:
    #     import scripts.network_proxy
    #     scripts.network_proxy.run()
    # except:
    #     print("#### Exception starting scheduled job: network_proxy")
