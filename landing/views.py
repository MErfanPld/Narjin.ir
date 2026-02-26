from django.shortcuts import render

# Create your views here.

from rest_framework.generics import ListAPIView
from .models import ContactMessage, Plan
from .serializers import ContactMessageSerializer, PlanSerializer

class PlanListAPIView(ListAPIView):
    queryset = Plan.objects.filter(is_active=True)
    serializer_class = PlanSerializer


from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAdminUser
from .models import Feature
from .serializers import FeatureSerializer

class FeatureAdminViewSet(ModelViewSet):
    queryset = Feature.objects.all()
    serializer_class = FeatureSerializer
    permission_classes = [IsAdminUser]


from .models import PlanFeature
from .serializers import PlanFeatureSerializer

class PlanFeatureAdminViewSet(ModelViewSet):
    queryset = PlanFeature.objects.all()
    serializer_class = PlanFeatureSerializer
    permission_classes = [IsAdminUser]


from rest_framework.generics import RetrieveAPIView
from business.models import Subscription
from .serializers import SubscriptionSerializer
from rest_framework.permissions import IsAuthenticated

class SubscriptionDetailAPIView(RetrieveAPIView):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # فرض: کاربر فقط یک کسب‌وکار دارد
        return self.request.user.business.subscription
    

from rest_framework import generics
from .models import Article
from .serializers import ArticleSerializer

class ArticleListAPIView(generics.ListAPIView):
    queryset = Article.objects.filter(is_published=True)
    serializer_class = ArticleSerializer


class ArticleDetailAPIView(generics.RetrieveAPIView):
    queryset = Article.objects.filter(is_published=True)
    serializer_class = ArticleSerializer
    lookup_field = 'slug'
    
class ContactMessageCreateAPIView(generics.CreateAPIView):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer