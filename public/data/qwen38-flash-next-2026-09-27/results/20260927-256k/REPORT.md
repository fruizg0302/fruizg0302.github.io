# 256K native-context attempt

Configured context and KV pool: 262,144 tokens, one slot, 16,384-token prefill arena. Desktop active. Same pinned Halogen 0.14.0 image, native W4B weights and quality overlay as the earlier tests. Thinking off, temperature zero. MTP includes default prompt-lookup assistance.

Actual input: **259,933 tokens**, 99.16% of the configured window. Output allowance: 1,024 tokens. This is near-full occupancy, not 262,144 input tokens plus output.

One synthetic archive holds independent random codes at approximately 5%, 50% and 95% of its rows. The answer must return all three, null for an absent key, and the complete sequence 1–128. This is one task in two decoding modes, not five independent retrieval tasks.

| Mode | Correct | Code checks | Absent key | Sequence | Output tokens | Decode tok/s | Request s | Cached / restored |
|---|---|---|---|---|---:|---:|---:|---:|
| serial | True | 3/3 | True | True | 867 | 32.58 | 263.65 | 0 / 0 |
| mtp | True | 3/3 | True | True | 867 | 53.13 | 49.63 | 229376 / 0 |

Identical full messages: **True**. MTP/serial engine decode ratio: **1.63x**.

Serial ran first, MTP second; there is only one pair and no counterbalanced thermal control. Prompt caching remained enabled, so compare engine decode rates separately from request wall time. Cache counters above identify reused input. This result does not establish general long-document comprehension, coding quality, or performance on unrelated prompts.

Full requests/responses and prompt text are saved here. `memory.jsonl` samples host memory, swap and PSI; `startup-memory.txt` contains the engine memory-accounting excerpt; full system journals remain local. `session.json` records the temporary configuration and `cleanup.json` records restoration after the model unloads.

## Memory and cleanup

Engine startup: 68.0 GiB locked weights + 7.2 GiB KV pool + 12.2 GiB working memory = **87.4 GiB**, with **16.7 GiB reported host headroom**. The lookup table remains demand-paged.

Monitoring retained 69 samples. Maximum swap used: **0 MiB**; maximum memory PSI full avg10: **0.00%**; minimum MemFree: **14.82 GiB**. Largest sampling gap: 5.0 seconds. MemAvailable is not a reliable estimate of reclaimable headroom for these pinned mappings.

Cleanup verified: model inactive, TuneD inactive, power-profiles-daemon active with the previous performance profile. Temporary runtime override removed; the persistent launcher remains at 65,536 tokens. The boot-time IOMMU/GTT parameters were unchanged.

The first launcher attempt stopped at its Ollama preflight check before loading the model because it lacked the desktop user environment. The preflight was corrected to run as the desktop user. The completed inference run used the corrected helper saved alongside these results.
