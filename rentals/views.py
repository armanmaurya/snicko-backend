from .models import Item, Booking
from .serializers import ItemSerializer, ItemGetSerializer, BookingSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.gis.measure import D
from django.contrib.gis.geos import Point
from django.db import models
from datetime import datetime
from rest_framework.decorators import api_view, permission_classes
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

channel_layer = get_channel_layer()


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
                serializer = ItemGetSerializer(item)
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
                    # items = items.filter(location__distance_lte=(user_location, D(km=radius)))

                except ValueError:
                    return Response(
                        {
                            "error": "Latitude, longitude, and radius must be valid numbers."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            serializer = ItemSerializer(items, many=True)
            data = serializer.data
            # Add the owner name
            for item_data in data:
                item = Item.objects.get(pk=item_data["id"])
                item_data["owner_name"] = item.owner.name if item.owner else None
            return Response(serializer.data)

    def post(self, request):
        serializer = ItemSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(owner=request.user)
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

    # def get_permissions(self):
    #     if self.request.method in ["POST", "PUT", "DELETE"]:
    #         return [IsAuthenticated()]
    #     return super().get_permissions()


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
        items = Item.objects.filter(
            location__distance_lte=(user_location, D(km=radius))
        )

        # Apply search query filter if provided
        if search_query:
            items = items.filter(
                models.Q(name__icontains=search_query)
                | models.Q(description__icontains=search_query)
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

    def send_booking_notification(self, user, booking):
        """
        Send a notification to the user via WebSocket
        """
        channel_layer = get_channel_layer()
        group_name = f"user_{user.id}"

        print(f"[DEBUG] Sending booking notification to group: {group_name}")

        # Determine the notification title and body based on booking status
        if booking.status == "PENDING":
            title = "Booking Request Received"
            body = f"Your booking request for {booking.item.name} from {booking.start_date} to {booking.end_date} is pending approval."
        elif booking.status == "APPROVED":
            title = "Booking Approved"
            body = f"Your booking for {booking.item.name} from {booking.start_date} to {booking.end_date} has been approved."
        elif booking.status == "REJECTED":
            title = "Booking Rejected"
            body = f"Your booking request for {booking.item.name} from {booking.start_date} to {booking.end_date} has been rejected."
        elif booking.status == "ACTIVE":
            title = "Booking Active"
            body = f"Your booking for {booking.item.name} is now active from {booking.start_date} to {booking.end_date}."
        elif booking.status == "COMPLETED":
            title = "Booking Completed"
            body = f"Your booking for {booking.item.name} from {booking.start_date} to {booking.end_date} has been completed."
        else:
            title = "Booking Update"
            body = f"Your booking for {booking.item.name} has been updated."

        # Notification content
        notification_content = {
            "title": title,
            "body": body,
            "redirectTo": "requestpage",
        }

        # Send the notification to the user via WebSocket
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "send_notification",  # This is the method in the consumer
                "content": notification_content,
            },
        )

    def post(self, request, pk=None):
        """
        Create a new booking for an item.
        """
        if pk:
            try:
                item = Item.objects.get(pk=pk)
                # Parse ISO 8601 strings to date objects
                start_date = datetime.fromisoformat(
                    request.data.get("start_date")
                ).date()
                end_date = datetime.fromisoformat(request.data.get("end_date")).date()

                booking = Booking.objects.create(
                    item=item,
                    renter=request.user,
                    start_date=start_date,
                    end_date=end_date,
                    status="PENDING",
                )
                print(item.owner.name, item.owner.email)
                # Send notification to the item owner
                self.send_booking_notification(item.owner, booking)
                return Response(
                    {"message": "Item rented successfully", "booking_id": booking.id},
                    status=status.HTTP_201_CREATED,
                )
            except Item.DoesNotExist:
                return Response(
                    {"error": "Item not found"}, status=status.HTTP_404_NOT_FOUND
                )
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use ISO 8601 format."},
                    status=status.HTTP_400_BAD_REQUEST,
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
                if (
                    booking.renter != request.user
                    and booking.item.owner != request.user
                ):
                    return Response(
                        {"error": "You do not have permission to view this booking"},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                serializer = BookingSerializer(booking)
                return Response(serializer.data)
            except Booking.DoesNotExist:
                return Response(
                    {"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Filter bookings where the user is either the renter or the owner
            bookings = Booking.objects.filter(models.Q(renter=request.user))
            serializer = BookingSerializer(bookings, many=True)
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


class ManageBookingStatusView(APIView):
    """
    View for managing the status of a booking (approve or reject).
    """

    permission_classes = [IsAuthenticated]

    def send_notification(self, user, booking, status):
        """
        Send a WebSocket notification to the user about the booking status update.
        """
        channel_layer = get_channel_layer()
        group_name = f"user_{user.id}"

        if status == "APPROVED":
            notification_content = {
                "title": "Booking Status Updated",
                "body": f"The status of your booking for {booking.item.name} has been updated to {booking.status}.",
                "redirectTo": "paymentpage",
                "booking_id": booking.id,
            }
        elif status == "REJECTED":
            notification_content = {
                "title": "Booking Request Rejected",
                "body": f"Your booking request for {booking.item.name} from {booking.start_date} to {booking.end_date} has been rejected.",
            }

        # Send the notification to the user via WebSocket
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "send_notification",  # This is the method in the consumer
                "content": notification_content,
            },
        )

    def post(self, request, pk=None):
        """
        Update the status of a booking (approve or reject).
        """
        if not pk:
            return Response(
                {"error": "Booking ID is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        action = request.data.get("status")
        if action not in ["APPROVED", "REJECTED"]:
            return Response(
                {"error": "Invalid action. Use 'APPROVED' or 'REJECTED'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            booking = Booking.objects.get(pk=pk)
            if booking.item.owner != request.user:
                return Response(
                    {"error": "You do not have permission to update this booking"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            if action == "APPROVED":
                booking.status = "APPROVED"
                booking.item.is_available = False
                booking.save()

                # Reject other pending bookings for the same item
                Booking.objects.filter(item=booking.item, status="PENDING").exclude(
                    pk=pk
                ).update(status="REJECTED")

            elif action == "REJECTED":
                booking.status = "REJECTED"
                booking.save()

            # Send WebSocket notification to the renter
            self.send_notification(booking.renter, booking, action)

            return Response(
                {"message": f"Booking status updated to {action} successfully"},
                status=status.HTTP_200_OK,
            )
        except Booking.DoesNotExist:
            return Response(
                {"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND
            )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_item_booking_requests(request):
    """
    View for retrieving booking requests for the authenticated user.
    """
    if request.method == "GET":
        bookings = Booking.objects.filter(item__owner=request.user, status="PENDING")
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
