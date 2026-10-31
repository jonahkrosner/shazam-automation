"""Bridge: feeds Shazam spike events into each label's weekly digest.

Reads spikes.json (output of shazam_tracker.py), matches tracks to labels
via labels.json, and regenerates each label's digest with a Spike alerts
section on top. Regenerating from scratch each run makes it idempotent:
running twice produces identical output.
"""

import json
from pathlib import Path

from label_digest import build_digest, load_data

BASE = Path(__file__).parent


def load_json(name):
    with open(BASE / name) as f:
        return json.load(f)


def main():
    spikes = load_json("spikes.json")
    track_to_label = load_json("labels.json")
    data = load_data()

    # Group spikes by label; skip tracks with no label match.
    by_label = {}
    for s in spikes:
        label = track_to_label.get(s["track"])
        if label is None:
            continue
        by_label.setdefault(label, []).append(s)

    out = BASE / "digests"
    out.mkdir(exist_ok=True)
    for label, label_data in data.items():
        label_spikes = by_label.get(label, [])
        text = build_digest(label, label_data, spikes=label_spikes)
        path = out / f"{label}.md"
        path.write_text(text)
        print(f"wrote {path.name} ({len(label_spikes)} spike alerts)")


if __name__ == "__main__":
    main()
