from rest_framework import serializers
from .models import Item, Booking

class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = ['id', 'name', 'description', 'condition_notes', 'price_per_day', 'deposit_amount', 'location', 'image']

class ItemGetSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.name')
    class Meta:
        model = Item
        fields = "__all__"

class BookingSerializer(serializers.ModelSerializer):
    item = ItemGetSerializer()  # Use ItemSerializer to make 'item' an object

    class Meta:
        model = Booking
        fields = ['id', 'renter', 'item', 'start_date', 'end_date', 'total_price', 'status', 'pickup_photo', 'return_photo', 'rejection_reason']