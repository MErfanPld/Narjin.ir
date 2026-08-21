from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import *
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, NotFound
from acl.mixins import PermissionMixin
from acl.rest_mixin import RestPermissionMixin
from drf_spectacular.utils import extend_schema, OpenApiParameter
from datetime import datetime
from rest_framework.exceptions import PermissionDenied

from .models import Business, Employee, Service, AvailableTimeSlot
from reservations.models import Appointment
from .serializers import *


# ================= Helper =================
def filter_by_owner(user, queryset):
    if user.is_superuser:
        return queryset
    return queryset.filter(business__owner=user)

# ================= Business CRUD =================
class BusinessListView(PermissionMixin, generics.ListAPIView):
    permission_classes = [IsAuthenticated, RestPermissionMixin]
    permissions = []
    serializer_class = BusinessSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Business.objects.all()
        return Business.objects.filter(owner=user)


class BusinessCreateView(PermissionMixin, generics.CreateAPIView):
    permission_classes = [IsAuthenticated, RestPermissionMixin]
    permissions = []
    serializer_class = BusinessSerializer
    queryset = Business.objects.all()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class BusinessRetrieveUpdateDestroyView(PermissionMixin, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, RestPermissionMixin]
    permissions = ['business_edit', 'business_delete']
    serializer_class = BusinessSerializer
    queryset = Business.objects.all()

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Business.objects.all()
        return Business.objects.filter(owner=user)


class BusinessMeView(PermissionMixin, generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, RestPermissionMixin]
    permissions = []
    serializer_class = BusinessSerializer

    def get_object(self):
        try:
            return Business.objects.get(owner=self.request.user)
        except Business.DoesNotExist:
            raise NotFound("شما هنوز کسب‌وکاری ثبت نکرده‌اید.")


