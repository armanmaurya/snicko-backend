from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.conf import settings
import razorpay
from .models import Payment
from rentals.models import Booking
from .serializers import PaymentSerializer

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


class CreateOrderAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        booking_id = request.data.get('booking_id')
        amount = request.data.get('amount')

        if not (booking_id and amount):
            return Response({'error': 'booking_id and amount are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)

        # Create Razorpay Order
        razorpay_order = client.order.create({
            'amount': int(float(amount) * 100),  # Convert to float first, then to int
            'currency': 'INR',
            'payment_capture': '1'
        })

        # Save in DB
        payment = Payment.objects.create(
            user=request.user,
            booking=booking,
            amount=amount,
            razorpay_order_id=razorpay_order['id'],
            status='PENDING'
        )

        return Response({
            'order_id': razorpay_order['id'],
            'razorpay_key': settings.RAZORPAY_KEY_ID,
            'amount': int(float(amount) * 100),  # Convert to float first, then to int
            'currency': 'INR'
        }, status=status.HTTP_201_CREATED)


class VerifyPaymentAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        data = request.data
        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': data['razorpay_order_id'],
                'razorpay_payment_id': data['razorpay_payment_id'],
                'razorpay_signature': data['razorpay_signature']
            })
        except razorpay.errors.SignatureVerificationError as e:
            return Response({'error': 'Signature verification failed'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = Payment.objects.get(razorpay_order_id=data['razorpay_order_id'])
        except Payment.DoesNotExist:
            return Response({'error': 'Payment record not found'}, status=status.HTTP_404_NOT_FOUND)

        payment.status = 'SUCCESS'
        payment.razorpay_payment_id = data['razorpay_payment_id']
        payment.razorpay_signature = data['razorpay_signature']
        payment.save()

        return Response({'status': 'Payment verified successfully'})
