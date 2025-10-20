from datetime import datetime
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .serializers import UserLoggedInSerializer, RegisterUserSerializer


def set_jwt_cookies(response, user):
    refresh_token = RefreshToken.for_user(user)
    access_token = refresh_token.access_token
    # Устанавливает JWT токены в cookie.
    access_expiry = datetime.fromtimestamp(access_token['exp'])
    refresh_expiry = datetime.fromtimestamp(refresh_token['exp'])

    response.set_cookie(
        key='access_token',
        value=str(access_token),
        httponly=True,
        secure=False,
        samesite='Lax',
        expires=access_expiry,
        path='/'
    )
    response.set_cookie(
        key='refresh_token',
        value=str(refresh_token),
        httponly=True,
        secure=False,
        samesite='Lax',
        expires=refresh_expiry,
        path='/'
    )

@extend_schema(
    description="Register a new user. Role is required. On success sets JWT cookies (access_token, refresh_token).",
    request=RegisterUserSerializer,
    responses={
        201: OpenApiResponse(description="User registered and JWT cookies set"),
        400: OpenApiResponse(description="Validation error"),
    },
)
class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterUserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            response = Response({'user': {'username': user.username,'email': user.email}}, status=status.HTTP_201_CREATED)
            set_jwt_cookies(response, user)
            return response
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Get current user (requires authentication).",
    request=None,
    responses={200: OpenApiResponse(response=UserLoggedInSerializer, description="Current user")},
)
@extend_schema(
    summary="Update current user (partial).",
    request=UserLoggedInSerializer,
    responses={
        200: OpenApiResponse(response=UserLoggedInSerializer, description="Profile updated"),
        400: OpenApiResponse(description="Validation error"),
    },
    methods=["PATCH"],
)
class UserLoggedInView(generics.RetrieveUpdateAPIView):
    serializer_class = UserLoggedInSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


@extend_schema(
    description=(
        "Login with email/password. On success sets JWT cookies "
        "(`access_token`, `refresh_token`). Body: `{ \"email\": \"...\", \"password\": \"...\" }`."
    ),
    request={
        "application/json": {
            "type": "object",
            "properties": {"email": {"type": "string", "format": "email"}, "password": {"type": "string"}},
        }
    },
    responses={
        200: OpenApiResponse(description="Authenticated; JWT cookies set"),
        401: OpenApiResponse(description="Invalid credentials"),
    },
)
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get("email") or request.data.get("username")
        password = request.data.get('password')
        user = authenticate(request, username=email, password=password)
        # username = request.data.get('username')
        # password = request.data.get('password')
        # user = authenticate(request, username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            # Используем exp для установки времени истечения куки
            access_expiry = datetime.fromtimestamp(access_token['exp'])
            refresh_expiry = datetime.fromtimestamp(refresh['exp'])
            response = Response(status=status.HTTP_200_OK)
            response.set_cookie(
                key='access_token',
                value=str(access_token),
                httponly=True,
                secure=False, # Используйте True для HTTPS
                samesite='Lax',
                expires=access_expiry,
                path='/'
            )
            response.set_cookie(
                key='refresh_token',
                value=str(refresh),
                httponly=True,
                secure=False,
                samesite='Lax',
                expires=refresh_expiry,
                path='/'
            )
            return response
        else:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)


@extend_schema(
    summary="Logout: clear JWT cookies (`access_token`, `refresh_token`).",
    request=None,
    responses={204: OpenApiResponse(description="Logged out; cookies cleared")},
)
class LogoutView(APIView):
     def post(self, request, *args, **kwargs):
        response = Response(status=status.HTTP_204_NO_CONTENT)
        # response.delete_cookie('access_token')
        # response.delete_cookie('refresh_token')
        response.delete_cookie("access_token", path="/")
        response.delete_cookie("refresh_token", path="/")
        return response

