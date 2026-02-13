---
layout: post
title: "Encode Your Rules as Tools: A Compile-to-Test Quality Stack for Elixir"
date: 2026-02-12
categories: elixir quality
---

Every codebase has conventions. Most get written in a document. And every document drifts.

I learned this the hard way. I'm a solo developer, and most of my code is written with AI assistants, specifically Claude Code. I had an `AGENTS.md` file: roughly 450 lines of rules for how the AI should write code in this project. No bare `Task.async`. No `Process.sleep` in tests. One HTTP client library. Use `stream/3` for LiveView collections. Don't rescue inside OTP callbacks. It was thorough, well-organized, and almost immediately out of date.

The problem isn't the AI's capability. The problem is that prose rules require the assistant to notice and follow them at the exact moment it's generating code, and across sessions, it doesn't. Not reliably. The conventions drifted not because I forgot my own rules, but because an AI assistant doesn't internalize a style guide the way a long-tenured teammate would.

The fix wasn't better documentation. It was replacing documentation with build failures. Over two weeks, I took that 450-line file and turned roughly 80% of it into automated checks that fail `mix compile`, `mix credo`, or `mix test`. Now it doesn't matter whether the AI follows the prose rules, the build catches violations before they land. The remaining 20% are rules that genuinely can't be expressed as tooling, so they stayed in the docs.

This post walks through the full stack, organized by when each layer fires: compile-time checks first (cheapest to catch), static analysis second, test-time enforcement last. The project is Elixir/Phoenix, but the principle (encode rules as tools, not prose) applies to any language with a halfway decent tooling ecosystem.

## Compile-Time: The Cheapest Failures

The best time to catch a bug is before the code finishes compiling.

### The Compiler Itself

Elixir's compiler is surprisingly helpful when you stop ignoring its warnings:

```bash
mix compile --warnings-as-errors
```

This catches unused variables, unreachable code branches, deprecated function calls, and pattern match warnings. It's the lowest-effort, highest-value quality check you can add. If you only do one thing from this post, do this.

### Boundary: Module Dependency Enforcement

Every Elixir project eventually develops context coupling. A LiveView starts importing from a context it shouldn't know about. A context reaches into another context's internal schemas. By the time you notice, the coupling is deep and painful to unwind.

