from rest_framework import serializers
from django.db import transaction
from datetime import datetime
from users.models import User
from .models import AvailableTimeSlot, Business, Employee, Service, Subscription
from reservations.models import Appointment


# ================= Business =================
class BusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = ['id', 'name', 'slug', 'random_code', 'business_type', 'address', 'telephone_number','phone_number', 'is_active']
        read_only_fields = ['random_code', 'is_active']


# ================= Employee =================

class EmployeeSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    business = serializers.SerializerMethodField()
 
    class Meta:
        model = Employee
        fields = ['id', 'user', 'business', 'skill']
 
    def get_user(self, obj):
        role_name = getattr(getattr(obj.user, 'role', None), 'role_name', 'کاربر')
        return {
            "id": obj.user.id,
            "name": f"{obj.user.first_name} {obj.user.last_name}".strip(),
            "phone": obj.user.phone_number,
            "role": role_name
        }
 
    def get_business(self, obj):
        if obj.business:
            return {
                "id": obj.business.id,
                "name": obj.business.name,
                "type": obj.business.business_type,
                "is_active": obj.business.is_active
            }
        return None
 


class EmployeeCreateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(write_only=True, max_length=150)
    last_name = serializers.CharField(write_only=True, max_length=150, required=False, allow_blank=True)
    phone_number = serializers.CharField(write_only=True, max_length=15)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
 
    user = serializers.SerializerMethodField(read_only=True)
    business = serializers.SerializerMethodField(read_only=True)
 
    class Meta:
        model = Employee
        fields = [
            'id', 'first_name', 'last_name', 'phone_number', 'password',
            'user', 'business', 'skill'
        ]
 
    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("کاربری با این شماره تلفن قبلاً ثبت شده است.")
        return value
 
    def get_user(self, obj):
        role_name = getattr(getattr(obj.user, 'role', None), 'role_name', 'کاربر')
        return {
            "id": obj.user.id,
            "name": f"{obj.user.first_name} {obj.user.last_name}".strip(),
            "phone": obj.user.phone_number,
            "role": role_name
        }
 
    def get_business(self, obj):
        if obj.business:
            return {
                "id": obj.business.id,
                "name": obj.business.name,
                "type": obj.business.business_type,
                "is_active": obj.business.is_active
            }
        return None
 
    def create(self, validated_data):
        request = self.context.get('request')
        business = Business.objects.filter(owner=request.user).first()
        if not business:
            raise serializers.ValidationError("شما صاحب کسب‌وکار نیستید یا کسب‌وکار ثبت نشده است.")
 
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name', '')
        phone_number = validated_data.pop('phone_number')
        password = validated_data.pop('password', None) or User.objects.make_random_password()
 
        user = User.objects.create_user(
            phone_number=phone_number,
            first_name=first_name,
            last_name=last_name,
            password=password,
        )
 
        employee = Employee.objects.create(business=business, user=user, **validated_data)
        return employee
 
 
class EmployeeUpdateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', required=False, max_length=150)
    last_name = serializers.CharField(source='user.last_name', required=False, allow_blank=True, max_length=150)
 
    user = serializers.SerializerMethodField(read_only=True)
    business = serializers.SerializerMethodField(read_only=True)
 
    class Meta:
        model = Employee
        fields = ['id', 'first_name', 'last_name', 'user', 'business', 'skill']
 
    def get_user(self, obj):
        role_name = getattr(getattr(obj.user, 'role', None), 'role_name', 'کاربر')
        return {
            "id": obj.user.id,
            "name": f"{obj.user.first_name} {obj.user.last_name}".strip(),
            "phone": obj.user.phone_number,
            "role": role_name
        }
 
    def get_business(self, obj):
        if obj.business:
            return {
                "id": obj.business.id,
                "name": obj.business.name,
                "type": obj.business.business_type,
                "is_active": obj.business.is_active
            }
        return None
 
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        if user_data:
            for attr, value in user_data.items():
                setattr(instance.user, attr, value)
            instance.user.save()
 
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
 

# ================= Service =================
class ServiceSerializer(serializers.ModelSerializer):
    employee_id = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        source='employee',
        write_only=True,
        allow_null=True,
        required=False
    )

    business = BusinessSerializer(read_only=True)
    employee = EmployeeSerializer(read_only=True)

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'price', 'description', 'duration',
            'employee_id', 'business', 'employee', 'is_active'
        ]
        read_only_fields = ['business']

    def create(self, validated_data):
        request = self.context.get('request')
        business = Business.objects.filter(owner=request.user).first()
        validated_data['business'] = business
        return super().create(validated_data)


# ================= AvailableTimeSlot =================
class AvailableTimeSlotSerializer(serializers.ModelSerializer):
    service_id = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.filter(is_active=True),
        source='service',
        write_only=True
    )
    start_time = serializers.TimeField(format='%H:%M')
    end_time = serializers.SerializerMethodField()

    class Meta:
        model = AvailableTimeSlot
        fields = [
            'id', 'service_id', 'service',
            'date', 'start_time', 'end_time',
            'is_available'
        ]
        read_only_fields = ['service']

    def get_end_time(self, obj):
        end = datetime.combine(obj.date, obj.start_time) + obj.service.duration
        return end.time().strftime('%H:%M')


class TimeSlotStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailableTimeSlot
        fields = ['is_available']


# ================= Appointment =================
class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = "__all__"

    def validate(self, attrs):
        service = attrs['service']
        time_slot = attrs['time_slot']

        if time_slot.service != service:
            raise serializers.ValidationError("این ساعت متعلق به سرویس نیست")

        if not time_slot.is_available:
            raise serializers.ValidationError("این ساعت غیرفعال است")

        start_dt = datetime.combine(time_slot.date, time_slot.start_time)
        end_dt = start_dt + service.duration

        conflict = Appointment.objects.filter(
            service=service,
            time_slot__date=time_slot.date,
            status='confirmed',
            time_slot__start_time__lt=end_dt.time(),
            time_slot__end_time__gt=start_dt.time()
        ).exists()

        if conflict:
            raise serializers.ValidationError("این بازه قبلاً رزرو شده")

        return attrs

    def create(self, validated_data):
        with transaction.atomic():
            appointment = super().create(validated_data)
            slot = appointment.time_slot
            slot.is_available = False
            slot.save(update_fields=['is_available'])
            return appointment



class CustomerSerializer(serializers.ModelSerializer):
    appointments_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'phone_number', 'image', 'appointments_count']