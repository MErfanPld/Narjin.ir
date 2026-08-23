from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta
from users.models import User
from landing.models import Plan, PlanFeature
import string, random


def default_trial_end():
    return timezone.now() + timedelta(days=7)


def generate_unique_random_code(length=6):
    from .models import Business
    import random

    while True:
        code = ''.join(random.choices('0123456789', k=length))
        if not Business.objects.filter(random_code=code).exists():
            return code

class Business(models.Model):
    BUSINESS_TYPES = [
        ('male_salon', 'آرایشگاه مردانه'),
        ('female_salon', 'آرایشگاه زنانه'),
    ]

    owner = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='business',
        verbose_name='مالک'
    )
    name = models.CharField(max_length=255, verbose_name='نام کسب‌وکار')
    slug = models.SlugField(max_length=255, unique=True, verbose_name='اسلاگ')
    business_type = models.CharField(max_length=20, choices=BUSINESS_TYPES, verbose_name='نوع کسب‌وکار')
    address = models.CharField(max_length=255, verbose_name='آدرس')
    telephone_number = models.CharField(max_length=15, verbose_name='تلفن ثابت')
    phone_number = models.CharField(max_length=15, verbose_name='شماره تماس')
    is_coffee_shop = models.BooleanField(default=False, verbose_name='کافی‌شاپ')
    is_parking = models.BooleanField(default=False, verbose_name='پارکینگ')
    instagram_link = models.URLField(blank=True, null=True, verbose_name='اینستاگرام')
    random_code = models.CharField(max_length=10, unique=True, default=generate_unique_random_code, verbose_name='کد تصادفی')
    is_active = models.BooleanField(default=False, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')

    class Meta:
        verbose_name = 'کسب‌وکار'
        verbose_name_plural = 'کسب‌وکارها'

    def __str__(self):
        return f"{self.name} - {self.owner.get_full_name() if self.owner else ''}"

    def has_feature(self, feature_key):
        if not hasattr(self, 'subscription'):
            return False
        return self.subscription.has_feature(feature_key)

class Subscription(models.Model):
    business = models.OneToOneField(
        Business,
        on_delete=models.CASCADE,
        related_name='subscription',
        verbose_name='کسب‌وکار'
    )
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='پلن')
    trial_start = models.DateTimeField(default=timezone.now, verbose_name='شروع تست')
    trial_end = models.DateTimeField(default=default_trial_end, verbose_name='پایان تست')
    active = models.BooleanField(default=True, verbose_name='فعال')

    class Meta:
        verbose_name = 'اشتراک'
        verbose_name_plural = 'اشتراک‌ها'

    def __str__(self):
        return f"{self.business.name if self.business else ''} - {self.plan.name if self.plan else 'بدون پلن'}"

    def is_trial(self):
        now = timezone.now()
        return self.trial_start <= now <= self.trial_end

    def has_feature(self, feature_key):
        if self.is_trial():
            return feature_key in ['reservations', 'employees', 'working_hours']
        if self.plan:
            return PlanFeature.objects.filter(plan=self.plan, feature__key=feature_key).exists()
        return False


class Employee(models.Model):
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='employees',
        verbose_name='کسب‌وکار'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='کاربر'
    )
    skill = models.CharField(max_length=255, verbose_name='مهارت')

    class Meta:
        verbose_name = 'کارمند'
        verbose_name_plural = 'کارمندان'

    def __str__(self):
        return f"{self.user.get_full_name() if self.user else 'کاربر حذف شده'} - {self.skill}"


class Service(models.Model):
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='services',
        verbose_name='کسب‌وکار'
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='services',
        verbose_name='کارمند'
    )
    name = models.CharField(max_length=255, verbose_name='نام سرویس')
    description = models.TextField(verbose_name='توضیحات')
    duration = models.DurationField(verbose_name='مدت زمان')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='قیمت')
    is_active = models.BooleanField(default=True, verbose_name='فعال')

    class Meta:
        verbose_name = 'سرویس'
        verbose_name_plural = 'سرویس‌ها'

    def __str__(self):
        return f"{self.name} - {self.business.name if self.business else ''}"


class AvailableTimeSlot(models.Model):
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='slots',
        verbose_name='سرویس'
    )
    date = models.DateField(verbose_name='تاریخ')
    start_time = models.TimeField(verbose_name='ساعت شروع')
    is_available = models.BooleanField(default=True, verbose_name='قابل رزرو')

    class Meta:
        unique_together = ('service', 'date', 'start_time')
        verbose_name = 'زمان قابل رزرو'
        verbose_name_plural = 'زمان‌های قابل رزرو'

    def __str__(self):
        return f"{self.service.name if self.service else ''} - {self.date} {self.start_time.strftime('%H:%M')}"

    @property
    def end_time(self):
        start_dt = datetime.combine(self.date, self.start_time)
        return (start_dt + self.service.duration).time()
