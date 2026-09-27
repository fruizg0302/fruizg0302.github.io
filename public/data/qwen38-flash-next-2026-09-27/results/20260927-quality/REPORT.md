# Qwen3.8 Flash Next: local quality diagnostics

Completed 45/45 requests. Updated 2026-09-27 10:11:30 -0600.

Configuration: Halogen 0.14.0, quality overlay, 65,536-token context, desktop active. Temperature 0. Retrieval uses MTP with thinking off. Coding compares thinking off and low effort with a 1,536-token thinking budget and 4,096 total output tokens. No repair attempts.

This is a small custom diagnostic suite, not HumanEval, SWE-bench or a general coding-quality score. Synthetic archive retrieval does not establish comprehension of real books or repositories. Ten unique Python tasks use deterministic hidden cases. Two tasks repeat with about 32K tokens of distractors. Complexity targets are not formally verified.

Requests are sequential; drafter order is alternated for long-context speed pairs. Cache counters are retained; wall time includes prompt processing and cannot be treated as cold-prefill speed. Context lengths below are actual API prompt-token counts, not requested targets. Generation speed is the engine decode metric, not full-request throughput.

| Test | Mode | Input tokens | Output tokens | Correct | Cases | Decode tok/s | Wall s | Cached / restored |
|---|---|---:|---:|---|---:|---:|---:|---:|
| retrieval-8192-early | none/mtp | 8174 | 24 | PASS | — | 61.1 | 8.4 | 0 / 0 |
| retrieval-8192-middle | none/mtp | 8192 | 25 | PASS | — | 58.6 | 8.5 | 0 / 0 |
| retrieval-8192-late | none/mtp | 8163 | 23 | PASS | — | 61.4 | 8.4 | 0 / 0 |
| retrieval-8192-multi | none/mtp | 8181 | 63 | PASS | — | 57.5 | 9.1 | 0 / 0 |
| retrieval-8192-absent | none/mtp | 8198 | 8 | PASS | — | 48.1 | 8.7 | 0 / 0 |
| decode-8192-serial | none/serial | 8213 | 818 | PASS | — | 33.2 | 32.9 | 0 / 0 |
| decode-8192-mtp | none/mtp | 8213 | 818 | PASS | — | 55.0 | 23.4 | 0 / 0 |
| retrieval-32768-early | none/mtp | 32777 | 26 | PASS | — | 59.1 | 29.9 | 0 / 0 |
| retrieval-32768-middle | none/mtp | 32735 | 24 | PASS | — | 62.0 | 29.7 | 0 / 0 |
| retrieval-32768-late | none/mtp | 32734 | 26 | PASS | — | 58.7 | 29.8 | 0 / 0 |
| retrieval-32768-multi | none/mtp | 32815 | 64 | PASS | — | 60.7 | 31.2 | 0 / 0 |
| retrieval-32768-absent | none/mtp | 32792 | 8 | PASS | — | 38.4 | 29.9 | 0 / 0 |
| decode-32768-mtp | none/mtp | 32762 | 819 | PASS | — | 54.5 | 44.4 | 0 / 0 |
| decode-32768-serial | none/serial | 32762 | 819 | PASS | — | 33.5 | 52.9 | 0 / 0 |
| retrieval-60000-early | none/mtp | 60003 | 22 | PASS | — | 56.7 | 56.0 | 0 / 0 |
| retrieval-60000-middle | none/mtp | 59933 | 23 | PASS | — | 59.6 | 56.1 | 0 / 0 |
| retrieval-60000-late | none/mtp | 59976 | 24 | PASS | — | 61.6 | 56.1 | 0 / 0 |
| retrieval-60000-multi | none/mtp | 59974 | 66 | PASS | — | 57.0 | 57.1 | 0 / 0 |
| retrieval-60000-absent | none/mtp | 59973 | 8 | PASS | — | 47.8 | 55.7 | 0 / 0 |
| decode-60000-serial | none/serial | 59972 | 820 | PASS | — | 33.3 | 78.6 | 0 / 0 |
| decode-60000-mtp | none/mtp | 59972 | 820 | PASS | — | 54.2 | 41.5 | 32768 / 0 |
| coding-intervals-none | none/mtp | 78 | 178 | PASS | 48/48 | 53.9 | 4.3 | 0 / 0 |
| coding-intervals-low | low/mtp | 106 | 440 | PASS | 48/48 | 53.3 | 9.3 | 0 / 0 |
| coding-toposort-low | low/mtp | 127 | 827 | PASS | 49/49 | 54.3 | 16.4 | 0 / 0 |
| coding-toposort-none | none/mtp | 99 | 262 | PASS | 49/49 | 57.3 | 5.5 | 0 / 0 |
| coding-lru-none | none/mtp | 115 | 251 | PASS | 47/47 | 54.3 | 5.8 | 0 / 0 |
| coding-lru-low | low/mtp | 143 | 727 | PASS | 47/47 | 53.2 | 14.9 | 0 / 0 |
| coding-min_window-low | low/mtp | 113 | 931 | PASS | 65/65 | 52.2 | 19.0 | 0 / 0 |
| coding-min_window-none | none/mtp | 85 | 260 | PASS | 65/65 | 55.3 | 5.6 | 0 / 0 |
| coding-wildcard-none | none/mtp | 94 | 477 | PASS | 85/85 | 52.5 | 10.1 | 0 / 0 |
| coding-wildcard-low | low/mtp | 122 | 1073 | PASS | 85/85 | 52.2 | 21.7 | 0 / 0 |
| coding-grid_paths-low | low/mtp | 127 | 469 | PASS | 50/50 | 53.8 | 9.9 | 0 / 0 |
| coding-grid_paths-none | none/mtp | 99 | 195 | PASS | 50/50 | 59.1 | 4.3 | 0 / 0 |
| coding-csv_parse-none | none/mtp | 107 | 118 | PASS | 45/45 | 47.5 | 3.6 | 0 / 0 |
| coding-csv_parse-low | low/mtp | 135 | 967 | PASS | 45/45 | 49.7 | 20.6 | 0 / 0 |
| coding-latest_events-low | low/mtp | 125 | 346 | PASS | 55/55 | 53.8 | 7.6 | 0 / 0 |
| coding-latest_events-none | none/mtp | 97 | 76 | PASS | 55/55 | 58.3 | 2.3 | 0 / 0 |
| coding-expression_parser-none | none/mtp | 99 | 587 | FAIL | 5/63 | 54.6 | 11.7 | 0 / 0 |
| coding-expression_parser-low | low/mtp | 127 | 1054 | PASS | 63/63 | 56.2 | 19.9 | 0 / 0 |
| coding-lis-low | low/mtp | 115 | 274 | PASS | 58/58 | 50.8 | 6.5 | 0 / 0 |
| coding-lis-none | none/mtp | 87 | 141 | PASS | 58/58 | 53.6 | 3.6 | 0 / 0 |
| coding-long-toposort-none | none/mtp | 32616 | 262 | PASS | 49/49 | 54.4 | 34.1 | 0 / 0 |
| coding-long-toposort-low | low/mtp | 32644 | 790 | PASS | 49/49 | 54.0 | 43.9 | 0 / 0 |
| coding-long-expression_parser-none | none/mtp | 32616 | 629 | PASS | 63/63 | 53.3 | 41.0 | 0 / 0 |
| coding-long-expression_parser-low | low/mtp | 32644 | 600 | PASS | 63/63 | 53.1 | 40.6 | 0 / 0 |

