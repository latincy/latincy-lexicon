# Startup performance baseline

Recorded on `v02-perf-baseline` branch before any optimization work.

## Environment

- Python 3.11 (project `.venv`)
- macOS Darwin 25.4.0
- `data/json/analyzer.json` — 15.1 MB
- `data/json/lexicon.json` — 16.2 MB

## Measurement script

`scripts/bench_startup.py` — in-process median of 5 runs. Cold-process numbers captured separately by invoking Python in a fresh subprocess per run.

## Warm in-process (N=5, median / min / max)

| Phase                         | Median   | Min      | Max      |
| ----------------------------- | -------- | -------- | -------- |
| `import latincy_lexicon.*`    | 36.9ms   | —        | —        |
| `Analyzer.from_json` total    | 330.3ms  | 322.7ms  | 520.2ms  |
| &nbsp;&nbsp;`json.load` (analyzer) | 70.5ms   | 67.2ms   | 248.1ms  |
| &nbsp;&nbsp;`_build_caches`   | 263.0ms  | 250.4ms  | 272.0ms  |
| `json.load` (lexicon)         | 143.0ms  | 132.7ms  | 311.1ms  |

## Cold process (N=3, one Python process per run)

| Run | Import  | `from_json` | Total   |
| --- | ------- | ----------- | ------- |
| 1   | 39.4ms  | 512.8ms     | 552.2ms |
| 2   | 16.0ms  | 372.8ms     | 388.9ms |
| 3   | 14.8ms  | 420.9ms     | 435.7ms |

## Summary

- **Library startup cost (ex spaCy):** ~500ms cold, dominated by `Analyzer._build_caches` (~260ms, 50–60% of `from_json`).
- **`json.load` is not the bottleneck:** 70ms for a 15MB file. Format swaps (orjson, msgpack) would save tens of ms at most.
- **`_build_caches` is the target:** the triple-nested stem fan-out at `analyzer.py:219-229` plus lowercase+setdefault work across ~40k inflections, ~3k uniques, ~39k entries.
- **`lexicon.json`:** loaded separately in the spaCy factory; adds ~140ms of `json.load` on top.

## Implications for the v0.2 plan

- Priority 1 (pickle cache): targets the right thing — would replace ~330ms of `from_json` with a pickle read (~50–100ms expected). Real but not dramatic savings.
- Priority 2 (lazy load): orthogonal; buys the full ~500ms for callers who add the component but never run a doc through it (tests, `nlp.pipe_names` inspection, `to_disk`/`from_disk` round-trips).
- Priority 4 (build-time lowercase): trims a slice of the 263ms `_build_caches` cost. Minor but free.
- Priority 3 (`str.translate` in `normalize_latin`): not a startup lever — per-token hot-path win.
