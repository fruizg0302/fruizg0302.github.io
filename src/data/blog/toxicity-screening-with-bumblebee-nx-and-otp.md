---
title: "The Model Is Just Another Process: Toxicity Screening with Bumblebee, Nx, and OTP"
author: Fernando Ruiz
pubDatetime: 2026-08-28T15:00:00Z
slug: "elixir/nx/2026/08/28/toxicity-screening-with-bumblebee-nx-and-otp"
featured: true
draft: false
tags:
  - elixir
  - nx
  - bumblebee
  - otp
  - phoenix
  - machine-learning
description: "Running a Spanish hate-speech transformer inside a Phoenix app as a supervised Nx.Serving: why in-process beat a moderation API or a Python sidecar, and what it cost."
---

I run a small side project called Encuentros extraños: a Spanish-language map of the inexplicable in Mexico. Ghost sightings, UFOs, the kind of story your aunt swears happened to a friend of a friend. Thirty-four curated reports seed the map, and visitors can submit their own.

That last part is the problem. The moment you let strangers write text that ends up on a public map, you need a moderation queue, and a moderation queue needs an order. Mine is a `screening_score`: every submission is inserted `:pending`, a screener scores it, and a moderator reads the queue worst-first. The score ranks. It never decides. No threshold approves, rejects or hides anything, and that invariant is written down in the codebase in more places than I'd like to admit.

The first screener was all deterministic heuristics. Links, shouting, character runs, repeated words, a body too short to be a story, a Spanish profanity wordlist, and two `pg_trgm` similarity queries for duplicates. Pure functions plus two SQL queries. Cheap, testable, nothing to mock.

It also has a hole you can drive a truck through. A grammatical, correctly-cased, link-free paragraph of hate speech scores zero. It sinks to the bottom of the queue, below the guy who typed his sighting in caps lock. Exactly backwards.

## What I didn't build

The obvious fix is a content moderation API. I looked at three shapes before writing any code.

**Google's Perspective API** was the first candidate, and it is being sunset. Building on it in 2026 means rebuilding in 2027.

**A hosted moderation endpoint** from one of the LLM providers would work, and it would work in Spanish. But it means every submission leaves the host. This app goes out of its way not to hold personal data: it never captures a visitor's IP, and the "where am I" button compares the geolocation fix against the coverage box in the browser and then drops it, with an e2e test that fails if a coordinate ever shows up in a websocket frame. Shipping the full text of every report to a third party would be a strange place to start making exceptions.

**A Python sidecar** is what most people would reach for: a small FastAPI service wrapping a Hugging Face pipeline, called over HTTP. It's a fine architecture. It's also a second runtime, a second container, a second thing to deploy, monitor and keep alive on a Hetzner box that already hosts two other sites. For one model called once per submission, on a project where submissions are rare, that's a lot of surface for the gain.

What I wanted was a model that behaves like everything else in the app: a process in the supervision tree, configured through `config/`, tested through a boundary, shipped inside the release. Elixir can do that now, and it's the reason this post exists.

## The model

`pysentimiento/robertuito-hate-speech` on the Hugging Face Hub. RoBERTuito is a RoBERTa pre-trained on Spanish tweets, and this head was fine-tuned on the SemEval-2019 HatEval Spanish task. Three labels: `hateful`, `targeted`, `aggressive`. Roughly 110M parameters.

Two things made it the right pick. It's Spanish in the social-media register, which is the register people actually write paranormal reports in: short sentences, slang, the occasional caps lock. And the head is **multi-label**, three independent sigmoid outputs rather than one softmax. A report can be aggressive without being hateful, and the queue benefits from knowing which.

The design had flagged two risks to check at implementation time: whether the repo shipped a fast `tokenizer.json` that Bumblebee could load, and whether Bumblebee's text classification could score a multi-label head per label instead of softmaxing it. Both were non-events. Bumblebee ships a RoBERTa implementation, the tokenizer loaded as-is, and `Bumblebee.Text.text_classification/3` takes `scores_function: :sigmoid`.

## The serving is a child spec

