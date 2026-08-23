from .models import Notification


def create_notification(user, notification_type, title, message, appointment=None):
    """
    هلپر مرکزی برای ساخت نوتیفیکیشن.
    معمولاً نیازی نیست مستقیم صداش بزنی - signals.py خودش این کارو
    برای رویدادهای مهم (رزرو، لغو، تایید، نظر جدید) انجام می‌ده.
    فقط برای رویدادهای سفارشی/دستی (مثل هشدار انقضای اشتراک) مستقیم استفاده‌ش کن.
    """
    return Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        appointment=appointment,
    )
