# First Halogen run — 2026-09-27

Smoke test passed: correct arithmetic and sorted-array JSON, thinking off. API and engine 0.14.0 match. Model remains available at http://127.0.0.1:8731/v1.

## Generation comparison

Ten upstream eval-prompts.json prompt types, three repetitions per type and drafter, up to 300 output tokens, greedy decoding, thinking off. These are short-prompt generation tests; they do not measure decode at 32K context.

| Metric | MTP off | MTP on |
| --- | ---: | ---: |
| Mean engine decode speed | 34.20 tok/s | 49.90 tok/s |
| Mean end-to-end output rate | 32.51 tok/s | 46.46 tok/s |
| Engine decode range | 32.90–35.01 tok/s | 38.87–58.14 tok/s |

MTP increased mean decode speed by 45.9% (1.46x), and mean end-to-end output rate by 42.9%. All 30 paired outputs matched exactly. This is a greedy output-equivalence check, not a coding correctness evaluation. Three repeats of each deterministic prompt do not represent 30 distinct tasks.

## Uncached synthetic prefill

| Actual prompt tokens | Mean end-to-end input rate | Uncached samples |
| --- | ---: | ---: |
| 1,021 | 536 tok/s | 6 |
| 8,185 | 1,071 tok/s | 6 |
| 32,773 | 1,188 tok/s | 1 |

These rates include HTTP overhead and one output token. Five 32K repetitions restored 32,768 cached tokens and are excluded here. The upstream summary.txt includes them and therefore must not be quoted as cold-prefill performance. “Cold” here means no restored prompt KV cache, not cold disk/file cache. The serial pass ran before the MTP pass, so run order and warm-up effects were not counterbalanced.

## Configuration and memory

ProArt PX13, Ryzen AI MAX+ 395, 128 GB installed RAM; kernel 7.2.5-3-omarchy-bore; amd_iommu=off; 115 GiB GTT limit and 4 GiB firmware VRAM. Desktop remained running. TuneD accelerator-performance was active, with the previously documented swap/scheduler limitations. Pinned native W4B model plus quality overlay; 65,536 context/pool positions; MAX_TOK=16384; one slot; prompt cache mode 1.

Engine startup reported 68.0 GiB locked weights + 1.8 GiB KV + 12.2 GiB working memory = 82.0 GiB, leaving roughly 23.3 GiB for other uses then. The 47.7 GiB lookup table is demand-paged. Kernel MemAvailable overstates reclaimable headroom because it counts the pinned weights as file cache. Swap remained unused in all sampled checks.

Initial launch failed because the container lacked a named render group. The service now passes numeric host groups video=983 and render=987. Cleanup restored the desktop power profile after that failure, and the corrected launch succeeded.

## Artifacts and next steps

Each numbered JSON retains the request, response, and wall time. analysis.json contains the filtered summary. service.log records startup and request diagnostics. The wrapper completed 80 HTTP benchmark requests successfully.

Still untested: long-context generation, coding correctness, sustained interactive use, and causal benefit from IOMMU/TuneD (no before/after control). No comparison here is directly equivalent to the earlier Qwen3.8-27B article or the video's benchmarks.

Stop the model and restore desktop power management with:

```bash
/home/wowzontle/Work/Experiments/qwen38-flash-next/stop.sh
```
