from rest_framework import serializers

from landing.models import Article, Feature, Plan, PlanFeature


class FeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = ['id', 'title', 'key', 'description']


class PlanFeatureSerializer(serializers.ModelSerializer):
    feature = FeatureSerializer()

    class Meta:
        model = PlanFeature
        fields = ['feature', 'value']


class PlanSerializer(serializers.ModelSerializer):
    features = PlanFeatureSerializer(many=True, read_only=True)

    class Meta:
        model = Plan
        fields = [
            'id',
            'title',
            'price',
            'duration_days',
            'features'
        ]


from rest_framework import serializers
from business.models import Business, Subscription
from business.serializers import BusinessSerializer
from landing.serializers import PlanSerializer

class SubscriptionSerializer(serializers.ModelSerializer):
    business = BusinessSerializer(read_only=True)
    plan = PlanSerializer(read_only=True)

    # مقداردهی queryset مستقیم
    business_id = serializers.PrimaryKeyRelatedField(
        queryset=Business.objects.all(), write_only=True, source='business'
    )
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=Plan.objects.filter(is_active=True),
        write_only=True,
        source='plan',
        required=False,
        allow_null=True
    )

    class Meta:
        model = Subscription
        fields = [
            'id',
            'business', 'plan',
            'business_id', 'plan_id',
            'trial_start', 'trial_end',
            'active'
        ]
        
        
class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = '__all__'
        
        
from .models import ContactMessage

class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = '__all__'
        read_only_fields = ('is_read', 'created_at')