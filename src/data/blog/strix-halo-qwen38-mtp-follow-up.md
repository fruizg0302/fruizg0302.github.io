---
title: "Strix Halo, Part 3: Qwen3.8-27B, MTP, and a 47-Minute Prompt"
author: Fernando Ruiz
pubDatetime: 2026-09-22T01:25:00Z
modDatetime: 2026-09-22T02:01:20Z
slug: "strix-halo-qwen38-mtp-follow-up"
featured: true
draft: false
tags:
  - llm
  - local-ai
  - amd
  - benchmarks
description: "Qwen3.8-27B fits an 18 GiB weight budget, and two-token MTP roughly doubles short-context generation. A 247K prompt still takes 46.5 minutes to read."
---

In [the last round](/posts/strix-halo-llm-tuning-follow-up/), smaller KV caches
and a batch-size change made two of my existing models faster. This time I added
a new model and a different way to accelerate generation: **Qwen3.8-27B with
multi-token prediction, or MTP**.

The question was specific: could I keep the weight file below **18 GiB**, allocate
the entire native **262,144-token window** with Q8_0 attention caches, and make
MTP work on this laptop's Vulkan runtime?

Yes. The selected file is **17.38 GiB**, and two-token MTP took short-context
generation from **11.29 to 23.36 tokens per second**. A prompt containing
**246,678 tokens** also completed, with peak sampled GTT usage of **26.94 GiB**.

Then there is the waiting: that enormous prompt took **46.5 minutes to process**
before generation. The memory budget worked. The stopwatch still matters.

## The model and the memory budget

