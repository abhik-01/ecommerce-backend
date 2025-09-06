from rest_framework import serializers
from .models import User, Role


class SignupSerializer(serializers.ModelSerializer):
    role = serializers.CharField(required=False)  # Make role optional

    class Meta:
        model = User
        fields = ['email', 'password', 'role']
        extra_kwargs = {'password': {'write_only': True}}

    def validate_role(self, value):
        try:
            return Role.objects.get(role=value)
        except Role.DoesNotExist:
            raise serializers.ValidationError(f"Role '{value}' does not exist.")

    def create(self, validated_data):
        role = validated_data.pop('role', None)
        if not role:
            # Default to 'user' role if not provided
            try:
                role = Role.objects.get(role='user')
            except Role.DoesNotExist:
                raise serializers.ValidationError("Default role 'user' does not exist.")
        user = User.objects.create_user(role=role, **validated_data)
        return user
