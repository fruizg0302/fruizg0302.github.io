---
title: "Strix Halo, Part 5: Halogen and 64K Coding on 64 GB"
author: Fernando Ruiz
pubDatetime: 2026-09-28T22:30:00Z
slug: "strix-halo-halogen-27b-coding-follow-up"
featured: true
draft: false
tags:
  - llm
  - local-ai
  - amd
  - benchmarks
description: "Back on the 64 GB A14: Halogen, Qwen3.8-27B, executable coding checks, a working 64K prompt cache, and a precision test that gave me no reason to disable W4A4."
---

## TL;DR

On my 64 GB ASUS TUF Gaming A14, using Qwen3.8-27B through Halogen 0.1.4:

- **A 65,536-token slot worked for the tested coding tasks.** The native Halogen
  checkpoint occupies 33.40 GiB on disk. This is a different package and runtime
  from the 17.38 GiB GGUF in Part 3.
- **MTP won the deep-context drafter comparison; DFlash2 won the short one.**
  At 64,468 input tokens, MTP decoded about 23% faster on average. These were
  greedy tests, not a comparison under the sampled settings I now use.
- **Actual cache hits changed the waiting time.** A cold 64K coding request took
  162.38 seconds; its identical repeat took 11.56 seconds, reusing 63,488 tokens.
  A follow-up took 13.55 seconds. All three generated functions passed their tests.
- **I kept W4A4 enabled.** With sampled generation and medium reasoning, both
  precision settings passed all six answers. Disabling the prefill int4 path
  was slower in both long-context pairs, with substantial timing variation.
- **I fixed a local API boundary check.** The stock front-end admitted a prompt
  larger than the configured slot and the container stopped. The patched
  front-end rejects those requests with HTTP 400.

These are small, synthetic coding diagnostics. They do not establish that this
setup beats Coder-Next, runs a complete coding agent reliably, or matches the
Flash-Next results from the 128 GB machine.

## Back to the smaller laptop

In [Part 3](/posts/strix-halo-qwen38-mtp-follow-up/), Qwen3.8-27B fit a full native
context window on this A14 through LM Studio. Two-token MTP roughly doubled
short-context generation, but the near-full prompt took 46.5 minutes to read.
Coding quality remained an open question.

[Part 4](/posts/strix-halo-flash-next-quality-follow-up/) moved to a 128 GB
ProArt PX13, Flash-Next, and Halogen Flash Server. That experiment added
executable coding tests and caught an arithmetic parser that forgot to tokenize
multiplication. It also involved a different computer, model, and backend.

This time I returned to the **64 GB A14** with a narrower target: a working
**64K coding configuration**, using **Halogen's Qwen3.8-27B backend**. I wanted
to check correctness, cold-prompt latency, follow-up latency, and whether the
faster prefill arithmetic was costing me anything visible in the generated code.

| Component                            | This experiment, September 28, 2026         |
| ------------------------------------ | ------------------------------------------- |
| Laptop                               | ASUS TUF Gaming A14                         |
| Processor / GPU                      | Ryzen AI MAX+ 392 / Radeon 8060S, `gfx1151` |
| Installed unified memory             | 64 GB                                       |
| GTT ceiling / firmware-reserved VRAM | 56 GiB / 0.5 GiB                            |
| Backend                              | Halogen 0.1.4, rootless Podman 6.1.1        |
| Checkpoint                           | `qwen3.8-27b-p1w4d-d2.hgn`, 33.40 GiB       |
| Context / resident slots             | 65,536 tokens / 1                           |

The firmware reservation is smaller than the 4 GiB used in Part 3. The runtime,
checkpoint, prompts, and host configuration also differ. Putting the old and new
throughputs in a leaderboard would imply a controlled comparison I did not run.

