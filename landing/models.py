from django.db import models
 
class Feature(models.Model):
    title = models.CharField(verbose_name='عنوان',max_length=100)
    key = models.SlugField(verbose_name='کلید',unique=True) 
    description = models.TextField(verbose_name='توضیحات',blank=True)

    def __str__(self):
        return self.title


class Plan(models.Model):
    title = models.CharField(verbose_name='عنوان',max_length=100)
    price = models.PositiveIntegerField(verbose_name='قیمت')
    duration_days = models.PositiveIntegerField(verbose_name='زمان')
    is_active = models.BooleanField(verbose_name='فعال؟',default=True)

    def __str__(self):
        return self.title


class PlanFeature(models.Model):
    plan = models.ForeignKey(
        Plan,
        verbose_name='پلن',
        on_delete=models.CASCADE,
        related_name='features'
    )
    feature = models.ForeignKey(
        Feature,
        verbose_name='ویژگی',
        on_delete=models.CASCADE
    )

    value = models.CharField(
        max_length=100,
        help_text="مثلا: دارد / ندارد / 5 / نامحدود"
    )

    class Meta:
        unique_together = ('plan', 'feature')


from django.utils.text import slugify

class Article(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    meta_title = models.CharField(max_length=255, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)
    content = models.TextField()
    image = models.ImageField(upload_to='articles/', blank=True, null=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title




class ContactMessage(models.Model):
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True, null=True)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.subject}"
