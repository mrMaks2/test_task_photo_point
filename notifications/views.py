from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Notification
from .serializers import NotificationSerializer, NotificationCreateSerializer
from .tasks import send_notification_task

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return NotificationCreateSerializer
        return NotificationSerializer
    
    def perform_create(self, serializer):
        notification = serializer.save()
        
        # Если не запланировано на будущее, отправляем сразу
        if not notification.scheduled_for:
            send_notification_task.delay(notification.id)
    
    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Повторная отправка уведомления"""
        notification = self.get_object()
        send_notification_task.delay(notification.id)
        return Response({'status': 'retry scheduled'})
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Статистика доставки уведомлений"""
        total = Notification.objects.count()
        sent = Notification.objects.filter(
            email_status='sent',
            sms_status='sent', 
            telegram_status='sent'
        ).count()
        failed = Notification.objects.filter(
            email_status='failed',
            sms_status='failed',
            telegram_status='failed'
        ).count()
        
        return Response({
            'total_notifications': total,
            'successfully_sent': sent,
            'completely_failed': failed,
            'success_rate': (sent / total * 100) if total > 0 else 0
        })