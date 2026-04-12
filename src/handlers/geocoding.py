from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from typing import Optional
import time

_geocoder = Nominatim(user_agent="photo-library-ama")


def reverse_geocode(lat: float, lon: float) -> Optional[str]:
    """Convert GPS coordinates to a human-readable address."""
    try:
        location = _geocoder.reverse((lat, lon), exactly_one=True)
        if location:
            return location.address
    except (GeocoderTimedOut, GeocoderUnavailable):
        pass
    return None


def geocode(address: str) -> Optional[tuple[float, float]]:
    """Convert an address to GPS coordinates."""
    try:
        location = _geocoder.geocode(address, exactly_one=True)
        if location:
            return (location.latitude, location.longitude)
    except (GeocoderTimedOut, GeocoderUnavailable):
        pass
    return None


def rate_limited_geocode(address: str, delay: float = 1.0) -> Optional[tuple[float, float]]:
    """Geocode with rate limiting to respect Nominatim's usage policy."""
    time.sleep(delay)
    return geocode(address)
