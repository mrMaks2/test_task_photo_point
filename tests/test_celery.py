from django.test import TestCase
from notification_service.celery import app
from django.conf import settings

class CeleryConfigurationTest(TestCase):
    def test_celery_app_configuration(self):
        """Тест конфигурации Celery"""
        self.assertEqual(app.conf.timezone, 'Europe/Moscow')
        self.assertFalse(app.conf.enable_utc)
        self.assertEqual(app.conf.task_serializer, 'json')
        self.assertEqual(app.conf.accept_content, ['json'])

    def test_celery_beat_schedule(self):
        """Тест расписания Celery Beat"""
        beat_schedule = app.conf.beat_schedule
        
        self.assertIn('send-scheduled-notifications', beat_schedule)
        self.assertIn('retry-failed-notifications', beat_schedule)
        
        scheduled_task = beat_schedule['send-scheduled-notifications']
        self.assertEqual(scheduled_task['task'], 'notifications.tasks.send_scheduled_notifications')
        self.assertEqual(scheduled_task['schedule'], 60.0)

    def test_redis_configuration(self):
        """Тест конфигурации Redis"""
        self.assertTrue(hasattr(settings, 'REDIS_URL'))
        self.assertIn('redis://', settings.REDIS_URL)