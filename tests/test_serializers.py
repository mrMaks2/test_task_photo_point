from django.test import TestCase
from django.contrib.auth import get_user_model
from notifications.models import Notification
from notifications.serializers import (
    NotificationSerializer,
    NotificationCreateSerializer
)

User = get_user_model()

class NotificationSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        self.notification_data = {
            'user': self.user.id,
            'title': 'Test Notification',
            'message': 'Test message content',
            'notification_type': 'info',
            'try_email': True,
            'try_sms': False,
            'try_telegram': True,
            'priority_order': ['email', 'telegram'],
            'max_retries': 5
        }

    def test_notification_create_serializer_valid_data(self):
        """Тест валидных данных для создания уведомления"""
        serializer = NotificationCreateSerializer(data=self.notification_data)
        self.assertTrue(serializer.is_valid())
        
        notification = serializer.save()
        self.assertEqual(notification.title, 'Test Notification')
        self.assertEqual(notification.max_retries, 5)
        self.assertEqual(notification.priority_order, ['email', 'telegram'])

    def test_notification_create_serializer_default_priority_order(self):
        """Тест порядка приоритетов по умолчанию"""
        data = self.notification_data.copy()
        data.pop('priority_order', None)
        
        serializer = NotificationCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        notification = serializer.save()
        self.assertEqual(notification.priority_order, ['email', 'sms', 'telegram'])

    def test_notification_serializer_read_only_fields(self):
        """Тест read-only полей сериализатора"""
        notification = Notification.objects.create(
            user=self.user,
            title='Test Notification',
            message='Test message'
        )
        
        serializer = NotificationSerializer(notification)
        data = serializer.data
        
        # Проверяем, что read-only поля присутствуют
        self.assertIn('created_at', data)
        self.assertIn('retry_count', data)

    def test_notification_serializer_invalid_priority_order(self):
        """Тест невалидного порядка приоритетов"""
        data = self.notification_data.copy()
        data['priority_order'] = ['invalid_method']
        
        serializer = NotificationCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('priority_order', serializer.errors)