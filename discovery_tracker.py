"""Archive US Shazam Discovery chart; reject incomplete/unexpected responses."""
import csv
import io
import json
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
URL = "https://www.shazam.com/services/charts/csv/discovery/united-states/"

def download():
    request = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/csv"})
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8-sig")
    if "<html" in body[:300].lower():
        raise ValueError("Discovery returned HTML rather than CSV")
    lines = body.splitlines()
    header_index = next((i for i, line in enumerate(lines) if line.strip().lower().replace(" ", "") == "rank,artist,title"), None)
    if header_index is None:
        raise ValueError(f"Missing Discovery CSV header; response_prefix={body[:220]!r}")
    rows = list(csv.DictReader(io.StringIO("\n".join(lines[header_index:]))))
    if not rows:
        raise ValueError("Discovery returned no rows")
    keys = {key.strip().lower(): key for key in rows[0] if key}
    if not {"rank", "artist", "title"}.issubset(keys):
        raise ValueError(f"Discovery CSV endpoint is not returning a chart. Headers={list(keys)!r}; response_prefix={body[:220]!r}. Do not archive this as valid data.")
    result = []
    for row in rows:
        position = int(row[keys["rank"]].strip())
        artist = row[keys["artist"]].strip()
        title = row[keys["title"]].strip()
        if not artist or not title:
            raise ValueError("Missing Discovery artist or title")
        result.append({"position": position, "artist": artist, "title": title})
    if len(result) != 10 or [r["position"] for r in result] != list(range(1, 11)):
        raise ValueError(f"Unexpected Discovery rankings: {len(result)} entries")
    return result

def main():
    today = datetime.now(ZoneInfo("America/Chicago")).date().isoformat()
    chart = download()
    directory = ROOT / "snapshots"
    directory.mkdir(exist_ok=True)
    destination = directory / f"discovery-{today}.json"
    if destination.exists():
        print("Discovery snapshot already exists; no changes")
        return
    earlier = sorted(p for p in directory.glob("discovery-*.json") if p.stem < f"discovery-{today}")
    destination.write_text(json.dumps(chart, indent=2, ensure_ascii=False) + "\n")
    if not earlier:
        print(f"Saved Discovery baseline: {len(chart)} entries")
        return
    previous = json.loads(earlier[-1].read_text())
    old_positions = {(row["artist"].casefold(), row["title"].casefold()): row["position"] for row in previous}
    spikes = []
    for row in chart:
        old = old_positions.get((row["artist"].casefold(), row["title"].casefold()))
        jump = old - row["position"] if old is not None else None
        if old is None or jump >= 20:
            spikes.append({"track": row["title"], "artist": row["artist"], "chart": "US Discovery", "old_position": old, "new_position": row["position"], "jump": jump, "date": today})
    path = ROOT / "spikes.json"
    existing = json.loads(path.read_text()) if path.exists() else []
    merged = [event for event in existing if event.get("chart") != "US Discovery"] + spikes
    path.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n")
    print(f"Saved Discovery chart; {len(spikes)} alerts")

if __name__ == "__main__":
    main()
