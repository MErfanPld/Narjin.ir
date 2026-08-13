from rest_framework import serializers
from business.models import Business
from .models import Package, Service
from business.serializers import BusinessSerializer, ServiceSerializer


class PackageSerializer(serializers.ModelSerializer):
    business = BusinessSerializer(read_only=True)
    business_id = serializers.PrimaryKeyRelatedField(
        queryset=Business.objects.all(),
        source='business',
        write_only=True,
        required=False,  # دیگه برای صاحب آرایشگاه اجباری نیست، خودکار ست میشه
    )
    services = ServiceSerializer(many=True, read_only=True)
    service_ids = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all(),
        source='services',
        many=True,
        write_only=True,
        required=True
    )

    class Meta:
        model = Package
        fields = [
            'id', 'business', 'business_id', 'name', 'desc',
            'total_price', 'image', 'services', 'service_ids',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and not getattr(request.user, 'is_superuser', False):
            self.fields.pop('business_id', None)

    def validate(self, attrs):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and not user.is_superuser:
            business = getattr(user, 'business', None)  # چون OneToOne با related_name='business'
            if not business:
                raise serializers.ValidationError("شما به هیچ کسب‌وکاری متصل نیستید.")
            attrs['business'] = business
        return attrs

    def validate_service_ids(self, value):
        if not value:
            raise serializers.ValidationError("حداقل یک سرویس باید انتخاب شود.")
        return value

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['image'] = instance.image.url if instance.image else None
        return representation