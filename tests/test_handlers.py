from django.test import TestCase
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from django.conf import settings
from notifications.models import Notification
from notifications.notification_handlers import (
    EmailHandler,
    SMSHandler,
    TelegramHandler,
    NotificationManager
)

User = get_user_model()

class EmailHandlerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        self.notification = Notification.objects.create(
            user=self.user,
            title='Test Email',
            message='Test email content'
        )
        self.handler = EmailHandler()

    @patch('notifications.notification_handlers.send_mail')
    def test_send_email_success(self, mock_send_mail):
        """Тест успешной отправки email"""
        mock_send_mail.return_value = 1
        
        success, message = self.handler.send(self.user, self.notification)
        
        self.assertTrue(success)
        self.assertEqual(message, "Электронная почта успешно отправлена")
        mock_send_mail.assert_called_once_with(
            subject='Test Email',
            message='Test email content',
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=['test@example.com'],
            fail_silently=False
        )

    @patch('notifications.notification_handlers.send_mail')
    def test_send_email_failure(self, mock_send_mail):
        """Тест неудачной отправки email"""
        mock_send_mail.side_effect = Exception("SMTP error")
        
        success, message = self.handler.send(self.user, self.notification)
        
        self.assertFalse(success)
        self.assertEqual(message, "SMTP error")


class SMSHandlerTest(TestCase):
    def setUp(self):
        self.user_with_phone = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='+1234567890'
        )
        self.user_without_phone = User.objects.create_user(
            username='testuser2',
            email='test2@example.com'
        )
        self.notification = Notification.objects.create(
            user=self.user_with_phone,
            title='Test SMS',
            message='Test SMS content'
        )
        self.handler = SMSHandler()

    @patch('notifications.notification_handlers.Client')
    def test_send_sms_success(self, mock_client_class):
        """Тест успешной отправки SMS"""
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.sid = 'SM123456'
        mock_client.messages.create.return_value = mock_message
        mock_client_class.return_value = mock_client
        
        success, message = self.handler.send(self.user_with_phone, self.notification)
        
        self.assertTrue(success)
        self.assertIn('SM123456', message)
        mock_client.messages.create.assert_called_once()

    def test_send_sms_no_phone_number(self):
        """Тест отправки SMS без номера телефона"""
        success, message = self.handler.send(self.user_without_phone, self.notification)
        
        self.assertFalse(success)
        self.assertEqual(message, "Номер телефона не указан")

    @patch('notifications.notification_handlers.Client')
    def test_send_sms_failure(self, mock_client_class):
        """Тест неудачной отправки SMS"""
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("Twilio error")
        mock_client_class.return_value = mock_client
        
        success, message = self.handler.send(self.user_with_phone, self.notification)
        
        self.assertFalse(success)
        self.assertEqual(message, "Twilio error")


class TelegramHandlerTest(TestCase):
    def setUp(self):
        self.user_with_chat_id = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            telegram_chat_id='123456'
        )
        self.user_without_chat_id = User.objects.create_user(
            username='testuser2',
            email='test2@example.com'
        )
        self.notification = Notification.objects.create(
            user=self.user_with_chat_id,
            title='Test Telegram',
            message='Test Telegram content'
        )
        self.handler = TelegramHandler()

    @patch('notifications.notification_handlers.requests.post')
    def test_send_telegram_success(self, mock_post):
        """Тест успешной отправки Telegram сообщения"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        success, message = self.handler.send(self.user_with_chat_id, self.notification)
        
        self.assertTrue(success)
        self.assertEqual(message, "Сообщение в Telegram отправлено успешно")
        mock_post.assert_called_once()

    def test_send_telegram_no_chat_id(self):
        """Тест отправки Telegram без chat_id"""
        success, message = self.handler.send(self.user_without_chat_id, self.notification)
        
        self.assertFalse(success)
        self.assertEqual(message, "ID чата Telegram не указан")

    @patch('notifications.notification_handlers.requests.post')
    def test_send_telegram_failure(self, mock_post):
        """Тест неудачной отправки Telegram сообщения"""
        mock_post.side_effect = Exception("Telegram API error")
        
        success, message = self.handler.send(self.user_with_chat_id, self.notification)
        
        self.assertFalse(success)
        self.assertEqual(message, "Telegram API error")


class NotificationManagerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='+1234567890',
            telegram_chat_id='123456'
        )
        self.notification = Notification.objects.create(
            user=self.user,
            title='Test Notification',
            message='Test content',
            try_email=True,
            try_sms=True,
            try_telegram=True,
            priority_order=['email', 'sms', 'telegram']
        )
        self.manager = NotificationManager()

    @patch.object(EmailHandler, 'send')
    def test_send_notification_success_first_method(self, mock_email_send):
        """Тест успешной отправки первым методом"""
        mock_email_send.return_value = (True, "Email sent")
        
        success, methods = self.manager.send_notification(self.notification)
        
        self.assertTrue(success)
        self.assertEqual(methods, ['email'])
        self.notification.refresh_from_db()
        self.assertEqual(self.notification.email_status, 'sent')
        # Другие методы не должны были быть вызваны
        mock_email_send.assert_called_once()

    @patch.object(EmailHandler, 'send')
    @patch.object(SMSHandler, 'send')
    def test_send_notification_fallback(self, mock_sms_send, mock_email_send):
        """Тест перехода к следующему методу при неудаче"""
        mock_email_send.return_value = (False, "Email failed")
        mock_sms_send.return_value = (True, "SMS sent")
        
        success, methods = self.manager.send_notification(self.notification)
        
        self.assertTrue(success)
        self.assertEqual(methods, ['sms'])
        self.notification.refresh_from_db()
        self.assertEqual(self.notification.email_status, 'failed')
        self.assertEqual(self.notification.sms_status, 'sent')

    @patch.object(EmailHandler, 'send')
    @patch.object(SMSHandler, 'send')
    @patch.object(TelegramHandler, 'send')
    def test_send_notification_all_failed(self, mock_tg_send, mock_sms_send, mock_email_send):
        """Тест неудачи всех методов отправки"""
        mock_email_send.return_value = (False, "Email failed")
        mock_sms_send.return_value = (False, "SMS failed")
        mock_tg_send.return_value = (False, "Telegram failed")
        
        success, methods = self.manager.send_notification(self.notification)
        
        self.assertFalse(success)
        self.assertEqual(methods, [])
        self.notification.refresh_from_db()
        self.assertEqual(self.notification.email_status, 'failed')
        self.assertEqual(self.notification.sms_status, 'failed')
        self.assertEqual(self.notification.telegram_status, 'failed')