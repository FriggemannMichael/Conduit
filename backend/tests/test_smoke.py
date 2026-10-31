from django.conf import settings


def test_settings_are_loaded():
    assert settings.ROOT_URLCONF == 'conduit.urls'


def test_url_config_imports():
    import conduit.urls  # noqa: F401

