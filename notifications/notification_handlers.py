import requests
from django.core.mail import send_mail
from django.conf import settings
from twilio.rest import Client
from logging_utils import setup_logger

logger = setup_logger('notifications.notification_handlers')

class NotificationHandler:
    """Базовый класс для обработчиков уведомлений"""
    
    def send(self, user, notification):
        raise NotImplementedError

class EmailHandler(NotificationHandler):
    def send(self, user, notification):
        try:
            send_mail(
                subject=notification.title,
                message=notification.message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
                fail_silently=False,
            )
            return True, "Электронная почта успешно отправлена"
        except Exception as e:
            logger.error(f"Ошибка при отправке электронной почты: {str(e)}")
            return False, str(e)

class SMSHandler(NotificationHandler):
    def send(self, user, notification):
        try:
            if not user.phone_number:
                return False, "Номер телефона не указан"
            
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            
            message = client.messages.create(
                body=f"{notification.title}: {notification.message}",
                from_=settings.TWILIO_PHONE_NUMBER,
                to=user.phone_number
            )
            return True, f"SMS сообщение отправлено: {message.sid}"
        except Exception as e:
            logger.error(f"Ошибка отправки SMS сообщения: {str(e)}")
            return False, str(e)

class TelegramHandler(NotificationHandler):
    def send(self, user, notification):
        try:
            if not user.telegram_chat_id:
                return False, "ID чата Telegram не указан"
            
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': user.telegram_chat_id,
                'text': f"*{notification.title}*\n{notification.message}",
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            return True, "Сообщение в Telegram отправлено успешно"
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения в telegram: {str(e)}")
            return False, str(e)

class NotificationManager:
    """Менеджер для управления отправкой уведомлений с отказоустойчивостью"""
    
    def __init__(self):
        self.handlers = {
            'email': EmailHandler(),
            'sms': SMSHandler(),
            'telegram': TelegramHandler(),
        }
    
    def send_notification(self, notification):
        user = notification.user
        methods_to_try = notification.priority_order
        
        successful_methods = []
        
        for method in methods_to_try:
            if not getattr(notification, f'try_{method}', False):
                continue
                
            handler = self.handlers.get(method)
            if not handler:
                continue
                
            try:
                success, message = handler.send(user, notification)
                status_field = f"{method}_status"
                setattr(notification, status_field, 'sent' if success else 'failed')
                
                if success:
                    successful_methods.append(method)
                    logger.info(f"Уведомление {notification.id} отправлено через {method}")
                    break
                    
            except Exception as e:
                logger.error(f"Ошибка при отправке через {method}: {str(e)}")
                setattr(notification, f"{method}_status", 'failed')
        
        notification.save()
        return len(successful_methods) > 0, successful_methods