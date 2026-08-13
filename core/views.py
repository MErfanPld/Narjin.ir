from rest_framework import generics, permissions

from acl.mixins import PermissionMixin
from acl.rest_mixin import RestPermissionMixin
from .models import Slider
from .serializers import SliderSerializer
from rest_framework.permissions import IsAuthenticated


from rest_framework import generics
from rest_framework.exceptions import NotFound
from business.models import Business


class SliderListView(generics.ListAPIView):
    """
    بنرهای قابل نمایش برای مشتری یک آرایشگاه خاص:
    بنرهای همون آرایشگاه + بنرهای سراسری ادمین.
    """
    serializer_class = SliderSerializer

    def get_queryset(self):
        random_code = self.kwargs.get("random_code") or self.request.query_params.get("random_code")

        if not random_code:
            raise NotFound("کد آرایشگاه ارسال نشده است.")

        business = Business.objects.filter(random_code=random_code, is_active=True).first()
        if not business:
            raise NotFound("آرایشگاهی با این کد یافت نشد.")

        return Slider.objects.filter(
            models.Q(business=business) | models.Q(business__isnull=True),
            is_active=True
        )


class SliderListCreateView(PermissionMixin, generics.ListCreateAPIView):
    serializer_class = SliderSerializer
    permission_classes = [RestPermissionMixin]
    permissions = ['slider_create', 'slider_list']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Slider.objects.all()
        # صاحب آرایشگاه فقط بنرهای خودش رو می‌بینه/می‌سازه
        return Slider.objects.filter(business__owner=user)  # فیلد owner رو مطابق مدل Business خودت تنظیم کن

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_superuser:
            serializer.save()  # ادمین می‌تونه business رو خالی بذاره یا هر بیزینسی بزنه
        else:
            business = Business.objects.filter(owner=user).first()
            serializer.save(business=business)

class SliderRetrieveUpdateDestroyView(PermissionMixin,generics.RetrieveUpdateDestroyAPIView):
    queryset = Slider.objects.all()
    serializer_class = SliderSerializer
    permission_classes = [RestPermissionMixin]  
    permissions = ['slider_edit','slider_delete']  


# from django.shortcuts import render, redirect
# from django.contrib.auth.mixins import LoginRequiredMixin
# from django.views import View
# from django.utils import timezone
#
# from acl.models import UserPermission
# from reservations.models import Appointment
# from business.models import Employee, Service
# from payments.models import *
# from reservations.forms import AppointmentForm
# from django.contrib.auth.decorators import login_required
# from django.urls import reverse
# # Create your views here.
#
# from decimal import Decimal
#
#
# @login_required
# def home(request):
#     if request.method == "POST":
#         form = AppointmentForm(request.POST)
#         if form.is_valid():
#             appointment = form.save(commit=False)
#             appointment.user = request.user
#             appointment.status = 'pending'
#             appointment.save()
#
#             # ایجاد یا دریافت کیف پول کاربر
#             wallet, created = Wallet.objects.get_or_create(user=request.user)
#             service = appointment.service
#             amount = Decimal(service.price)  # تبدیل قیمت سرویس به Decimal
#
#             # ایجاد تراکنش و افزودن مبلغ به کیف پول
#             Transaction.objects.create(
#                 wallet=wallet, amount=amount, appointment=appointment)
#             # اطمینان از اینکه هر دو مقدار Decimal هستند
#             wallet.balance = Decimal(wallet.balance) + amount
#             wallet.save()
#
#             # ایجاد درخواست برداشت برای ادمین
#             UserWithdrawalRequests.objects.create(
#                 user=request.user, appointment=appointment)
#
#             # هدایت به صفحه پرداخت
#             return redirect(reverse('payment', kwargs={'appointment_id': appointment.id}))
#
#     else:
#         form = AppointmentForm()
#
#     services = Service.objects.all()  # نمایش لیست خدمات برای انتخاب
#     return render(request, "core/home.html", {"form": form, "services": services})
#
#
# class Dashboard(LoginRequiredMixin, View):
#     template_name = './core/dashboard.html'
#
#     def get(self, request, *args, **kwargs):
#         user = request.user
#
#         if user.is_superuser or user.is_owner:
#             appointments = Appointment.objects.all().order_by('-id')
#
#         elif Employee.objects.filter(user=user).exists():
#             employee = Employee.objects.get(user=user)
#             appointments = Appointment.objects.filter(
#                 service__employee=employee).order_by('-id')
#
#         else:
#             appointments = Appointment.objects.filter(
#                 user=user).order_by('-id')
#
#         context = {
#             'appointments': appointments,
#             **self.get_context_data()
#         }
#         return render(request, self.template_name, context)
#
#     def get_context_data(self, **kwargs):
#         today = timezone.now().date()
#         current_time = timezone.now()
#
#         start_of_month = current_time.replace(day=1)
#         end_of_month = (start_of_month.replace(month=start_of_month.month + 1) if start_of_month.month < 12
#                         else start_of_month.replace(year=start_of_month.year + 1, month=1))
#
#         context = {
#             'appointments_count': Appointment.objects.filter(date=today).count(),
#             'transactions_count': Transaction.objects.filter(
#                 created_at__gte=start_of_month, created_at__lt=end_of_month
#             ).count(),
#         }
#         return context