This is the part that made me want to write. The whole integration with Nx and Bumblebee lives in one module, and its most important function returns a child spec:

```elixir
defmodule Liminal.Screening.Toxicity do
  @behaviour Liminal.Screening.ToxicityReader

  @serving Liminal.Screening.Toxicity.Serving

  def child_spec_if_enabled do
    if enabled?(), do: [serving_child_spec()], else: []
  end

  defp serving_child_spec do
    repo = Application.fetch_env!(:liminal, __MODULE__)[:model_repo]
    {:ok, model} = Bumblebee.load_model({:hf, repo})
    {:ok, tokenizer} = Bumblebee.load_tokenizer({:hf, repo})

    serving =
      Bumblebee.Text.text_classification(model, tokenizer,
        scores_function: :sigmoid,
        top_k: nil,
        compile: [batch_size: 1, sequence_length: 128],
        defn_options: [compiler: EXLA]
      )

    {Nx.Serving, serving: serving, name: @serving, batch_size: 1, batch_timeout: 50}
  end
end
```

The application splices it into the tree:

```elixir
children =
  [
    LiminalWeb.Telemetry,
    Liminal.Repo,
    {Phoenix.PubSub, name: Liminal.PubSub},
    {Task.Supervisor, name: Liminal.Screening.TaskSupervisor}
  ] ++
    Toxicity.child_spec_if_enabled() ++
    [LiminalWeb.Endpoint]
```

`Nx.Serving` is a GenServer that owns a compiled model, batches incoming requests, and answers them. It sits between the repo and the endpoint like any other worker. If it crashes, the supervisor restarts it. If it's disabled, it's simply not there: `enabled: false` is the default in `config/config.exs`, so dev, test and CI load no weights, compile nothing, and start no process. Only the `:prod` runtime flips it on. The test suite pins this with a `Process.whereis(Toxicity.Serving) == nil` assertion, because "off behaves exactly as before" is the property everything else depends on.

The `compile:` option is what makes the first request fast. EXLA compiles the model for a fixed `batch_size` and `sequence_length` when the serving starts, instead of on the first submission. And `sequence_length: 128` is not a round number I picked. The loaded model reports `max_positions: 130`, 128 content tokens plus two specials, and a serving compiled for a longer sequence fails only at inference time, the one path CI never exercises. So the number is pinned to what the weights actually say.

## Nothing on the visitor's path

Inference takes somewhere between fifty and a few hundred milliseconds on a couple of CPU cores. Not much. Also not something a visitor in Mexico City, already paying the round trip to Helsinki, should wait on.

So the submission commits first, and the model runs after:

```elixir
def create_report(attrs) do
  case Repo.transaction(fn -> do_create_report(attrs) end) do
    {:ok, report} ->
      Screening.maybe_rescore(report)
      {:ok, report}

    {:error, reason} ->
      {:error, reason}
  end
end
```

`maybe_rescore/1` checks that the reader is enabled, then starts a task under a supervisor that exists for exactly this:

```elixir
def maybe_rescore(%Report{} = report) do
  _ = if reader().enabled?(), do: dispatch_rescore(report, rescore_mode())
  :ok
end

defp dispatch_rescore(report, :sync), do: rescore_toxicity(report)

defp dispatch_rescore(report, _mode) do
  Task.Supervisor.start_child(Liminal.Screening.TaskSupervisor, fn ->
    rescore_toxicity(report)
  end)
end
```

The visitor's request returns at the insert. The task calls the serving and folds the answer back onto the row:

```elixir
def rescore_toxicity(%Report{} = report) do
  case reader().analyze(to_string(report.title) <> " " <> to_string(report.body)) do
    {:ok, probas} ->
      {delta, flags} = toxicity_delta(probas)

      report
      |> Ecto.Changeset.change(%{
        screening_score: min(100, report.screening_score + delta),
        screening_flags: report.screening_flags ++ Enum.map(flags, &Atom.to_string/1)
      })
      |> Repo.update()

    _ ->
      :noop
  end
end
```

Two details here are load-bearing.

