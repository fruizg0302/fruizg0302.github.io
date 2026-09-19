---
title: "Strix Halo Follow-Up: Faster Prompts, Smaller Caches, and 225K Context"
author: Fernando Ruiz
pubDatetime: 2026-09-19T22:00:00Z
modDatetime: 2026-09-19T23:22:51Z
slug: "strix-halo-llm-tuning-follow-up"
featured: true
draft: false
tags:
  - llm
  - local-ai
  - amd
  - benchmarks
description: "15 runs and 64 measurements later: q8_0 nearly doubles 30B prefill at 74K, Laguna gets a useful batch-size upgrade, and Coder-Next reaches 225K with a very long wait."
---

In [the previous post](/posts/your-laptop-is-bandwidth-bound-not-capacity-bound/),
I found that fitting a model into this laptop's memory was the easy part. Getting
through a large prompt in a reasonable amount of time was harder. Qwen3-Coder-Next
beat the smaller 30B model at depth, and prompt processing mattered much more than
the generation speed quoted for an almost empty context window.

I went back and tested the settings I had left as hypotheses: quantizing the KV
cache, increasing physical batch sizes, and actually filling more of the large
context window. After **15 runs and 64 depth measurements**, two changes earned a
place in my configuration:

- **30B with q8_0 KV:** almost twice the prompt throughput at 74K, 24% faster
  generation, and 5.6 GiB less GTT usage.
- **Laguna with physical batch 512:** 26–31% faster prompt processing at 40–81K,
  with essentially unchanged generation speed.

Coder-Next was less decisive. Its larger batches did too little to keep, and its
q8_0 result landed almost exactly on my adoption threshold. It also completed a
225K-token prompt. That last result needs a stopwatch alongside the memory figure.

## What I measured this time

Same ASUS TUF Gaming A14, Radeon 8060S / `gfx1151`, 64 GB unified memory, and 56 GiB
GTT ceiling. This run used AC power and the performance profile, Arch/Omarchy,
kernel `7.2.5-3-omarchy`, Mesa `26.2.2-1`, LM Studio `0.4.24-2`, and its Vulkan
llama.cpp runtime `2.41.0`.

The weight files stayed fixed:

| Model                        | Unsloth GGUF |
| ---------------------------- | ------------ |
| Qwen3-Coder-30B-A3B-Instruct | `UD-Q6_K_XL` |
| Qwen3-Coder-Next             | `UD-IQ4_XS`  |
| Laguna S 2.1                 | `UD-Q2_K_XL` |

**q8_0 below means the K and V cache format.** I did not replace the model weights
with a different quantization.

Each run started with a fresh model load, a ten-second settling period, and prompts
in increasing depth order. Models were unloaded between runs, with 150 seconds of
cooling before the next. Requests were sequential, even when a model was configured
with multiple parallel slots.

I measured prompt processing (**prefill**) and token generation (**decode**) from
the server's timing logs. These replace the client-side timing method in the first
post. The synthetic code filler used seed 7; requests used temperature 0.7 and an
output limit of 300 tokens, with generation seed unfixed. Two outputs ended a little
early; rates use the actual token counts.

Each model's baseline was measured twice. I compared variants with that mean and
treated differences below the larger of **5% or the baseline spread** as noise.
That is a practical selection rule, not a statistical confidence interval. Most
variants had one pass; the borderline Coder-Next cache setting received a repeat.

Nearly the entire prompt was evaluated at every point. The 30B reused a 20-token
prefix after the first depth, at most 0.22% of a prompt. Everything here therefore
describes processing a substantially new prompt. It does not measure the benefit
of reusing a large cached conversation prefix.

That also corrects my earlier wording about paying the full prefill cost "every
turn." These measurements establish the cost when the prompt must be evaluated;
they do not establish how much work a particular coding client and server can reuse.

The percentages below compare fresh baselines and variants from **this session**.
Comparing them directly with September 11 would mix the tuning changes with
differences in measurement method and configuration.

## 30B: the cache change was worth keeping

The cleanest result was Qwen3-Coder-30B. Switching both K and V from f16 to q8_0
reduced load GTT from **37.28 to 31.66 GiB**. Peak usage in the q8_0 run was 31.86 GiB.

Throughputs below are tokens per second. Baseline columns are the two-run means.

| Actual tokens | f16 prefill | q8 prefill | f16 decode | q8 decode |
| ------------: | ----------: | ---------: | ---------: | --------: |
|         1,197 |       832.7 |      878.1 |       60.6 |      60.6 |
|         9,250 |       740.1 |      802.1 |       47.4 |      48.9 |
|        37,171 |       313.4 |      419.7 |       29.0 |      34.4 |
|        74,385 |       124.7 |  **247.1** |       19.5 |  **24.2** |

