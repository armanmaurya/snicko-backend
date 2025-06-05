from django.shortcuts import render
from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.tokens import RefreshToken

# from users.serializers import EmailSerializer
from .models import CustomUser
import json
from django.core.mail import send_mail
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from .models import PickUpSpot
from .serializers import AddressSerializer
from google.oauth2 import id_token
from google.auth.transport import requests

User = get_user_model()


class GoogleLoginView(APIView):
    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response({'error': 'Token not provided'}, status=400)

        try:
            idinfo = id_token.verify_oauth2_token(token, requests.Request())

            # Check audience (YOUR_CLIENT_ID should be from Google Developer Console)
            if idinfo['aud'] != '431947796542-v5n1pf7srtpfifdqsvf8jvjia32c3ejg.apps.googleusercontent.com':
                return Response({'error': 'Invalid audience'}, status=403)

            email = idinfo['email']
            name = idinfo.get('name')

            print(f"\033[94midInfo: {idinfo}\033[0m")

            user, created = User.objects.get_or_create(email=email, defaults={'email': email, 'name': name})
            
            # Generate tokens for the user
            refresh = RefreshToken.for_user(user)

            # Return tokens along with other details
            return Response({
                'message': 'Login successful',
                'email': email,
                'name': name,
                'user_created': created,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        except ValueError:
            return Response({'error': 'Invalid token'}, status=403)

@csrf_exempt
def register_user(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')

        if not email or not password:
            print("Email and password are required")
            return JsonResponse({'error': 'Email and password are required'}, status=400)

        if CustomUser.objects.filter(email=email).exists():
            print("User with this email already exists")
            return JsonResponse({'error': 'User with this email already exists'}, status=400)

        user = CustomUser.objects.create_user(email=email, password=password, name=name)
        refresh = RefreshToken.for_user(user)
        return JsonResponse({
            'message': 'User registered successfully',
            'refresh': str(refresh),
            'access': str(refresh.access_token)
        }, status=201)
    
class FCMTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        fcm_token = request.data.get('fcm_token')

        if not fcm_token:
            return Response({"error": "FCM token is required"}, status=400)

        if user.fcm_token == fcm_token:
            return Response({"message": "FCM token is already up-to-date"}, status=200)

        user.fcm_token = fcm_token
        user.save()

        return Response({"message": "FCM token updated successfully"}, status=200)

@csrf_exempt
def login_user(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return JsonResponse({'error': 'Email and password are required'}, status=400)

        user = authenticate(email=email, password=password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            return JsonResponse({
                'message': 'Login successful',
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user_id': user.id,
            }, status=200)
        else:
            return JsonResponse({'error': 'Invalid credentials'}, status=401)
    

class PickUpSpotView(APIView):
    """
    API view to manage PickUpSpot objects for authenticated users.
    Provides methods to retrieve, create, update, and delete pickup spots.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        """
        Retrieve a specific pickup spot by its primary key (pk) or
        retrieve all pickup spots for the authenticated user.

        Args:
            request: The HTTP request object.
            pk (int, optional): The primary key of the pickup spot to retrieve.

        Returns:
            Response: Serialized data of the pickup spot(s) or an error message.
        """
        user = request.user
        if pk:
            try:
                address = PickUpSpot.objects.get(pk=pk, user=user)
                serializer = AddressSerializer(address)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except PickUpSpot.DoesNotExist:
                return Response({"error": "Pickup spot not found or not authorized"}, status=status.HTTP_404_NOT_FOUND)
        else:
            addresses = PickUpSpot.objects.filter(user=user)
            serializer = AddressSerializer(addresses, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Create a new pickup spot for the authenticated user.

        Args:
            request: The HTTP request object containing pickup spot data.

        Returns:
            Response: Serialized data of the created pickup spot or validation errors.
        """
        user = request.user
        request.data['user'] = user.id  # Set the user field to the authenticated user
        if request.data.get('is_default', False):
            # Unset any existing default pickup spot for the user
            PickUpSpot.objects.filter(user=user, is_default=True).update(is_default=False)
        serializer = AddressSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        """
        Update an existing pickup spot for the authenticated user.

        Args:
            request: The HTTP request object containing updated data.
            pk (int): The primary key of the pickup spot to update.

        Returns:
            Response: Serialized data of the updated pickup spot or an error message.
        """
        user = request.user
        try:
            address = PickUpSpot.objects.get(pk=pk, user=user)
            if request.data.get('is_default', False):
                # Unset any existing default pickup spot for the user
                PickUpSpot.objects.filter(user=user, is_default=True).update(is_default=False)
            serializer = AddressSerializer(address, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except PickUpSpot.DoesNotExist:
            return Response({"error": "Pickup spot not found or not authorized"}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        """
        Delete a specific pickup spot for the authenticated user.

        Args:
            request: The HTTP request object.
            pk (int): The primary key of the pickup spot to delete.

        Returns:
            Response: Success message or an error message.
        """
        user = request.user
        try:
            address = PickUpSpot.objects.get(pk=pk, user=user)
            address.delete()
            return Response({"message": "Pickup spot deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except PickUpSpot.DoesNotExist:
            return Response({"error": "Pickup spot not found or not authorized"}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_name(request):
    user = request.user
    return JsonResponse({"name": user.name}, status=200)

# Update adddress function
class UpdateAddressView(APIView):
    def post(self, request):
        user = request.user
        address = request.data.get('address')

        if not address:
            return Response({"error": "Address is required"}, status=400)

        user.address = address
        user.save()

        return Response({"message": "Address updated successfully"}, status=200)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_id(request):
    user = request.user
    if user.is_authenticated:
        return JsonResponse({"user_id": user.id}, status=200)
    else:
        return JsonResponse({"error": "User not authenticated"}, status=401)

