from scripts.dblog import *
# from django_apscheduler.models import DjangoJobExecution


def cleanup():
    # DjangoJobExecution.objects.delete_old_job_executions(3600)
    log = []
    task_types = ["client_monitor", "cloud_monitor", "interface_monitor", "network_monitor"]
    for t in task_types:
        tasks = Task.objects.filter(description=t)[:25].values_list("id", flat=True)
        Task.objects.filter(description=t).exclude(pk__in=list(tasks)).delete()
        append_log(log, "task_cleanup::", t)

    t1, _ = Task.objects.get_or_create(
        description="task_cleanup"
    )
    t1.task_data = "\n".join(log)
    t1.last_update = make_aware(datetime.datetime.now())
    t1.save()


def run():
    cleanup()
