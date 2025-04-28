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
from .models import Address
from .serializers import AddressSerializer

User = get_user_model()

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
    

class AddressView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        user = request.user
        if pk:
            try:
                address = Address.objects.get(pk=pk, user=user)
                serializer = AddressSerializer(address)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Address.DoesNotExist:
                return Response({"error": "Address not found or not authorized"}, status=status.HTTP_404_NOT_FOUND)
        else:
            addresses = Address.objects.filter(user=user)
            serializer = AddressSerializer(addresses, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user
        request.data['user'] = user.id  # Set the user field to the authenticated user
        if request.data.get('is_default', False):
            # Unset any existing default address for the user
            Address.objects.filter(user=user, is_default=True).update(is_default=False)
        serializer = AddressSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        user = request.user
        try:
            address = Address.objects.get(pk=pk, user=user)
            if request.data.get('is_default', False):
                # Unset any existing default address for the user
                Address.objects.filter(user=user, is_default=True).update(is_default=False)
            serializer = AddressSerializer(address, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Address.DoesNotExist:
            return Response({"error": "Address not found or not authorized"}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        user = request.user
        try:
            address = Address.objects.get(pk=pk, user=user)
            address.delete()
            return Response({"message": "Address deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except Address.DoesNotExist:
            return Response({"error": "Address not found or not authorized"}, status=status.HTTP_404_NOT_FOUND)

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

