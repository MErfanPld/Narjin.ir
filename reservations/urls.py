from django.urls import path
from .views import (
    AppointmentListView,
    AppointmentCreateView,
    AppointmentRetrieveUpdateDestroyView,
    AppointmentCancelView,
    BusinessAppointmentListView,
    BusinessAppointmentDetailView,
    BusinessAppointmentUpdateView,
)


urlpatterns = [
    # ====================== برای مشتری ======================
    path('my-appointments/', AppointmentListView.as_view(), name='appointment-list'),
    path('<str:random_code>/book/', AppointmentCreateView.as_view(), name='appointment-create'),
    path('my-appointments/<int:pk>/', AppointmentRetrieveUpdateDestroyView.as_view(), name='appointment-detail'),
    path('my-appointments/<int:pk>/cancel/', AppointmentCancelView.as_view(), name='appointment-cancel'),

    # ====================== برای صاحب آرایشگاه ======================
    path('business/appointments/', BusinessAppointmentListView.as_view(), name='business-appointment-list'),
    path('business/appointments/<int:pk>/', BusinessAppointmentDetailView.as_view(), name='business-appointment-detail'),
    path('business/appointments/<int:pk>/update/', BusinessAppointmentUpdateView.as_view(), name='business-appointment-update'),
]