from django.urls import path
from .views import register_user, login_user, UpdateAddressView, get_user_name, get_user_id, PickUpSpotView, GoogleLoginView, FCMTokenView

urlpatterns = [
    path('register/', register_user, name='register_user'),
    path('login/', login_user, name='login_user'),
    path('update_address/', UpdateAddressView.as_view(), name='update_address'),
    path('get_user_name/', get_user_name, name='get_user_name'),
    path('get_user_id/', get_user_id, name='get_user_id'),
    path('address/', PickUpSpotView.as_view(), name='address_list'),
    path('address/<int:pk>/', PickUpSpotView.as_view(), name='address_detail'),
    path('google-login/', GoogleLoginView.as_view(), name='google_login'),
    path('fcm_token/', FCMTokenView.as_view(), name='fcm_token'),
]
