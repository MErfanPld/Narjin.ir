from django.conf import settings
from django.db import models


class NotificationType(models.TextChoices):
    # --- سمت مشتری ---
    APPOINTMENT_CREATED = 'appointment_created', 'ثبت نوبت جدید'
    APPOINTMENT_CONFIRMED = 'appointment_confirmed', 'تایید نوبت'
    APPOINTMENT_CANCELED = 'appointment_canceled', 'لغو نوبت'
    APPOINTMENT_REMINDER = 'appointment_reminder', 'یادآوری نوبت'

    # --- سمت صاحب آرایشگاه ---
    NEW_APPOINTMENT = 'new_appointment', 'نوبت جدید (برای صاحب آرایشگاه)'
    APPOINTMENT_CANCELED_BY_CUSTOMER = 'appointment_canceled_by_customer', 'لغو نوبت توسط مشتری'
    NEW_PACKAGE_REVIEW = 'new_package_review', 'نظر جدید روی پکیج'
    SUBSCRIPTION_TRIAL_ENDING = 'subscription_trial_ending', 'پایان نزدیک دوره‌ی آزمایشی'
    SUBSCRIPTION_EXPIRED = 'subscription_expired', 'پایان اشتراک'

    # --- عمومی ---
    GENERAL = 'general', 'عمومی'


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='کاربر'
    )
    notification_type = models.CharField(
        max_length=40,
        choices=NotificationType.choices,
        default=NotificationType.GENERAL,
        verbose_name='نوع'
    )
    title = models.CharField(max_length=255, verbose_name='عنوان')
    message = models.TextField(verbose_name='متن پیام')
    is_read = models.BooleanField(default=False, verbose_name='خوانده‌شده؟')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')

    # ارتباط اختیاری با نوبت مرتبط - برای دیپ‌لینک یا نمایش جزئیات در فرانت
    appointment = models.ForeignKey(
        'reservations.Appointment',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name='نوبت مرتبط'
    )

    class Meta:
        verbose_name = 'اعلان'
        verbose_name_plural = 'اعلان‌ها'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', 'notification_type', 'created_at']),
        ]

    def __str__(self):
        return f"{self.title} - {self.user}"
