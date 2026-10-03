from django.db import models
from users.models import User
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone


class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = "کیف پول من"
        verbose_name_plural = "کیف پول‌ها"

    def __str__(self):
        return f'{self.user}'

    def increase(self, amount):
        self.balance += Decimal(amount)
        self.save()

    def decrease(self, amount):
        amount = Decimal(amount)
        if self.balance - amount < 0:
            raise ValidationError("موجودی کیف پول کافی نیست.")
        self.balance -= amount
        self.save()


class Transaction(models.Model):
    TYPE_CHOICES = [
        ('DEPOSIT', 'واریز'),
        ('WITHDRAW', 'برداشت'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'در انتظار'),
        ('SUCCESS', 'موفق'),
        ('FAILED', 'ناموفق'),
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(
        choices=[('DEPOSIT', 'واریز'), ('WITHDRAW', 'برداشت')],
        max_length=10,
        default='DEPOSIT',
        verbose_name='نوع تراکنش'
    )
    status = models.CharField(
        choices=[('SUCCESS', 'موفق'), ('FAILED', 'ناموفق')],
        max_length=10,
        default='SUCCESS',
        verbose_name='وضعیت'
    )
    reservation = models.ForeignKey('reservations.Appointment', null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تراکنش"
        verbose_name_plural = "تراکنش‌ها"

    def __str__(self):
        return f'{self.type} | {self.amount}'


class Payment(models.Model):
    METHOD_CHOICES = [
        ('WALLET', 'کیف پول'),
        ('GATEWAY', 'درگاه پرداخت'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'در انتظار'),
        ('SUCCESS', 'موفق'),
        ('FAILED', 'ناموفق'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    reservation = models.ForeignKey('reservations.Appointment', null=True, blank=True, on_delete=models.SET_NULL)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "پرداخت"
        verbose_name_plural = "پرداخت‌ها"

    def __str__(self):
        return f'{self.user} | {self.status}'


class NumbersCard(models.Model):
    """اطلاعات کارت‌به‌کارت / حساب بانکی متعلق به یک آرایشگاه."""
    business = models.ForeignKey(
        'business.Business',
        on_delete=models.CASCADE,
        related_name='payment_cards',
        null=True,
        blank=True,
        verbose_name='کسب‌وکار',
    )
    num_code = models.CharField(max_length=26, verbose_name='شماره کارت / شبا')
    name_bank = models.CharField(max_length=50, verbose_name='نام بانک')
    card_holder_name = models.CharField(max_length=100, blank=True, default='', verbose_name='نام صاحب حساب')
    description = models.CharField(max_length=255, blank=True, default='', verbose_name='توضیح پرداخت')
    status = models.BooleanField(default=True, verbose_name='فعال')

    class Meta:
        verbose_name = 'شماره کارت'
        verbose_name_plural = 'شماره کارت‌ها'

    def __str__(self):
        return f'{self.name_bank} | {self.num_code}'


class ManualPayment(models.Model):
    """آپلود فیش کارت‌به‌کارت توسط مشتری و بررسی توسط صاحب آرایشگاه."""
    STATUS_CHOICES = [
        ('pending', 'در انتظار بررسی'),
        ('approved', 'تأیید شده'),
        ('rejected', 'رد شده'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='manual_payments',
        verbose_name='مشتری',
    )
    business = models.ForeignKey(
        'business.Business',
        on_delete=models.CASCADE,
        related_name='manual_payments',
        null=True,
        blank=True,
        verbose_name='کسب‌وکار',
    )
    appointment = models.ForeignKey(
        'reservations.Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='manual_payments',
        verbose_name='نوبت',
    )
    amount = models.DecimalField(
        max_digits=12, decimal_places=0, null=True, blank=True, verbose_name='مبلغ'
    )
    tracking_code = models.CharField(max_length=50, unique=True, verbose_name='کد پیگیری')
    receipt_image = models.ImageField(
        upload_to='payment_receipts/', null=True, blank=True, verbose_name='تصویر فیش'
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name='وضعیت'
    )
    owner_note = models.TextField(blank=True, default='', verbose_name='یادداشت صاحب آرایشگاه')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_manual_payments',
        verbose_name='بررسی‌کننده',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان بررسی')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='زمان ثبت')

    class Meta:
        verbose_name = 'پرداخت دستی'
        verbose_name_plural = 'پرداخت‌های دستی'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} | {self.tracking_code} | {self.status}'
