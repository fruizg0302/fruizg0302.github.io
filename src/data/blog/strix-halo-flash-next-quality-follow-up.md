---
title: "Strix Halo, Part 4: Flash-Next, 60K Context, and a Parser That Forgot Multiplication"
author: Fernando Ruiz
pubDatetime: 2026-09-27T16:48:42Z
slug: "strix-halo-flash-next-quality-follow-up"
featured: true
draft: false
tags:
  - llm
  - local-ai
  - amd
  - benchmarks
description: "Flash-Next with Halogen reaches 49.9 tok/s, passes retrieval through 60K context, and exposes a coding mistake. Omarchy tuning, exact settings, and reproducible tests."
---

Qwen3.8 Flash-Next reached **49.90 tokens per second** on my short-prompt test with Halogen's MTP mode, compared with **34.20** in serial mode. At approximately 60K input tokens, a separate structured-output test still generated at **54.2 tokens per second**. All fifteen retrieval checks passed. Coding was more revealing: nine of ten problems passed with thinking off, and all ten passed with bounded reasoning.

The failure was small enough to look harmless in a code review: an arithmetic parser implemented multiplication but forgot to let its tokenizer recognize `*`.

That is the useful shape of this follow-up. The server is fast, long inputs worked in the tests I ran, and executable checks caught a mistake that throughput numbers would never reveal.

