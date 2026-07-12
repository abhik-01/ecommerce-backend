from rest_framework import serializers
from .models import User, Role


class SignupSerializer(serializers.ModelSerializer):
    role = serializers.CharField(required=False)

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
            try:
                role = Role.objects.get(role='user')
            except Role.DoesNotExist:
                raise serializers.ValidationError("Default role 'user' does not exist.")
        user = User.objects.create_user(role=role, **validated_data)
        return user


class ProfileSerializer(serializers.ModelSerializer):
    role = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'role', 'is_active', 'last_login']
        read_only_fields = ['id', 'email', 'role', 'last_login']


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email']

    def validate_email(self, value):
        user = self.instance
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value
