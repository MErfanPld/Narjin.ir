from django.contrib.auth import get_user_model
from rest_framework import serializers, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.exceptions import ValidationError

from business.models import Business
from reservations.models import Appointment
from .models import Notification, NotificationType

User = get_user_model()


TARGET_CHOICES = [
    'all_customers',        # همه‌ی مشتریان پلتفرم (کاربرانی که صاحب آرایشگاه نیستن)
    'all_business_owners',  # همه‌ی صاحبان آرایشگاه
    'business_customers',   # فقط مشتریانی که از یک آرایشگاه خاص نوبت گرفته‌اند (نیاز به business_id)
    'business_owner',       # فقط صاحب یک آرایشگاه خاص (نیاز به business_id)
    'specific_user',        # فقط یک کاربر خاص (نیاز به user_id)
]


class BroadcastNotificationSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    message = serializers.CharField()
    target = serializers.ChoiceField(choices=TARGET_CHOICES)
    business_id = serializers.IntegerField(required=False, allow_null=True)
    user_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        target = attrs['target']

        if target in ('business_customers', 'business_owner') and not attrs.get('business_id'):
            raise serializers.ValidationError("برای این نوع هدف، business_id الزامی است.")

        if target == 'specific_user' and not attrs.get('user_id'):
            raise serializers.ValidationError("برای ارسال به یک کاربر خاص، user_id الزامی است.")

        if attrs.get('business_id'):
            if not Business.objects.filter(id=attrs['business_id']).exists():
                raise serializers.ValidationError("آرایشگاهی با این شناسه یافت نشد.")

        if attrs.get('user_id'):
            if not User.objects.filter(id=attrs['user_id']).exists():
                raise serializers.ValidationError("کاربری با این شناسه یافت نشد.")

        return attrs

    def _resolve_recipients(self, attrs):
        target = attrs['target']

        if target == 'all_business_owners':
            return User.objects.filter(business__isnull=False).distinct()

        if target == 'all_customers':
            # مشتری یعنی کاربری که صاحب آرایشگاه نیست
            return User.objects.filter(business__isnull=True)

        if target == 'business_owner':
            return User.objects.filter(business__id=attrs['business_id'])

        if target == 'business_customers':
            customer_ids = Appointment.objects.filter(
                service__business_id=attrs['business_id']
            ).values_list('user_id', flat=True).distinct()
            return User.objects.filter(id__in=customer_ids)

        if target == 'specific_user':
            return User.objects.filter(id=attrs['user_id'])

        return User.objects.none()

    def save(self, **kwargs):
        recipients = self._resolve_recipients(self.validated_data)
        title = self.validated_data['title']
        message = self.validated_data['message']

        notifications = [
            Notification(
                user=user,
                notification_type=NotificationType.GENERAL,
                title=title,
                message=message,
            )
            for user in recipients
        ]
        Notification.objects.bulk_create(notifications)
        return {"sent_count": len(notifications)}


class BroadcastNotificationView(generics.GenericAPIView):
    """
    ساخت نوتیف هدفمند توسط سوپرادمین.
    مثال بدنه‌ی درخواست:
        {
            "title": "اطلاعیه مهم",
            "message": "...",
            "target": "business_customers",
            "business_id": 5
        }
    """
    permission_classes = [IsAdminUser]  # فقط is_staff/is_superuser
    serializer_class = BroadcastNotificationSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=201)