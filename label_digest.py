"""Weekly label digest: turns For Artists numbers into a clean per-label report.

In production this reads from the Apple Music for Artists API.
Here it reads for_artists_data.json (a simulated weekly export).
"""

import json
from pathlib import Path

BASE = Path(__file__).parent


def load_data():
    with open(BASE / "for_artists_data.json") as f:
        return json.load(f)


def recommendation(spike):
    """Turn one spike event into a plain-English recommendation."""
    track = spike["track"]
    artist = spike["artist"]
    chart = spike["chart"]
    if spike.get("old_position") is None:
        return (
            f"{track} by {artist} entered the Shazam {chart} at "
            f"#{spike['new_position']} this week. "
            f"Suggested action: push it to Promote for social assets this week."
        )
    return (
        f"{track} by {artist} jumped {spike['jump']} spots on the Shazam {chart} "
        f"(#{spike['old_position']} to #{spike['new_position']}) this week. "
        f"Suggested action: pitch it via Connect before the 10-day release window closes."
    )


def build_digest(label, data, spikes=None):
    """Build the digest text for one label.

    spikes: list of spike dicts for this label's tracks (or None).
    """
    lines = [f"# Weekly digest: {label}", ""]
    if spikes:
        lines.append("## Spike alerts")
        for s in spikes:
            lines.append(f"- {recommendation(s)}")
        lines.append("")
    lines.append("## This week's numbers")
    for track, nums in data["tracks"].items():
        lines.append(
            f"- {track}: {nums['streams']:,} streams, "
            f"{nums['playlist_adds']} playlist adds, "
            f"{nums['shazam_count']:,} Shazams"
        )
    lines.append("")
    return "\n".join(lines)


def main():
    data = load_data()
    out = BASE / "digests"
    out.mkdir(exist_ok=True)
    for label, label_data in data.items():
        text = build_digest(label, label_data)
        (out / f"{label}.md").write_text(text)
        print(f"wrote {label}.md")


if __name__ == "__main__":
    main()
