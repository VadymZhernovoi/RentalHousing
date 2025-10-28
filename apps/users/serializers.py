from django.contrib.auth.models import Group
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

from .models import User
from ..core.enums import Roles

# class RegisterUserSerializer(serializers.ModelSerializer):
#     password = serializers.CharField(write_only=True)
#
#     class Meta:
#         model = User
#         fields = ("id", "username", "nickname", "email", "password", "first_name", "last_name", "role")
#
#     def validate_password(self, value):
#         validate_password(value)
#         return value
#
#     def create(self, validated):
#         pwd = validated.pop("password")
#         user = User(**validated)
#         user.set_password(pwd)
#         user.save()
#         return user
#
# class UserLoggedInSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = User
#         fields = ("id", "username", "nickname", "email", "first_name", "last_name", "role")

class RegisterUserSerializer(serializers.ModelSerializer):
    """
    Register user serializer.

    Password is accepted separately and validated.
    """
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=Roles.choices, required=True)

    class Meta:
        model = User
        fields = ("email", "username", "first_name", "last_name", "password", "password2", "role", "nickname")

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email already exists.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        validate_password(attrs["password"])
        # Self-registration: only renters/lessors possible
        allowed_self_signup = {Roles.RENTER, Roles.LESSOR}
        role = attrs["role"]
        req = self.context.get("request")
        is_elevated = bool(req and req.user and (req.user.is_superuser or req.user.is_staff))
        if not is_elevated and role not in allowed_self_signup: # only renters/lessors possible
            raise serializers.ValidationError({"role": "This role cannot be set during self-registration."})

        return attrs

    def create(self, validated):
        validated.pop("password2")
        pwd = validated.pop("password")
        role = validated["role"]
        user = User(**validated)
        user.set_password(pwd)

        user.save()

        # Set a group by role (for model permissions )
        try:
            gr = Group.objects.get(name=role)
            user.groups.set([gr])

        except Group.DoesNotExist:
            pass

        return user


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    class Meta:
        model = User
        fields = ['username', 'password', 'email']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            email=validated_data.get('email', '')
        )
        return user

class UserLoggedInSerializer(serializers.ModelSerializer):
    """
    Current user profile for /user/login/.
    """
    class Meta:
        model = User
        fields = ("id", "email", "username", "first_name", "last_name", "role", "nickname")
        read_only_fields = fields