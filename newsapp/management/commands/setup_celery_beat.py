from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from celery.schedules import crontab

class Command(BaseCommand):
    help = 'Setup periodic tasks for Celery'

    def handle(self, *args, **options):
        PeriodicTask.objects.filter(name='send_weekly_digest').delete()

        PeriodicTask.objects.create(
            name='send_weekly_digest',
            task='newsapp.tasks.send_weekly_digest',
            schedule=crontab(hour=8, minute=0, day_of_week='1'),  # Пн в 8:00
            options={'queue': 'default'}
        )

        self.stdout.write(self.style.SUCCESS('Successfully set up Celery Beat tasks'))
