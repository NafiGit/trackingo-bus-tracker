import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trackingo_tracker.client import parse_eta_map


def test_parse_sample():
    sample = json.loads((Path(__file__).resolve().parents[1] / "examples" / "sample_eta_map.json").read_text())
    parsed = parse_eta_map(sample)
    assert parsed["latitude"] == 13.00515
    assert parsed["longitude"] == 77.68488
    assert parsed["speed"] == 0
    assert parsed["state"] == "idle"
    assert len(parsed["stops"]) == 6
    assert parsed["stops"][3]["name"] == "TC Palya"
    assert parsed["stops"][3]["delay_min"] == 28
    assert parsed["stops"][0]["arrival"] == "10:28 PM"
    assert parsed["stops"][2]["arrival"] == ""
