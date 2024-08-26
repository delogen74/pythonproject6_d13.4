from django.apps import AppConfig

class NewsappConfig(AppConfig):
    name = 'newsapp'

    def ready(self):
        from .tasks import start_scheduler
        start_scheduler()
        import newsapp.signals