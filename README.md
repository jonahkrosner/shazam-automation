# Shazam spike alerts + label digest

Two automations, one pipeline.

## The pieces

- `shazam_tracker.py`: pulls the Shazam US Top 200 (via the public kworb.net
  mirror), saves a daily snapshot in `snapshots/`, diffs against the previous
  day, and writes spike events to `spikes.json`. Run it daily with
  `python3 shazam_tracker.py`. First run only saves a baseline.
- `label_digest.py`: builds a weekly per-label digest from For Artists numbers.
  Run it alone with `python3 label_digest.py`.
- `bridge.py`: reads the tracker's spike output, matches tracks to labels, and
  regenerates each digest with a Spike alerts section on top.
  Run it with `python3 bridge.py`. Output lands in `digests/`.

## The contract between your tracker and the bridge

`bridge.py` reads `spikes.json`, a list of dicts in this exact shape:

```json
[
  {"track": "Dracula", "artist": "Tame Impala", "chart": "US Top 200",
   "old_position": 45, "new_position": 9, "jump": 36, "date": "2026-10-30"},
  {"track": "Go", "artist": "The Chemical Brothers", "chart": "US Top 200",
   "old_position": null, "new_position": 4, "jump": null, "date": "2026-10-30"}
]
```

New entries use `"old_position": null` and `"jump": null`. If your tracker
writes a different shape, either adjust it to match or tell me and I'll
adjust the bridge.

## The data files

- `labels.json`: maps each track to its label. Add your real mappings here.
- `for_artists_data.json`: simulates a weekly Apple Music for Artists export.
  In production this would come from the For Artists API; here it's a file
  so the pipeline runs end to end.
- `spikes.json`: sample tracker output. Replace with your tracker's real output.

## Run order

1. Your tracker writes `spikes.json`.
2. `python3 bridge.py` regenerates every digest in `digests/`.
3. Open `digests/` and read the Spike alerts section on each label's report.
