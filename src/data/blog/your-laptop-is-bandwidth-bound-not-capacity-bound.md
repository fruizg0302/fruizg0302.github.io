---
title: "Your Laptop Is Bandwidth-Bound, Not Capacity-Bound"
author: Fernando Ruiz
pubDatetime: 2026-09-11T00:00:00Z
slug: "your-laptop-is-bandwidth-bound-not-capacity-bound"
featured: false
draft: false
tags:
  - llm
  - local-ai
  - amd
  - benchmarks
description: "What 56 GB of unified memory on a Strix Halo laptop actually buys you for local LLM inference — and why prefill, not decode, is the number that matters."
---

I spent a couple of days benchmarking local LLM inference on an ASUS TUF Gaming A14
(Ryzen AI MAX+ 392, Radeon 8060S / `gfx1151`, 64 GB unified memory, Arch + Omarchy 4).
The headline result is not a number, it's a correction: on a unified-memory laptop, the
interesting constraint is memory *bandwidth*, and the second most interesting one is how
your model's attention scales with context depth. Total RAM barely enters into it.

## Raising the GTT ceiling

On an APU there is no VRAM to speak of — the BIOS UMA frame buffer is 512 MB and should
stay there. What the GPU actually allocates from is GTT, and the kernel caps GTT at half
of system RAM by default (~31 GB here). Two kernel parameters raise it:

| Parameter | Value | Meaning |
|---|---|---|
| `amdgpu.gttsize` | `57344` | 56 GB, in MiB |
| `ttm.pages_limit` | `14680064` | 56 GiB ÷ 4 KiB pages |

GTT is a ceiling on on-demand allocation, not a reservation, so it costs nothing until
used. After a reboot, `mem_info_gtt_total` reads 56.00 GB and Ollama logs
`total="56.0 GiB"` on ROCm.

Mind the failure mode: with ~6 GB left for the host, a model that overcommits meets the
OOM killer rather than failing gracefully, and GTT pages are pinned, so it can take your
desktop session with it. 48 GB (`gttsize=49152`) is the conservative setting.

## The trap the extra memory sets for you

A dense 70B *fits* in 56 GB. It is also unusable. A dense model activates every parameter
for every token, so at this machine's ~156 GB/s it lands around 4–5 tok/s. Fitting and
being usable are different questions, and the GTT bump only answered the first.

This is the whole lesson: **spare RAM cannot be spent on speed.** Only sparse MoE models —
few active parameters per token — are worth running here.

## Benchmark method

Everything below was measured with a small script that sends a fixed 300-token completion
request behind a synthetic code context of a target depth, streams the response, and times
prefill (time to first token) separately from decode (tokens per second thereafter).
Timing them separately matters, and I'll show why in a moment.

Two models, both from Unsloth GGUF quants, served by LM Studio 0.4.24 on the Vulkan
backend:

- **Qwen3-Coder-30B-A3B**, `UD-Q6_K_XL`, 24.53 GiB
- **Qwen3-Coder-Next 80B-A3B**, `UD-IQ4_XS`, 35.79 GiB

## Predicting memory before you download 36 GiB

LM Studio's `lms load --estimate-only` undershoots KV cache by roughly 65%. You don't need
it. The KV cache is arithmetic you can do from the model's `config.json`:

```
bytes/token = 2 (K+V) × n_full_attention_layers × n_kv_heads × head_dim × 2 (fp16)
total GTT   = weights + bytes/token × context + ~0.7 GiB compute buffers
```

This predicted actual GTT usage to under 1% on both models, including one whose
architecture it wasn't derived from:

| Model | KV/token | @32K | @64K | @128K |
|---|---|---|---|---|
| Qwen3-Coder-30B-A3B (48 attn layers, 4 kv heads) | 96 KiB | 3.0 | 6.0 | 12.0 GiB |
| GLM-4.5-Air (46 attn layers, 8 kv heads) | 184 KiB | 5.8 | 11.5 | 23.0 GiB |
| Qwen3-Coder-Next (**12** attn layers, 2 kv heads) | 24 KiB | 0.75 | 1.5 | 3.0 GiB |

That middle row is why GLM-4.5-Air was ruled out without downloading it: at 128K it needs
about 65 GiB, over the ceiling, and the quant small enough to fit is 2-bit — which
llama.cpp's own documentation calls "extreme quality loss, not recommended". The quant
that fits is not the quant that is good.

That bottom row is the entire argument for the model I ended up adopting.

## Throughput collapses with context depth

The "~55–60 tok/s" figure you see quoted for a 30B-A3B on this hardware is an
**empty-window** number. Here is the same model at four real depths:

