"""Daily Shazam US Top 200 tracker with validated, persistent snapshots."""
import json
import re
import urllib.request
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

BASE = Path(__file__).resolve().parent
CHART_URL = "https://kworb.net/charts/shazam/us.html"
CHART_NAME = "US Top 200"
SPIKE_THRESHOLD = 20

class ChartParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None
        self.cell_text = []
    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = tag
            self.cell_text = []
    def handle_data(self, data):
        if self.cell is not None:
            self.cell_text.append(data)
    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell == tag:
            self.row.append("".join(self.cell_text).strip())
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None

def fetch_chart():
    req = urllib.request.Request(CHART_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        html = response.read().decode("utf-8", errors="replace")
    parser = ChartParser()
    parser.feed(html)
    chart = []
    for cells in parser.rows:
        if len(cells) < 3:
            continue
        position_text = re.sub(r"[^0-9]", "", cells[0])
        if not position_text:
            continue
        position = int(position_text)
        # Kworb's third cell contains the artist and title.
        artist_title = unescape(cells[2]).strip()
        if " - " in artist_title:
            artist, title = artist_title.split(" - ", 1)
        else:
            artist, title = "", artist_title
        if artist_title:
            chart.append({"position": position, "artist": artist.strip(), "title": title.strip()})
    positions = [item["position"] for item in chart]
    if len(chart) != 200 or sorted(positions) != list(range(1, 201)):
        raise ValueError(f"Invalid or incomplete chart: {len(chart)} entries")
    return chart

def load_previous_snapshot(today):
    directory = BASE / "snapshots"
    candidates = sorted(p for p in directory.glob("chart-*.json") if p.stem < f"chart-{today}")
    if not candidates:
        return None
    return json.loads(candidates[-1].read_text())

def detect_spikes(chart, previous, today):
    previous_positions = {(row["artist"].casefold(), row["title"].casefold()): row["position"] for row in previous}
    events = []
    for row in chart:
        old = previous_positions.get((row["artist"].casefold(), row["title"].casefold()))
        jump = old - row["position"] if old is not None else None
        if old is None or jump >= SPIKE_THRESHOLD:
            events.append({
                "track": row["title"], "artist": row["artist"], "chart": CHART_NAME,
                "old_position": old, "new_position": row["position"],
                "jump": jump, "date": today,
            })
    return events

def main():
    today = datetime.now(timezone.utc).date().isoformat()
    chart = fetch_chart()  # Fail before writing anything if the download is bad.
    previous = load_previous_snapshot(today)
    directory = BASE / "snapshots"
    directory.mkdir(exist_ok=True)
    (directory / f"chart-{today}.json").write_text(json.dumps(chart, indent=2) + "\n")
    if previous is None:
        print(f"Saved baseline of {len(chart)} entries. Spike detection begins on next snapshot.")
        return  # Preserve any existing alert file until comparison is possible.
    spikes = detect_spikes(chart, previous, today)
    (BASE / "spikes.json").write_text(json.dumps(spikes, indent=2) + "\n")
    print(f"Saved {len(chart)} entries; detected {len(spikes)} alerts")
    for spike in spikes:
        change = "NEW" if spike["jump"] is None else f"+{spike['jump']}"
        print(f"{change}: {spike['artist']} - {spike['track']} (#{spike['new_position']})")

if __name__ == "__main__":
    main()
