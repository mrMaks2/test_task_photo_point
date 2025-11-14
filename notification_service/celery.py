# notification_service/celery.py
import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'notification_service.settings')

app = Celery('notification_service')
app.config_from_object('django.conf:settings', namespace='CELERY')

redis_url = settings.REDIS_URL
app.conf.broker_url = redis_url
app.conf.result_backend = redis_url

app.conf.broker_connection_retry_on_startup = True
app.conf.broker_connection_retry = True
app.conf.broker_connection_max_retries = 100
app.conf.broker_transport_options = {
    'visibility_timeout': 7200,
    'socket_keepalive': True,
    'socket_timeout': 60,
    'retry_on_timeout': True,
    'max_connections': 10,
}

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Moscow',
    enable_utc=False,
)

app.autodiscover_tasks()

app.conf.beat_schedule = {
    'send-scheduled-notifications': {
        'task': 'notifications.tasks.send_scheduled_notifications',
        'schedule': 60.0,  # Каждую минуту
    },
    'retry-failed-notifications': {
        'task': 'notifications.tasks.retry_failed_notifications',
        'schedule': 300.0,  # Каждые 5 минут
    },
}