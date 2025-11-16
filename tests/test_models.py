from django.test import TestCase
from django.contrib.auth import get_user_model
from notifications.models import Notification

User = get_user_model()

class UserModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            phone_number='+1234567890',
            telegram_chat_id='123456'
        )

    def test_user_creation(self):
        """Тест создания пользователя"""
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertEqual(self.user.phone_number, '+1234567890')
        self.assertEqual(self.user.telegram_chat_id, '123456')
        self.assertTrue(self.user.prefer_email)
        self.assertFalse(self.user.prefer_sms)

    def test_user_string_representation(self):
        """Тест строкового представления пользователя"""
        self.assertEqual(str(self.user), 'testuser')


class NotificationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        self.notification = Notification.objects.create(
            user=self.user,
            title='Test Notification',
            message='This is a test message',
            notification_type='info',
            try_email=True,
            try_sms=False,
            try_telegram=True,
            priority_order=['email', 'telegram']
        )

    def test_notification_creation(self):
        """Тест создания уведомления"""
        self.assertEqual(self.notification.title, 'Test Notification')
        self.assertEqual(self.notification.message, 'This is a test message')
        self.assertEqual(self.notification.notification_type, 'info')
        self.assertTrue(self.notification.try_email)
        self.assertFalse(self.notification.try_sms)
        self.assertTrue(self.notification.try_telegram)
        self.assertEqual(self.notification.priority_order, ['email', 'telegram'])
        self.assertEqual(self.notification.retry_count, 0)
        self.assertEqual(self.notification.max_retries, 3)

    def test_notification_default_statuses(self):
        """Тест статусов уведомления по умолчанию"""
        self.assertEqual(self.notification.email_status, 'pending')
        self.assertEqual(self.notification.sms_status, 'pending')
        self.assertEqual(self.notification.telegram_status, 'pending')

    def test_notification_string_representation(self):
        """Тест строкового представления уведомления"""
        expected_str = f"{self.user.username} - {self.notification.title}"
        self.assertEqual(str(self.notification), expected_str)

    def test_notification_ordering(self):
        """Тест порядка сортировки уведомлений"""
        # Создаем второе уведомление
        notification2 = Notification.objects.create(
            user=self.user,
            title='Second Notification',
            message='Another test message'
        )
        
        notifications = list(Notification.objects.all())
        # Более новое уведомление должно быть первым
        self.assertEqual(notifications[0], notification2)
        self.assertEqual(notifications[1], self.notification)