At 74K, prefill improved **98.2%** and decode improved **24.0%**. Prompt processing
fell from about ten minutes to five. That still feels long at a keyboard, but it is
a substantial improvement from one setting that also frees memory.

The gain grows with context depth. Short-prompt generation is essentially
unchanged. This is why testing the cache setting only on a small prompt would have
missed its value.

I kept q8_0, flash attention, batch 2048 / physical batch 512, a 131,072-token
configured window, and one slot. The deepest prompt tested for this model was 74K;
the configured window is larger than the workload validated here.

## The crossover is a band, not a magic token count

The faster 30B made it worth checking where Coder-Next takes over. I added two
matched depths with the selected configurations, 30B q8_0 and Next f16.

![Prompt and generation throughput for 30B f16, 30B q8_0, and Coder-Next f16. The selected models are close at 18.5K tokens; Next pulls ahead as context grows.](/images/strix-halo-follow-up-throughput.svg)

The baseline points in the chart are two-run means, with whiskers showing the
observed range. The q8_0 series and added midpoint checks are single measurements.
Lines connect measured points; they are not a fitted model.

| Actual tokens | 30B prefill | Next prefill | 30B decode | Next decode |
| ------------: | ----------: | -----------: | ---------: | ----------: |
|        18,542 |       622.3 |        631.9 |       42.7 |        41.8 |
|        27,853 |       498.2 |    **593.5** |       38.0 |        38.8 |

At 18.5K, both metrics are within 5%. At 27.9K, Next processes the prompt **19.1%
faster**, while generation still ties by that rule. By 37K, Next clearly leads in
both, and its lead grows at 74K.

My practical choice is now 30B for short prompts, a **20–30K transition band**, and
Next around 28K or deeper when feeding it substantial new context. The old rough
20K switching heuristic was useful; the measurements do not support an exact
cutoff. This is a speed comparison, not a ranking of coding ability.

## Coder-Next: a borderline cache result, and no batch upgrade

For Next, my predeclared rule required at least an 8% decode improvement at 74K,
without a prefill regression greater than 5% at any shared depth.

After two q8_0 measurements, the 74K decode mean went from **31.62 to 34.12 tok/s**:
**7.89% faster**. Prefill fell 2.35% there, and the largest shared-depth prefill
regression was 4.38%. It met the prefill condition and narrowly missed the decode
condition, so I retained f16.

The difference between 7.89% and 8% has no special physical meaning. It is a
threshold decision, and a sensitive one. A later f16 confirmation measured
30.88 tok/s at 74K, which would shift the comparison if folded into the baseline.
I kept that confirmation separate from the original two-baseline/two-variant
selection and retained all measurements in the data.

There are good reasons to revisit q8_0 for a workload dominated by long-context
generation: it saved roughly **2.8 GiB**, and the single 149K measurement generated
at **29.35 tok/s versus the f16 baseline mean of 24.57**, a 19.4% improvement.
I did not repeat q8_0 at that depth or extend it to 225K. Calling it a failed
optimization would overstate the evidence.

Increasing physical batch size was less interesting. With q8_0 held constant,
physical batches of 1024 and 2048 both completed 149K without GPU errors. Neither
met the required 10% deep-prefill improvement over physical batch 512. The 1024
setting gained about 9%, 8%, and 2% at 37K, 74K, and 149K; 2048 gained about 2% at
each. More memory for little consistent benefit.

Next therefore stays on **f16 KV, batch 2048 / physical batch 512, four slots,
and a 262,144-token configured window**.

## Laguna: physical batch 512 works in this configuration

The first article included a Laguna GPU hang with f16 KV, logical batch 2048,
physical batch 512, and four slots on an older runtime. My working fallback used
q8_0, logical batch 512, physical batch 256, and two slots.

This time I kept that fallback's other settings and changed only physical batch
from 256 to 512.

| Actual tokens | 256 prefill | 512 prefill |        Gain | 512 decode |
| ------------: | ----------: | ----------: | ----------: | ---------: |
|         1,334 |       261.8 |       343.2 |       31.1% |       39.7 |
|        10,118 |       288.8 |       392.9 |       36.0% |       37.9 |
|        40,535 |       251.1 |       329.5 |   **31.2%** |       32.1 |
|        81,068 |       210.1 |       264.3 |   **25.8%** |       27.0 |
|       121,704 |    untested |       226.5 | no baseline |       23.0 |

Generation differences at the shared depths stayed below 5%. The benefit is faster
prompt ingestion. Load GTT increased only from **44.28 to 44.62 GiB**, and the
deepest run peaked at **45.12 GiB**.

That is enough to adopt physical batch 512 with **q8_0, logical batch 512, two
slots, and runtime 2.41.0**. It does not prove the old crashing combination is safe,
or isolate which difference prevented the old crash.

