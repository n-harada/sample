from django.apps import AppConfig


class PrescriptionConfig(AppConfig):
    name = 'prescription'

    def ready(self):
        print("//////////////READY/////////////", flush=True)
