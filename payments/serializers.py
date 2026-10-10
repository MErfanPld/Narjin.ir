from rest_framework import serializers
from payments.models import *
from business.models import Business
from business.utils import get_business_or_404
import uuid


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['balance']


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'amount', 'type', 'status', 'created_at', 'reservation']
        depth = 1


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"


class NumbersCardSerializer(serializers.ModelSerializer):
    """کارت بانکی؛ business در پاسخ به‌صورت آبجکت برمی‌گردد."""
    business = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = NumbersCard
        fields = [
            'id', 'business', 'num_code', 'name_bank',
            'card_holder_name', 'description', 'status',
        ]
        read_only_fields = ['business']

    def get_business(self, obj):
        if not obj.business_id:
            return None
        b = obj.business
        return {
            'id': b.id,
            'name': b.name,
            'random_code': b.random_code,
            'is_active': b.is_active,
        }

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and not user.is_superuser:
            business = getattr(user, 'business', None)
            if not business:
                raise serializers.ValidationError('شما صاحب کسب‌وکار نیستید.')
            validated_data['business'] = business
        return super().create(validated_data)


class ManualPaymentSerializer(serializers.ModelSerializer):
    business_code = serializers.CharField(write_only=True, required=False, allow_blank=True)
    customer_name = serializers.SerializerMethodField(read_only=True)
    customer_phone = serializers.SerializerMethodField(read_only=True)
    business_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ManualPayment
        fields = [
            'id', 'user', 'business', 'business_code', 'appointment',
            'amount', 'tracking_code', 'receipt_image', 'status',
            'owner_note', 'reviewed_by', 'reviewed_at', 'created_at',
            'customer_name', 'customer_phone', 'business_name',
        ]
        read_only_fields = [
            'status', 'created_at', 'user', 'reviewed_by', 'reviewed_at',
            'owner_note', 'business',
        ]

    def get_customer_name(self, obj):
        if obj.user:
            return obj.user.get_full_name()
        return None

    def get_customer_phone(self, obj):
        return obj.user.phone_number if obj.user else None

    def get_business_name(self, obj):
        return obj.business.name if obj.business else None

    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        business_code = validated_data.pop('business_code', None)
        business = validated_data.get('business')

        if business_code:
            business = get_business_or_404(business_code)
        elif not business:
            raise serializers.ValidationError({
                'business_code': 'کد آرایشگاه یا شناسه کسب‌وکار الزامی است.'
            })

        tracking = validated_data.get('tracking_code') or str(uuid.uuid4())[:12].upper()
        validated_data['tracking_code'] = tracking
        validated_data['user'] = user
        validated_data['business'] = business
        validated_data['status'] = 'pending'
        return super().create(validated_data)


class ManualPaymentReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['approved', 'rejected'])
    owner_note = serializers.CharField(required=False, allow_blank=True, default='')
