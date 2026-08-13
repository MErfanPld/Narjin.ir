from rest_framework import serializers
from .models import Slider
from business.models import Business


class SliderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Slider
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and not request.user.is_superuser:
            # صاحب آرایشگاه اصلاً فیلد business رو نمی‌بینه و نمی‌فرسته
            self.fields.pop("business", None)

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if user and not user.is_superuser:
            business = Business.objects.filter(owner=user).first()
            if not business:
                raise serializers.ValidationError("شما به هیچ آرایشگاهی متصل نیستید.")
            attrs["business"] = business  # همیشه بیزینس خودش، صرف‌نظر از هر ورودی

        return attrs