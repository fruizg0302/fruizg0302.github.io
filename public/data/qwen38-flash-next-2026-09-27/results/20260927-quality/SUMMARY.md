# Long-context and coding results — 2026-09-27

Completed all 45 runs: 44 passed, one model-code failure, no API/harness errors, no truncated answers. Desktop remained active. Swap was unused at the final check.

| Check | Result |
|---|---:|
| Retrieval across approximately 8K, 32K and 60K input tokens | 15/15 |
| Long-context generation, serial and MTP | 6/6 |
| Short-context coding, thinking off | 9/10 tasks |
| Short-context coding, low reasoning | 10/10 tasks |
| Coding specifications embedded in approximately 32K tokens | 4/4 |

Ten Python tasks cover interval merging, topological sorting, LRU caching, minimum-window substring, wildcard matching, grid paths, CSV parsing, latest-event selection, arithmetic expression parsing and increasing subsequences. Their 565 deterministic hidden cases are reused across modes; the long-context coding subset contains two of these tasks. These repeated runs are not 24 independent coding problems.

The one failure was the short-prompt arithmetic parser with thinking off: its tokenizer accepted `+` and `-` but omitted `*`, even though the parser contained multiplication logic. It passed 5/63 cases. The independently generated low-reasoning answer passed 63/63, as did both long-context variants. No repair feedback was given. This illustrates a first-attempt reliability difference in this small sample, not proof that reasoning always fixes bugs or that longer context improves coding.

| Approximate input context | Serial decode | MTP decode | Speed ratio |
|---|---:|---:|---:|
| 8K | 33.2 tok/s | 55.0 tok/s | 1.65x |
| 32K | 33.5 tok/s | 54.5 tok/s | 1.63x |
| 60K | 33.3 tok/s | 54.2 tok/s | 1.63x |

All three serial/MTP pairs produced identical correct messages. Each length has just one pair, using a structured retrieval-and-counting response. These are decode rates, not total request throughput or a representative coding-speed estimate. Cache reuse is recorded in the detailed report.

This is a custom diagnostic suite, not HumanEval, SWE-bench or a repository-level agent evaluation. Retrieval used synthetic archives, not real-document comprehension. Coding used Python functions in one attempt, not file editing, tool use or multi-step debugging. Bounded reasoning was low effort with at most 1,536 thinking tokens and 4,096 total output tokens; temperature was zero throughout.

The results support using this setup for further practical trials, with reasoning enabled for coding and executable tests to catch mistakes. They do not establish general coding accuracy or a ranking against other models.

[Detailed report](REPORT.md) · [Machine-readable summary](validated-summary.json) · [Runner](../../run-quality.py) · [Task definitions](../../quality-cases.py)
