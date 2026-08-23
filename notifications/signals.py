from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from reservations.models import Appointment
from .models import NotificationType
from .utils import create_notification

try:
    from packages.models import PackageReview
except ImportError:
    PackageReview = None  # اگه اسم اپ پکیج‌ها فرق داره، این importرو اصلاح کن


# ============================== Appointment ==============================

@receiver(pre_save, sender=Appointment)
def _cache_old_appointment_status(sender, instance, **kwargs):
    """قبل از ذخیره، وضعیت قبلی رو کش می‌کنه تا توی post_save بشه فهمید تغییر کرده یا نه."""
    if instance.pk:
        try:
            instance._old_status = Appointment.objects.only('status').get(pk=instance.pk).status
        except Appointment.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Appointment)
def _appointment_notifications(sender, instance, created, **kwargs):
    appointment = instance
    service_name = appointment.service.name if appointment.service else "سرویس"

    # نوبت جدید ثبت شد
    if created:
        # به مشتری
        create_notification(
            user=appointment.user,
            notification_type=NotificationType.APPOINTMENT_CREATED,
            title="نوبت شما ثبت شد",
            message=f"نوبت شما برای «{service_name}» با موفقیت ثبت شد.",
            appointment=appointment,
        )

        # به صاحب آرایشگاه
        business = getattr(appointment.service, 'business', None)
        if business and business.owner_id:
            customer_name = appointment.user.get_full_name() or appointment.user.phone_number
            create_notification(
                user=business.owner,
                notification_type=NotificationType.NEW_APPOINTMENT,
                title="نوبت جدید ثبت شد",
                message=f"مشتری {customer_name} برای «{service_name}» نوبت گرفت.",
                appointment=appointment,
            )
        return

    # تغییر وضعیت یک نوبت موجود
    old_status = getattr(instance, '_old_status', None)
    new_status = instance.status

    if old_status == new_status:
        return  # هیچ تغییری در وضعیت نبوده، نوتیف اضافه نساز

    if new_status == 'confirmed':
        create_notification(
            user=appointment.user,
            notification_type=NotificationType.APPOINTMENT_CONFIRMED,
            title="نوبت شما تایید شد",
            message=f"نوبت شما برای «{service_name}» تایید شد.",
            appointment=appointment,
        )

    elif new_status == 'canceled':
        # به مشتری - همیشه اطلاع بده که نوبتش لغو شد
        create_notification(
            user=appointment.user,
            notification_type=NotificationType.APPOINTMENT_CANCELED,
            title="نوبت شما لغو شد",
            message=f"نوبت شما برای «{service_name}» لغو شد.",
            appointment=appointment,
        )

        # به صاحب آرایشگاه - فقط برای اطلاع (مثلاً وقتی خود مشتری لغو کرده)
        business = getattr(appointment.service, 'business', None)
        if business and business.owner_id:
            customer_name = appointment.user.get_full_name() or appointment.user.phone_number
            create_notification(
                user=business.owner,
                notification_type=NotificationType.APPOINTMENT_CANCELED_BY_CUSTOMER,
                title="یک نوبت لغو شد",
                message=f"نوبت «{service_name}» مربوط به {customer_name} لغو شد.",
                appointment=appointment,
            )


# ============================== Package Review ==============================

if PackageReview is not None:
    @receiver(post_save, sender=PackageReview)
    def _package_review_notification(sender, instance, created, **kwargs):
        if not created:
            return

        package = instance.package
        business = getattr(package, 'business', None)
        if not business or not business.owner_id:
            return

        reviewer_name = instance.user.get_full_name() or instance.user.phone_number
        create_notification(
            user=business.owner,
            notification_type=NotificationType.NEW_PACKAGE_REVIEW,
            title="نظر جدید ثبت شد",
            message=f"{reviewer_name} روی پکیج «{package.name}» {instance.rating} ستاره داد.",
        )
