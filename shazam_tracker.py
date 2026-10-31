"""Shazam spike tracker.

Pulls the Shazam US Top 200 chart (via the public kworb.net mirror, which
publishes it as a plain HTML table), saves a daily snapshot, compares it
against the previous snapshot, and writes spike events to spikes.json
for bridge.py.

Run daily:  python3 shazam_tracker.py
First run only saves a baseline (no previous day to compare against).
"""

import json
import re
import urllib.request
from datetime import date
from pathlib import Path

BASE = Path(__file__).parent
CHART_URL = "https://kworb.net/charts/shazam/us.html"
CHART_NAME = "US Top 200"
SPIKE_THRESHOLD = 20  # positions gained in a day to count as a spike


def fetch_chart():
    """Return today's chart as a list of (position, artist, title)."""
    req = urllib.request.Request(CHART_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    rows = re.findall(r"<tr>(.*?)</tr>", html, re.S)
    chart = []
    for row in rows[1:]:  # skip the header row
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        if len(cells) < 3:
            continue
        pos = int(re.sub(r"<[^>]+>", "", cells[0]).strip())
        artist_title = re.sub(r"<[^>]+>", "", cells[2]).strip()
        if " - " in artist_title:
            artist, title = artist_title.split(" - ", 1)
        else:
            artist, title = "", artist_title
        chart.append((pos, artist.strip(), title.strip()))
    return chart


def snapshot_path(day):
    return BASE / "snapshots" / f"chart-{day}.json"


def load_previous_snapshot(today):
    """Return the most recent snapshot before today, or None."""
    snap_dir = BASE / "snapshots"
    if not snap_dir.exists():
        return None
    prev = sorted(p for p in snap_dir.glob("chart-*.json") if p.stem < f"chart-{today}")
    if not prev:
        return None
    with open(prev[-1]) as f:
        return json.load(f)


def detect_spikes(chart, prev_lookup, day):
    """Flag songs that jumped SPIKE_THRESHOLD+ spots or are new entries."""
    spikes = []
    for pos, artist, title in chart:
        old_pos = prev_lookup.get((artist, title))
        if old_pos is None:
            spikes.append({
                "track": title, "artist": artist, "chart": CHART_NAME,
                "old_position": None, "new_position": pos,
                "jump": None, "date": day,
            })
        elif old_pos - pos >= SPIKE_THRESHOLD:
            spikes.append({
                "track": title, "artist": artist, "chart": CHART_NAME,
                "old_position": old_pos, "new_position": pos,
                "jump": old_pos - pos, "date": day,
            })
    return spikes


def main():
    today = date.today().isoformat()
    try:
        chart = fetch_chart()
    except Exception as e:
        print(f"could not fetch the chart: {e}")
        return
    print(f"fetched {len(chart)} chart entries")

    prev = load_previous_snapshot(today)

    (BASE / "snapshots").mkdir(exist_ok=True)
    snap = [{"position": pos, "artist": a, "title": t} for pos, a, t in chart]
    with open(snapshot_path(today), "w") as f:
        json.dump(snap, f, indent=2)

    if prev is None:
        print("no previous snapshot, baseline saved. Run again tomorrow for spikes.")
        spikes = []
    else:
        lookup = {(e["artist"], e["title"]): e["position"] for e in prev}
        spikes = detect_spikes(chart, lookup, today)
        print(f"found {len(spikes)} spikes")

    with open(BASE / "spikes.json", "w") as f:
        json.dump(spikes, f, indent=2)
    for s in spikes:
        if s["old_position"] is None:
            print(f"  NEW: {s['track']} by {s['artist']} entered at #{s['new_position']}")
        else:
            print(f"  {s['track']} by {s['artist']}: #{s['old_position']} -> #{s['new_position']}")


if __name__ == "__main__":
    main()
