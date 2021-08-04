from collections.abc import Callable

from django.contrib.auth.decorators import user_passes_test
from django.core import exceptions

__all__ = ["check_permissions", "permissions_required"]


def check_permissions(user, permissions):
    """
    Permissions can be a list or a tuple of lists. If it is a tuple,
    every permission list will be evaluated and the outcome will be checked
    for truthiness.
    Each item of the list(s) must be either a valid Django permission name
    (model.codename) or a property or method on the User model
    (e.g. 'is_active', 'is_superuser').

    Example usage:
    - permissions_required(['is_anonymous', ])
      would replace login_forbidden
    - permissions_required((['is_staff',], ['partner.dashboard_access']))
      allows both staff users and users with the above permission
    """

    def _check_one_permission_list(perms):
        regular_permissions = [perm for perm in perms if "." in perm]
        conditions = [perm for perm in perms if "." not in perm]
        # always check for is_active if not checking for is_anonymous
        if conditions and "is_anonymous" not in conditions and "is_active" not in conditions:
            conditions.append("is_active")
        attributes = [getattr(user, perm) for perm in conditions]
        # evaluates methods, explicitly casts properties to booleans
        passes_conditions = all([attr() if isinstance(attr, Callable) else bool(attr) for attr in attributes])
        return passes_conditions and user.has_perms(regular_permissions)

    if not permissions:
        return True
    elif isinstance(permissions, list):
        return _check_one_permission_list(permissions)
    else:
        return any(_check_one_permission_list(perm) for perm in permissions)


def permissions_required(permissions, login_url, api_exception=True):
    """
    Decorator that checks if a user has the given permissions.
    Accepts a list or tuple of lists of permissions (see check_permissions
    documentation).

    If the user is not logged in and the test fails, she is redirected to a
    login page. If the user is logged in, she gets a HTTP 403 Permission Denied
    message, analogous to Django's permission_required decorator.
    """

    def _check_permissions(user):
        outcome = check_permissions(user, permissions)
        if not outcome and user.is_authenticated:
            if api_exception:
                try:
                    from rest_framework import exceptions as api_exceptions
                except ImportError:
                    pass
                else:
                    raise api_exceptions.PermissionDenied
            raise exceptions.PermissionDenied
        return outcome

    return user_passes_test(_check_permissions, login_url=login_url)