| Actual ctx | Decode | vs shallow | Prefill | Time to first token |
|---|---|---|---|---|
| 1,197 | 56.9 tok/s | 100% | 593 tok/s | 2 s |
| 9,250 | 43.1 tok/s | 76% | 525 tok/s | 18 s |
| 37,171 | 28.4 tok/s | 50% | 246 tok/s | **151 s** |
| 74,385 | **19.1 tok/s** | **34%** | **92 tok/s** | **809 s** |

Decode falls to a third. But prefill collapses 6.5×, and that is the one that actually
hurts: 13.5 minutes to ingest a 74K context, every turn, because agentic coding tools
re-read a large context constantly. If you only benchmark decode on a short prompt you
will not see any of this.

## The architecture that doesn't collapse

Qwen3-Coder-Next is a hybrid: only every 4th of its 48 layers is full attention, the rest
are Gated DeltaNet carrying a constant-size recurrent state. That makes KV 24 KiB/token
and makes 36 of 48 layers O(n) rather than O(n²) in prefill. Same benchmark, same machine,
both loaded at 128K:

| Actual ctx | 30B decode | **Next decode** | 30B prefill | **Next prefill** |
|---|---|---|---|---|
| 1,197 | **56.9** | 42.3 | **593** t/s | 406 t/s |
| 9,250 | **43.1** | 35.5 | **524** t/s | 436 t/s |
| 37,171 | 28.4 | **34.4** | 246 t/s | **389** t/s |
| 74,385 | 19.1 | **29.4** | 92 t/s | **323** t/s |

**The curves cross between 9K and 37K.** Below that the 30B is genuinely faster — about
35% quicker on short prompts. Above it, Coder-Next wins and the gap widens: +21% decode
at 37K, +54% at 74K. Retention against each model's own shallow figure: the 30B holds
33.5% at 74K, Coder-Next holds 69.6%.

Look at the prefill column again. Coder-Next's prefill throughput *rises* from 1.2K to
9.3K (406 → 436 t/s) before easing off, while the 30B's falls monotonically. Rising
throughput with depth is the signature of linear-cost attention.

End to end, a finished 300-token answer at 74K context:

| | 30B-A3B | Coder-Next |
|---|---|---|
| prefill | 809.5 s | **230.3 s** |
| decode | 15.7 s | **10.2 s** |
| **total** | **13.8 min** | **4.0 min** |

3.4× faster at depth, for 2.6 GiB more memory.

And because its KV cache is tiny, doubling the window from 128K to 256K costs **3.2 GiB
and nothing else** — 42.84 GiB total, 13.2 GiB of headroom, decode measured at 42.7 tok/s
versus 42.3 at 128K, i.e. unchanged. The 30B could not reach 256K at all; KV alone would
be 24 GiB.

## Loose ends worth knowing

**ROCm is not faster than Vulkan here.** On a third model (Laguna S 2.1, 118B-A8B) on the
same 35K prompt, ROCm prefilled at 181 tok/s against Vulkan's 227, and decoded at 12.8
against 33. Vulkan stays selected. LM Studio 0.4.24 doesn't even ship a ROCm backend, so
the widely-cited `gfx1151` ROCm crash is unreachable — don't paste the README "fix" that
pins a runtime version that doesn't exist on your install.

**Batch size can hang the GPU.** LM Studio's default load for that model (batch 2048,
ubatch 512, f16 KV) died at ~57K tokens of prefill with an amdgpu `ring comp_1.3.0
timeout`, a compute ring reset, and a `vk::DeviceLostError` abort. Batch 512 / ubatch 256
with a q8_0 KV cache fixed it.

**Your client's timeouts are now a real problem.** OpenCode defaults `headerTimeout` and
`chunkTimeout` to 300 s. Measured prefill at 74K is 230 s, and 256K is well past that —
the defaults abort a perfectly healthy request mid-prompt and it looks like a model
failure. Raise them to an hour.

**HuggingFace throttles per connection, not per client.** A single `curl` got 1.8 MB/s
(5.8 hour ETA). Eight parallel range requests got 42 MB/s aggregate, about 15 minutes, on
the same link. Also never pass `--max-time` to a large download; use
`--speed-limit`/`--speed-time` so you abort on genuine stalls instead of on the clock.

## What I'd tell someone buying one of these

The 64 GB unified memory is real and it is useful, but not in the way the spec sheet
implies. It does not let you run big dense models usefully; it lets you run a sparse MoE
with an enormous context window. The two numbers to check before you download anything are
the model's active parameter count and its KV bytes per token — and of those, the second
one is the one nobody quotes.
