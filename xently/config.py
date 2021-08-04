from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.urls import URLPattern, include, re_path, path

from xently.decorators import permissions_required
from xently.utils import get_installed_app_config

__all__ = ["AutoLoadURLsConfigMixin", "AppConfigMixin", "XentlyAppConfig"]


class AutoLoadURLsConfigMixin:
    include_urls_in_parent = False

    def get_app_label_url_endpoint_mapping(self):
        return {}

    def _create_required_attributes(self):
        for label in self.get_app_label_url_endpoint_mapping().keys():
            setattr(self, f"{label}_app", get_installed_app_config(label))

    def ready(self):
        super().ready()
        self._create_required_attributes()

    def get_auto_loaded_urls(self):
        urls = []
        for label, value in self.get_app_label_url_endpoint_mapping().items():
            endpoint, regex = value, False
            if isinstance(value, dict):
                endpoint = value.get("endpoint") or ""
                regex = value.get("regex", False)

            app_config = getattr(self, f"{label}_app")
            if app_config is None:
                continue  # app with the label probably wasn't installed

            if getattr(app_config, "include_urls_in_parent", self.include_urls_in_parent):
                child_app_urls = app_config.urls[0]  # we need the processed routes if applicable
                if not child_app_urls:
                    continue  # no point clogging the route configs
                namespace = app_config.namespace
                child_app_urls = (
                    include((child_app_urls, namespace))
                    if settings.NAMESPACE_AUTO_INCLUDED_URLS
                    else include(child_app_urls)
                )
            else:
                child_app_urls = app_config.urls
                if not child_app_urls[0]:
                    continue  # no point clogging the route configs
            urls.append(re_path(endpoint, child_app_urls) if regex else path(endpoint, child_app_urls))
        return urls


class AppConfigMixin:
    """
    Base app configuration mixin, used to extend `django.apps.AppConfig` to also provide URL configurations
     and permissions.
    """

    # Instance namespace for the URLs
    namespace = None
    login_url = None
    auto_process_urls = True

    #: Maps view names to lists of permissions. We expect tuples of
    #: lists as dictionary values. A list is a set of permissions that all
    #: need to be fulfilled (AND). Only one set of permissions has to be
    #: fulfilled (OR).
    #: If there's only one set of permissions, as a shortcut, you can also
    #: just define one list.
    permissions_map = {}

    #: Default permission for any view not in permissions_map
    default_permissions = None

    def __init__(self, app_name, app_module, namespace=None, **kwargs):
        """
        kwargs:
            namespace: optionally specify the URL instance namespace
        """
        app_config_attrs = ["name", "module", "apps", "label", "verbose_name", "path", "models_module", "models"]
        # To ensure sub classes do not add kwargs that are used by
        # :py:class:`django.apps.AppConfig`
        clashing_kwargs = set(kwargs).intersection(app_config_attrs)
        if clashing_kwargs:
            clashing = ", ".join(clashing_kwargs)
            raise ImproperlyConfigured(
                f"Passed in kwargs can't be named the same as properties of AppConfig; clashing: {clashing}."
            )
        super().__init__(app_name, app_module)
        if namespace is not None:
            self.namespace = namespace
        if self.namespace is None:
            self.namespace = self.label
        # Set all kwargs as object attributes
        for key, value in kwargs.items():
            setattr(self, key, value)

    def get_urls(self):
        """
        Return the URL patterns for this app.
        """
        return self.get_auto_loaded_urls()

    def _post_processed_urls(self, urlpatterns):
        """
        Customise URL patterns.

        This method allows decorators to be wrapped around an apps URL
        patterns.

        By default, this only allows custom decorators to be specified, but you
        could override this method to do anything you want.

        Args:
            urlpatterns (list): A list of URL patterns

        """
        for pattern in urlpatterns:
            if hasattr(pattern, "url_patterns"):
                self._post_processed_urls(pattern.url_patterns)

            if isinstance(pattern, URLPattern):
                # Apply the custom view decorator (if any) set for this class if this
                # is a URL Pattern.
                decorator = self.get_url_decorator(pattern)
                if decorator:
                    pattern.callback = decorator(pattern.callback)

        return urlpatterns

    def get_permissions(self, url):
        """
        Return a list of permissions for a given URL name

        Args:
            url (str): A URL name (e.g., ``basket.basket``)

        Returns:
            list: A list of permission strings.
        """
        # url namespaced?
        if url is not None and ":" in url:
            view_name = url.split(":")[1]
        else:
            view_name = url
        return self.permissions_map.get(view_name, self.default_permissions)

    def get_url_decorator(self, pattern):
        """
        Return the appropriate decorator for the view function with the passed
        URL name. Mainly used for access-protecting views.

        It's possible to specify:

        - no permissions necessary: use None
        - a set of permissions: use a list
        - two set of permissions (`or`): use a two-tuple of lists

        See permissions_required decorator for details
        """
        permissions = self.get_permissions(pattern.name)
        if permissions:
            return permissions_required(permissions, self.login_url, self.label.startswith("api_"))

    @property
    def urls(self):
        # We set the application and instance namespace here
        urls = self.get_urls()
        if self.auto_process_urls:
            urls = self._post_processed_urls(urls)
        return urls, self.label, self.namespace


class XentlyAppConfig(AutoLoadURLsConfigMixin, AppConfigMixin, AppConfig):
    pass
