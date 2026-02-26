from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register('admin/features', FeatureAdminViewSet)
router.register('admin/plan-features', PlanFeatureAdminViewSet)

urlpatterns = [
    path('plans/', PlanListAPIView.as_view()),
    path('', include(router.urls)),
    path('subscription/', SubscriptionDetailAPIView.as_view(), name='subscription-detail'),
    path('article/', ArticleListAPIView.as_view(), name='article-list'),
    path('article/<slug:slug>/', ArticleDetailAPIView.as_view(), name='article-detail'),
    path('contact/', ContactMessageCreateAPIView.as_view(), name='contact-create'),
]
