from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('business', '0003_alter_business_business_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='business',
            name='logo',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='business_logos/',
                verbose_name='لوگوی آرایشگاه',
            ),
        ),
    ]