Laguna tokenizes this synthetic prompt differently from the Qwen models, which is
why its actual token counts differ. These comparisons stay within Laguna. Although
thinking was enabled, all its responses reported zero reasoning tokens, so this
does not establish performance on extended reasoning workloads.

## 225K fits. Reading it takes 17.6 minutes.

The selected Coder-Next configuration completed a prompt containing **224,842
actual tokens**. Prefill was **213.21 tok/s**, generation was **20.12 tok/s**, and
peak GTT was **43.15 GiB**. No GPU kernel errors were observed.

The server spent **1,054.5 seconds**, or **17.6 minutes**, processing that prompt
before generation. The following 300 tokens took about 15 seconds.

In the first article I described doubling the configured window as costing memory
and "nothing else," based on a shallow-prompt comparison. That needs a narrower
claim: reserving a larger window did not meaningfully change shallow decode in
that test. **Filling the window has a substantial cost.** The new 225K measurement
puts a number on it.

A short client timeout can end such a request before the model starts answering.
For my workload, trimming the new context sent on a turn remains valuable even
when the full prompt fits comfortably in memory.

## TL;DR: recommended configurations for programmers

For programming on this 64 GB Strix Halo laptop, I would start with **30B for
focused edits, small code questions, and short prompts**. Use **Coder-Next for
larger repository context**, especially around 28K tokens and deeper when sending
substantial new code. Around 18.5K they effectively tie; treat **20–30K as a
transition band**, with the choice depending on how much new context each turn
needs to process.

These are the presets I would keep in LM Studio. Batch sizes below are logical /
physical, and the context column is the configured window, not the deepest prompt
tested.

| Model      | K/V cache | Logical / physical batch | Configured tokens / slots |
| ---------- | --------- | ------------------------ | ------------------------- |
| 30B        | q8_0      | 2048 / 512               | 131,072 / 1               |
| Coder-Next | f16       | 2048 / 512               | 262,144 / 4               |
| Laguna     | q8_0      | 512 / 512                | 262,144 / 2               |

The weight quants remain **UD-Q6_K_XL for 30B, UD-IQ4_XS for Coder-Next, and
UD-Q2_K_XL for Laguna**. The cache column refers only to K and V. Use the Laguna
preset if Laguna already suits your coding workflow: increasing physical batch to
512 makes large prompts faster to ingest. These tests do not rank the models'
coding ability.

For planning memory and waiting time:

- **30B:** about **31.9 GiB peak GTT**, tested through **74K**. The clearest tuning
  win was q8_0: nearly twice the prefill throughput and 24% faster generation at
  that depth.
- **Coder-Next:** about **43.2 GiB peak GTT**, tested through **225K**. Keep f16 as
  the selected default; q8_0 remains a candidate for workloads dominated by
  long-context generation. Do not expect interactive turnaround when ingesting
  225K new tokens: prefill alone took **17.6 minutes**.
- **Laguna:** about **45.1 GiB peak GTT**, tested through **122K**. Keep q8_0 and
  batch 512 / 512 with two slots; the measured gain is faster prompt processing,
  with generation speed essentially unchanged.

For a coding assistant, send the files and excerpts needed for the current task,
preserve reusable prompt prefixes where your client supports it, and allow enough
request time for large uncached prompts. The largest available context window
does not need to become the default amount of code sent on every turn.

All three use Vulkan and flash attention. After the benchmarks, I also made
Coder-Next's sampling defaults explicit: top_p 0.95, top_k 40, repetition penalty
disabled. Those changes were applied afterward, so they did not contribute to the
reported tuning gains.

Across the matrix, no GPU timeouts, resets, or device-loss errors were observed.
GTT was sampled every two seconds, with a 50 GiB stop condition; the highest sample
was 45.12 GiB. This is evidence for the tested workloads and configurations, not a
guarantee for every prompt or concurrent load. I did not benchmark a third-party
fork, rerun ROCm, or evaluate answer quality and long-context recall.

The first post's practical lesson still holds: a large memory ceiling tells you
what can load, while prompt depth tells you whether you will enjoy using it. This
round adds two settings worth keeping, a better model-switching rule, and an actual
measurement of how long an enormous context takes to read.

The [complete measurement data](/data/strix-halo-perf-2026-09-19.json) includes all
15 runs and 64 points, server token counts and timings, memory measurements, and
the tested variants. The
[chart script](https://github.com/fruizg0302/fruizg0302.github.io/blob/master/scripts/plot-strix-halo-followup.py)
rebuilds the figure from that data.

### AI usage disclosure

_Codex GPT-6 Astra conducted the benchmark tests on my laptop, collected and
analyzed the results, and helped me write and edit this post._