In [the previous article](https://fruizg0302.github.io/posts/strix-halo-qwen38-mtp-follow-up/), I tested Qwen3.8-27B in LM Studio on a 64 GB ASUS TUF Gaming A14. MTP made generation substantially faster, but coding quality and long-context recall remained open questions. This round starts investigating those questions on a different setup. It does **not** retrospectively validate the earlier 27B model, and the two articles are not a controlled performance comparison.

| Component          | Previous article                 | This test, September 27, 2026                      |
| ------------------ | -------------------------------- | -------------------------------------------------- |
| Laptop             | ASUS TUF Gaming A14              | ASUS ProArt PX13 HN7306EAC                         |
| Processor          | Ryzen AI MAX+ 392                | Ryzen AI MAX+ 395                                  |
| Installed memory   | 64 GB                            | 128 GB; approximately 121 GiB visible to Linux     |
| GPU                | Radeon 8060S / gfx1151           | Radeon 8060S / gfx1151                             |
| Model              | Qwen3.8-27B                      | Qwen3.8-Flash-Next                                 |
| Weights            | UD-Q5_K_S GGUF                   | Native Halogen W4B checkpoint plus quality overlay |
| Runtime            | LM Studio, Vulkan runtime 2.42.0 | Halogen Flash Server 0.14.0 in Docker              |
| Configured context | 262,144 tokens                   | 65,536 tokens                                      |

The starting point was [Donato Capitella's video about Flash-Next on Strix Halo](https://www.youtube.com/watch?v=Nm_zN6RQ_eE), which I worked through using a cleaned transcript. It pointed me toward Halogen and toward testing quality alongside speed. The video's results belong to its own setup; the numbers below come from the runs on this laptop.

The model bundle was substantial: **117.96 GiB** for the selected checkpoint, quality overlay, tokenizer and supporting files. I pinned the [model repository revision](https://huggingface.co/peonist-ai/halogen-qwen3.8-flash-next/tree/aece4671397244cfc02beed2610ff342b1f9bb21) and verified all nine downloaded files against their recorded SHA-256 or Git blob hashes. The native checkpoint includes the MTP head. I did not use the optional vision file, alternative speed overlay or separate GGUF draft-head sidecar. These `.hgn` files are Halogen-specific; they are not interchangeable with the GGUF from the earlier article. The [model card](https://huggingface.co/peonist-ai/halogen-qwen3.8-flash-next) describes that packaging.

For reproducibility, the exact engine image was:

```text
ghcr.io/peonist-ai/halogen-flash-server@sha256:ec7ec0c6f955f48329bb444efa97286dc8216e9ab1b130bc40d7d8c3babdf6b2
```

The source checkout used for documentation and benchmark tools was [Halogen v0.14.0](https://github.com/peonist-ai/halogen-flash-server/tree/v0.14.0), commit `c8270bb31cd824a0bf53fe9ecf80059c13e7a5bf`. The API and engine both reported version 0.14.0. At the time of this test, the engine was distributed as a closed-source binary; having its deployment repository does not make the inference engine itself open source.

I also installed [AI Toolbox Cockpit](https://github.com/kyuz0/ai-toolbox-cockpit). The catalog in the installed version pointed to an older model revision, so this experiment used the explicitly pinned download and launch scripts instead. That describes the version I inspected, not a permanent limitation of Cockpit.

Before loading the model, I adapted the [Strix Halo Toolboxes host-configuration guide](https://strix-halo-toolboxes.com/#config) to Omarchy. This machine uses Arch and Limine, so copying the guide's Ubuntu package commands and GRUB instructions verbatim would have been the wrong approach. I also kept the graphical desktop running throughout the tests.

The boot parameters in effect were:

```text
amd_iommu=off amdgpu.gttsize=117760 ttm.pages_limit=30146560
```

The GTT and TTM settings were already configured at **115 GiB**, with **4 GiB of firmware-reserved VRAM**. I retained those limits rather than raising them to the guide's 124 GiB example. The GTT ceiling permits allocations from shared system RAM; it does not reserve another 115 GiB or add physical memory.

The new boot change for this experiment was `amd_iommu=off`. On this installation, the persistent configuration lives in Limine entry-tool drop-ins:

```bash
# /etc/limine-entry-tool.d/iommu-off.conf
KERNEL_CMDLINE[default]+=" amd_iommu=off"

# Existing /etc/limine-entry-tool.d/amdgpu-gtt.conf
KERNEL_CMDLINE[default]+=" amdgpu.gttsize=117760 ttm.pages_limit=30146560"
```

After regenerating the boot configuration with `limine-update` and rebooting, I checked the running kernel command line and confirmed that the IOMMU groups were empty. The kernel was `7.2.5-3-omarchy-bore`.

Disabling IOMMU has a real tradeoff: the [host guide](https://strix-halo-toolboxes.com/#config) notes that it prevents NPU operation and removes DMA isolation. I did not run an IOMMU-on control, so this article cannot assign any measured speed improvement to that setting.

Power management needed a little more care than enabling a service permanently. I installed TuneD 2.28.0 through Omarchy's package command:

```bash
omarchy pkg add tuned
```

Then I tied the `accelerator-performance` profile to the model's systemd service. Before starting inference, a helper saves the existing desktop power profile, temporarily masks and stops `power-profiles-daemon`, starts TuneD, and selects `accelerator-performance`. On shutdown, the service's cleanup hook turns TuneD off and restores the desktop power manager and its saved profile.

That gives the model session temporary ownership of the power settings. TuneD and the model were not enabled to start at boot. Closing a terminal leaves inference running; stopping the model service triggers restoration. The integration applies to this Halogen launcher, not automatically to every model application on the machine.

The [upstream TuneD profile](https://raw.githubusercontent.com/redhat-performance/tuned/master/profiles/accelerator-performance/tuned.conf) requests performance-oriented CPU and platform settings, boost, latency controls and several memory/scheduler adjustments. But an active profile is not proof that every request took effect. On this machine, `tuned-adm verify` did **not** fully pass:

| Check                                           | Observed result                                                     |
| ----------------------------------------------- | ------------------------------------------------------------------- |
| CPU boost and ACPI platform performance setting | Verified                                                            |
| `vm.swappiness`                                 | Stayed at Omarchy's `150`, rather than the profile's requested `10` |
| Scheduler `base_slice_ns`                       | Stayed at `2000000`; writing the requested `10000000` was denied    |

TuneD's `reapply_sysctl=1` caused the existing Omarchy sysctl configuration to be reapplied. I left those system settings intact. The precise description of the experiment is therefore **TuneD active with documented settings that did not apply**, rather than a fully verified application of every profile setting. There was no TuneD-off benchmark, either.

Halogen's memory settings were deliberately smaller than its large-pool examples. These were the environment variables in the actual service:

```bash
HALOGEN_CHECKPOINT=/models/qwen38-flash-next-w4b.hgn
HALOGEN_CK_OVERLAY=/models/qwen38-flash-next-w4b.overlay.hgn
HALOGEN_TOKENIZER=/models/tokenizer
HALOGEN_CTX=65536
HALOGEN_KV_POOL_POSITIONS=65536
HALOGEN_KV_SLOTS=1
HALOGEN_MAX_TOK=16384
HALOGEN_PROMPT_CACHE=1
```

Here, `HALOGEN_MAX_TOK` controls the prefill arena/call size; it is not the per-request output-token budget. The [versioned server documentation](https://github.com/peonist-ai/halogen-flash-server/blob/v0.14.0/README.md) explains the distinction and the memory tradeoffs. Requests supplied their own `max_tokens` values.

The container received `/dev/kfd` and `/dev/dri`, used `--ipc=host` and unlimited memlock, and mounted the model files read-only. The API was exposed only at `127.0.0.1:8731`. My first launch failed because the image lacked a named `render` group. Passing the host's numeric video/render group IDs—`983` and `987` here—resolved it. Those IDs are machine-specific; readers should inspect their own groups rather than copy the numbers.

At startup, the engine reported approximately **68.0 GiB of locked weights, 1.8 GiB of KV storage and 12.2 GiB of working memory**, for **82.0 GiB** in those allocations. It reported roughly 23.3 GiB remaining at that point. A separate 47.7 GiB lookup table was demand-paged, rather than all locked into RAM with the weights.

Linux's `MemAvailable` was misleading for this workload because file-cache accounting included pinned weight pages. I used the engine's memory report rather than treating the much larger `free` estimate as permission to load another large model. Swap was unused in the sampled checks. The desktop remained active, but I did not measure UI latency or run a concurrent-workload benchmark.

The first performance pass wrapped Halogen's [upstream benchmark script](https://github.com/peonist-ai/halogen-flash-server/blob/v0.14.0/tools/halogen-bench.py), saving every request, response and wall time. Generation used ten prompt types, three repetitions per type and mode, up to 300 output tokens, temperature zero and thinking off.

| Short-prompt generation metric |            Serial |          MTP mode |
| ------------------------------ | ----------------: | ----------------: |
| Mean engine decode speed       |       34.20 tok/s |       49.90 tok/s |
| Mean end-to-end output rate    |       32.51 tok/s |       46.46 tok/s |
| Decode range across requests   | 32.90–35.01 tok/s | 38.87–58.14 tok/s |

That is a **45.9% increase in mean decode speed**, or 1.46×. All thirty paired outputs matched exactly. The repetitions help describe variability; they do not turn ten deterministic prompts into thirty independent tasks. Serial ran before MTP in this pass, without counterbalanced ordering or a controlled thermal cooldown.

There is another configuration detail behind the label “MTP mode.” The health response showed Halogen's default prompt-lookup assistance enabled for greedy MTP requests, with n-gram size three and chain length three. The comparison measures the engine's serial mode against that configured MTP mode. It does not isolate the prediction head's contribution from every other optimization in that path.

Prompt-cache accounting also needed correction. Five repeated 32K prefill requests restored 32,768 cached tokens. Counting their full prompt length as newly processed input would produce an inflated prefill figure. After excluding those requests, the synthetic input rates were:

| Actual input tokens | Mean end-to-end input rate | Uncached samples |
| ------------------- | -------------------------: | ---------------: |
| 1,021               |                  536 tok/s |                6 |
| 8,185               |                1,071 tok/s |                6 |
| 32,773              |                1,188 tok/s |                1 |

These rates include HTTP overhead and one generated token. “Uncached” here means the prompt KV state was not restored; it does not mean the model files were cold in the operating system's disk cache. The single uncached 32K sample deserves correspondingly limited confidence. The saved raw upstream summary contains the cached repetitions; the corrected report excludes them.

For the quality tests, Codex built a separate automated runner. I wanted the experiment to continue independently of the conversation and retain the evidence without loading every long prompt into the chat. The runner saves each response before evaluation, updates a report after each check, supports resuming, and sends a desktop notification when finished.

Its retrieval tests used synthetic archives at approximately 8K, 32K and 60K tokens. At each length, the model had to retrieve a random code near the beginning, middle or end; retrieve three codes spread across the archive; and return `null` for an absent key. Scoring compared the parsed JSON with the exact expected answer. Actual API-reported input counts ranged from **8,163–8,213**, **32,734–32,815** and **59,933–60,003** across the retrieval and paired-generation requests.

All **15/15 retrieval checks passed**. Those retrieval requests recorded no prompt-cache hits or disk restores. Their full request times were about 8–9 seconds at 8K, 30–31 seconds at 32K, and 56–57 seconds at 60K, including their short answers. The generation rate alone would hide that wait.

I also tested generation with the long archive actually present, rather than pairing a long-prefill number with an unrelated short-prompt decode number. Each response had to retrieve a code and produce a JSON array containing every integer from 1 through 128. Each depth ran once in serial mode and once in MTP mode; the order alternated across depths.

| Approximate input context | Serial decode | MTP-mode decode | Ratio |
| ------------------------- | ------------: | --------------: | ----: |
| 8K                        |    33.2 tok/s |      55.0 tok/s | 1.65× |
| 32K                       |    33.5 tok/s |      54.5 tok/s | 1.63× |
| 60K                       |    33.3 tok/s |      54.2 tok/s | 1.63× |

All six responses were correct, and the messages matched exactly within each pair. Decode stayed close to its 8K rate through 60K on this workload. There was only one pair per depth, and a structured counting response is not representative of arbitrary prose or code. These results should not be combined with the earlier ten-prompt average into a single universal speed figure.

Coding evaluation used ten Python function problems: interval merging, topological sorting, LRU caching, minimum-window substring, wildcard matching, grid paths, CSV parsing, latest-event selection, arithmetic expression parsing and longest increasing subsequence. Together they had **565 deterministic hidden input/output cases**, including empty inputs, cycles, duplicate edges, repeated characters, Unicode, quoted CSV fields and unary operators.

Each problem received one answer with thinking off and one with low reasoning effort. Both used temperature zero and MTP mode. Reasoning runs had a maximum of **1,536 thinking tokens** within a **4,096-token total output budget**. The returned usage confirmed that the off runs used no thinking tokens and the reasoning runs did use them. No repair feedback or second attempt was supplied.

Generated code ran in Bubblewrap with no home-directory mount, an isolated network namespace, read-only runtime files, and time, memory and output limits. The expected answers stayed in the parent evaluator. Correctness came from executing the functions against their cases, not from asking another model whether the code looked convincing. Complexity goals were not formally benchmarked.

| Coding condition                                                         | Complete-task passes |
| ------------------------------------------------------------------------ | -------------------: |
| Ten short-prompt tasks, thinking off                                     |                 9/10 |
| Same ten tasks, bounded reasoning                                        |                10/10 |
| Two task specifications embedded in approximately 32K tokens, both modes |                  4/4 |

The arithmetic parser explains the one failure. Its no-thinking answer included a multiplication branch in the parser, but its tokenizer accepted operators with:

```python
elif c in '+-':
```

As a result, `-(2+3)*4` raised `ValueError: Invalid character: *` rather than returning `-20`. That candidate passed **5/63 cases**. The independently generated reasoning-enabled answer passed **63/63**.

Both long-context versions of the parser also passed, including the one with thinking off. That makes the result more interesting and less universal: this was a first-attempt failure under one prompt, not a demonstrated inability to implement multiplication. Nor is it evidence that padding a prompt makes code better. The sample is too small for either claim.

Across the second suite, **44 of 45 runs passed**: fifteen retrieval checks, six long-context generation checks and twenty-four coding runs. There were no API/harness errors or truncated answers. The coding runs reused the same ten tasks and their cases across conditions; “44/45” is an inventory of this experiment, not a general accuracy score. This was not HumanEval, SWE-bench, Terminal-Bench Mini or a repository-level agent evaluation.

My practical conclusion is to keep MTP mode enabled in this setup and use bounded reasoning for coding, with executable tests still part of the workflow. The measured decode gain was substantial, and the tested serial/MTP pairs agreed. Long-context retrieval held up through 60K. Reasoning avoided the one short-prompt coding failure in this sample.

There are clear limits to that conclusion. I have not shown that this model is better than the earlier 27B model, measured the individual benefit of IOMMU or TuneD, tested retrieval near a quarter-million tokens, or established that the model can navigate and modify a real repository. Synthetic archives and isolated functions are useful checks before that work; they do not replace it. Real bug fixes and small features, judged by a project's existing tests and review, are the next useful experiment.

After testing, I unloaded the model. The service stopped TuneD and restored `power-profiles-daemon` with the previous `performance` profile. Reported host memory use returned to approximately 9.2 GiB, and swap remained unused. The container's shutdown exit code left a systemd failure marker, which I cleared after confirming that engine shutdown and power restoration had completed. The boot-time IOMMU and GTT settings remain in place; stopping the model does not revert them.

The local experiment keeps the [corrected throughput report](/data/qwen38-flash-next-2026-09-27/results/20260927-093157-benchmark/REPORT.md), [quality summary](/data/qwen38-flash-next-2026-09-27/results/20260927-quality/SUMMARY.md), [full quality report](/data/qwen38-flash-next-2026-09-27/results/20260927-quality/REPORT.md), [resumable runner](/data/qwen38-flash-next-2026-09-27/run-quality.py), [hidden-case definitions](/data/qwen38-flash-next-2026-09-27/quality-cases.py), and [systemd service](/data/qwen38-flash-next-2026-09-27/system/qwen38-halogen.service) with its [power-management helper](/data/qwen38-flash-next-2026-09-27/system/qwen38-power). Exact prompts, responses, timings, script snapshots and failure details are preserved alongside those reports. The [downloadable evidence bundle](/data/qwen38-flash-next-2026-09-27/evidence.zip) includes the raw requests, responses and generated candidates, with checksums. The [artifact notes](/data/qwen38-flash-next-2026-09-27/README.md) explain how to use the files.

The external sources consulted for preparation and interpretation were:

- [The previous Qwen3.8-27B article](https://fruizg0302.github.io/posts/strix-halo-qwen38-mtp-follow-up/), for the earlier configuration and the questions left open.
- [Donato Capitella's Flash-Next/Strix Halo video](https://www.youtube.com/watch?v=Nm_zN6RQ_eE), via the cleaned transcript, for the starting point and emphasis on both speed and task quality.
- [Strix Halo Toolboxes: host configuration](https://strix-halo-toolboxes.com/#config), for the IOMMU, shared-memory, TuneD and GPU-access guidance adapted to this installation.
- [Halogen Flash Server v0.14.0 documentation](https://github.com/peonist-ai/halogen-flash-server/blob/v0.14.0/README.md) and its [benchmark tool](https://github.com/peonist-ai/halogen-flash-server/blob/v0.14.0/tools/halogen-bench.py), for launch settings, memory accounting, request controls and the initial measurements.
- [The pinned Halogen model repository](https://huggingface.co/peonist-ai/halogen-qwen3.8-flash-next/tree/aece4671397244cfc02beed2610ff342b1f9bb21), for the checkpoint, quality overlay, tokenizer and file verification.
- [TuneD's accelerator-performance profile](https://raw.githubusercontent.com/redhat-performance/tuned/master/profiles/accelerator-performance/tuned.conf), for checking what the profile requests against what the host actually applied.
- [AI Toolbox Cockpit](https://github.com/kyuz0/ai-toolbox-cockpit), which I inspected and installed during preparation; the reported runs used the pinned scripts described above.

AI usage disclosure: Codex helped configure the environment, wrote and ran the automated tests, collected and analyzed the results, and helped draft this article. The local model produced the coding candidates; executable checks determined their pass/fail results.
