import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.iam_mfa.serializers import (
    MFABackupCodeSerializer,
    MFAConfirmSetupSerializer,
    MFADisableSerializer,
    MFALoginVerifySerializer,
    MFASetupSerializer,
    MFAStatusSerializer,
    MFAVerifySerializer,
)

logger = logging.getLogger(__name__)


class MFASetupView(APIView):
    """Generate a TOTP secret and QR code for MFA enrollment."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: MFASetupSerializer},
    )
    def get(self, request: Request) -> Response:
        serializer = MFASetupSerializer(context={"request": request})
        return Response(serializer.save())


class MFAConfirmSetupView(APIView):
    """Confirm MFA setup by verifying a TOTP code against the client-held secret."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=MFAConfirmSetupSerializer,
        responses={201: None},
    )
    def post(self, request: Request) -> Response:
        serializer = MFAConfirmSetupSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_201_CREATED)


class MFAVerifyView(APIView):
    """Verify a TOTP code. Used during login challenge and MFA verification."""

    permission_classes = [AllowAny]

    @extend_schema(
        request=MFAVerifySerializer,
        responses={200: None},
    )
    def post(self, request: Request) -> Response:
        serializer = MFAVerifySerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        return Response(status=status.HTTP_200_OK)


class MFADisableView(APIView):
    """Disable MFA for the authenticated user."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=MFADisableSerializer,
        responses={204: None},
    )
    def post(self, request: Request) -> Response:
        serializer = MFADisableSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MFALoginVerifyView(APIView):
    """Complete login by verifying a TOTP or backup code against an MFA challenge token.

    Called after LoginSerializer returns mfa_required=True. On success, issues
    a real JWT token pair. Accepts AllowAny since the user is not yet authenticated.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        request=MFALoginVerifySerializer,
        responses={200: None},
    )
    def post(self, request: Request) -> Response:
        serializer = MFALoginVerifySerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class MFABackupCodesView(APIView):
    """Generate new backup codes for MFA recovery."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=MFABackupCodeSerializer,
        responses={200: MFABackupCodeSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = MFABackupCodeSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_201_CREATED)


class MFAStatusView(APIView):
    """Return the authenticated user's MFA status."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: MFAStatusSerializer})
    def get(self, request: Request) -> Response:
        serializer = MFAStatusSerializer(context={"request": request})
        return Response(serializer.to_representation(None))
