from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role", "date_joined"]
        read_only_fields = ["id", "role", "date_joined"]


class SignupSerializer(serializers.ModelSerializer):
    """
    Public signup always creates a regular MEMBER account. There is no
    "pick your role" control -- becoming an admin requires either:
      1) knowing the private ADMIN_SIGNUP_CODE (set via env var) and
         supplying it in the optional `admin_code` field, or
      2) being promoted afterward by an existing admin/superuser via
         the Django admin panel at /admin/.
    If ADMIN_SIGNUP_CODE is unset/blank, option 1 is disabled entirely
    and every new signup is a member, full stop.
    """

    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)
    admin_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "password", "password2", "admin_code"]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password2"):
            raise serializers.ValidationError({"password2": "Passwords do not match."})

        admin_code = (attrs.pop("admin_code", "") or "").strip()
        wants_admin = bool(admin_code)
        configured_code = getattr(settings, "ADMIN_SIGNUP_CODE", "") or ""

        if wants_admin:
            if not configured_code or admin_code != configured_code:
                raise serializers.ValidationError({"admin_code": "Invalid admin invite code."})
            attrs["role"] = User.Role.ADMIN
        else:
            attrs["role"] = User.Role.MEMBER

        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds extra user info into the JWT payload/response."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["role"] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data
