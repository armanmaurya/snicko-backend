from django.urls import path
from .views import ItemView, BookingView, get_item_booking_requests, ManageBookingStatusView

urlpatterns = [
    path('items/<int:pk>/', ItemView.as_view(), name='item-detail'),
    path('items/', ItemView.as_view(), name='item-list'),
    path('bookings/<int:pk>/', BookingView.as_view(), name='booking-detail'),
    path('bookings/', BookingView.as_view(), name='booking-list'),
    path('booking/requests/', get_item_booking_requests, name='booking-requests'),
    path('booking/update-status/<int:pk>/', ManageBookingStatusView.as_view(), name='update-booking-status'),
    # path("all-bookings/", BookingView.as_view(), name="all-bookings"),
]