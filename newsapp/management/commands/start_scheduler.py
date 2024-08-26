from django.core.management.base import BaseCommand
from newsapp.tasks import start_scheduler

class Command(BaseCommand):
    help = 'Start the APScheduler'

    def handle(self, *args, **kwargs):
        start_scheduler()
        self.stdout.write(self.style.SUCCESS('Scheduler started successfully.'))