This backend is [Halogen Server](https://github.com/peonist-ai/halogen-server),
not the separate Halogen Flash Server from Part 4. Its `.hgn` file is not a GGUF
that LM Studio can load. At the tested version, the inference engine is a
closed-source binary with public deployment and API code.

I pinned the image and model revision and verified the downloads. The checkpoint
is 35,865,565,184 bytes; all eight selected files total 33.424 GiB. The exact
image digest, model revision, and checkpoint checksum are in the
[measurement data](/data/halogen-qwen38-coding-2026-09-28.json).

## Host tuning was a starting condition

The laptop ran on AC power with the Performance profile, kernel
`7.2.5-3-omarchy-bore`, and these live boot parameters:

```text
amd_iommu=off amdgpu.gttsize=57344 ttm.pages_limit=14680064
```

The 56 GiB GTT figure is an on-demand ceiling within the installed RAM.
It is not another pool of physical memory, nor a reservation of all 56 GiB
at boot. Before loading, approximately 54 GiB of host memory was available,
swap was unused, and no LM Studio model was loaded.

On this A14, TuneD and tuned-ppd provide the desktop power profiles. Performance
maps to a local profile inheriting `accelerator-performance`, with the read-only
BORE scheduler setting skipped. This differs from Part 4's temporary TuneD
handoff on the PX13. I did not run IOMMU-on or TuneD-off controls, so neither
setting gets credit for a measured speedup here. The
[host configuration guide](https://strix-halo-toolboxes.com/#config) also notes
the IOMMU tradeoffs, including DMA isolation and NPU operation.

Only one large model was loaded at a time. That rule matters with this backend:
GTT counters omit part of the GPU-registered checkpoint, and Linux file-cache
accounting can make `MemAvailable` look more generous than the practical
headroom for another model.

## Correct output can still be poor code

The first suite used greedy generation and three Python workloads:

| Task                        | Checks per generated answer | What it exercised                                                          |
| --------------------------- | --------------------------: | -------------------------------------------------------------------------- |
| Dependency ordering         |                         505 | Determinism, duplicate edges, missing keys, cycles, input preservation     |
| Interval subtraction        |                       1,004 | Half-open ranges, merging, invalid ranges, negative endpoints              |
| Synthetic repository repair |                         507 | A ledger contract, a policy elsewhere in the context, and a buggy function |

The repository fixture placed the contract near the beginning, another policy
near the middle, and the repair request at the end of varied synthetic Python
files. The repaired function had to handle duplicate IDs, malformed records,
booleans, validation order, zero totals, and cross-account duplicates.

These case counts describe checks on the same generated function. They are not
hundreds of independent coding tasks. Generated code ran under restricted local
validation, with syntax/import checks and execution limits. Optional Markdown
fences were stripped for execution, so functional correctness and raw-output
format compliance were tracked separately.

The first dependency sorter passed its functional cases but scanned all nodes
at every step. On 6,000 independent nodes, its median CPU time was **2.495
seconds**. After I added an explicit complexity requirement and enabled low
reasoning, the answer used reverse adjacency and a heap, taking **0.00866
seconds** on that check.

Both the prompt and reasoning setting changed. This is evidence that the revised
request produced a better algorithm, not a measurement of reasoning's isolated
effect. It is also a useful reminder to test the properties that matter. A
function can return every expected answer and still be a bad fit for its workload.

## The fastest drafter depended on context

Halogen offers serial generation, MTP, and DFlash2. I compared the draft modes
on identical coding prompts with temperature zero and thinking off:

| Actual input tokens | DFlash2 decode, tok/s | MTP decode, tok/s |
| ------------------: | --------------------: | ----------------: |
|                 140 |          36.35, 42.28 |      31.70, 36.22 |
|              64,468 |        10.286, 10.383 |    12.761, 12.625 |

DFlash2 won the short prompt. MTP was about **23% faster on average** at the deep
prompt, so I selected MTP for this 64K experiment. A single short serial run
measured 10.09 tok/s. These numbers do not establish a universal drafter ranking.

The saved responses for each matched prompt contained identical source across
drafter variants. One deep MTP repeat has surviving server timings but no full
response: it was lost with the temporary container during the later boundary
probe. I include its timing above, not as another independently validated answer.

Cold deep prefill still took roughly **152 to 163 seconds**. Improving generation
did not remove the time spent reading new input. That made cache behavior the
next practical question.

## An enabled cache that stored nothing

I initially gave the prompt cache a **5,120 MiB budget**, keeping the default
**8,192 MiB reserve**. The server started, but `/cache` reported zero stores and
two refusals. Repeating the deep prompt still took **172.46 seconds**, with no
cached tokens.

With the same cache budget and a **4,096 MiB reserve**, it stored a **4.26 GiB
snapshot** and reported real hits. The measured sequence was:

| Request                      | Input tokens | Output tokens | Cached tokens |  Prefill | Total request |
| ---------------------------- | -----------: | ------------: | ------------: | -------: | ------------: |
| Cold repair                  |       64,468 |           170 |             0 | 153.52 s |      162.38 s |
| Identical repeat             |       64,468 |           170 |        63,488 |   3.53 s |       11.56 s |
| Follow-up adding a docstring |       64,675 |           190 |        63,488 |   4.04 s |       13.55 s |

![Greedy, thinking-off coding requests: the cold request took 162.38 seconds, its cached repeat 11.56 seconds, and a cached follow-up 13.55 seconds. Prefill accounts for most of the cold request.](/images/strix-halo-halogen-27b-cache.svg)

The identical repeat was about **14 times faster end to end**, with byte-identical
source. All three functions passed 507 checks each. The follow-up occupied
64,865 tokens including its answer, within the 65,536-token slot.

This was one sequential synthetic conversation with short answers, using greedy
generation and thinking off. **It is not the measured latency of the sampled,
medium-reasoning preset below.** Competing conversations can evict snapshots,
and changing the shared prefix can reduce reuse. I left cache alignment at the
documented default of 2,048 tokens.

## Testing the boundary found an API defect

The slot had room for 65,536 tokens, but the stock API's admission checks and
health response used the model's native 262,144-token context. A deliberate
**66,008-token prompt** reached the engine, produced an out-of-range prefill
message, returned HTTP 502, and stopped the container. No kernel OOM, GPU reset,
or coredump was found for that event.

I patched the local front-end so both admission checks and `/health.context`
use the smaller of native context and slot capacity. The launcher mounts that
API file read-only; the engine binary and model arithmetic are unchanged.
Integration checks then confirmed HTTP 400 for an oversized chat prompt, an
oversized prompt-plus-output budget, and an oversized completions prompt.
The server stayed healthy.

That override is tied to the pinned 0.1.4 image and needs review when upgrading.
The original over-limit failure also belongs in the stability report. Calling
the whole unpatched session error-free would erase the most useful boundary test.

## Sampling recommendations changed the daily preset

Greedy generation made the earlier comparisons easier to interpret. For actual
coding use, I then checked the
[Qwen model card](https://huggingface.co/Qwen/Qwen3.8-27B#api-usage) and adopted
its thinking-mode sampling settings, with **medium reasoning**:

```json
{
  "model": "halogen-qwen3.8-27b-64k",
  "drafter": "mtp",
  "temperature": 1.0,
  "top_p": 0.95,
  "top_k": 20,
  "min_p": 0.0,
  "presence_penalty": 0.0,
  "reasoning_effort": "medium",
  "preserve_thinking": true,
  "max_completion_tokens": 8192
}
```

These are request fields to merge with the actual `messages` and optional
`tools`. I also made the sampling and reasoning values local chat API defaults;
explicit client values override them. There is no fixed seed on ordinary
requests. Raw completions retain their upstream defaults.

The installed API does not declare `repetition_penalty`, so I omitted Qwen's
no-op value of 1. Preserving thinking also requires the client to send prior
assistant `reasoning_content` back. A flag cannot restore discarded history.

**64K includes the prompt, reasoning, and final answer.** A 57,344-token prompt
leaves 8,192 tokens for generation; a 64,468-token prompt leaves only 1,068.
Templates, tool definitions, and retained reasoning all count toward the input.
The server's 16,384-token output ceiling does not create extra context space.

Medium is a chosen starting point, not a demonstrated optimum. I have not run
a matched low-versus-medium coding comparison or repeated the DFlash2/MTP
comparison under sampling.

## Did higher-precision prefill improve the code?

The image ships with `HALOGEN_W4A4=64` and no excluded weight planes. The value
64 is the minimum row count for its int4 prefill path, not a bit width or context
size. The [precision flags](https://github.com/peonist-ai/halogen-server/blob/main/docs/FLAGS.md#precision)
document `HALOGEN_W4A4=0` as a way to disable that path for higher-precision
prefill. It does **not** convert the checkpoint to BF16 or change the decode
kernel's precision.

I tested those two settings in **ABBA order**, with a fresh model load for each
leg. A1/B1 used seed 42; B2/A2 used seed 73. Every leg ran dependency ordering,
interval subtraction, and the synthetic repository repair with the new sampled
medium defaults, MTP, and an 8,192-token output allowance.

For this experiment, the long prompt was **57,281 tokens**. I removed only whole,
unrelated metric files from the earlier fixture, preserving the contract, policy,
and bug. That left room for the full reasoning-and-answer allowance inside 64K.
The prompt cache was disabled in all four legs to isolate cold prefill. Normal
launcher cache settings remained intact.

| Prefill setting    | Functional answers | Raw-format answers | Deep prefill, seconds |
| ------------------ | -----------------: | -----------------: | --------------------- |
| W4A4 enabled, `64` |                6/6 |                5/6 | 154.47, 209.57        |
| W4A4 disabled, `0` |                6/6 |                5/6 | 255.86, 229.54        |

All twelve answers passed their functional checks and stopped normally. None
exhausted the output budget. One interval answer per precision setting included
Markdown fences despite the raw-source request. All four dependency sorters
used efficient algorithms, taking approximately 4 to 7 milliseconds of CPU time
on the 6,000-independent-node check.

![Cold prefill measurements in execution order: A1 with W4A4 enabled took 154.47 seconds; B1 disabled took 255.86; B2 disabled took 229.54; A2 enabled took 209.57. All used 57,281 input tokens and no prompt cache.](/images/strix-halo-halogen-27b-precision.svg)

Mean deep prefill was **182.02 seconds enabled** and **242.70 seconds disabled**,
an observed increase of **33.3%**. That percentage is approximate evidence, not
a stable performance estimate: the two enabled runs themselves differed by
35.7%. The paired penalties were 65.6% and 9.5%. Two observations per setting
with that much drift cannot support a precise universal speed claim.

I kept **W4A4 enabled**. Disabling it showed no functional or formatting advantage
on this suite and took longer in both paired deep requests. The sample is too
small and narrow to establish equivalent quality on harder coding tasks.

Sampled output lengths also changed. The long requests generated 870 to 1,197
tokens including reasoning, with decode rates from 9.57 to 12.80 tok/s.
Those differences do not isolate prefill arithmetic's effect on generation.
Even the short interval task took **135.23 seconds** in one enabled run and
**259.80 seconds** in the other, producing 3,925 and 5,146 tokens respectively.
Both answers were correct. Medium reasoning can spend real time on a small task.

## What I kept, and what remains open

The normal server configuration now uses:

```text
HALOGEN_KV_SLOTS=1
HALOGEN_SLOT_CTX=65536
HALOGEN_DRAFTER=1
HALOGEN_CACHE_MB=5120
HALOGEN_CACHE_RESERVE_MB=4096
HALOGEN_MAX_TOKENS_CAP=16384
HALOGEN_QUEUE_TIMEOUT=2400
```

W4A4 and cache alignment retain the image defaults. The local API adds the
context guard and sampled medium chat defaults. The launcher exposes only
`127.0.0.1:8731`, mounts the weights read-only, checks for a loaded LM Studio
model, and requires 53 GiB of available host RAM plus low existing GTT use
before starting. Those startup checks do not measure safe concurrency with
another large model.

In the earlier coding/cache session, minimum sampled free RAM was **6.36 GiB**
and swap stayed unused. In the separate, roughly 38-minute precision experiment
with the cache disabled, minimum free RAM was **10.33 GiB**, swap remained zero,
and the highest sampled temperature was **97°C**. The recorded journals showed
no GPU reset or OOM. Power and temperature readings did not establish the cause
of the prefill timing drift. The test containers were removed afterward.

A forced `read_file` tool call and a supplied synthetic tool-result turn also
worked. That checks one API round trip, not filesystem access or an autonomous
coding session. Streaming, real repository changes, sampled warm-cache behavior,
and sustained agent loops remain untested.

**Coder-Next remains my established coding default in LM Studio.** I have not
run a head-to-head quality or performance comparison against this Halogen setup.
What I now have is a second, tested configuration: deep-context function repairs
that passed executable checks, a cache whose hits were measured, and no local
evidence to justify paying for higher-precision prefill on these tasks.

The next useful test is an actual repository change, with its existing tests,
tool history, and review. For that workflow, the interesting number will be the
time to a correct patch, including retries and reasoning. This round already
shows why: 64K can mean a cold wait of several minutes or a short cached follow-up,
and passing examples can still conceal a quadratic algorithm.

The [downloadable measurement summary](/data/halogen-qwen38-coding-2026-09-28.json)
contains the plotted timings, all twelve precision outcomes, configuration
provenance, and test limitations. It is a curated numeric summary, not a full
benchmark reproduction bundle. The
[plotting script](https://github.com/fruizg0302/fruizg0302.github.io/blob/master/scripts/plot-halogen-qwen38.py)
rebuilds both figures from it.
