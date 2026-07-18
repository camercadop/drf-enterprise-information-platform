import logging

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.exceptions import AuthenticationFailed, Throttled
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

from apps.sys_user_event.models import AuthAttemptLog
from apps.sys_user_event.services import record_event
from apps.tenants.utils import get_tenant_id
from core.utils.request import get_client_ip

from .lockout import clear_lockout, is_locked
from .serializers import (
    LoginSerializer,
    LogoutSerializer,
    PasswordChangeResponseSerializer,
    PasswordChangeSerializer,
    RefreshSerializer,
)
from .signals import login_failed
from .throttling import LoginEmailThrottle, LoginIPThrottle

logger = logging.getLogger(__name__)


class LoginView(TokenObtainPairView):  # type: ignore[type-arg]
    """Authenticate user and return JWT token pair.

    Enforces rate limiting (per IP and per email), account lockout, and
    failed-attempt tracking. Clears lockout state on successful login.
    """

    permission_classes = (AllowAny,)  # type: ignore[assignment]
    serializer_class = LoginSerializer
    throttle_classes = [LoginIPThrottle, LoginEmailThrottle]

    def throttled(self, request: Request, wait: float) -> None:
        """Raise a Throttled exception with code ``rate_limit_exceeded``.

        Args:
            request: The incoming DRF request.
            wait: Seconds until the next allowed request.

        Raises:
            Throttled: Always, with ``rate_limit_exceeded`` detail code.
        """
        exc = Throttled(detail="Too many login attempts. Please try again later.")
        exc.detail.code = "rate_limit_exceeded"  # type: ignore[union-attr]
        raise exc

    def post(self, request: Request, *args: object, **kwargs: object) -> Response:
        """Handle login, enforcing lockout checks around the auth flow.

        Args:
            request: The incoming DRF request.

        Returns:
            JWT token pair response on success.
        """
        email: str = request.data.get("email", "") if isinstance(request.data, dict) else ""

        ip: str = get_client_ip(request)

        if is_locked(email):
            logger.warning("Login blocked: account locked email=%s", email)
            AuthAttemptLog.objects.create(
                email=email, ip_address=ip, success=False, failure_reason="account_locked"
            )
            raise serializers.ValidationError(
                {"detail": "Account is locked due to too many failed login attempts."},
                code="account_locked",
            )

        try:
            response = super().post(request, *args, **kwargs)
        except AuthenticationFailed:
            logger.warning("Login failed: invalid credentials email=%s", email)
            AuthAttemptLog.objects.create(
                email=email, ip_address=ip, success=False, failure_reason="invalid_credentials"
            )
            login_failed.send(sender=self.__class__, email=email)
            raise

        AuthAttemptLog.objects.create(email=email, ip_address=ip, success=True)
        record_event(
            actor=request.user,
            user_email=email,
            category="auth",
            event="login",
            metadata={"ip_address": ip},
        )
        clear_lockout(email)
        logger.info("Login successful email=%s", email)
        return response


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
        record_event(
            actor=request.user,
            user_email=request.user.email,
            category="auth",
            event="logout",
        )
        logger.info("Logout email=%s", request.user.email)
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
        record_event(
            actor=request.user,
            user_email=request.user.email,
            category="auth",
            event="logout_all",
        )
        logger.info("Logout all email=%s", request.user.email)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UnlockAccountView(APIView):
    """Allow tenant admins and superusers to unlock a locked account.

    Tenant admins can unlock any account within their tenant except their own.
    Superusers can unlock any account.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={204: None})
    def post(self, request: Request, email: str) -> Response:
        """Unlock the account associated with the given email.

        Args:
            request: The authenticated DRF request.
            email: The email address of the account to unlock.

        Returns:
            204 No Content on success.
        """
        if request.user.email == email:
            raise serializers.ValidationError(
                {"detail": "You cannot unlock your own account."},
                code="self_unlock_forbidden",
            )

        is_superuser: bool = bool(request.user.is_superuser)

        if not is_superuser:
            tenant_id = get_tenant_id(request)
            if not tenant_id:
                return Response(status=status.HTTP_403_FORBIDDEN)

            membership = (
                request.user.memberships.filter(
                    tenant_id=tenant_id,
                    is_active=True,
                    is_admin=True,
                ).first()
            )
            if not membership:
                return Response(status=status.HTTP_403_FORBIDDEN)

        clear_lockout(email)
        record_event(
            actor=request.user,
            user_email=email,
            category="auth",
            event="account_unlocked",
            metadata={"unlocked_by": request.user.email},
        )
        logger.info("Account unlocked target=%s actor=%s", email, request.user.email)
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
        record_event(
            actor=request.user,
            user_email=request.user.email,
            category="auth",
            event="password_change",
        )
        logger.info("Password changed email=%s", request.user.email)
        # Issue a new token pair so the user stays logged in
        token = AccessToken.for_user(request.user)  # type: ignore[arg-type]
        return Response(
            {"access": str(token)},
            status=status.HTTP_200_OK,
        )
