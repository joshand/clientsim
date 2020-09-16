# import sys
# import os
# from django_apscheduler.models import DjangoJob
# from apscheduler.schedulers.background import BackgroundScheduler
# from django_apscheduler.jobstores import DjangoJobStore
# # from django_apscheduler.jobstores import register_events
# import scripts.interface_monitor
# import scripts.network_monitor
# import scripts.clean_tasks
# import scripts.client_monitor
# import scripts.cloud_monitor
#
# scheduler = BackgroundScheduler()
# scheduler.add_jobstore(DjangoJobStore(), "default")
#
#
# def run():     # pragma: no cover
#     scheduler.add_job(scripts.interface_monitor.run, "interval", id="interface_monitor", seconds=10,
#                       replace_existing=True)
#     scheduler.add_job(scripts.network_monitor.run, "interval", id="network_monitor", seconds=10, replace_existing=True)
#     scheduler.add_job(scripts.clean_tasks.cleanup, "interval", id="clean_tasks", hours=8, replace_existing=True)
#     scheduler.add_job(scripts.client_monitor.run, "interval", id="client_monitor", hours=24, replace_existing=True)
#     scheduler.add_job(scripts.cloud_monitor.run, "interval", id="cloud_monitor", hours=24, replace_existing=True)
#
#     scheduler.start()
#     # while True:
#     #     pass


import atexit
from apscheduler.schedulers.background import BackgroundScheduler
import scripts.interface_monitor
import scripts.network_monitor
import scripts.clean_tasks
import scripts.client_monitor
import scripts.cloud_monitor

cron = BackgroundScheduler()


def run():
    # Explicitly kick off the background thread
    cron.start()
    cron.remove_all_jobs()
    job1 = cron.add_job(scripts.interface_monitor.run, 'interval', seconds=30)
    job2 = cron.add_job(scripts.network_monitor.run, 'interval', seconds=30)
    job3 = cron.add_job(scripts.client_monitor.run, 'interval', seconds=30)
    job4 = cron.add_job(scripts.clean_tasks.run, 'interval', minutes=60)

    # Shutdown your cron thread if the web process is stopped
    atexit.register(lambda: cron.shutdown(wait=False))