I used [Unsloth's Qwen3.8-27B GGUF](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF),
specifically `Qwen3.8-27B-UD-Q5_K_S.gguf`. The complete file is 18,665,753,504 bytes,
including its bundled MTP head. I verified the downloaded file's SHA-256 against
the publisher's checksum. The next `UD-Q5_K_M` file was 18.41 GiB, just outside
my chosen weight budget.

[Qwen describes this as a dense 27B model](https://huggingface.co/Qwen/Qwen3.8-27B),
with a hybrid layout: 48 Gated DeltaNet layers and 16 full-attention layers.
Its native context is 262,144 tokens. The advertised extension to one million
tokens is a separate experiment; I did not test it.

The hybrid layout matters for memory accounting. The ordinary attention cache
belongs to those 16 attention layers. At the full native window, its calculated
Q8_0 allocation is **8.5 GiB**. The bundled MTP head adds another attention layer
and **0.53125 GiB** of Q8_0 cache.

| Component                                |        Budget |
| ---------------------------------------- | ------------: |
| Complete GGUF file, including MTP head   |     17.38 GiB |
| Main attention K/V, 262,144 tokens, Q8_0 |      8.50 GiB |
| MTP attention K/V, same window, Q8_0     |      0.53 GiB |
| Calculated subtotal                      | **26.42 GiB** |

For the main cache, the calculation is `2 × 16 × 4 × 256 × (34/32)` bytes per
token: K and V, attention layers, KV heads, head dimension, and Q8_0 storage
including scales. That is 34 KiB per token, multiplied by 262,144 tokens.

This subtotal combines file size with calculated cache storage. Runtime buffers,
recurrent state, and checkpoint storage still need room. The recurrent state
remains floating point in this build. **Q8_0 K/V does not mean every piece of
model state becomes eight-bit.**

There is also an easy configuration trap: the MTP attention cache has its own
settings. Setting the main K and V caches to Q8_0 did not set the draft caches.
I explicitly configured both draft cache types as Q8_0; their default in this
runtime was f16.

## What changed in the test setup

Same ASUS TUF Gaming A14: Ryzen AI MAX+ 392, Radeon 8060S / `gfx1151`, 64 GB unified
memory, a 56 GiB GTT ceiling, and 4 GiB reserved VRAM. GTT uses system RAM; it is
not another 56 GiB of physical memory on top of the installed 64 GB.

This September 21 session used AC power, the performance profile, kernel
`7.2.5-3-omarchy-bore`, Mesa `26.2.2-1`, LM Studio `0.4.24-2`, and Vulkan runtime
**2.42.0**, with server commit `c21284c`. The previous article used runtime 2.41.0.
I did not rerun the older models, so this is not a controlled comparison against
their published speeds.

Every depth started with a fresh model load. All points allocated the full
262,144-token window, with one slot, full GPU offload, flash attention, Q8_0 main
and draft caches, and logical / physical batches of 512 / 512. I allowed 150
seconds of cooling between variants and kept only one model loaded.

The workload was synthetic JavaScript filler with seed 7, followed by a
300-token completion. **Thinking was off and sampling was greedy** throughout
the performance comparison. Timings came from the server logs. These settings
help control the comparison; they are not a recommendation for everyday sampling.

I measured two MTP-off baselines at short and roughly 10K context, tried maximum
draft lengths of one, two, and three, then repeated two-token MTP and tested
deeper prompts. Baseline decode varied by about 6%; prefill varied more. As
before, I treated differences below the larger of 5% or the repeated-baseline
spread as noise.

## Two draft tokens were worth keeping

MTP uses a prediction head bundled with this model to propose upcoming tokens,
which the main model verifies. It can accept several tokens in a verification
step. This GGUF did not need a separate draft model download.

Here is the initial draft-length comparison. All rates are generated tokens per
second; the baseline column uses the **faster of the two baseline measurements**.

| Actual prompt tokens | MTP off | MTP 1 |     MTP 2 | MTP 3 |
| -------------------: | ------: | ----: | --------: | ----: |
|                1,316 |   11.29 | 18.88 | **23.04** | 22.44 |
|               10,173 |   11.09 | 18.11 | **21.77** | 20.98 |

One draft token already helped substantially. Two helped more. Three did not
improve on two within the observed noise, so I kept **a maximum of two draft
tokens**. That selects among the settings tested on this workload; it does not
establish a universal optimum for every prompt.

Acceptance rate alone would have picked the wrong setting. At 10K, one-token
MTP accepted **88.1%** of proposed tokens, while two-token MTP accepted **78.4%**.
Despite its lower percentage, two-token MTP produced more output per second.
Drafting and verification costs matter alongside the fraction accepted.

The repeat confirmed the result: **23.36 tok/s** at 1,316 input tokens and
**21.80 tok/s** at 10,173. Those were within 1.4% and 0.2% of the first two-token
measurements.

![Qwen3.8-27B generation throughput with MTP off and two-token MTP at 1,316, 10,173, and 40,847 prompt tokens. Two-token MTP also reaches 9.18 tokens per second at 246,678 tokens, where MTP off was not tested.](/images/strix-halo-qwen38-mtp.svg)

The chart uses the faster baseline at the first two depths and the two-token
confirmation run. Whiskers show the observed repeat ranges at those depths, not
confidence intervals. The deeper points are single measurements.

At **40,847 input tokens**, decode improved from **10.39 to 19.11 tok/s**, an
**84% gain**. Baseline and MTP produced byte-identical output there. At 10K, some
MTP runs changed the wording of the final code comments, so I am not claiming
bit-for-bit equivalence across the matrix.

## Faster generation barely changed the cold 40K request

This was the most useful qualification in the results. At 40K, the server spent
most of its time processing the incoming prompt:

| Stage               |     MTP off |       MTP 2 |
| ------------------- | ----------: | ----------: |
| Prefill             |     170.1 s |     178.8 s |
| Generate 300 tokens |      28.8 s |      15.6 s |
| Total               | **198.9 s** | **194.5 s** |

Generation became much faster, but total request time fell only about **2.2%**,
well inside the noise rule. Prefill throughput was 4.9% lower in this single
comparison. I would not call that a demonstrated prefill regression, nor claim
a meaningful improvement in total cold-request time at this depth.

The measured MTP win is in **decode**. A workload that spends more of its time
generating could benefit more overall, but I did not measure long completions
or conversations that reuse substantial cached prefixes.

## 246,678 tokens: plenty of memory, 46.5 minutes of prefill

The longest request filled **94.1% of the native window with input**, then
generated another 300 tokens. The configured window was fully allocated in all
runs; this one tested near-full occupancy, not exactly 262,144 occupied tokens.

| Measurement                           |     Two-token MTP |
| ------------------------------------- | ----------------: |
| Input tokens                          |           246,678 |
| Prefill throughput                    |       88.38 tok/s |
| Prefill time                          | **46.52 minutes** |
| Decode throughput                     |        9.18 tok/s |
| Time for 300 output tokens            |     32.56 seconds |
| Total server request time             | **47.06 minutes** |
| Peak sampled GTT                      |     **26.94 GiB** |
| Peak sampled GTT + reserved VRAM use  |     **30.77 GiB** |
| Minimum sampled host memory available |     **22.79 GiB** |

The combined GPU-memory measurement includes the desktop and other GPU clients.
It is not an isolated model allocation, and GTT alone omits the reserved VRAM
pool. Both are more useful than describing a 17.38 GiB file as the model's entire
runtime footprint.

I did not run an MTP-off baseline at this depth. **9.18 tok/s is a measured
throughput, with no measured speedup ratio at 247K.**

The laptop was thoroughly warm: a spot check during the long prefill showed
95.2°C CPU Tctl, 95.0°C GPU edge, and about 85 W PPT. Performance mode remained
enabled. Those readings describe the conditions; one snapshot cannot establish
whether thermal throttling occurred over the run.

No GPU compute timeouts, resets, device-loss errors, or OOM kills were observed.
The kernel did log a DisplayPort DPCD read warning that had also occurred several
times before testing. I cannot call the entire journal warning-free or attribute
that warning to inference. Swap usage also ended at 164 MiB, up from zero; I did
not collect enough information to assign it to a particular process.

The long request completed, and the following short sanity check passed. That
establishes inference at this depth on this configuration. It says nothing yet
about retrieving the right detail from a quarter-million-token prompt.

## One thinking-control mistake, caught before comparison

My first baseline request supplied `chat_template_kwargs.enable_thinking=false`
through the OpenAI-compatible endpoint. It still produced 300 reasoning tokens
and no answer text. I excluded that run and switched to the installed LM Studio
SDK's explicit `enableThinking: false` prediction setting.

That worked. Checking the actual response mattered more than trusting that the
request field had taken effect on this stack.

After saving the selected load settings, I also checked thinking-on operation
with a short prompt and a 128-token reasoning budget. The model emitted reasoning
and the correct JSON answer with MTP enabled. The arithmetic, sorting, and
JavaScript mutation checks passed in non-thinking mode too.

These are operational sanity checks. The timed code completions stop at 300
tokens, and the short checks do not establish coding quality, long-context recall,
or sustained reasoning performance.

## The configuration I kept

For this GGUF on the tested Vulkan runtime:

| Setting                               | Saved value                 |
| ------------------------------------- | --------------------------- |
| Context / parallel slots              | 262,144 / 1                 |
| Main K and V cache                    | Q8_0 / Q8_0                 |
| MTP K and V cache                     | Q8_0 / Q8_0, explicitly set |
| GPU offload / flash attention         | Full / on                   |
| Logical / physical batch              | 512 / 512                   |
| Context checkpoints                   | 32                          |
| MTP maximum / minimum draft tokens    | 2 / 1                       |
| Draft continuation probability cutoff | 0                           |
| Separate draft model                  | None                        |

In LM Studio, the two draft-cache argument overrides were:

```text
--spec-draft-type-k q8_0
--spec-draft-type-v q8_0
```

I saved these settings only for Qwen3.8-27B and verified a fresh load with no
explicit load configuration supplied. The running server's arguments confirmed
the context, caches, batch sizes, and MTP settings. That verification generated
at **23.33 tok/s** on the short benchmark. Sampling and thinking defaults were
left unchanged; the benchmark controls applied only to its requests.

The [saved LM Studio load configuration](/data/qwen38-27b-q8-mtp2.json) records the
exact settings for this installation. Its internal configuration keys and runtime
flags are version-specific.

My existing 30B, Coder-Next, and Laguna presets remain as they were. Qwen3.8-27B
now has a measured configuration of its own, and **two-token MTP earns its place
in it**. Deciding whether it earns a place in my coding workflow needs task-quality
tests. Vision, other weight quantizations, larger batches, and the extended
context window remain untested too.

For now, I have the answer to the capacity and runtime questions: weights below
18 GiB, full native Q8_0 attention caches, working MTP, and roughly twice the
short-context generation speed. I also have another reason to keep new context
focused. Waiting 47 minutes for 300 output tokens is a successful capacity test
and a poor interactive loop.

The [measurement data](/data/qwen38-27b-perf-2026-09-21.json) includes every timed
point, the excluded initial control, the saved-settings verification, draft
acceptance counts, and sampled memory summaries. The
[chart script](https://github.com/fruizg0302/fruizg0302.github.io/blob/master/scripts/plot-qwen38-mtp.py)
rebuilds the figure from that data.

## Further viewing

For more on the model and serving it, see Sam Witteveen's
[Qwen3.8-27B & How to Serve it Fast](https://youtu.be/PTuGGdDuyPI).

### AI usage disclosure

_Codex conducted the benchmark tests on my laptop, collected and analyzed the
results, and helped me write and edit this post and create its chart._
