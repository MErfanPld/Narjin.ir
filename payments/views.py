import io
import base64

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from acl.rest_mixin import RestPermissionMixin
from payments.models import Wallet, Transaction, NumbersCard, ManualPayment
from .serializers import (
    WalletSerializer,
    TransactionSerializer,
    NumbersCardSerializer,
    ManualPaymentSerializer,
    ManualPaymentReviewSerializer,
)
from rest_framework import status, generics, permissions
from django.shortcuts import get_object_or_404
from reservations.models import Appointment
from django.core.exceptions import ValidationError
from django.utils import timezone
from business.models import Business
from business.utils import get_business_or_404


class WalletView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        serializer = WalletSerializer(wallet)
        return Response(serializer.data)

    def post(self, request):
        amount = request.data.get('balance')
        if not amount:
            return Response({'error': 'مبلغ وارد نشده است'}, status=400)

        try:
            amount = float(amount)
        except ValueError:
            return Response({'error': 'مبلغ معتبر نیست'}, status=400)

        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        wallet.increase(amount)

        Transaction.objects.create(
            wallet=wallet,
            amount=amount,
            type='DEPOSIT',
            status='SUCCESS'
        )

        return Response({'message': 'شارژ با موفقیت انجام شد'}, status=status.HTTP_200_OK)


class WalletTransactionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        transactions = Transaction.objects.filter(wallet=wallet).order_by('-created_at')
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)


class PayAppointmentWithWalletAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, appointment_id):
        appointment = get_object_or_404(Appointment, pk=appointment_id, user=request.user)

        if appointment.status != 'pending':
            return Response(
                {"error": "رزرو قبلاً پرداخت یا تایید شده است."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            appointment.pay_with_wallet()
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "پرداخت با کیف پول موفقیت‌آمیز بود."})


class NumbersCardListView(generics.ListAPIView):
    """لیست کارت‌های فعال یک آرایشگاه برای مشتری (با random_code)."""
    serializer_class = NumbersCardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        random_code = self.request.query_params.get('business_code') or self.kwargs.get('random_code')
        if random_code:
            business = get_business_or_404(random_code)
            return NumbersCard.objects.filter(business=business, status=True)
        return NumbersCard.objects.filter(status=True, business__isnull=True)


class NumbersCardListCreateView(generics.ListCreateAPIView):
    """صاحب آرایشگاه: مدیریت کارت‌های خودش."""
    serializer_class = NumbersCardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return NumbersCard.objects.all()
        business = getattr(user, 'business', None)
        if not business:
            return NumbersCard.objects.none()
        return NumbersCard.objects.filter(business=business)

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_superuser:
            serializer.save()
            return
        business = getattr(user, 'business', None)
        if not business:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('شما صاحب کسب‌وکار نیستید.')
        serializer.save(business=business)


class NumbersCardDetailView(generics.RetrieveUpdateDestroyAPIView):
    """ویرایش/حذف کارت — فقط صاحب همان آرایشگاه یا ادمین."""
    serializer_class = NumbersCardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return NumbersCard.objects.all()
        business = getattr(user, 'business', None)
        if not business:
            return NumbersCard.objects.none()
        return NumbersCard.objects.filter(business=business)


class ManualPaymentListCreateView(generics.ListCreateAPIView):
    """مشتری: فیش‌های خودش؛ صاحب آرایشگاه: فیش‌های سالنش."""
    serializer_class = ManualPaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return ManualPayment.objects.all().select_related('user', 'business')
        business = getattr(user, 'business', None)
        if business:
            return ManualPayment.objects.filter(business=business).select_related('user', 'business')
        return ManualPayment.objects.filter(user=user).select_related('user', 'business')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ManualPaymentDetailView(generics.RetrieveAPIView):
    serializer_class = ManualPaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return ManualPayment.objects.all()
        business = getattr(user, 'business', None)
        if business:
            return ManualPayment.objects.filter(business=business)
        return ManualPayment.objects.filter(user=user)


class ManualPaymentStatusUpdateView(APIView):
    """تأیید یا رد فیش توسط صاحب آرایشگاه (یا ادمین)."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        payment = get_object_or_404(ManualPayment.objects.select_related('business'), pk=pk)
        user = request.user

        is_owner = (
            payment.business
            and getattr(user, 'business', None)
            and payment.business_id == user.business.id
        )
        if not (user.is_superuser or user.is_staff or is_owner):
            return Response({"error": "دسترسی ندارید."}, status=status.HTTP_403_FORBIDDEN)

        serializer = ManualPaymentReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data['status']
        if payment.status != 'pending':
            return Response(
                {"error": "این فیش قبلاً بررسی شده است."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment.status = new_status
        payment.owner_note = serializer.validated_data.get('owner_note', '')
        payment.reviewed_by = user
        payment.reviewed_at = timezone.now()
        payment.save(update_fields=['status', 'owner_note', 'reviewed_by', 'reviewed_at'])

        return Response({
            "message": "وضعیت پرداخت با موفقیت تغییر کرد.",
            "payment": ManualPaymentSerializer(payment, context={'request': request}).data,
        })


class BusinessQRCodeView(APIView):
    """تولید QR لینک رزرو؛ اگر لوگو باشد در مرکز QR قرار می‌گیرد."""
    permission_classes = [AllowAny]

    def get(self, request, random_code):
        business = get_object_or_404(Business, random_code=random_code, is_active=True)

        base_url = request.query_params.get('base_url', '').rstrip('/')
        if not base_url:
            base_url = request.build_absolute_uri('/').rstrip('/')
        booking_url = f"{base_url}/salon/{business.random_code}"

        try:
            import qrcode
            from qrcode.image.styledpil import StyledPilImage
            from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
            from PIL import Image
        except ImportError:
            return Response(
                {"error": "کتابخانه qrcode یا pillow نصب نیست."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=12,
            border=2,
        )
        qr.add_data(booking_url)
        qr.make(fit=True)

        try:
            img = qr.make_image(
                image_factory=StyledPilImage,
                module_drawer=RoundedModuleDrawer(),
            )
        except Exception:
            img = qr.make_image(fill_color="black", back_color="white")

        img = img.convert('RGB')

        if business.logo:
            try:
                logo = Image.open(business.logo.path).convert('RGBA')
                qr_w, qr_h = img.size
                logo_max = int(min(qr_w, qr_h) * 0.22)
                logo.thumbnail((logo_max, logo_max), Image.Resampling.LANCZOS)

                pad = 8
                bg_size = (logo.size[0] + pad * 2, logo.size[1] + pad * 2)
                bg = Image.new('RGBA', bg_size, (255, 255, 255, 255))
                bg.paste(logo, (pad, pad), logo if logo.mode == 'RGBA' else None)

                pos = ((qr_w - bg_size[0]) // 2, (qr_h - bg_size[1]) // 2)
                img_rgba = img.convert('RGBA')
                img_rgba.paste(bg, pos, bg)
                img = img_rgba.convert('RGB')
            except Exception:
                pass

        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        b64 = base64.b64encode(buffer.read()).decode('ascii')

        return Response({
            "business": {
                "id": business.id,
                "name": business.name,
                "random_code": business.random_code,
                "logo": request.build_absolute_uri(business.logo.url) if business.logo else None,
            },
            "booking_url": booking_url,
            "qr_image_base64": f"data:image/png;base64,{b64}",
        })
