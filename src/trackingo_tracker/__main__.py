"""CLI: python -m trackingo_tracker --key YOUR_KEY [--once] [--json] [--demo]"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .client import fetch_eta_map, fetch_journey_details, format_live, parse_eta_map, watch


def _load_demo() -> dict:
    demo = Path(__file__).resolve().parents[2] / "examples" / "sample_eta_map.json"
    return json.loads(demo.read_text())


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Live-track a bus from its Trackingo tracking key."
    )
    parser.add_argument("--key", help="Tracking key from your own tracking link")
    parser.add_argument("--once", action="store_true", help="Fetch once, then stop")
    parser.add_argument("--json", action="store_true", help="Print raw JSON instead of a table")
    parser.add_argument("--interval", type=float, default=20.0,
                        help="Seconds between polls (default 20, like the tracker page)")
    parser.add_argument("--journey", action="store_true",
                        help="Fetch journey_details instead of the live map")
    parser.add_argument("--demo", action="store_true",
                        help="Show output using the bundled sample data (no key, no network)")
    args = parser.parse_args(argv)

    if args.demo:
        parsed = parse_eta_map(_load_demo())
        print(json.dumps(parsed, indent=2) if args.json else format_live(parsed))
        return 0

    if not args.key:
        parser.error("--key is required unless you pass --demo")
    if args.key in {"YOUR_KEY", "YOUR_TRACKING_KEY", "KEY"}:
        parser.error("that is a placeholder, not a real key. Use the key from your own tracking link.")

    if args.journey:
        data = fetch_journey_details(args.key)
    else:
        data = fetch_eta_map(args.key)
    if args.json:
        print(json.dumps(data, indent=2))
        return 0
    if args.journey:
        print(json.dumps(data, indent=2))
        print("\nTip: journey_details can include booking / contact fields. Do not share its output.")
        return 0
    print(format_live(parse_eta_map(data)))
    if not args.once:
        print(f"\nWatching every {args.interval:g}s. Ctrl+C to stop.")
        try:
            watch(args.key, interval=args.interval)
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
