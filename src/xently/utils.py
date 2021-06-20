import math

from django.apps import apps
from django.conf import settings
from django.contrib.gis.geos import Point
from django.utils import timezone

__all__ = [
    "as_dict",
    "get_as_python_date",
    "get_installed_app_config",
    "srid",
    "as_valid_geom",
    "distance_to_decimal_degrees",
]

srid = settings.GEO_SRID


def as_valid_geom(location, _srid=srid):
    """
    :param location: can either be list of [x,y[,z]] coordinates or string in one of the following patterns:
        1. https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry
        2. https://en.wikipedia.org/wiki/GeoJSON
    :param _srid: integer of https://en.wikipedia.org/wiki/Spatial_reference_system
    """
    if location is None:
        return Point(srid=srid)
    return location if isinstance(location, str) else Point(*location, srid=srid)


def distance_to_decimal_degrees(distance, latitude):
    """
    Source of calculation logic:
        1. https://en.wikipedia.org/wiki/Decimal_degrees
        2. http://www.movable-type.co.uk/scripts/latlong.html
    :param distance: an instance of `from django.contrib.gis.measure.Distance`
    :param latitude: y - coordinate of a point/location
    """
    lat_radians = latitude * (math.pi / 180)
    # 1 longitudinal degree at the equator equal 111,319.5m equiv to 111.32km
    return distance.m / (111_319.5 * math.cos(lat_radians))


def as_dict(obj, fields, ignore_nulls=True, **kwargs):
    _dict = {}
    for field in fields:
        value = getattr(obj, field, None)
        if not value and ignore_nulls:
            continue
        _dict[field] = value
    _dict.update(**kwargs)
    return _dict


def get_as_python_date(_date, formats=None, make_aware=True):
    if isinstance(_date, str):
        formats = list(formats) or settings.DATETIME_INPUT_FORMATS + settings.DATE_INPUT_FORMATS
        formats_count = len(formats)
        for i, f in enumerate(formats):
            try:
                _date = timezone.datetime.strptime(_date, f)
            except ValueError:
                if i == formats_count - 1:
                    raise ValueError(f'Provide an appropriate format for "{_date}"')
            else:
                if make_aware and timezone.is_naive(_date):
                    _date = timezone.make_aware(_date)
                break
    return _date


def get_installed_app_config(app_label):
    try:
        return apps.get_app_config(app_label)
    except LookupError:
        pass
