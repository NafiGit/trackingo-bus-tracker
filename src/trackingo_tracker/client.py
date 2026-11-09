"""Client for the Trackingo live-tracking endpoints.

Endpoints (found from the tracker page's own network requests):
  GET https://bus.trackingo.in/api/live/journey_details
      ?key=<KEY>&zoom_position=12&platform=mobile
  GET https://bus.trackingo.in/api/live/eta_map
      ?current_status=true&key=<KEY>

These are the website's internal endpoints, not a published developer
API. They worked without a login in a fresh browser session, they may
change without notice, and they should be treated as unsupported.
The page itself polls the eta_map endpoint about every 20 seconds.

The tracking key is the key from your own tracking link
(for example, the link RedBus / the operator sends you, which
redirects to bus.trackingo.in/customer/track_vehicle?<KEY>).
Treat your key as private: the journey_details response can include
booking / contact fields. Never commit a real key, ticket number,
vehicle number or phone number. This repo contains only placeholders.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

BASE = "https://bus.trackingo.in"
USER_AGENT = "trackingo-bus-tracker/0.1.0 (+https://github.com/NafiGit/trackingo-bus-tracker)"


class TrackingoError(RuntimeError):
    """Raised when the tracker API cannot be read."""


def _get(url: str, timeout: float = 15.0) -> dict:
    request = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise TrackingoError(f"HTTP {exc.code} from {url}") from exc
    except urllib.error.URLError as exc:
        raise TrackingoError(f"could not reach {url}: {exc}") from exc


def fetch_journey_details(key: str, timeout: float = 15.0) -> dict:
    """Return the journey record: operator, vehicle, service, stops."""
    url = f"{BASE}/api/live/journey_details?key={key}&zoom_position=12&platform=mobile"
    return _get(url, timeout=timeout)


def fetch_eta_map(key: str, timeout: float = 15.0) -> dict:
    """Return the live position + ETA record."""
    url = f"{BASE}/api/live/eta_map?current_status=true&key={key}"
    return _get(url, timeout=timeout)


def _as_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return list(value.values())
    return []


def _minutes_between(scheduled: str, expected: str) -> int | None:
    """Delay in minutes from two 'HH:MM AM/PM' strings, or None."""
    def _mins(text: str):
        if not text:
            return None
        text = text.strip()
        try:
            time_part, meridiem = text.rsplit(" ", 1)
            hours, minutes = (int(part) for part in time_part.split(":"))
        except ValueError:
            return None
        if meridiem.upper() == "PM" and hours != 12:
            hours += 12
        if meridiem.upper() == "AM" and hours == 12:
            hours = 0
        return hours * 60 + minutes
    start, end = _mins(scheduled), _mins(expected)
    if start is None or end is None:
        return None
    delay = end - start
    if delay < -12 * 60:
        delay += 24 * 60
    if delay > 12 * 60:
        delay -= 24 * 60
    return delay


def parse_eta_map(data: dict) -> dict:
    """Pull the useful fields out of an eta_map response.

    Documented fields:
      current_status_details.lat_long          -> [latitude, longitude]
      current_status_details.details.speed     -> speed
      current_status_details.details.timestamp -> GPS update time
      current_status_details.details.location  -> location description
      current_status_details.details.hstate    -> vehicle state
      eta_map_data                             -> stop timings / status
      distance_details                         -> distance information
    """
    status = data.get("current_status_details") or {}
    details = status.get("details") or {}
    lat_long = status.get("lat_long") or [None, None]

    stops = []
    for stop in _as_list(data.get("eta_map_data")):
        if not isinstance(stop, dict):
            continue
        name = stop.get("stop_name") or stop.get("name") or stop.get("location") or "?"
        scheduled = stop.get("scheduled_time") or stop.get("schedule_time") or ""
        expected = stop.get("expected_time") or stop.get("eta") or ""
        stops.append({
            "name": name,
            "scheduled": scheduled,
            "expected": expected,
            "arrival": stop.get("arrival_time") or "",
            "departure": stop.get("departure_time") or "",
            "delay_min": _minutes_between(scheduled, expected),
            "status": stop.get("status") or "",
            "raw": stop,
        })

    return {
        "latitude": lat_long[0] if len(lat_long) > 0 else None,
        "longitude": lat_long[1] if len(lat_long) > 1 else None,
        "speed": details.get("speed"),
        "timestamp": details.get("timestamp"),
        "location": details.get("location"),
        "state": details.get("hstate") or details.get("state"),
        "stops": stops,
        "distance": data.get("distance_details"),
        "raw": data,
    }


def format_live(parsed: dict) -> str:
    """Render one poll as a short human-readable table."""
    lines = []
    lines.append(
        f"Live: {parsed.get('location') or '?'} "
        f"({parsed.get('latitude')}, {parsed.get('longitude')})"
    )
    lines.append(
        f"Speed: {parsed.get('speed')} km/h  "
        f"State: {parsed.get('state') or '?'}  "
        f"GPS at: {parsed.get('timestamp') or '?'}"
    )
    lines.append("")
    lines.append(f"{'Stop':<22} {'Sched':<10} {'Expected':<10} {'Delay':<7} {'Arrived':<10}")
    for stop in parsed["stops"]:
        delay = stop["delay_min"]
        delay_text = f"+{delay}m" if delay is not None and delay > 0 else (
            f"{delay}m" if delay is not None else "-"
        )
        lines.append(
            f"{stop['name']:<22} {stop['scheduled']:<10} "
            f"{stop['expected']:<10} {delay_text:<7} {stop['arrival'] or '-':<10}"
        )
    return "\n".join(lines)


def watch(key: str, interval: float = 20.0, once: bool = False) -> None:
    """Poll eta_map forever (or once) and print each update."""
    while True:
        parsed = parse_eta_map(fetch_eta_map(key))
        print(format_live(parsed))
        print()
        if once:
            return
        time.sleep(interval)
