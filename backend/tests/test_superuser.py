import pytest

from conduit.apps.authentication.models import User


@pytest.mark.django_db
def test_superuser_uses_given_password(monkeypatch):
    monkeypatch.delenv('DJANGO_SUPERUSER_PASSWORD', raising=False)

    user = User.objects.create_superuser('admin', 'admin@example.com', 'given-password')

    assert user.check_password('given-password')
    assert not user.check_password('securepass')
    assert user.is_superuser and user.is_staff


@pytest.mark.django_db
def test_superuser_prefers_password_from_env(monkeypatch):
    monkeypatch.setenv('DJANGO_SUPERUSER_PASSWORD', 'env-password')

    user = User.objects.create_superuser('admin', 'admin@example.com', 'given-password')

    assert user.check_password('env-password')


@pytest.mark.django_db
def test_superuser_without_password_is_rejected(monkeypatch):
    monkeypatch.delenv('DJANGO_SUPERUSER_PASSWORD', raising=False)

    with pytest.raises(TypeError):
        User.objects.create_superuser('admin', 'admin@example.com', None)

    assert not User.objects.filter(username='admin').exists()
