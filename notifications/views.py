from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    """
    لیست نوتیفیکیشن‌های کاربر لاگین‌شده (چه مشتری، چه صاحب آرایشگاه - فقط مال خودش).
    فیلتر اختیاری: ?is_read=true / ?is_read=false
    """
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        queryset = Notification.objects.filter(user=self.request.user)
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == 'true')
        return queryset


class NotificationUnreadCountView(APIView):
    """تعداد نوتیفیکیشن‌های خوانده‌نشده - برای بج روی آیکون زنگوله"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({"unread_count": count})


class NotificationMarkReadView(APIView):
    """علامت‌گذاری یک نوتیفیکیشن به‌عنوان خوانده‌شده"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk)
        except Notification.DoesNotExist:
            return Response({"error": "نوتیفیکیشن یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        if notification.user != request.user:
            raise PermissionDenied("دسترسی ندارید.")

        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=['is_read'])

        return Response(NotificationSerializer(notification).data)


class NotificationMarkAllReadView(APIView):
    """علامت‌گذاری همه‌ی نوتیفیکیشن‌های کاربر به‌عنوان خوانده‌شده"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated = Notification.objects.filter(
            user=request.user, is_read=False
        ).update(is_read=True)
        return Response({"message": f"{updated} نوتیفیکیشن خوانده شد."})


class NotificationDeleteView(generics.DestroyAPIView):
    """حذف یک نوتیفیکیشن (فقط مال خودش)"""
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
