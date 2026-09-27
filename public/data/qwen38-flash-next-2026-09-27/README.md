# Qwen3.8 Flash-Next experiment artifacts, 2026-09-27

Companion material for the fourth Strix Halo article. The evidence ZIP contains exact benchmark requests/responses, quality evaluations, generated code, suite definitions, script snapshots and aggregate reports. It excludes host boot metadata, system journals, model weights and download caches.

`run-quality.py` requires Python 3 and Bubblewrap on Linux, plus the prepared Halogen API at http://127.0.0.1:8731 with a 65,536-token context. It executes model-generated code inside Bubblewrap. Run it with `python3 run-quality.py --out results/new-quality-run`. Reuse the same output directory to resume an unchanged suite. Read the script before running.

The throughput wrapper expects the upstream Halogen v0.14.0 checkout at the path recorded in its source; adapt this for another host. Service/helper files are records of this machine's setup, not universal installation scripts. Model paths and numeric GPU group IDs are host-specific. The article describes the IOMMU tradeoff and TuneD settings that did not apply.

The saved reports describe the state at measurement time. Any statement that the model remains running is historical; it was unloaded after testing. Original filesystem paths in records are retained for provenance. Generated candidate code is test output, not vetted reusable software.

All raw requests contain synthetic benchmark material. No personal project documents were used in this suite. `SHA256SUMS` verifies every original file packaged in the ZIP.