The write uses `Ecto.Changeset.change/2`, never `cast/3`. The three screening columns are deliberately outside the schema's castable fields, so no form parameter and no admin edit form can reach a screening verdict. The async path keeps that property: it's a server-side `change/2` on the same protected columns. Adding those fields to `cast/3` to make some admin field "just work" would hand a submitter a way to score themselves zero.

And `analyze/1` rescues everything:

```elixir
def analyze(text) when is_binary(text) do
  if enabled?() do
    %{predictions: preds} = Nx.Serving.batched_run(@serving, text)
    {:ok, to_probabilities(preds)}
  else
    :disabled
  end
rescue
  e -> {:error, e}
end
```

A blanket `rescue` is normally a smell. Here it's the contract. This is a ranking signal. If the serving is down, the compile failed, or the model returns something unexpected, the report keeps its heuristic score and the moderator reads it a little later than they otherwise would. A model hiccup degrades ranking quality; it must never drop, delay or corrupt a submission.

One thing bit me here. The design called for `Nx.Serving.run(@serving, text)`. `run/2` takes a `%Nx.Serving{}` struct and runs it inline; a named, supervised serving is called with `batched_run/2`. Elixir 1.18's type checker flagged the mismatch at compile time, before a single test ran. That's a new kind of safety net for this ecosystem, and I was glad to hit it.

## The fold

The three probabilities become a score delta and a list of flags:

```elixir
@toxicity_scale 50
@toxicity_flag_threshold 0.7
@toxicity_attributes [:hateful, :targeted, :aggressive]

def toxicity_delta(probas) do
  values = Enum.map(@toxicity_attributes, &Map.fetch!(probas, &1))
  delta = round(Enum.max(values) * @toxicity_scale)

  flags =
    Enum.filter(@toxicity_attributes, &(Map.fetch!(probas, &1) >= @toxicity_flag_threshold))

  {delta, flags}
end
```

`max`, not sum: one strongly hateful signal shouldn't be diluted by two weak ones. Scaled to 50 so a submission that's both toxic and spammy can reach the 100 cap and top the queue, while a clean one adds nothing and the common case doesn't regress. The flags are labels for the moderator, `hateful` sitting next to `too_short` in the same column, and they change no report's fate.

## Testing without the model

CI has no weights, no network, and no interest in compiling XLA on every run. So the tests exercise the logic around a boundary, not inference. The boundary is a behaviour:

```elixir
defmodule Liminal.Screening.ToxicityReader do
  @type probabilities :: %{hateful: float, targeted: float, aggressive: float}

  @callback enabled?() :: boolean
  @callback analyze(String.t()) :: {:ok, probabilities} | :disabled | {:error, term}
end
```

`config/test.exs` swaps the real reader for a Mox double and sets `rescore_mode: :sync`, so the rescore runs inline instead of in a task and the test can read the row right after `create_report/1` returns:

```elixir
test "an enabled reader rescores the inserted report (sync mode)" do
  expect(Liminal.Screening.ToxicityMock, :analyze, fn _ ->
    {:ok, %{hateful: 0.95, targeted: 0.0, aggressive: 0.0}}
  end)

  {:ok, report} = Liminal.Reports.create_report(valid_report_attrs())
  reloaded = Liminal.Repo.get!(Liminal.Reports.Report, report.id)

  assert "hateful" in reloaded.screening_flags
  assert reloaded.screening_score >= 47
end
```

The mapping is pure and tested directly: `0.9` hateful is `+45` and one flag, the max-not-sum property, the 100 cap, no flags under `0.7`. The disabled path is pinned: no serving process, an empty child spec, `analyze/1` returning `:disabled`.

What CI can't tell you is whether the model actually scores a Spanish slur high. That's a manual check in `iex` against the baked cache, and it's written down in the infra doc rather than pretended into a test. Both sample calls came back with the three labels and independent sigmoid scores, which is the mechanism working. The scores themselves run lower than you'd expect on plain sentences, because RoBERTuito was trained on tweets with `pysentimiento`'s preprocessing (mentions to `@usuario`, emoji handling) that Bumblebee's plain tokenizer path doesn't apply. For a ranker that's tolerable. For a decider it would not be, and that's one more reason it isn't one.

