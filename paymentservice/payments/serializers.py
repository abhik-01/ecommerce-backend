from rest_framework import serializers
from .models import Payment, Transaction


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

class PaymentSerializer(serializers.ModelSerializer):
    transactions = TransactionSerializer(many=True, read_only=True)
    metadata = serializers.DictField(required=False, allow_null=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'amount', 'currency', 'status', 'order_id', 'metadata', 'quantity',
            'created_at', 'updated_at', 'transactions'
        ]
        read_only_fields = ('created_at', 'updated_at', 'status')

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than zero.')
        return value

    def validate_metadata(self, value):
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError('Metadata must be a dictionary.')
        # Optionally, restrict keys to safe/expected ones
        allowed_keys = {'user_id', 'cart_id', 'order_id'}
        for k in value.keys():
            if k not in allowed_keys:
                raise serializers.ValidationError(f'Metadata key "{k}" is not allowed.')
        return value