[Boundary](https://hex.pm/packages/boundary) (by Sasa Juric) makes illegal dependencies a compile error on the first line of code. Each context module declares its allowed dependencies and public exports:

```elixir
# lib/my_app/incidents.ex
use Boundary,
  deps: [MyApp.Repo, MyApp.Alerts],
  exports: [Incident, RCAReport]
```

If any module inside `MyApp.Incidents` tries to call something from `MyApp.AI`, which isn't in the `deps` list, the compiler stops:

```
** (boundary) MyApp.Incidents.SomeModule references MyApp.AI.Client
   which is not an allowed dependency
```

Not a warning. A compile error. You can't ship it, and neither can an AI assistant generating code on your behalf.

If you're coming from Java, think `package-private`. From C#, think `internal`. From Go, think unexported identifiers at the package level. Boundary gives Elixir the same capability, but at the context level rather than the module level, which is exactly where Phoenix applications need it.

**Setup is minimal:** add `{:boundary, "~> 0.10", runtime: false}` to your deps, and the library hooks into the Elixir compiler as a tracer. No extra build step.

**One gotcha:** Boundary only sees compile-time references (function calls, aliases, imports). Runtime calls via `apply/3` or message passing bypass it entirely.

## Static Analysis: Credo and Custom Checks

If you come from Ruby, Credo is RuboCop. From JavaScript, ESLint. From Python, Ruff. It's a static analysis tool that checks style, consistency, and design rules against your codebase's AST.

```bash
mix credo --strict
```

### Built-in Checks Worth Enabling

Credo ships with dozens of checks. Most defaults are fine, but a few deserve explicit attention:

| Check | Why it matters |
|---|---|
| `Readability.Specs` | Enforces `@spec` on public functions, set to low priority, visible in `--strict` |
| `Warning.UnsafeToAtom` | Prevents `String.to_atom/1` on untrusted input (atoms aren't garbage collected, so it's a DoS vector) |
| `Warning.Dbg` / `Warning.IoInspect` | Catches debug statements left in code |
| `Warning.ApplicationConfigInModuleAttribute` | Module attributes are evaluated at compile time; reading app config there bakes in compile-time values that won't respect runtime configuration |

### Writing Custom Checks

This is where it gets interesting. Credo lets you write project-specific checks that understand your conventions. Each check walks the Elixir AST with `Macro.prewalk/3`, matches specific node shapes, collects line numbers, and emits issues.

You put them in `lib/<app>_checks/` and load them via the `requires` key in `.credo.exs`:

```elixir
# .credo.exs
requires: ["lib/my_app_checks/**/*.ex"],
```

I wrote eight custom checks for my project. Rather than walk through all of them, here are two that illustrate the pattern, and happen to teach something about Elixir/OTP that polyglot developers often find surprising.

#### NoUnsupervisedTask: "Every process needs a parent"

In most languages, spinning up a background thread or goroutine is casual. In Elixir, it's a design decision, because every process should be part of the supervision tree.

`Task.async/1`, `Task.start/1`, and `Task.start_link/1` create processes outside the supervision tree. If they crash, nobody restarts them. If the parent crashes, linked tasks die silently. They can't be tracked or shut down gracefully during application shutdown.

The supervised alternatives:

- `Task.Supervisor.async_nolink/2`, isolated failure, no crash propagation
- `Task.Supervisor.async/2`, linked but supervised
- `Task.Supervisor.start_child/2`, fire-and-forget under supervision

The check matches a simple AST pattern:

{% raw %}
```elixir
# Matches: Task.async(...), Task.start(...), Task.start_link(...)
# Does NOT match: Task.Supervisor.async(...), different alias shape
{{:., _, [{:__aliases__, _, [:Task]}, func]}, meta, _}
when func in [:async, :start, :start_link]
```
{% endraw %}

It only runs against `lib/`. Test files can use bare `Task.async` since test processes have their own lifecycle.

**For Go developers:** imagine if `go func()` triggered a lint error and you had to use a `context.Context`-aware worker pool instead. That's essentially what this check enforces.

#### NoRescueInCallbacks: "Let it crash"

This one surprises people from exception-heavy languages. In Elixir, the "let it crash" philosophy isn't recklessness, it's a deliberate recovery strategy.

When a GenServer callback crashes, the supervisor restarts the process with clean state. That's the mechanism. `try/rescue` inside a callback actively sabotages it:

1. **Masks bugs:** the process continues with potentially corrupted state
2. **Prevents supervisor recovery:** the supervisor never sees the crash, never increments its restart counter, never triggers escalation
3. **Makes debugging harder:** errors are silently swallowed instead of appearing in crash logs with full stacktraces

The check flags `try/rescue` blocks inside any function whose name and arity match a known OTP callback: `init/1`, `handle_call/3`, `handle_cast/2`, `handle_info/2`, `handle_continue/2`, `terminate/2`.

The correct approach for expected error conditions is pattern matching or tagged tuples (`{:ok, _}` / `{:error, _}`), not rescue blocks. If you absolutely must handle an exception, like parsing untrusted external input, do it in a helper function, not in the callback itself.

**For Java developers:** imagine a lint rule that flagged `try/catch` inside Kubernetes health check handlers, because the orchestrator's restart policy IS your error handling strategy. Same principle.

### The Full Check Catalog

Here are all eight checks. The two above got the deep-dive; the rest are straightforward:

| ID | Check | Category | What it flags |
|---|---|---|---|
| EX9001 | NoNestedModules | Design | More than one `defmodule` per file |
| EX9002 | NoProcessSleepInTests | Warning | `Process.sleep/1` in test files |
| EX9003 | NoDeprecatedLiveHelpers | Warning | `live_redirect`, `live_patch`, `form_for`, `inputs_for` |
| EX9004 | NoForbiddenHttpClients | Warning | HTTPoison, Tesla, or `:httpc` usage (project standardized on Req) |
| EX9005 | NoUnsupervisedTask | Warning | Bare `Task.async/start/start_link` outside supervision |
| EX9006 | NoUnsupervisedSpawn | Warning | Bare `spawn/spawn_link` |
| EX9007 | NoRescueInCallbacks | Design | `try/rescue` inside OTP callbacks |
| EX9008 | NoSyncCallInCallbacks | Warning | `GenServer.call` inside OTP callbacks (deadlock risk) |

Each one replaced a prose rule that the AI wasn't consistently following across sessions.

## Static Analysis: Dialyzer

Dialyzer is Elixir's type checker, though calling it that undersells what it does and oversells how it works.

Unlike TypeScript or mypy, Dialyzer uses "success typing": it doesn't require annotations to find bugs. It infers types from your code and flags contradictions. Add `@spec` annotations and it validates them too, catching places where your documentation claims one thing and your code does another.

### Strict Flags

The default Dialyzer configuration is conservative. These flags tighten it:

```elixir
# mix.exs
dialyzer: [
  plt_file: {:no_warn, "priv/plts/dialyzer.plt"},
  ignore_warnings: ".dialyzer_ignore.exs",
  list_unused_filters: true,
  flags: [
    :unmatched_returns,
    :error_handling,
    :underspecs,
    :extra_return,
    :missing_return
  ]
]
```

| Flag | What it catches |
|---|---|
| `:unmatched_returns` | Ignoring return values that contain error tuples |
| `:error_handling` | Unreachable error clauses, functions that always raise |
| `:underspecs` | `@spec` is more restrictive than what the code actually returns |
| `:extra_return` | `@spec` includes return types the code never produces |
| `:missing_return` | Code returns types not declared in the `@spec` |

The `:unmatched_returns` flag deserves special mention. It forces you to write `_ = PubSub.broadcast(...)` for fire-and-forget calls, making the decision to ignore a return value explicit and visible when reviewing a diff. It's a small thing that prevents a category of silent failure.

### Known Limitations

Dialyzer isn't perfect, and pretending otherwise would waste your time:

- **Ecto return types:** `Repo.get!/2` returns `Ecto.Schema.t()`, not your specific struct type. Dialyzer can't narrow this, so you'll get false positives on functions that wrap Ecto queries. Document and ignore.
- **gen_statem specs:** The return type of `:gen_statem.start_link/4` includes `:ignore`, but if your `init/1` never returns `:ignore`, Dialyzer flags a mismatch. You can't win: narrowing the spec triggers one warning, broadening it triggers another. Ignore with documentation.
- **First run is slow:** Building the PLT (Persistent Lookup Table) takes 3-5 minutes. Subsequent runs are 10-30 seconds. Add `/priv/plts/` to `.gitignore`.

**Tip:** `list_unused_filters: true` ensures that when you fix the underlying issue, Dialyzer tells you the ignore entry is stale. Without this, your ignore file silently accumulates dead entries.

## Static Analysis: Sobelow

Short section, because Sobelow is simple and focused. It's a Phoenix-specific security scanner, think [Brakeman](https://brakemanscanner.org/) for Rails.

```bash
mix sobelow --config
```

General-purpose tools like Credo and Dialyzer don't understand Phoenix conventions. Sobelow knows that `Ecto.Adapters.SQL.query("SELECT * FROM users WHERE id = #{id}")` is SQL injection, that `raw/1` in templates bypasses HTML escaping, and that `Plug.Conn.put_resp_cookie` without the `:secure` flag is a security issue.

It catches things that would otherwise require a security-focused eye to spot manually. When you're a solo developer reviewing AI-generated code, you can't be an expert in everything on every diff. Sobelow covers the Phoenix-specific blind spots.

## Test-Time: Coverage and Mocking

### ExCoveralls: A Coverage Floor

```elixir
# mix.exs
{:excoveralls, "~> 0.18", only: :test}
```

```json
// coveralls.json
{
  "minimum_coverage": 70,
  "treat_no_relevant_lines_as_covered": true,
  "skip_files": [
    "test/support",
    "lib/my_app_web/components/core_components.ex"
  ]
}
```

The build fails if coverage drops below 70%. This isn't about chasing 100%, it's about preventing coverage from silently eroding. Ratchet the number up as you add tests. Start at 50% if that's where you are; the point is that it only goes up.

### Mox: Behaviour-Enforced Mocking

[Mox](https://hex.pm/packages/mox) is Elixir's answer to mock drift. Instead of generating mocks from thin air, Mox requires that every mock implements a behaviour (Elixir's version of an interface):

```elixir
# Define the behaviour
defmodule MyApp.AI.ClientBehaviour do
  @callback post(String.t(), map(), keyword()) :: {:ok, map()} | {:error, term()}
end

# In test_helper.exs
Mox.defmock(MyApp.AI.MockClient, for: MyApp.AI.ClientBehaviour)
```

If you add a callback to the behaviour, Mox fails until you update the mock. The mock can never drift from the real implementation's contract.

**One pattern worth knowing:** when the code under test spawns tasks (`Task.Supervisor.async_nolink`), use `async: false` + `setup :set_mox_global` + `stub/3` instead of `expect/3`. Global mode allows any process to use the mock, not just the test process. Without this, your spawned tasks will crash with "no expectations defined."

## Tying It Together: Quality Aliases

Two Mix aliases wire everything into a single command:

**`mix precommit`**, fast, runs before every commit (~15 seconds):

```elixir
precommit: [
  "compile --warnings-as-errors",
  "deps.unlock --unused",
  "format",
  "credo --strict",
  "test"
]
```

**`mix quality`**, thorough, CI-equivalent:

```elixir
quality: [
  "compile --warnings-as-errors",
  "deps.unlock --check-unused",
  "format --check-formatted",
  "credo --strict",
  "sobelow --config",
  "cmd mix hex.audit",
  "dialyzer",
  "cmd MIX_ENV=test mix coveralls"
]
```

Notice the subtle difference: `precommit` auto-formats your code and removes unused dependency locks. `quality` only checks. It fails if formatting is off or unused locks exist, but doesn't fix them. The precommit alias fixes things for you during development. The quality alias verifies things are correct in CI.

## What Can't Be Automated

Not every rule can become a tool. Here's what still lives in documentation, and why:

| Rule | Why it resists automation |
|---|---|
| Use `stream/3` for collections, never assign lists | Requires understanding the template's intent, can't distinguish lists-as-assigns from other list usage |
| Use `to_form/2` for forms, never pass changesets directly | Needs template-aware analysis beyond Credo's scope |
| Fields set programmatically must not be in `cast` calls | Requires understanding the domain intent of each field |
| PubSub broadcasts after DB transaction commits | Requires understanding transaction boundaries |
| Use `start_supervised!/1` in tests | Can't statically distinguish test setup from production code |
| HEEx template conventions (`:for`, class list syntax) | Needs HEEx-aware AST analysis that doesn't exist yet |

This is the honest remainder. These rules require understanding intent, not just syntax. They stay in the docs, and those docs are now short enough that both I and my AI assistant actually absorb them. A 30-line conventions section gets followed. A 450-line `AGENTS.md` gets skimmed.

## Porting This Stack to Your Project

Here's the step-by-step if you want to add this to an existing Elixir/Phoenix project.

### 1. Add Dependencies

```elixir
# In deps/0 of mix.exs
{:credo, "~> 1.7", only: [:dev, :test], runtime: false},
{:dialyxir, "~> 1.4", only: [:dev, :test], runtime: false},
{:sobelow, "~> 0.13", only: [:dev, :test], runtime: false},
{:excoveralls, "~> 0.18", only: :test},
{:mox, "~> 1.1", only: :test},
{:boundary, "~> 0.10", runtime: false}
```

### 2. Configure Dialyzer

Add to `project/0` in `mix.exs`:

```elixir
dialyzer: [
  plt_file: {:no_warn, "priv/plts/dialyzer.plt"},
  ignore_warnings: ".dialyzer_ignore.exs",
  list_unused_filters: true,
  flags: [
    :unmatched_returns,
    :error_handling,
    :underspecs,
    :extra_return,
    :missing_return
  ]
],
test_coverage: [tool: ExCoveralls]
```

Add `/priv/plts/` to `.gitignore`. Create an empty `.dialyzer_ignore.exs` containing just `[]`.

### 3. Configure Coverage

Create `coveralls.json`:

```json
{
  "minimum_coverage": 50,
  "treat_no_relevant_lines_as_covered": true,
  "skip_files": ["test/support"]
}
```

Start at 50%, or wherever you are today, and ratchet up.

### 4. Set Up Credo

Run `mix credo gen.config` to generate `.credo.exs`. If you want custom checks:

1. Create `lib/<app>_checks/` and add your check modules
2. Set `requires: ["lib/<app>_checks/**/*.ex"]` in `.credo.exs`
3. Add each check to the `enabled` list
4. If using custom checks, add `plt_add_apps: [:credo]` to the Dialyzer config so Dialyzer can resolve the `use Credo.Check` macro

### 5. Add Quality Aliases

Add to `aliases/0` in `mix.exs`:

```elixir
precommit: [
  "compile --warnings-as-errors",
  "deps.unlock --unused",
  "format",
  "credo --strict",
  "test"
],
quality: [
  "compile --warnings-as-errors",
  "deps.unlock --check-unused",
  "format --check-formatted",
  "credo --strict",
  "sobelow --config",
  "cmd mix hex.audit",
  "dialyzer",
  "cmd MIX_ENV=test mix coveralls"
]
```

### 6. Set Up Boundary

Add `use Boundary` to each context module. Start with no deps or exports, then add them as the compiler tells you what's missing, it's the fastest way to discover your actual dependency graph.

### 7. First Run

```bash
mix deps.get
mix compile --warnings-as-errors   # Fix warnings
mix credo --strict                  # Fix style issues
mix sobelow --config                # Review security findings
mix dialyzer                        # First run builds PLT (~3-5 min)
                                    # Fix warnings, add ignores for framework quirks
mix quality                         # Full suite, everything green?
```

### Iterative Tightening

Don't try to fix everything at once. The order that works:

1. Start with the compiler flags and Credo, they're fast and give immediate feedback
2. Add Boundary to one or two contexts and expand from there
3. Add `@spec` to public functions incrementally. Dialyzer gets more valuable as specs accumulate
4. Run `mix dialyzer` after each batch of spec additions. Fixing 5 warnings is manageable, fixing 60 is demoralizing

## Closing

The stack replaced roughly 80% of my prose conventions with build failures. Eight custom Credo checks, strict Dialyzer flags, compile-time boundary enforcement, and a security scanner, all wired into two Mix aliases.

The remaining 20% of rules stay in documentation, and that's fine. Those rules require understanding intent, not syntax. But 30 lines of conventions is a document that gets followed, by me when I'm coding manually, and by the AI when it's generating on my behalf.

If you're working with AI assistants, and in 2026 most of us are, the lesson is simple: don't fight the drift with better prose. Fight it with tooling. Every rule that becomes a build failure is a rule that never drifts again, no matter who or what is writing the code.

---

_This post is based on tooling built for an Elixir/Phoenix incident command center project that uses a multi-model Claude AI pipeline._

### AI usage disclosure

_Most of the work for this project and this post has been by me as a solo developer assisted with Claude Code Opus 4.6_

_Grammar has been reviewed and corrected by Claude Sonnet 4.5 as Spanish is my native language_
