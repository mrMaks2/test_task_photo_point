# tests/test_views.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch
from notifications.models import Notification

User = get_user_model()

class NotificationViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.notification = Notification.objects.create(
            user=self.user,
            title='Test Notification',
            message='Test message content',
            try_email=True
        )
        
        self.valid_payload = {
            'user': self.user.id,
            'title': 'New Notification',
            'message': 'New message content',
            'notification_type': 'info',
            'try_email': True,
            'try_sms': False,
            'try_telegram': False,
            'priority_order': ['email'],
            'max_retries': 3
        }

    def test_list_notifications_authenticated(self):
        """Тест получения списка уведомлений аутентифицированным пользователем"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get('/api/v1/notifications/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results'] if 'results' in response.data else response.data), 1)

    def test_create_notification_authenticated(self):
        """Тест создания уведомления аутентифицированным пользователем"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.post(
            '/api/v1/notifications/',
            data=self.valid_payload,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Notification.objects.count(), 2)
        self.assertEqual(response.data['title'], 'New Notification')

    def test_retrieve_notification(self):
        """Тест получения деталей уведомления"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get(f'/api/v1/notifications/{self.notification.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test Notification')

    @patch('notifications.views.send_notification_task.delay')
    def test_retry_notification(self, mock_delay):
        """Тест повторной отправки уведомления"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.post(f'/api/v1/notifications/{self.notification.id}/retry/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'retry scheduled')
        mock_delay.assert_called_once_with(self.notification.id)

    def test_stats_endpoint(self):
        """Тест endpoint статистики"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Создаем еще одно успешное уведомление
        Notification.objects.create(
            user=self.user,
            title='Successful Notification',
            message='Success content',
            email_status='sent',
            sms_status='sent',
            telegram_status='sent'
        )
        
        response = self.client.get('/api/v1/notifications/stats/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_notifications'], 2)
        self.assertEqual(response.data['successfully_sent'], 1)
        self.assertEqual(response.data['completely_failed'], 0)

    @patch('notifications.views.send_notification_task.delay')
    def test_create_notification_immediate_send(self, mock_delay):
        """Тест немедленной отправки при создании уведомления без планирования"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.post(
            '/api/v1/notifications/',
            data=self.valid_payload,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Проверяем, что задача отправки была вызвана
        mock_delay.assert_called_once()

    def test_create_notification_scheduled(self):
        """Тест создания запланированного уведомления (без немедленной отправки)"""
        self.client.force_authenticate(user=self.admin_user)
        
        from django.utils import timezone
        import datetime
        
        scheduled_payload = self.valid_payload.copy()
        scheduled_payload['scheduled_for'] = timezone.now() + datetime.timedelta(hours=1)
        
        with patch('notifications.views.send_notification_task.delay') as mock_delay:
            response = self.client.post(
                '/api/v1/notifications/',
                data=scheduled_payload,
                format='json'
            )
            
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            # Для запланированного уведомления задача не должна вызываться немедленно
            mock_delay.assert_not_called()

    def test_unauthenticated_access(self):
        """Тест доступа без аутентификации"""
        response = self.client.get('/api/v1/notifications/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_regular_user_access(self):
        """Тест доступа обычного пользователя"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get('/api/v1/notifications/')
        # Зависит от настроек permissions в вашем проекте
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN])