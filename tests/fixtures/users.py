import pytest

from apps.users.models import User
from tests.factories.users import UserFactory


@pytest.fixture()
def user() -> User:
    return UserFactory()


@pytest.fixture()
def superuser() -> User:
    return UserFactory(is_superuser=True)
