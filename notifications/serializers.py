from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ('created_at', 'retry_count')

class NotificationCreateSerializer(serializers.ModelSerializer):
    priority_order = serializers.ListField(
        child=serializers.ChoiceField(choices=['email', 'sms', 'telegram']),
        default=['email', 'sms', 'telegram']
    )
    
    class Meta:
        model = Notification
        fields = [
            'user', 'title', 'message', 'notification_type',
            'scheduled_for', 'try_email', 'try_sms', 'try_telegram',
            'priority_order', 'max_retries'
        ]