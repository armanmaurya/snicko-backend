from .models import Item, Booking
from .serializers import ItemSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

# Create your views here.


class ItemView(APIView):
    def get(self, request, pk=None):
        if pk:
            try:
                item = Item.objects.get(pk=pk)
                serializer = ItemSerializer(item)
                return Response(serializer.data)
            except Item.DoesNotExist:
                return Response(
                    {"error": "Item not found"}, status=status.HTTP_404_NOT_FOUND
                )
        else:
            items = Item.objects.all()
            serializer = ItemSerializer(items, many=True)
            return Response(serializer.data)

    def post(self, request):
        serializer = ItemSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk=None):
        try:
            item = Item.objects.get(pk=pk)
            serializer = ItemSerializer(item, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Item.DoesNotExist:
            return Response(
                {"error": "Item not found"}, status=status.HTTP_404_NOT_FOUND
            )
        
    def delete(self, request, pk=None):
        try:
            item = Item.objects.get(pk=pk)
            if item.owner != request.user:
                return Response(
                    {"error": "You do not have permission to delete this item"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            item.delete()
            return Response({"message": "Item deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except Item.DoesNotExist:
            return Response(
                {"error": "Item not found"}, status=status.HTTP_404_NOT_FOUND
            )
    
    def get_permissions(self):
        if self.request.method in ["POST", "PUT", "DELETE"]:
            return [IsAuthenticated()]
        return super().get_permissions()


class BookingView(APIView):
    def post(self, request, pk=None):
        if pk:
            try:
                item = Item.objects.get(pk=pk)
                booking = Booking.objects.create(
                    item=item,
                    renter=request.user,
                    start_date=request.data.get("start_date"),
                    end_date=request.data.get("end_date"),
                    status="PENDING",
                )
                return Response(
                    {"message": "Item rented successfully", "booking_id": booking.id},
                    status=status.HTTP_201_CREATED,
                )
            except Item.DoesNotExist:
                return Response(
                    {"error": "Item not found"}, status=status.HTTP_404_NOT_FOUND
                )
        return Response(
            {"error": "Item ID is required"}, status=status.HTTP_400_BAD_REQUEST
        )
    
    def get(self, request, pk=None):
        if pk:
            try:
                booking = Booking.objects.get(pk=pk)
                serializer = ItemSerializer(booking)
                return Response(serializer.data)
            except Booking.DoesNotExist:
                return Response(
                    {"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND
                )
        else:
            bookings = Booking.objects.filter(renter=request.user)
            serializer = ItemSerializer(bookings, many=True)
            return Response(serializer.data)
    
    def put(self, request, pk=None):
        try:
            booking = Booking.objects.get(pk=pk)
            if booking.renter != request.user:
                return Response(
                    {"error": "You do not have permission to modify this booking"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            serializer = ItemSerializer(booking, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Booking.DoesNotExist:
            return Response(
                {"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND
            )
    
    def delete(self, request, pk=None):
        try:
            booking = Booking.objects.get(pk=pk)
            if booking.renter != request.user:
                return Response(
                    {"error": "You do not have permission to cancel this booking"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            booking.delete()
            return Response({"message": "Booking cancelled successfully"}, status=status.HTTP_204_NO_CONTENT)
        except Booking.DoesNotExist:
            return Response(
                {"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND
            )
