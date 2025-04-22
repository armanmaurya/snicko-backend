from .models import Item, Booking
from .serializers import ItemSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.gis.measure import D
from django.contrib.gis.geos import Point
from django.db import models


class ItemView(APIView):
    """
    View for managing items (create, retrieve, update, delete).
    """

    def get(self, request, pk=None):
        """
        Retrieve item details or all items, optionally filtering by location.
        """
        latitude = request.query_params.get("latitude")
        longitude = request.query_params.get("longitude")
        radius = request.query_params.get("radius")

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

            # Filter by location if latitude, longitude, and radius are provided
            if latitude and longitude and radius:
                try:
                    latitude = float(latitude)
                    longitude = float(longitude)
                    radius = float(radius)

                    # Validate latitude and longitude ranges
                    if not (-90 <= latitude <= 90):
                        return Response(
                            {"error": "Latitude must be between -90 and 90."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    if not (-180 <= longitude <= 180):
                        return Response(
                            {"error": "Longitude must be between -180 and 180."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    # Create a Point object for the location
                    user_location = Point(longitude, latitude)

                    # Filter items within the radius
                    items = items.filter(location__distance_lte=(user_location, D(km=radius)))

                except ValueError:
                    return Response(
                        {"error": "Latitude, longitude, and radius must be valid numbers."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

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
            return Response(
                {"message": "Item deleted successfully"},
                status=status.HTTP_204_NO_CONTENT,
            )
        except Item.DoesNotExist:
            return Response(
                {"error": "Item not found"}, status=status.HTTP_404_NOT_FOUND
            )

    def get_permissions(self):
        if self.request.method in ["POST", "PUT", "DELETE"]:
            return [IsAuthenticated()]
        return super().get_permissions()


class SearchItemView(APIView):
    """
    View for searching items within a given radius of a location (latitude, longitude)
    and optionally filtering by a search query.
    """

    def get(self, request):
        """
        Search for items within a specified radius of a given location and filter by query.
        """
        latitude = request.query_params.get("latitude")
        longitude = request.query_params.get("longitude")
        radius = request.query_params.get("radius")
        search_query = request.query_params.get("query", "").strip()

        # Validate required parameters
        if not latitude or not longitude or not radius:
            return Response(
                {"error": "Latitude, longitude, and radius are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            latitude = float(latitude)
            longitude = float(longitude)
            radius = float(radius)

            # Validate latitude and longitude ranges
            if not (-90 <= latitude <= 90):
                return Response(
                    {"error": "Latitude must be between -90 and 90."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not (-180 <= longitude <= 180):
                return Response(
                    {"error": "Longitude must be between -180 and 180."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except ValueError:
            return Response(
                {"error": "Latitude, longitude, and radius must be valid numbers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create a Point object for the location
        user_location = Point(longitude, latitude)

        # Query items within the radius
        items = Item.objects.filter(location__distance_lte=(user_location, D(km=radius)))

        # Apply search query filter if provided
        if search_query:
            items = items.filter(
                models.Q(name__icontains=search_query) | models.Q(description__icontains=search_query)
            )

        if not items.exists():
            return Response(
                {"message": "No items found matching the criteria."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Serialize and return the results
        serializer = ItemSerializer(items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BookingView(APIView):
    """
    View for managing bookings (create, retrieve, update, delete).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None):
        """
        Create a new booking for an item.
        """
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
        """
        Retrieve booking details or all bookings for the authenticated user.
        - Renter can see their bookings.
        - Owner can see bookings for their items.
        """
        if pk:
            try:
                booking = Booking.objects.get(pk=pk)
                # Ensure the user is either the renter or the owner of the item
                if booking.renter != request.user and booking.item.owner != request.user:
                    return Response(
                        {"error": "You do not have permission to view this booking"},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                serializer = ItemSerializer(booking)
                return Response(serializer.data)
            except Booking.DoesNotExist:
                return Response(
                    {"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Filter bookings where the user is either the renter or the owner
            bookings = Booking.objects.filter(
                models.Q(renter=request.user) | models.Q(item__owner=request.user)
            )
            serializer = ItemSerializer(bookings, many=True)
            return Response(serializer.data)

    def put(self, request, pk=None):
        """
        Update booking details.
        """
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
        """
        Cancel a booking.
        """
        try:
            booking = Booking.objects.get(pk=pk)
            if booking.renter != request.user:
                return Response(
                    {"error": "You do not have permission to cancel this booking"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            booking.delete()
            return Response(
                {"message": "Booking cancelled successfully"},
                status=status.HTTP_204_NO_CONTENT,
            )
        except Booking.DoesNotExist:
            return Response(
                {"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND
            )
