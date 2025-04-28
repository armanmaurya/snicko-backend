from rest_framework import serializers
from .models import Item, Booking

class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = ['id', 'name', 'description', 'condition_notes', 'price_per_day', 'deposit_amount', 'location', 'image', 'is_available']

class ItemGetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = "__all__"

class BookingSerializer(serializers.ModelSerializer):
    item = ItemSerializer()  # Use ItemSerializer to make 'item' an object

    class Meta:
        model = Booking
        fields = ['id', 'renter', 'item', 'start_date', 'end_date', 'total_price', 'status', 'pickup_photo', 'return_photo']