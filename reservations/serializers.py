from rest_framework import serializers
from business.models import AvailableTimeSlot, Employee, Service
from business.serializers import AvailableTimeSlotSerializer, EmployeeSerializer, ServiceSerializer
from .models import Appointment
from django.db import transaction


class AppointmentSerializer(serializers.ModelSerializer):
    get_status = serializers.ReadOnlyField()
    service = ServiceSerializer(read_only=True)
    employee = EmployeeSerializer(read_only=True)
    employee_name = serializers.SerializerMethodField()
    service_id = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all(), write_only=True
    )
    employee_id = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(), write_only=True, required=False
    )
    time_slot_id = serializers.PrimaryKeyRelatedField(
        queryset=AvailableTimeSlot.objects.all(), write_only=True
    )
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'status', 'user', 'service', 'employee', 'get_status', 'employee_name',
            'service_id', 'employee_id', 'time_slot_id'
        ]

    def get_employee_name(self, obj):
        if obj.employee and obj.employee.user:
            return obj.employee.user.get_full_name() or obj.employee.user.username
        return None

    def validate(self, attrs):
        user = self.context['request'].user
        business = self.context['business']  # از URL random_code میاد

        service = attrs.get('service_id')
        employee = attrs.get('employee_id')
        time_slot = attrs.get('time_slot_id')

        # ۱. سرویس باید متعلق به همین آرایشگاه باشد
        if service.business_id != business.id:
            raise serializers.ValidationError("این سرویس متعلق به این آرایشگاه نیست.")

        # ۲. کارمند (اگر انتخاب شده) باید متعلق به همین آرایشگاه باشد
        if employee and employee.business_id != business.id:
            raise serializers.ValidationError("این کارمند متعلق به این آرایشگاه نیست.")

        # ۳. تایم‌اسلات باید برای همین سرویس تعریف شده باشد
        if time_slot.service_id != service.id:
            raise serializers.ValidationError("این ساعت برای این سرویس تعریف نشده است.")

        # ۴. جلوگیری از رزرو تکراری همان کاربر روی همان اسلات
        if Appointment.objects.filter(user=user, time_slot=time_slot).exists():
            raise serializers.ValidationError("شما قبلاً این بازه زمانی را رزرو کرده‌اید.")

        return attrs

    def create(self, validated_data):
        service = validated_data.pop('service_id')
        employee = validated_data.pop('employee_id', None)
        time_slot = validated_data.pop('time_slot_id')
        user = self.context['request'].user
        validated_data.pop('user', None)

        with transaction.atomic():
            locked_slot = AvailableTimeSlot.objects.select_for_update().get(pk=time_slot.id)

            if not locked_slot.is_available:
                raise serializers.ValidationError("متأسفانه این ساعت لحظاتی پیش رزرو شد.")

            locked_slot.is_available = False
            locked_slot.save(update_fields=['is_available'])

            appointment = Appointment.objects.create(
                user=user,
                service=service,
                employee=employee,
                time_slot=locked_slot,
                **validated_data
            )

        return appointment

# ============================== جدید: برای صاحب ارایشگاه ==============================
class AppointmentBusinessSerializer(serializers.ModelSerializer):
    """سریالایزر برای نمایش نوبت‌ها به صاحب ارایشگاه"""
    customer_name = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    service_name = serializers.CharField(source='service.name')
    employee_name = serializers.SerializerMethodField()
    date = serializers.DateField(source='time_slot.date')
    start_time = serializers.TimeField(source='time_slot.start_time')
    end_time = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            'id', 'status', 'customer_name', 'customer_phone',
            'service_name', 'employee_name', 'date', 'start_time', 'end_time',
            'reminder_sent'
        ]

    def get_customer_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_customer_phone(self, obj):
        return obj.user.phone_number

    def get_employee_name(self, obj):
        if obj.employee and obj.employee.user:
            return obj.employee.user.get_full_name() or obj.employee.user.username
        return "بدون کارمند"

    def get_end_time(self, obj):
        from datetime import datetime, timedelta
        
        # دریافت duration از سرویس
        duration = obj.service.duration
        
        # اگه duration None باشه، مقدار پیش‌فرض بذار
        if duration is None:
            duration = timedelta(minutes=30)
        
        # اگه duration timedelta نباشه، تبدیلش کن
        if not isinstance(duration, timedelta):
            try:
                # اگه به صورت رشته باشه (مثل "00:30:00")
                if isinstance(duration, str):
                    parts = duration.split(':')
                    if len(parts) == 3:
                        h, m, s = map(int, parts)
                        duration = timedelta(hours=h, minutes=m, seconds=s)
                    else:
                        duration = timedelta(minutes=30)
                else:
                    # اگه نوع دیگه‌ای باشه
                    duration = timedelta(minutes=30)
            except:
                duration = timedelta(minutes=30)
        
        # محاسبه زمان پایان
        start_datetime = datetime.combine(obj.time_slot.date, obj.time_slot.start_time)
        end_datetime = start_datetime + duration
        
        return end_datetime.time().strftime("%H:%M")