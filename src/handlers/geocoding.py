from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable, GeocoderQueryError
from typing import Optional
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_geocoder = Nominatim(user_agent="photo-library-ama", timeout=10)


def reverse_geocode(lat: float, lon: float, max_retries: int = 1) -> Optional[str]:
    """Convert GPS coordinates to a human-readable address."""
    for attempt in range(max_retries):
        try:
            time.sleep(2.5)  # Increased delay to respect rate limits
            location = _geocoder.reverse((lat, lon), exactly_one=True)
            if location:
                return location.address
        except (GeocoderTimedOut, GeocoderUnavailable, GeocoderQueryError) as e:
            logger.warning(f"Geocoding attempt {attempt + 1} failed for ({lat}, {lon}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))  # Backoff on retry
        except Exception as e:
            logger.error(f"Unexpected geocoding error for ({lat}, {lon}): {e}")
            break
    return None


def geocode(address: str, max_retries: int = 1) -> Optional[tuple[float, float]]:
    """Convert an address to GPS coordinates."""
    for attempt in range(max_retries):
        try:
            time.sleep(2.5)  # Increased delay to respect rate limits
            location = _geocoder.geocode(address, exactly_one=True)
            if location:
                return (location.latitude, location.longitude)
        except (GeocoderTimedOut, GeocoderUnavailable, GeocoderQueryError) as e:
            logger.warning(f"Geocoding attempt {attempt + 1} failed for '{address}': {e}")
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))  # Backoff on retry
        except Exception as e:
            logger.error(f"Unexpected geocoding error for '{address}': {e}")
            break
    return None


def rate_limited_geocode(address: str, delay: float = 1.5) -> Optional[tuple[float, float]]:
    """Geocode with rate limiting to respect Nominatim's usage policy."""
    time.sleep(delay)
    return geocode(address)