"""Live bus tracking through the Trackingo tracker page's own API.

The tracker page at bus.trackingo.in polls two internal endpoints.
This package calls those same endpoints directly, so you get the GPS
position, speed and per-stop ETA without scraping the map page.
"""

__version__ = "0.1.0"
__all__ = ["client"]

from .client import fetch_eta_map, fetch_journey_details, parse_eta_map
