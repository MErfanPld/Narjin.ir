from django.urls import path
from .views import *

urlpatterns = [
    # ================= Business =================
    path('', BusinessListView.as_view(), name='business-list'),
    path('create/', BusinessCreateView.as_view(), name='business-create'),
    path('<int:pk>/', BusinessRetrieveUpdateDestroyView.as_view(), name='business-detail'),
    path('me/', BusinessMeView.as_view(),name='business-me'),
    path('resolve/<str:random_code>/', ResolveBusinessAPI.as_view(), name='resolve-business'),
    # ================= Employee =================
    path('employees/', EmployeeListView.as_view(), name='employee-list'),
    path('employees/create/', EmployeeCreateView.as_view(), name='employee-create'),
    path('employees/update/<int:pk>/', EmployeeUpdateView.as_view(), name='employee-update'),
    path('employees/<int:pk>/', EmployeeRetrieveDestroyView.as_view(), name='employee-detail'),

    # ================= Service =================
    path('services/', ServiceListView.as_view(), name='service-list'),
    path('services/create/', ServiceCreateView.as_view(), name='service-create'),
    path('services/<int:pk>/', ServiceRetrieveUpdateDestroyView.as_view(), name='service-detail'),

    # ================= AvailableTimeSlot =================
    path('slots/', AvailableTimeSlotListView.as_view(), name='slot-list'),
    path('slots/create/', AvailableTimeSlotCreateView.as_view(), name='slot-create'),
    path('slots/<int:pk>/', AvailableTimeSlotRetrieveUpdateDestroyView.as_view(), name='slot-detail-update-delete'),
    path('slots/<int:pk>/status/', TimeSlotStatusUpdateView.as_view(), name='slot-status-update'),

    # ================= Available times by service =================
    path("available-times/", AvailableTimesByServiceView.as_view(), name="available-times-by-service"),

    path('customer/business/<str:random_code>/', CustomerBusinessView.as_view(), name='customer-business'),

    path('employees/mine/', EmployeeListView.as_view(), name='employee-list-mine'),
    path('customers/mine/', BusinessCustomerListView.as_view(), name='customer-list-mine'),

]
