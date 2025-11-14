# notifications/models.py
from django.db import models
from django.conf import settings

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('success', 'Success'),
    )
    
    DELIVERY_STATUS = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('delivered', 'Delivered'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    
    # Статусы доставки для каждого канала
    email_status = models.CharField(max_length=20, choices=DELIVERY_STATUS, default='pending')
    sms_status = models.CharField(max_length=20, choices=DELIVERY_STATUS, default='pending')
    telegram_status = models.CharField(max_length=20, choices=DELIVERY_STATUS, default='pending')
    
    # Методы доставки, которые нужно попробовать
    try_email = models.BooleanField(default=True)
    try_sms = models.BooleanField(default=False)
    try_telegram = models.BooleanField(default=False)
    
    # Очередь приоритетов
    priority_order = models.JSONField(default=list)  # ['email', 'sms', 'telegram']
    
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"