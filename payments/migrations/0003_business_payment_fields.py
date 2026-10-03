import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('business', '0004_business_logo'),
        ('payments', '0002_initial'),
        ('reservations', '0002_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='numberscard',
            name='business',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='payment_cards',
                to='business.business',
                verbose_name='کسب‌وکار',
            ),
        ),
        migrations.AddField(
            model_name='numberscard',
            name='card_holder_name',
            field=models.CharField(
                blank=True, default='', max_length=100, verbose_name='نام صاحب حساب'
            ),
        ),
        migrations.AddField(
            model_name='numberscard',
            name='description',
            field=models.CharField(
                blank=True, default='', max_length=255, verbose_name='توضیح پرداخت'
            ),
        ),
        migrations.AlterField(
            model_name='numberscard',
            name='num_code',
            field=models.CharField(max_length=26, verbose_name='شماره کارت / شبا'),
        ),
        migrations.AlterField(
            model_name='numberscard',
            name='name_bank',
            field=models.CharField(max_length=50, verbose_name='نام بانک'),
        ),
        migrations.AlterField(
            model_name='numberscard',
            name='status',
            field=models.BooleanField(default=True, verbose_name='فعال'),
        ),
        migrations.AddField(
            model_name='manualpayment',
            name='business',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='manual_payments',
                to='business.business',
                verbose_name='کسب‌وکار',
            ),
        ),
        migrations.AddField(
            model_name='manualpayment',
            name='appointment',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='manual_payments',
                to='reservations.appointment',
                verbose_name='نوبت',
            ),
        ),
        migrations.AddField(
            model_name='manualpayment',
            name='amount',
            field=models.DecimalField(
                blank=True,
                decimal_places=0,
                max_digits=12,
                null=True,
                verbose_name='مبلغ',
            ),
        ),
        migrations.AddField(
            model_name='manualpayment',
            name='owner_note',
            field=models.TextField(blank=True, default='', verbose_name='یادداشت صاحب آرایشگاه'),
        ),
        migrations.AddField(
            model_name='manualpayment',
            name='reviewed_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='reviewed_manual_payments',
                to=settings.AUTH_USER_MODEL,
                verbose_name='بررسی‌کننده',
            ),
        ),
        migrations.AddField(
            model_name='manualpayment',
            name='reviewed_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='زمان بررسی'),
        ),
        migrations.AlterField(
            model_name='manualpayment',
            name='tracking_code',
            field=models.CharField(max_length=50, unique=True, verbose_name='کد پیگیری'),
        ),
        migrations.AlterField(
            model_name='manualpayment',
            name='receipt_image',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='payment_receipts/',
                verbose_name='تصویر فیش',
            ),
        ),
        migrations.AlterField(
            model_name='manualpayment',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'در انتظار بررسی'),
                    ('approved', 'تأیید شده'),
                    ('rejected', 'رد شده'),
                ],
                default='pending',
                max_length=10,
                verbose_name='وضعیت',
            ),
        ),
        migrations.AlterField(
            model_name='manualpayment',
            name='created_at',
            field=models.DateTimeField(
                default=django.utils.timezone.now, verbose_name='زمان ثبت'
            ),
        ),
        migrations.AlterField(
            model_name='manualpayment',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='manual_payments',
                to=settings.AUTH_USER_MODEL,
                verbose_name='مشتری',
            ),
        ),
    ]
