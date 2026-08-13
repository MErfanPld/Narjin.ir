from rest_framework import generics
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated

from acl.mixins import PermissionMixin
from acl.rest_mixin import RestPermissionMixin
from .models import Package
from .serializers import PackageSerializer
from business.models import Business


class PackageUserListView(generics.ListAPIView):
    """مشتری: فقط پکیج‌های همون آرایشگاه، از روی کد تصادفی"""
    serializer_class = PackageSerializer

    def get_queryset(self):
        random_code = self.kwargs.get('random_code')
        business = Business.objects.filter(random_code=random_code, is_active=True).first()
        if not business:
            raise NotFound("آرایشگاهی با این کد یافت نشد.")
        return Package.objects.filter(business=business)


class PackageListView(PermissionMixin, generics.ListAPIView):
    """پنل مدیریت: صاحب فقط پکیج‌های خودش، ادمین همه رو می‌بینه"""
    permission_classes = [RestPermissionMixin]
    permissions = ['packages_list']
    serializer_class = PackageSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Package.objects.all()
        return Package.objects.filter(business__owner=user)


class PackageCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, RestPermissionMixin]
    permissions = ['packages_create']
    serializer_class = PackageSerializer
    # دیگه نیازی به perform_create دستی نیست؛ business توی validate() سریالایزر ست میشه


class PackageDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PackageSerializer

    def get_queryset(self):
        return Package.objects.all()


class PackageUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated, RestPermissionMixin]
    permissions = ["packages_edit"]
    serializer_class = PackageSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Package.objects.all()
        return Package.objects.filter(business__owner=user)


class PackageDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated, RestPermissionMixin]
    permissions = ['packages_delete']
    serializer_class = PackageSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Package.objects.all()
        return Package.objects.filter(business__owner=user)