from django.urls import path
from . import views

urlpatterns = [
    path('user/<str:random_code>/', views.PackageUserListView.as_view(), name='package-list-user'),
    path('', views.PackageListView.as_view(), name='package-list'),
    path('create/', views.PackageCreateView.as_view(), name='package-create'),
    path('<int:pk>/', views.PackageDetailView.as_view(), name='package-detail'),
    path('<int:pk>/update/', views.PackageUpdateView.as_view(), name='package-update'),
    path('<int:pk>/delete/', views.PackageDeleteView.as_view(), name='package-delete'),
]