## Shipping 417 MB of weights

The model has to come from somewhere at boot, and "from Hugging Face" is the wrong answer on a box that shouldn't depend on a third party being up. The pattern was already in the repo: the map's basemap tiles are gitignored local build input, copied into the image and guarded by the Dockerfile. The weights follow it exactly.

Locally, one script populates a Bumblebee cache directory:

```bash
BUMBLEBEE_CACHE_DIR=priv/models mix run tools/fetch_toxicity_model.exs
```

The Dockerfile copies `priv` and refuses to build without the cache:

```dockerfile
RUN set -e; dir=priv/models/huggingface/pysentimiento--robertuito-hate-speech; \
    test -n "$(ls ${dir}/*.json 2>/dev/null)" || \
      { echo "toxicity model cache missing under ${dir}" >&2; exit 1; }
```

And the prod runtime runs Bumblebee offline, pointed at the baked cache:

```elixir
config :bumblebee, offline: true

cache_dir =
  System.get_env("BUMBLEBEE_CACHE_DIR") || Application.app_dir(:liminal, "priv/models")

config :bumblebee, cache_dir: cache_dir

config :exla, :clients, host: [platform: :host, num_replicas: 1]
```

Two of those lines earned their place.

`Application.app_dir/2` rather than a literal path: in a Mix release, `priv` lives under the versioned lib directory (`/app/lib/liminal-<vsn>/priv`), not `/app/priv`. A hardcoded absolute path would miss the cache silently, the Dockerfile guard would have passed, and the serving would fail to load at boot on the host.

`num_replicas: 1` caps EXLA's CPU parallelism. The admin login on this app runs bcrypt on Erlang's dirty CPU schedulers, and the box is shared with two other sites. Inference that fans out across every core is a way to starve those schedulers for everyone. One replica, once per submission, is invisible at the box's baseline load.

The cost is real: about 417 MB more in the build context and the image, on top of the XLA runtime. The budget is one to two gigabytes resident for the model and its buffers, on a box with tens of gigabytes free. Fine, and worth watching the container's RSS after the first deploy rather than assuming.

One note for anyone on macOS with OTP 27.2: `exla` pulls a precompiled `xla_extension` tarball from `release-assets.githubusercontent.com`, a host that OTP version cannot always complete a TLS handshake with. I'd braced for the same manual download I do for the Tailwind binary. It didn't bite this time, and if it does for you, it's a plain tarball into the XLA cache directory, no `codesign` needed.

## Honest assessment

This isn't in production yet. The branch is green and verified by hand against the weights, and it's targeted at a mid-September deploy, partly because more hardware is on the way and partly because there's no queue to rank until real submissions arrive.

CPU-only inference at batch size one is right for this volume and wrong for almost any other. If submissions ever come in bursts, `Nx.Serving`'s batching is already there and the batch size is one number in a child spec, but nothing is tuned for it today.

The 128-token window means a long report is scored on its first 128 subword tokens and the tail is discarded. For a ranker, that just places a long report somewhere in a sorted list. It's worth knowing when you read the queue.

The `pysentimiento` models are released for non-commercial use. This is a non-revenue project about ghosts, so that's the intended use, and I've written the decision down so it gets revisited if that ever changes rather than rediscovered.

And the scores are uncalibrated for this input. Tweet preprocessing, threshold tuning, and a backfill of an accumulated queue are all follow-ups. None of them change the shape of what's here.

## The shape is the point

What I got from Elixir here is not that it can run a transformer. Python does that with more choices and more people who've done it before. What I got is that the transformer became a process. It has a name, a supervisor, a config key, a behaviour in front of it for tests, and a place in the release. The same `mix precommit` that enforces the map boundary and rejects a `Process.sleep` in a test runs over it. No second runtime, no network hop, no text leaving the BEAM.

For a solo developer shipping a side project to a shared box, that's the difference between a feature and an ops project.

### AI usage disclosure

_Most of the work for this project and this post has been by me as a solo developer assisted with Claude Code Fable 5_

_Grammar has been reviewed and corrected by Claude Fable 5 as Spanish is my native language_
