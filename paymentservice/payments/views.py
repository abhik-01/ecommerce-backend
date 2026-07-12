from django.shortcuts import redirect
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Payment
from .serializers import PaymentSerializer, TransactionSerializer
from .services import PaymentService
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    service = PaymentService()
    permission_classes = [IsAuthenticated]

    # Gateways (webhooks) and browser redirects (cancel) carry no JWT.
    PUBLIC_ACTIONS = {'stripe_webhook', 'razorpay_webhook', 'cancel'}

    def get_permissions(self):
        if self.action in self.PUBLIC_ACTIONS:
            return [AllowAny()]
        return super().get_permissions()

    @action(detail=False, methods=['post'])
    def initiate(self, request):
        serializer = PaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = self.service.initiate_checkout_payment(
            serializer.validated_data,
            success_url=request.data.get('success_url')
        )
        if result.get('error'):
            return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)
        response_data = {
            'payment_id': result['payment_id'],
            'order_id': result['order_id'],
            'status': result['status'],
            'redirect_url': result['redirect_url'],
            'session_id': result['session_id']
        }
        return Response(response_data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def status(self, request):
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response({'error': 'session_id is required'}, status=400)
        payment = Payment.objects.filter(session_id=session_id).first()
        if not payment:
            return Response({'error': 'Payment not found'}, status=404)
        latest_txn = payment.latest_transaction()
        receipt_url = latest_txn.receipt_url if latest_txn and latest_txn.receipt_url else None
        return Response({
            'status': payment.status,
            'payment': PaymentSerializer(payment).data,
            'latest_transaction': TransactionSerializer(latest_txn).data if latest_txn else None,
            'receipt_url': receipt_url
        })

    @action(detail=False, methods=['post'], url_path='stripe/webhook')
    @method_decorator(csrf_exempt, name='dispatch')
    def stripe_webhook(self, request):
        result = self.service.handle_webhook(request, gateway_name='stripe')
        status_code = result.get('status', 200)
        return Response(result, status=status_code)

    @action(detail=False, methods=['post'], url_path='razorpay/webhook')
    @method_decorator(csrf_exempt, name='dispatch')
    def razorpay_webhook(self, request):
        result = self.service.handle_webhook(request, gateway_name='razorpay')
        status_code = result.get('status', 200)
        return Response(result, status=status_code)

    @action(detail=False, methods=['get'], url_path='cancel')
    def cancel(self, request):
        session_id = request.query_params.get('session_id')
        order_id = request.query_params.get('order_id')
        result = self.service.cancel_payment(session_id=session_id)

        if order_id:
            return redirect(f'/orders/{order_id}')
        status_code = 200 if not result.get('error') else 400
        return Response(result, status=status_code)

    @action(detail=False, methods=['post'])
    def refund(self, request):
        payment_id = request.data.get('payment_id')
        amount = request.data.get('amount')
        if not payment_id:
            return Response({'error': 'payment_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        result = self.service.refund_payment(payment_id, amount)
        if result.get('error'):
            return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'payment_id': result['payment_id'],
            'refund_status': result['refund_status'],
            'refund_id': result['refund_id'],
            'receipt_url': result.get('receipt_url'),
            'gateway_response': result.get('gateway_response')
        }, status=status.HTTP_200_OK)
