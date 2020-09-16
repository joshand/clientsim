from django.apps import AppConfig
import os


class ClientSimConfig(AppConfig):
    name = 'client_sim'

    def ready(self):
        if os.environ.get('RUN_MAIN', None):
            import scripts.tasks
            scripts.tasks.run()
