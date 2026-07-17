import pytest
from rest_framework.test import APIClient


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(username="ana", password="pw12345")


@pytest.fixture
def other_user(django_user_model):
    return django_user_model.objects.create_user(username="beto", password="pw12345")


@pytest.fixture
def client(user) -> APIClient:
    api_client = APIClient()
    api_client.force_authenticate(user)
    return api_client


@pytest.fixture
def other_client(other_user) -> APIClient:
    api_client = APIClient()
    api_client.force_authenticate(other_user)
    return api_client
