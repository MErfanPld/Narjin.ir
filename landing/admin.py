from django.contrib import admin
from .models import *

class PlanFeatureInline(admin.TabularInline):
    model = PlanFeature
    extra = 1
    autocomplete_fields = ['feature']
    fields = ('feature', 'value')


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'price_display',
        'duration_days',
        'feature_count',
        'is_active',
    )

    list_filter = ('is_active',)
    search_fields = ('title',)
    list_editable = ('is_active',)
    ordering = ('price',)

    inlines = [PlanFeatureInline]

    fieldsets = (
        ('اطلاعات پلن', {
            'fields': ('title', 'price', 'duration_days')
        }),
        ('وضعیت', {
            'fields': ('is_active',)
        }),
    )

    def price_display(self, obj):
        return f"{obj.price:,} تومان"
    price_display.short_description = 'قیمت'

    def feature_count(self, obj):
        return obj.features.count()
    feature_count.short_description = 'تعداد ویژگی‌ها'


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ('title', 'key')
    search_fields = ('title', 'key')
    prepopulated_fields = {
        'key': ('title',)
    }
    
    
# @admin.register(PlanFeature)
# class PlanFeatureAdmin(admin.ModelAdmin):
#     list_display = ('plan', 'feature', 'value')
#     list_filter = ('plan',)
#     search_fields = ('feature__title', 'plan__title')

from .models import Article

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_published', 'created_at')
    prepopulated_fields = {"slug": ("title",)}
    list_filter = ('is_published',)
    search_fields = ('title', 'content')

from django.contrib import admin
from .models import ContactMessage

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'subject', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('full_name', 'subject')
    readonly_fields = ('created_at',)
