from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.db import transaction

from acl.rest_mixin import RestPermissionMixin
from reservations.models import Appointment
from reservations.serializers import AppointmentSerializer, AppointmentBusinessSerializer
from reservations.utils import send_cancel_sms, send_reservation_sms
from business.utils import get_business_or_404


# ============================== Appointment - سمت مشتری ==============================

class AppointmentListView(generics.ListAPIView):
    """لیست نوبت‌های خود مشتری (همه‌ی آرایشگاه‌ها)"""
    permission_classes = [IsAuthenticated]
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Appointment.objects.all()
        return Appointment.objects.filter(user=user)


class AppointmentCreateView(generics.CreateAPIView):
    """رزرو نوبت جدید - فقط از طریق کد آرایشگاه (random_code)"""
    permission_classes = [IsAuthenticated]
    serializer_class = AppointmentSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        random_code = self.kwargs.get('random_code')
        if not random_code:
            raise ValidationError("برای رزرو نوبت باید از لینک آرایشگاه (کد) استفاده کنید.")
        context['business'] = get_business_or_404(random_code)
        return context

    @transaction.atomic
    def perform_create(self, serializer):
        appointment = serializer.save()

        phone = appointment.user.phone_number
        name = appointment.user.first_name or "کاربر"
        date = str(appointment.time_slot.date)
        time_ = str(appointment.time_slot.start_time)
        send_reservation_sms(phone, name, date, time_)


class AppointmentRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """جزئیات و حذف نوبت مشتری (بدون وابستگی به random_code)"""
    permission_classes = [IsAuthenticated]
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Appointment.objects.all()
        return Appointment.objects.filter(user=user)


class AppointmentCancelView(APIView):
    """لغو نوبت توسط مشتری - با قفل و جلوگیری از لغو تکراری"""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        appointment = get_object_or_404(
            Appointment.objects.select_for_update(), pk=pk
        )

        # دسترسی: فقط خود کاربر یا superuser
        if not request.user.is_superuser and appointment.user != request.user:
            return Response({"error": "دسترسی ندارید"}, status=403)

        # جلوگیری از لغو دوباره (و ریفاند دوبل)
        if appointment.status == 'canceled':
            return Response({"error": "این نوبت قبلاً لغو شده است."}, status=400)

        # لغو نوبت + بازگشت وجه
        appointment.cancel(refund=True)

        # باز کردن time_slot برای رزرو بعدی
        slot = appointment.time_slot
        slot.is_available = True
        slot.save(update_fields=['is_available'])

        # ارسال پیامک لغو
        send_cancel_sms(
            appointment.user.phone_number,
            appointment.user.first_name or "کاربر",
            appointment.service.name
        )

        return Response({"message": "نوبت با موفقیت لغو شد."}, status=200)


# ============================== Appointment - سمت صاحب آرایشگاه ==============================

class BusinessAppointmentListView(generics.ListAPIView):
    """لیست نوبت‌های آرایشگاه برای صاحب کسب‌وکار"""
    permission_classes = [IsAuthenticated, RestPermissionMixin]
    permissions = ['reservations_list']
    serializer_class = AppointmentBusinessSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Appointment.objects.all()

        # فقط نوبت‌های آرایشگاه متعلق به کاربر
        return Appointment.objects.filter(
            time_slot__service__business__owner=user
        ).select_related(
            'user', 'service', 'employee', 'time_slot'
        ).order_by('-time_slot__date', '-time_slot__start_time')

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        status_param = request.query_params.get('status')
        date_param = request.query_params.get('date')
        service_id_param = request.query_params.get('service_id')

        if status_param:
            queryset = queryset.filter(status=status_param)
        if date_param:
            queryset = queryset.filter(time_slot__date=date_param)
        if service_id_param:
            queryset = queryset.filter(service_id=service_id_param)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class BusinessAppointmentUpdateView(generics.UpdateAPIView):
    """تایید/رد نوبت توسط صاحب آرایشگاه"""
    permission_classes = [IsAuthenticated, RestPermissionMixin]
    permissions = ['reservations_edit']
    serializer_class = AppointmentBusinessSerializer

    def get_queryset(self):
        return Appointment.objects.filter(
            time_slot__service__business__owner=self.request.user
        )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        appointment = self.get_object()
        new_status_value = request.data.get('status')

        if new_status_value not in ['pending', 'confirmed', 'canceled']:
            return Response({"error": "وضعیت نامعتبر است"}, status=400)

        old_status = appointment.status
        appointment.status = new_status_value
        appointment.save(update_fields=['status'])

        # اگر لغو شد، اسلات آزاد بشه
        if new_status_value == 'canceled' and old_status != 'canceled':
            slot = appointment.time_slot
            slot.is_available = True
            slot.save(update_fields=['is_available'])

            send_cancel_sms(
                appointment.user.phone_number,
                appointment.user.first_name or "کاربر",
                appointment.service.name
            )

        serializer = self.get_serializer(appointment)
        return Response(serializer.data)


class BusinessAppointmentDetailView(generics.RetrieveAPIView):
    """جزئیات یک نوبت برای صاحب آرایشگاه"""
    permission_classes = [IsAuthenticated, RestPermissionMixin]
    permissions = ['reservations_list']
    serializer_class = AppointmentBusinessSerializer

    def get_queryset(self):
        return Appointment.objects.filter(
            time_slot__service__business__owner=self.request.user
        )