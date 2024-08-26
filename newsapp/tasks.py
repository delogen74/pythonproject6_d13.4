from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore, register_events
from django.core.mail import send_mail
from .models import Post, Subscriber, DigestRun
from datetime import datetime, timedelta
from django.db import OperationalError
from celery import shared_task
import time


def retry_db_operation(func, max_retries=5, wait_time=1):
    """Повторить операцию с базой данных при возникновении блокировки."""
    for attempt in range(max_retries):
        try:
            return func()
        except OperationalError as e:
            if "database is locked" in str(e):
                time.sleep(wait_time)
            else:
                raise
    raise OperationalError("Max retries reached. Database is still locked.")


def get_last_run_time():
    """Получить время последней рассылки."""
    last_run = retry_db_operation(lambda: DigestRun.objects.last())
    return last_run.last_run if last_run else datetime.now() - timedelta(days=7)


def update_last_run_time():
    """Обновить время последней рассылки."""
    retry_db_operation(lambda: DigestRun.objects.create())


@shared_task
def notify_subscribers(post_id):
    """Уведомить подписчиков о новой новости."""
    post = Post.objects.get(id=post_id)
    subscribers = Subscriber.objects.filter(category__name=post.postCategory.name).values_list('user__email',
                                                                                               flat=True).distinct()

    for email in subscribers:
        send_mail(
            subject=f'Новая новость: {post.title}',
            message=f'Вышла новая статья: {post.title}\n\nЧитать здесь: http://127.0.0.1:8000/news/{post.id}/',
            from_email='autotechsupp74@yandex.ru',
            recipient_list=[email]
        )


@shared_task
def send_weekly_digest():
    from .models import Post, Subscriber, DigestRun
    """Отправить еженедельную рассылку с последними новостями."""
    last_run_time = get_last_run_time()
    now_time = datetime.now()

    def fetch_posts():
        return Post.objects.filter(dateCreation__gte=last_run_time)

    posts = retry_db_operation(fetch_posts)

    if posts.exists():
        categories = set(posts.values_list('postCategory__name', flat=True))
        subscribers = Subscriber.objects.filter(category__name__in=categories).values_list('user__email',
                                                                                           flat=True).distinct()

        for email in subscribers:
            post_list = "\n".join([f'{post.title}: http://127.0.0.1:8000/news/{post.id}/' for post in posts])
            send_mail(
                subject='Weekly Digest',
                message=f'Вот новые статьи за последнюю неделю:\n{post_list}',
                from_email='autotechsupp74@yandex.ru',
                recipient_list=[email]
            )

    update_last_run_time()


def start_scheduler():
    """Запустить планировщик задач."""
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")

    scheduler.remove_all_jobs()

    scheduler.add_job(
        send_weekly_digest,
        trigger='cron',
        day_of_week='mon',
        hour=8,
        minute=0,
        id='weekly_digest',
        max_instances=1,
        replace_existing=True,
    )

    register_events(scheduler)
    scheduler.start()
    print("Scheduler started.")
