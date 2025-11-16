from django.test import TestCase
from unittest.mock import patch, MagicMock
from django.utils import timezone
from django.contrib.auth import get_user_model
from notifications.models import Notification
from notifications.tasks import (
    send_notification_task, 
    send_scheduled_notifications,
    retry_failed_notifications
)

User = get_user_model()

class SendNotificationTaskTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )

    @patch('notifications.tasks.NotificationManager')
    @patch('notifications.tasks.transaction.atomic')
    def test_send_notification_task_success(self, mock_atomic, mock_manager_class):
        """Тест успешного выполнения задачи отправки уведомления"""
        notification = Notification.objects.create(
            user=self.user,
            title='Test Notification',
            message='Test content',
            try_email=True
        )
        
        # Мокаем транзакцию
        mock_atomic.return_value.__enter__ = MagicMock()
        mock_atomic.return_value.__exit__ = MagicMock(return_value=None)
        
        mock_manager = MagicMock()
        mock_manager.send_notification.return_value = (True, ['email'])
        mock_manager_class.return_value = mock_manager
        
        result = send_notification_task(notification.id)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['methods_used'], ['email'])
        self.assertEqual(result['retry_count'], 0)

    @patch('notifications.tasks.NotificationManager')
    @patch('notifications.tasks.transaction.atomic')
    def test_send_notification_task_failure_with_retry(self, mock_atomic, mock_manager_class):
        """Тест неудачи отправки с повторной попыткой"""
        notification = Notification.objects.create(
            user=self.user,
            title='Test Notification',
            message='Test content',
            try_email=True
        )
        
        # Мокаем транзакцию
        mock_atomic.return_value.__enter__ = MagicMock()
        mock_atomic.return_value.__exit__ = MagicMock(return_value=None)
        
        mock_manager = MagicMock()
        mock_manager.send_notification.return_value = (False, [])
        mock_manager_class.return_value = mock_manager
        
        # Мокаем retry метод
        with patch('notifications.tasks.send_notification_task.retry') as mock_retry:
            mock_exception = Exception("Retry called")
            mock_retry.return_value = mock_exception
            
            # Вызываем задачу и ожидаем исключение
            with self.assertRaises(Exception) as context:
                send_notification_task(notification.id)
            
            self.assertEqual(str(context.exception), "Retry called")
        
        # Проверяем что retry был вызван
        self.assertTrue(mock_retry.called)
        mock_manager.send_notification.assert_called_once()

    @patch('notifications.tasks.NotificationManager')
    @patch('notifications.tasks.transaction.atomic')
    def test_send_notification_task_failure_retry_logic(self, mock_atomic, mock_manager_class):
        """Тест логики повторных попыток при неудаче"""
        notification = Notification.objects.create(
            user=self.user,
            title='Test Notification',
            message='Test content',
            try_email=True,
            retry_count=1
        )
        
        # Мокаем транзакцию
        mock_atomic.return_value.__enter__ = MagicMock()
        mock_atomic.return_value.__exit__ = MagicMock(return_value=None)
        
        mock_manager = MagicMock()
        mock_manager.send_notification.return_value = (False, [])
        mock_manager_class.return_value = mock_manager
        
        with patch('notifications.tasks.send_notification_task.retry') as mock_retry:
            mock_exception = Exception("Retry")
            mock_retry.return_value = mock_exception
            
            with self.assertRaises(Exception):
                send_notification_task(notification.id)
            
            # Проверяем что retry был вызван
            self.assertTrue(mock_retry.called)

    def test_send_notification_task_not_found(self):
        """Тест обработки несуществующего уведомления"""
        result = send_notification_task(999)  # Несуществующий ID
        self.assertEqual(result['error'], 'Notification not found')

    @patch('notifications.tasks.NotificationManager')
    @patch('notifications.tasks.transaction.atomic')
    def test_send_notification_task_max_retries_exceeded(self, mock_atomic, mock_manager_class):
        """Тест превышения максимального количества попыток"""
        notification = Notification.objects.create(
            user=self.user,
            title='Test Notification',
            message='Test content',
            retry_count=3,
            max_retries=3
        )
        
        # Мокаем транзакцию
        mock_atomic.return_value.__enter__ = MagicMock()
        mock_atomic.return_value.__exit__ = MagicMock(return_value=None)
        
        result = send_notification_task(notification.id)
        
        self.assertEqual(result['status'], 'max_retries_exceeded')
        # Менеджер не должен вызываться при превышении лимита
        mock_manager_class.assert_not_called()

    @patch('notifications.tasks.NotificationManager')
    @patch('notifications.tasks.transaction.atomic')
    def test_send_notification_task_no_retry_when_successful(self, mock_atomic, mock_manager_class):
        """Тест что retry не вызывается при успешной отправке"""
        notification = Notification.objects.create(
            user=self.user,
            title='Test Notification',
            message='Test content',
            try_email=True
        )
        
        # Мокаем транзакцию
        mock_atomic.return_value.__enter__ = MagicMock()
        mock_atomic.return_value.__exit__ = MagicMock(return_value=None)
        
        mock_manager = MagicMock()
        mock_manager.send_notification.return_value = (True, ['email'])
        mock_manager_class.return_value = mock_manager
        
        # Мокаем retry чтобы убедиться что он не вызывается
        with patch('notifications.tasks.send_notification_task.retry') as mock_retry:
            result = send_notification_task(notification.id)
            
            # Проверяем что retry не был вызван
            mock_retry.assert_not_called()
            self.assertTrue(result['success'])


class ScheduledNotificationsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        self.now = timezone.now()

    @patch('notifications.tasks.send_notification_task.delay')
    def test_send_scheduled_notifications(self, mock_delay):
        """Тест отправки запланированных уведомлений"""
        # Создаем уведомление, запланированное на прошлое
        scheduled_notification = Notification.objects.create(
            user=self.user,
            title='Scheduled Notification',
            message='Scheduled content',
            scheduled_for=self.now - timezone.timedelta(hours=1)
        )
        
        result = send_scheduled_notifications()
        
        self.assertIn('Обработано 1 запланированных уведомлений', result)
        mock_delay.assert_called_once_with(scheduled_notification.id)

    @patch('notifications.tasks.send_notification_task.delay')
    def test_send_scheduled_notifications_future(self, mock_delay):
        """Тест игнорирования уведомлений, запланированных на будущее"""
        # Создаем уведомление, запланированное на будущее
        Notification.objects.create(
            user=self.user,
            title='Future Notification',
            message='Future content',
            scheduled_for=self.now + timezone.timedelta(hours=1)
        )
        
        result = send_scheduled_notifications()
        
        self.assertIn('Обработано 0 запланированных уведомлений', result)
        mock_delay.assert_not_called()


class RetryFailedNotificationsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )

    @patch('notifications.tasks.send_notification_task.delay')
    def test_retry_failed_notifications(self, mock_delay):
        """Тест повторной отправки неудачных уведомлений"""
        # Создаем неудачное уведомление с возможностью повторной попытки
        failed_notification = Notification.objects.create(
            user=self.user,
            title='Failed Notification',
            message='Failed content',
            email_status='failed',
            sms_status='failed',
            telegram_status='failed',
            retry_count=1,
            max_retries=3
        )
        
        result = retry_failed_notifications()
        
        self.assertIn('Повторная обработка 1 неудачных уведомлений', result)
        mock_delay.assert_called_once_with(failed_notification.id)

    @patch('notifications.tasks.send_notification_task.delay')
    def test_retry_failed_notifications_max_retries(self, mock_delay):
        """Тест игнорирования уведомлений с превышенным лимитом попыток"""
        # Создаем уведомление с превышенным лимитом попыток
        Notification.objects.create(
            user=self.user,
            title='Max Retries Notification',
            message='Max retries content',
            email_status='failed',
            sms_status='failed',
            telegram_status='failed',
            retry_count=3,
            max_retries=3
        )
        
        result = retry_failed_notifications()
        
        self.assertIn('Повторная обработка 0 неудачных уведомлений', result)
        mock_delay.assert_not_called()