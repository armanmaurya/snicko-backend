from django.urls import path
from .views import ItemView

urlpatterns = [
    path('items/<int:pk>/', ItemView.as_view(), name='item-detail'),
    path('items/', ItemView.as_view(), name='item-list'),
]
