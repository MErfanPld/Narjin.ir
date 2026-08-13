from django.urls import path
from .views import SliderListCreateView, SliderRetrieveUpdateDestroyView, SliderListView

urlpatterns = [
    path("sliders/user/<str:random_code>/", SliderListView.as_view(), name="slider-list-customer"),
    path("sliders/", SliderListCreateView.as_view(), name="slider-list-create"),
    path("sliders/<int:pk>/", SliderRetrieveUpdateDestroyView.as_view(), name="slider-detail"),
]