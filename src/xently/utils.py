from django.apps import apps

__all__ = ["get_installed_app_config"]


def get_installed_app_config(app_label):
    try:
        return apps.get_app_config(app_label)
    except LookupError:
        pass