## Aggregate results

- retrieval, thinking none: 15/15 complete-task passes.
- decode, thinking none: 6/6 complete-task passes.
- coding, thinking none: 9/10 complete-task passes.
- coding, thinking low: 10/10 complete-task passes.
- coding_long, thinking none: 2/2 complete-task passes.
- coding_long, thinking low: 2/2 complete-task passes.

## Long-context generation comparison

- Target 8,192: serial 33.2 tok/s; MTP 55.0 tok/s; ratio 1.65x; identical messages: True. One pair only; structured counting output is not representative of all generation.
- Target 32,768: serial 33.5 tok/s; MTP 54.5 tok/s; ratio 1.63x; identical messages: True. One pair only; structured counting output is not representative of all generation.
- Target 60,000: serial 33.3 tok/s; MTP 54.2 tok/s; ratio 1.63x; identical messages: True. One pair only; structured counting output is not representative of all generation.

## Failures to inspect

- coding-expression_parser-none: [{"case": 1, "args": ["-(2+3)*4"], "expected": -20, "actual": {"error": "ValueError: Invalid character: *"}}, {"case": 2, "args": ["2*-3 + 4"], "expected": -2, "actual": {"error": "ValueError: Invalid character: *"}}, {"case": 7, "args": ["(2+3)*(4-7)"], "expected": -15, "actual": {"error": "ValueError: Invalid character: *"}}, {"case": 8, "args": ["(19 * -6) * -(5)"], "expected": 570, "actual": {"error": "ValueError: Invalid character: *"}}, {"case": 9, "args": ["(10 + -12) * -(-7)"], "expected": -14, "actual": {"error": "ValueError: Invalid character: *"}}, {"case": 10, "args": ["(-2 - 0) * . Full request, answer and checks: `coding-expression_parser-none.json`.

Artifacts: manifest.json records the planned tests and script hashes; each per-test JSON retains the exact request, full answer, timings and evaluation; suite-cases.json contains hidden checks; progress.json is machine-readable. API errors count as errors rather than model-quality failures. Code runs with no network or home mount, read-only runtime and time/memory limits.
