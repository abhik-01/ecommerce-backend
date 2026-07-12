from abc import ABC, abstractmethod


class PaymentGatewayAdapter(ABC):
    @abstractmethod
    def create_checkout_session(self, amount, currency, order_id, quantity, metadata=None, success_url=None, cancel_url=None):
        pass

    @abstractmethod
    def refund_payment(self, payment_id, amount=None, **kwargs):
        pass

    @abstractmethod
    def check_health(self):
        pass

    @abstractmethod
    def process_webhook_event(self, request):
        pass

    @abstractmethod
    def cancel_payment(self, session_id):
        pass
