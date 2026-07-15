from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    LoginSerializer,
    LogoutSerializer,
    PasswordChangeResponseSerializer,
    PasswordChangeSerializer,
    RefreshSerializer,
)


class LoginView(TokenObtainPairView):  # type: ignore[type-arg]
    """Authenticate user and return JWT token pair."""

    permission_classes = (AllowAny,)  # type: ignore[assignment]
    serializer_class = LoginSerializer


class RefreshView(TokenRefreshView):  # type: ignore[type-arg]
    """Return a new access token given a valid refresh token."""

    permission_classes = (AllowAny,)  # type: ignore[assignment]
    serializer_class = RefreshSerializer


class LogoutView(APIView):
    """Blacklist the refresh token to end the session."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=LogoutSerializer, responses={204: None})
    def post(self, request: Request) -> Response:
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LogoutAllView(APIView):
    """Blacklist all outstanding refresh tokens for the authenticated user."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={204: None})
    def post(self, request: Request) -> Response:
        tokens = OutstandingToken.objects.filter(user=request.user).exclude(
            blacklistedtoken__isnull=False
        )
        for token in tokens:
            BlacklistedToken.objects.create(token=token)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordChangeView(APIView):
    """Change the authenticated user's password."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=PasswordChangeSerializer,
        responses={200: PasswordChangeResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = PasswordChangeSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # Issue a new token pair so the user stays logged in
        token = AccessToken.for_user(request.user)  # type: ignore[arg-type]
        return Response(
            {"access": str(token)},
            status=status.HTTP_200_OK,
        )
