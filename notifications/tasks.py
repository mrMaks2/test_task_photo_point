from celery import shared_task
from django.utils import timezone
from .models import Notification
from .notification_handlers import NotificationManager
from django.db import models, transaction
from logging_utils import setup_logger

logger = setup_logger('notifications.tasks')

@shared_task(bind=True, max_retries=3)
def send_notification_task(self, notification_id):
    """Задача для отправки одного уведомления с правильной обработкой повторов"""
    try:
        with transaction.atomic():
            # Используем select_for_update для предотвращения конкурентного доступа
            notification = Notification.objects.select_for_update().get(id=notification_id)
            
            # Проверяем, не обрабатывается ли уже уведомление
            if notification.retry_count >= notification.max_retries:
                logger.warning(f"Уведомление {notification_id} превысило лимит повторов")
                return {'status': 'max_retries_exceeded'}
            
            manager = NotificationManager()
            success, methods = manager.send_notification(notification)
            
            if not success:
                notification.retry_count += 1
                notification.save()
                
                if notification.retry_count < notification.max_retries:
                    raise self.retry(countdown=60 * (2 ** notification.retry_count))
            
            return {
                'notification_id': notification_id,
                'success': success,
                'methods_used': methods,
                'retry_count': notification.retry_count
            }
            
    except Notification.DoesNotExist:
        logger.error(f"Уведомление {notification_id} не найдено")
        return {'error': 'Notification not found'}
    except Exception as exc:
        logger.error(f"Ошибка для уведомления {notification_id}: {str(exc)}")
        raise self.retry(countdown=60, exc=exc)

@shared_task
def send_scheduled_notifications():
    """Задача для отправки запланированных уведомлений"""
    now = timezone.now()
    scheduled_notifications = Notification.objects.filter(
        scheduled_for__lte=now,
        email_status='pending',
        sms_status='pending', 
        telegram_status='pending'
    )
    
    for notification in scheduled_notifications:
        send_notification_task.delay(notification.id)
    
    return f"Обработано {scheduled_notifications.count()} запланированных уведомлений"

@shared_task
def retry_failed_notifications():
    """Задача для повторной отправки неудачных уведомлений"""
    failed_notifications = Notification.objects.filter(
        retry_count__lt=models.F('max_retries'),
        email_status='failed',
        sms_status='failed',
        telegram_status='failed'
    )
    
    for notification in failed_notifications:
        if notification.retry_count < notification.max_retries:
            send_notification_task.delay(notification.id)
    
    return f"Повторная обработка {failed_notifications.count()} неудачных уведомлений"