class ResolveBusinessAPI(APIView):
    """
    API برای گرفتن اطلاعات آرایشگاه از طریق کد
    مشتری باید لاگین باشد
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, random_code):  # <-- اضافه شد
        code = random_code  # مسیر رو می‌گیری
        try:
            business = Business.objects.get(random_code=code, is_active=True)
        except Business.DoesNotExist:
            return Response({"error": "کد معتبر نیست یا آرایشگاه فعال نیست"}, status=HTTP_404_NOT_FOUND)

        services = Service.objects.filter(business=business, is_active=True)
        services_data = ServiceSerializer(services, many=True).data

        return Response({
            "business": {
                "id": business.id,
                "name": business.name,
                "address": business.address,
                "phone_number": business.phone_number,
                "instagram_link": business.instagram_link,
            },
            "services": services_data
        }, status=HTTP_200_OK)


# business/views.py

from django.db.models import Count
from reservations.models import Appointment  # مسیر واقعی اپ نوبت‌دهی رو تنظیم کن


class BusinessCustomerListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, RestPermissionMixin]
    permissions = ['customer_list']
    serializer_class = CustomerSerializer

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return User.objects.all()

        business = getattr(user, 'business', None)
        if not business:
            raise PermissionDenied("شما صاحب هیچ کسب‌وکاری نیستید.")

        customer_ids = Appointment.objects.filter(
            employee__business=business
        ).values_list('user_id', flat=True).distinct()

        return User.objects.filter(id__in=customer_ids)
        


# ================= Employee CRUD =================
class EmployeeListView(PermissionMixin, generics.ListAPIView):
    """صاحب آرایشگاه فقط کارمندان خودش را می‌بیند"""
    permission_classes = [IsAuthenticated, RestPermissionMixin]
    permissions = ['employee_list']
    serializer_class = EmployeeSerializer
 
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Employee.objects.all()
 
        business = getattr(user, 'business', None)
        if not business:
            raise PermissionDenied("شما صاحب هیچ کسب‌وکاری نیستید.")
 
        return Employee.objects.filter(business=business)
 
 
class EmployeeCreateView(PermissionMixin, generics.CreateAPIView):
    """
    ساخت کارمند جدید.
    صاحب آرایشگاه هیچ دسترسی‌ای به لیست کاربران موجود ندارد -
    فقط اطلاعات کارمند جدید (نام، تلفن) را وارد می‌کند و یک حساب کاربری
    جدید برایش ساخته می‌شود.
    """
    permission_classes = [IsAuthenticated, RestPermissionMixin]
    permissions = ['employee_create']
    serializer_class = EmployeeCreateSerializer
 
 
class EmployeeUpdateView(PermissionMixin, generics.UpdateAPIView):
    """ویرایش کارمند - فقط مهارت و اطلاعات خودش، بدون امکان تعویض user"""
    permission_classes = [IsAuthenticated, RestPermissionMixin]
    permissions = ['employee_edit']
    serializer_class = EmployeeUpdateSerializer
 
    def get_queryset(self):
        return filter_by_owner(self.request.user, Employee.objects.all())
 
 
class EmployeeRetrieveDestroyView(PermissionMixin, generics.RetrieveDestroyAPIView):
    permission_classes = [IsAuthenticated, RestPermissionMixin]
    permissions = ['employee_delete']
    serializer_class = EmployeeSerializer
 
    def get_queryset(self):
        return filter_by_owner(self.request.user, Employee.objects.all())
 
 
class EmployeeDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, RestPermissionMixin]
    serializer_class = EmployeeSerializer
 
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Employee.objects.all()
        return Employee.objects.filter(business__owner=user)
 
# ================= Service CRUD =================
class ServiceListView(PermissionMixin, generics.ListAPIView):
    permission_classes = [IsAuthenticated, RestPermissionMixin]
    permissions = ['service_list']
    serializer_class = ServiceSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Service.objects.all()
        return Service.objects.filter(business__owner=user)


class ServiceCreateView(PermissionMixin, generics.CreateAPIView):
    permission_classes = [IsAuthenticated, RestPermissionMixin]
    permissions = ['service_create']
    serializer_class = ServiceSerializer
    queryset = Service.objects.all()

    def perform_create(self, serializer):
        business = Business.objects.filter(owner=self.request.user).first()
        if not business:
            raise ValidationError("کاربر صاحب کسب‌وکار نیست")
        serializer.save(business=business)


class ServiceRetrieveUpdateDestroyView(PermissionMixin, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, RestPermissionMixin]
    permissions = ['service_edit', 'service_delete']
    serializer_class = ServiceSerializer
    queryset = Service.objects.all()

    def get_queryset(self):
        return Service.objects.filter(business__owner=self.request.user)

# ================= Available Time Slot CRUD =================

def filter_available_slots_by_owner(user, queryset):
    if user.is_superuser:
        return queryset
    return queryset.filter(service__business__owner=user)

class AvailableTimeSlotListView(PermissionMixin, generics.ListAPIView):
    permission_classes = [IsAuthenticated, RestPermissionMixin]
    permissions = ['time_slot_list']
    serializer_class = AvailableTimeSlotSerializer
    queryset = AvailableTimeSlot.objects.all()

    def get_queryset(self):
        return filter_available_slots_by_owner(self.request.user, AvailableTimeSlot.objects.all())


class AvailableTimeSlotCreateView(PermissionMixin, generics.CreateAPIView):
    permission_classes = [IsAuthenticated, RestPermissionMixin]
    permissions = ['time_slot_create']
    serializer_class = AvailableTimeSlotSerializer
    queryset = AvailableTimeSlot.objects.all()

    def perform_create(self, serializer):
        user = self.request.user
        business = Business.objects.filter(owner=user).first()
        if not business:
            raise ValidationError("کاربر صاحب کسب‌وکار نیست")

        service = serializer.validated_data.get('service')
        if service.business != business:
            raise ValidationError("سرویس انتخاب‌شده متعلق به کسب‌وکار شما نیست")

        serializer.save()



class AvailableTimeSlotRetrieveUpdateDestroyView(PermissionMixin, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, RestPermissionMixin]
    permissions = ['time_slot_update', 'time_slot_delete']
    serializer_class = AvailableTimeSlotSerializer
    queryset = AvailableTimeSlot.objects.all()

    def get_queryset(self):
        return AvailableTimeSlot.objects.filter(
            service__business__owner=self.request.user
        )

class TimeSlotStatusUpdateView(PermissionMixin, generics.UpdateAPIView):
    permission_classes = [IsAuthenticated, RestPermissionMixin]
    permissions = []
    serializer_class = TimeSlotStatusUpdateSerializer
    queryset = AvailableTimeSlot.objects.all()

    def get_queryset(self):
        return AvailableTimeSlot.objects.filter(
            service__business__owner=self.request.user
        )

class AvailableTimeSlotListCreateView(PermissionMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, RestPermissionMixin]
    permissions = ['time_slot_list', 'time_slot_create']
    serializer_class = AvailableTimeSlotSerializer

    def get_queryset(self):
        service_id = self.request.query_params.get('service_id')
        date = self.request.query_params.get('date')
        
        # فیلتر بر اساس مالک
        queryset = AvailableTimeSlot.objects.filter(
            service__business__owner=self.request.user,
            is_available=True
        )
        
        if service_id:
            queryset = queryset.filter(service_id=service_id)
        if date:
            queryset = queryset.filter(date=date)
        return queryset

# ================= Available Times by Service =================
@extend_schema(
    parameters=[
        OpenApiParameter(name='service_id', description='ID سرویس انتخاب‌شده', required=True, type=int),
        OpenApiParameter(name='date', description='تاریخ رزرو (YYYY-MM-DD)', required=True, type=str),
    ],
    responses={200: OpenApiParameter(name='available_times', description='لیست ساعت‌های دردسترس', type=dict)}
)
class AvailableTimesByServiceView(APIView):
    permission_classes = [IsAuthenticated]
    permissions = []

    def get(self, request):
        service_id = request.query_params.get('service_id')
        date = request.query_params.get('date')
        if not service_id or not date:
            return Response({"error": "service_id و date الزامی است"}, status=400)

        try:
            service = Service.objects.get(id=service_id)
        except Service.DoesNotExist:
            return Response({"error": "سرویس یافت نشد"}, status=404)

        slots = AvailableTimeSlot.objects.filter(service=service, date=date, is_available=True)
        available_times = []

        for slot in slots:
            start_dt = datetime.combine(slot.date, slot.start_time)
            end_dt = start_dt + service.duration

            has_conflict = Appointment.objects.filter(
                service=service,
                time_slot__date=date,
                status='confirmed',
                time_slot__start_time__lt=end_dt.time(),
                time_slot__end_time__gt=start_dt.time()
            ).exists()

            if not has_conflict:
                available_times.append({
                    "slot_id": slot.id,
                    "start_time": slot.start_time.strftime("%H:%M"),
                    "end_time": end_dt.time().strftime("%H:%M")
                })

        return Response(available_times)


# ================= Customer View =================

from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import *
from datetime import datetime
from .models import Business, Employee, Service, AvailableTimeSlot
from reservations.models import Appointment
from .serializers import (
    EmployeeSerializer,
    ServiceSerializer,
    AvailableTimeSlotSerializer
)
from datetime import datetime, date as dt_date, timedelta


class CustomerBusinessView(APIView):
    permission_classes = [IsAuthenticated]
    """
    نمایش اطلاعات بیزینس و داده‌های مختلف برای مشتری از طریق لینک.
    Query parameter:
        tab: "services" | "employees" | "slots"
        date: "YYYY-MM-DD" (برای اسلات، اختیاری)
    """
    def get(self, request, random_code):
        tab = request.query_params.get('tab')
        date_str = request.query_params.get('date')
        business = get_object_or_404(Business, random_code=random_code, is_active=True)
        services = Service.objects.filter(business=business, is_active=True)
        employees = Employee.objects.filter(business=business, user__is_active=True)
        result = {
            "business": {
                "id": business.id,
                "name": business.name,
                "address": business.address,
                "phone_number": business.phone_number,
                "instagram_link": business.instagram_link,
            },
            "tab": tab or "all",
            "data": {}
        }

        # ================= Helper برای اسلات =================
        def get_available_slots(slots_queryset):
            available_slots = []
            for slot in slots_queryset:
                slot_start = datetime.combine(slot.date, slot.start_time)
                slot_end = slot_start + slot.service.duration

                appointments = Appointment.objects.filter(
                    service=slot.service,
                    time_slot__date=slot.date,
                    status='confirmed'
                )

                conflict = False
                for appt in appointments:
                    appt_start = datetime.combine(appt.time_slot.date, appt.time_slot.start_time)
                    appt_end = appt_start + appt.service.duration
                    if slot_start < appt_end and slot_end > appt_start:
                        conflict = True
                        break

                if not conflict:
                    available_slots.append({
                        "slot_id": slot.id,
                        "service_id": slot.service.id,
                        "service_name": slot.service.name,
                        "date": slot.date,
                        "start_time": slot.start_time.strftime("%H:%M"),
                        "end_time": slot_end.time().strftime("%H:%M"),
                    })
            return available_slots

        # ================= همه تب‌ها =================
        if not tab:
            # سرویس‌ها
            services = Service.objects.filter(business=business, is_active=True)
            result["data"]["services"] = ServiceSerializer(services, many=True).data

            # کارمندان
            employees = Employee.objects.filter(business=business)
            result["data"]["employees"] = EmployeeSerializer(employees, many=True).data

            # اسلات‌ها
            if date_str:
                try:
                    filter_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    return Response({"error": "فرمت date صحیح نیست. YYYY-MM-DD"}, status=400)
                slots = AvailableTimeSlot.objects.filter(
                    service__business=business,
                    date=filter_date,
                    is_available=True
                )
            else:
                # اگر تاریخ داده نشده → تمام اسلات‌های آینده
                today = dt_date.today()
                slots = AvailableTimeSlot.objects.filter(
                    service__business=business,
                    date__gte=today,
                    is_available=True
                ).order_by('date', 'start_time')

            result["data"]["slots"] = get_available_slots(slots)

        # ================= یک تب مشخص =================
        elif tab == "services":
            services = Service.objects.filter(business=business, is_active=True)
            result["data"] = ServiceSerializer(services, many=True).data

        elif tab == "employees":
            employees = Employee.objects.filter(business=business)
            result["data"] = EmployeeSerializer(employees, many=True).data

        elif tab == "slots":
            if date_str:
                try:
                    filter_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    return Response({"error": "فرمت date صحیح نیست. YYYY-MM-DD"}, status=400)
                slots = AvailableTimeSlot.objects.filter(
                    service__business=business,
                    date=filter_date,
                    is_available=True
                )
            else:
                today = dt_date.today()
                slots = AvailableTimeSlot.objects.filter(
                    service__business=business,
                    date__gte=today,
                    is_available=True
                ).order_by('date', 'start_time')

            result["data"] = get_available_slots(slots)

        else:
            return Response({"error": "tab نامعتبر است"}, status=400)

        return Response(result, status=HTTP_200_OK)