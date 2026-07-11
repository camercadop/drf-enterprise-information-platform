from rest_framework import status

from apps.authentication.models import UserPasswordHistory
from tests.base import BaseActionAPITest


class TestPasswordChangeView(BaseActionAPITest):
    url = "/api/auth/password/change/"

    def test_change_password_success(self) -> None:
        response = self.client.post(
            self.url,
            {
                "old_password": "TestPass123!",
                "new_password": "NewSecure456!",
                "new_password_confirmation": "NewSecure456!",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        self.user.refresh_from_db()
        assert self.user.check_password("NewSecure456!")

    def test_change_password_saves_history(self) -> None:
        self.client.post(
            self.url,
            {
                "old_password": "TestPass123!",
                "new_password": "NewSecure456!",
                "new_password_confirmation": "NewSecure456!",
            },
        )

        assert UserPasswordHistory.objects.filter(user=self.user).count() == 1

    def test_wrong_old_password(self) -> None:
        response = self.client.post(
            self.url,
            {
                "old_password": "WrongPass999!",
                "new_password": "NewSecure456!",
                "new_password_confirmation": "NewSecure456!",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_passwords_do_not_match(self) -> None:
        response = self.client.post(
            self.url,
            {
                "old_password": "TestPass123!",
                "new_password": "NewSecure456!",
                "new_password_confirmation": "Different789!",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_weak_password_rejected(self) -> None:
        response = self.client.post(
            self.url,
            {
                "old_password": "TestPass123!",
                "new_password": "short",
                "new_password_confirmation": "short",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_reuse_rejected(self) -> None:
        UserPasswordHistory.objects.create(
            user=self.user, hashed_password=self.user.password
        )

        response = self.client.post(
            self.url,
            {
                "old_password": "TestPass123!",
                "new_password": "TestPass123!",
                "new_password_confirmation": "TestPass123!",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
